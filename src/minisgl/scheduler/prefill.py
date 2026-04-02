"""
Modified minisgl/scheduler/prefill.py
Changes:
  - PrefillManager now accepts `policy`, `static_Q`, `deficit_state`, and
    `controller` at construction time.
  - schedule_next_batch() reorders pending_list via policies.reorder_pending_list()
    before passing it to PrefillAdder, then updates the deficit state.
  - add_one_req() copies client_id and arrival_time from UserMsg → PendingReq.
Everything else (PrefillAdder, ChunkedReq) is unchanged.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional, Tuple

import torch
from minisgl.core import Batch, Req
from minisgl.utils import init_logger

from .policies import DeficitState, reorder_pending_list
from .utils import PendingReq

if TYPE_CHECKING:
    from minisgl.kvcache import BaseCacheHandle
    from minisgl.message import UserMsg

    from .cache import CacheManager
    from .decode import DecodeManager
    from .table import TableManager
    from .telemetry import AIMDController

logger = init_logger(__name__)

# Policy can be overridden via environment variable for easy benchmarking.
# Valid values: lpm | dlpm | adaptive_dlpm | fcfs
_DEFAULT_POLICY = os.environ.get("MINISGL_POLICY", "lpm")
_DEFAULT_STATIC_Q = float(os.environ.get("MINISGL_STATIC_Q", "4000"))


class ChunkedReq(Req):
    def append_host(self, next_token: torch.Tensor) -> None:
        raise NotImplementedError("ChunkedReq should not be sampled")

    @property
    def can_decode(self) -> bool:
        return False  # avoid being added to decode manager


@dataclass
class PrefillAdder:
    token_budget: int
    reserved_size: int
    cache_manager: CacheManager
    table_manager: TableManager

    def _try_allocate_one(self, req: PendingReq) -> Tuple[BaseCacheHandle, int] | None:
        if self.table_manager.available_size == 0:
            return None

        # TODO: consider host cache match case
        handle = self.cache_manager.match_req(req).cuda_handle
        cached_len = handle.cached_len
        # TODO: better estimate policy
        extend_len = req.input_len - cached_len
        estimated_len = extend_len + req.output_len

        if estimated_len + self.reserved_size > self.cache_manager.available_size:
            return None
        self.cache_manager.lock(handle)
        if estimated_len + self.reserved_size > self.cache_manager.available_size:
            return self.cache_manager.unlock(handle)

        table_idx = self.table_manager.allocate()
        if cached_len > 0:  # NOTE: set the cached part
            device_ids = self.table_manager.token_pool[table_idx][:cached_len]
            page_entry = self.table_manager.page_table[table_idx][:cached_len]
            device_ids.copy_(req.input_ids[:cached_len].pin_memory(), non_blocking=True)
            page_entry.copy_(handle.get_matched_indices())

        return handle, table_idx

    def _add_one_req(
        self,
        pending_req: PendingReq,
        cache_handle: BaseCacheHandle,
        table_idx: int,
        cached_len: int,
    ) -> Req:
        remain_len = pending_req.input_len - cached_len
        chunk_size = min(self.token_budget, remain_len)
        is_chunked = chunk_size < remain_len
        CLS = ChunkedReq if is_chunked else Req
        self.token_budget -= chunk_size
        self.reserved_size += remain_len + pending_req.output_len
        # NOTE: update the tokens ids only; new pages will be allocated in the scheduler
        _slice = slice(cached_len, cached_len + chunk_size)
        device_ids = self.table_manager.token_pool[table_idx, _slice]
        device_ids.copy_(pending_req.input_ids[_slice].pin_memory(), non_blocking=True)
        return CLS(
            input_ids=pending_req.input_ids[: cached_len + chunk_size],
            table_idx=table_idx,
            cached_len=cached_len,
            output_len=pending_req.output_len,
            uid=pending_req.uid,
            cache_handle=cache_handle,
            sampling_params=pending_req.sampling_params,
        )

    def try_add_one(self, pending_req: PendingReq) -> Req | None:
        if self.token_budget <= 0:
            return None

        if chunked_req := pending_req.chunked_req:
            return self._add_one_req(
                pending_req=pending_req,
                cache_handle=chunked_req.cache_handle,
                table_idx=chunked_req.table_idx,
                cached_len=chunked_req.cached_len,
            )

        if resource := self._try_allocate_one(pending_req):
            cache_handle, table_idx = resource
            return self._add_one_req(
                pending_req=pending_req,
                cache_handle=cache_handle,
                table_idx=table_idx,
                cached_len=cache_handle.cached_len,
            )

        return None


@dataclass
class PrefillManager:
    cache_manager: CacheManager
    table_manager: TableManager
    decode_manager: DecodeManager
    pending_list: List[PendingReq] = field(default_factory=list)

    # --- scheduling policy fields (new) ---
    policy: str = field(default_factory=lambda: _DEFAULT_POLICY)
    static_Q: float = field(default_factory=lambda: _DEFAULT_STATIC_Q)
    deficit_state: DeficitState = field(default_factory=DeficitState)
    controller: Optional[AIMDController] = field(default=None)

    def add_one_req(self, req: UserMsg) -> None:
        # Use str(uid) as fallback client_id so callers that don't set it
        # still get a unique, stable identifier.
        client_id = req.client_id if req.client_id else str(req.uid)
        self.pending_list.append(
            PendingReq(
                uid=req.uid,
                input_ids=req.input_ids,
                sampling_params=req.sampling_params,
                client_id=client_id,
                # arrival_time defaults to time.perf_counter() in PendingReq
            )
        )

    def schedule_next_batch(self, prefill_budget: int) -> Batch | None:
        if len(self.pending_list) == 0:
            return None

        # ------------------------------------------------------------------
        # Step 1: advance AIMD controller (no-op for non-adaptive policies)
        # ------------------------------------------------------------------
        if self.controller is not None:
            self.controller.step()

        # ------------------------------------------------------------------
        # Step 2: determine Q and reorder the pending list
        # ------------------------------------------------------------------
        Q = (
            self.controller.get_Q()
            if self.policy == "adaptive_dlpm" and self.controller is not None
            else self.static_Q
        )

        ordered = reorder_pending_list(
            pending_list=self.pending_list,
            cache_manager=self.cache_manager,
            policy=self.policy,
            deficit_state=self.deficit_state,
            Q=Q,
        )

        # ------------------------------------------------------------------
        # Step 3: run PrefillAdder on the reordered list (unchanged logic)
        # ------------------------------------------------------------------
        adder = PrefillAdder(
            token_budget=prefill_budget,
            reserved_size=self.decode_manager.inflight_tokens,
            cache_manager=self.cache_manager,
            table_manager=self.table_manager,
        )
        reqs: List[Req] = []
        chunked_list: List[PendingReq] = []
        num_attempted = 0

        for pending_req in ordered:
            num_attempted += 1
            if req := adder.try_add_one(pending_req):
                pending_req.chunked_req = None
                if isinstance(req, ChunkedReq):
                    pending_req.chunked_req = req
                    chunked_list.append(pending_req)
                reqs.append(req)
            else:
                break  # PrefillAdder is full — remaining requests stay queued

        if len(reqs) == 0:
            return None

        # ------------------------------------------------------------------
        # Step 4: rebuild pending_list (chunked first, then un-attempted)
        # ------------------------------------------------------------------
        # Requests that were attempted but not added (PrefillAdder ran out of
        # budget) are put back; their order within the un-attempted tail is
        # whatever `ordered` had (policy-determined).
        self.pending_list = chunked_list + ordered[num_attempted:]

        # ------------------------------------------------------------------
        # Step 5: update deficit state for DLPM policies
        # ------------------------------------------------------------------
        if self.policy in ("dlpm", "adaptive_dlpm"):
            served_ids = {pending_req.client_id for pending_req in ordered[:num_attempted]
                          if not isinstance(pending_req.chunked_req, ChunkedReq)}
            # Actually track which pending_reqs produced a non-chunked Req
            served_ids = set()
            for pending_req, req in zip(ordered[:num_attempted], reqs):
                if not isinstance(req, ChunkedReq):
                    served_ids.add(pending_req.client_id)
            self.deficit_state.update(ordered[:num_attempted], served_ids)

        return Batch(reqs=reqs, phase="prefill")

    def abort_req(self, uid: int) -> Req | None:
        for i, req in enumerate(self.pending_list):
            if req.uid == uid:
                self.pending_list.pop(i)
                return req.chunked_req
        return None

    @property
    def runnable(self) -> bool:
        return len(self.pending_list) > 0
