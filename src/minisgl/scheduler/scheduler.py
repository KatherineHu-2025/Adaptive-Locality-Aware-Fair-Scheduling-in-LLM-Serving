"""
Modified minisgl/scheduler/scheduler.py
Changes (all marked NEW):
  - Imports SlidingWindowTelemetry, AIMDController, AIMDConfig, DeficitState, policies
  - __init__ wires telemetry + controller into PrefillManager
  - __init__ accepts `policy`, `static_Q`, `aimd_config` via SchedulerConfig or env
  - _process_one_msg records uid → (client_id, arrival_time) when request arrives
  - _process_last_data records first_token_time and completion telemetry
Everything else is unchanged from the original.
"""
from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Dict, List, NamedTuple, NoReturn, Optional, Set, Tuple, TypeAlias

import torch
from minisgl.core import Batch, Req
from minisgl.env import ENV
from minisgl.message import (
    AbortBackendMsg,
    BaseBackendMsg,
    BatchBackendMsg,
    DetokenizeMsg,
    ExitMsg,
    ResetBackendMsg,
    UserMsg,
)
from minisgl.utils import init_logger, load_tokenizer

from .cache import CacheManager
from .config import SchedulerConfig
from .decode import DecodeManager
from .io import SchedulerIOMixin
from .prefill import ChunkedReq, PrefillManager
from .table import TableManager
# --- NEW ---
from .telemetry import AIMDConfig, AIMDController, CompletedReqRecord, RequestLogger, SlidingWindowTelemetry
from .policies import DeficitState

if TYPE_CHECKING:
    from minisgl.engine import BatchSamplingArgs, ForwardOutput


logger = init_logger(__name__)

Indice2D: TypeAlias = Tuple[torch.Tensor, torch.Tensor]


class ForwardInput(NamedTuple):
    batch: Batch
    sample_args: BatchSamplingArgs
    input_tuple: Indice2D
    write_tuple: Indice2D


ForwardData: TypeAlias = "Tuple[ForwardInput, ForwardOutput]"


class Scheduler(SchedulerIOMixin):
    def __init__(self, config: SchedulerConfig):
        from minisgl.engine import Engine

        self.engine = Engine(config)

        self.device = self.engine.device
        self.stream = torch.cuda.Stream(device=self.device)
        self.engine_stream_ctx = torch.cuda.stream(self.engine.stream)
        torch.cuda.set_stream(self.stream)

        self.table_manager = TableManager(config.max_running_req, self.engine.page_table)
        self.cache_manager = CacheManager(
            self.engine.num_pages, config.page_size, self.engine.page_table, config.cache_type
        )
        self.decode_manager = DecodeManager(config.page_size)

        # --- NEW: build telemetry + AIMD controller ---
        policy = os.environ.get("MINISGL_POLICY", "lpm")
        static_Q = float(os.environ.get("MINISGL_STATIC_Q", "4000"))
        telemetry_window = int(os.environ.get("MINISGL_TELEMETRY_WINDOW", "200"))

        self.telemetry = SlidingWindowTelemetry(window_size=telemetry_window)
        self.controller: Optional[AIMDController] = None
        if policy == "adaptive_dlpm":
            aimd_debug_log = os.environ.get("AIMD_DEBUG_LOG_PATH", "/tmp/minisgl_aimd_history.jsonl")
            if aimd_debug_log:
                try:
                    # Fresh file on startup so each run has clean AIMD history.
                    open(aimd_debug_log, "w", encoding="utf-8").close()
                except Exception:
                    pass
            aimd_cfg = AIMDConfig(
                Q_min=float(os.environ.get("AIMD_Q_MIN", "500")),
                Q_max=float(os.environ.get("AIMD_Q_MAX", "64000")),
                Q_init=float(os.environ.get("AIMD_Q_INIT", "4000")),
                jain_threshold=float(os.environ.get("AIMD_JAIN_THRESHOLD", "0.75")),
                ttft_slo_ms=float(os.environ.get("AIMD_TTFT_SLO_MS", "2000")),
                additive_step=float(os.environ.get("AIMD_ADDITIVE_STEP", "500")),
                multiplicative_factor=float(os.environ.get("AIMD_MULT_FACTOR", "0.5")),
                control_interval=int(os.environ.get("AIMD_CONTROL_INTERVAL", "50")),
                debug_log_path=aimd_debug_log,
            )
            self.controller = AIMDController(aimd_cfg, self.telemetry)
            logger.info_rank0("Adaptive DLPM: AIMD controller initialized (Q_init=%.0f)", aimd_cfg.Q_init)

        self.prefill_manager = PrefillManager(
            cache_manager=self.cache_manager,
            table_manager=self.table_manager,
            decode_manager=self.decode_manager,
            policy=policy,
            static_Q=static_Q,
            deficit_state=DeficitState(),
            controller=self.controller,
        )
        logger.info_rank0("Scheduler policy: %s (static_Q=%.0f)", policy, static_Q)

        # --- NEW: per-request metadata for telemetry ---
        # uid → (client_id, arrival_time, orig_prompt_len, cached_len, q_at_scheduling)
        self._req_meta: Dict[int, Tuple[str, float, int, int, float]] = {}
        # uid → first_token_time (set when prefill result is processed)
        self._first_token_time: Dict[int, float] = {}

        # --- NEW: file logger (opt-in via MINISGL_LOG_DIR) ---
        log_dir = os.environ.get("MINISGL_LOG_DIR", "")
        self._req_logger: Optional[RequestLogger] = (
            RequestLogger(log_dir, policy) if log_dir else None
        )

        self.finished_reqs: Set[Req] = set()
        self.tokenizer = load_tokenizer(config.model_path)
        self.eos_token_id = self.tokenizer.eos_token_id
        self.token_pool = self.table_manager.token_pool
        self.prefill_budget = config.max_extend_tokens

        super().__init__(config, self.engine.tp_cpu_group)

    def run_when_idle(self) -> None:
        logger.info_rank0("Scheduler is idle, waiting for new reqs...")
        self.cache_manager.check_integrity()

    def overlap_loop(self, last_data: ForwardData | None) -> ForwardData | None:
        blocking = not (
            last_data is not None
            or self.prefill_manager.runnable
            or self.decode_manager.runnable
        )
        for msg in self.receive_msg(blocking=blocking):
            self._process_one_msg(msg)

        forward_input = self._schedule_next_batch()
        ongoing_data = None
        if forward_input is not None:
            with self.engine_stream_ctx:
                self.engine.stream.wait_stream(self.stream)
                ongoing_data = (forward_input, self._forward(forward_input))

        self._process_last_data(last_data)
        return ongoing_data

    def normal_loop(self) -> None:
        blocking = not (self.prefill_manager.runnable or self.decode_manager.runnable)
        for msg in self.receive_msg(blocking=blocking):
            self._process_one_msg(msg)

        forward_input = self._schedule_next_batch()
        ongoing_data = None
        if forward_input is not None:
            ongoing_data = (forward_input, self._forward(forward_input))

        self._process_last_data(ongoing_data)

    @torch.inference_mode()
    def run_forever(self) -> NoReturn:
        if ENV.DISABLE_OVERLAP_SCHEDULING:
            with self.engine_stream_ctx:
                self.engine.stream.wait_stream(self.stream)
                while True:
                    self.normal_loop()
        else:
            assert torch.cuda.current_stream() == self.stream
            data = None
            while True:
                data = self.overlap_loop(data)

    def shutdown(self) -> None:
        self._flush_logs()
        torch.cuda.synchronize(self.device)
        self.sync_all_ranks()
        self.engine.shutdown()

    def reset_experiment_state(self) -> None:
        """
        Clear per-run AIMD and fairness state while keeping the service alive.

        This is intended for the experiment harness after warmup completes, so
        the measured probe starts from a clean controller/telemetry baseline.
        """
        self.telemetry.reset()
        if self.controller is not None:
            self.controller.reset()
        self.prefill_manager.deficit_state.reset()
        self._req_meta.clear()
        self._first_token_time.clear()

    def _flush_logs(self) -> None:
        """Flush Q trajectory to CSV and close the request log file."""
        if self._req_logger is None:
            return
        if self.controller is not None:
            self._req_logger.flush_q_history(self.controller.history)
        self._req_logger.close()

    def _process_last_data(self, last_data: ForwardData | None) -> None:
        if last_data is None:
            return

        batch, (_, next_tokens_cpu, copy_done) = last_data[0].batch, last_data[1]
        copy_done.synchronize()
        now = time.perf_counter()  # NEW: wall time for TTFT calculation

        reply: List[DetokenizeMsg] = []
        new_finished_reqs: Set[Req] = set()

        jain_control_msg = self.telemetry.jain_fairness_index()
        jain_prompt_msg = self.telemetry.jain_fairness_index_prompt()
        p99_ttft_ms_msg = self.telemetry.p99_ttft() * 1000.0
        aimd_violated_msg = False
        aimd_violation_reason_msg = "none"
        aimd_step_msg = -1
        if self.controller is not None and self.controller.history:
            last_aimd = self.controller.history[-1]
            aimd_violated_msg = bool(last_aimd.get("violated", False))
            aimd_violation_reason_msg = str(last_aimd.get("violation_reason", "none"))
            try:
                aimd_step_msg = int(last_aimd.get("step", -1))
            except (TypeError, ValueError):
                aimd_step_msg = -1

        with self.cache_manager.lazy_free_region():
            for i, req in enumerate(batch.reqs):
                if isinstance(req, ChunkedReq):
                    continue
                next_token = next_tokens_cpu[i]
                req.append_host(next_token.unsqueeze(0))
                next_token = int(next_token.item())
                finished = not req.can_decode
                if not req.sampling_params.ignore_eos:
                    finished |= next_token == self.eos_token_id

                cached_len_msg = -1
                q_at_sched_msg = -1.0
                if req.uid in self._req_meta:
                    _, _, _, cached_len_msg, q_at_sched_msg = self._req_meta[req.uid]

                reply.append(
                    DetokenizeMsg(
                        uid=req.uid,
                        next_token=next_token,
                        finished=finished,
                        cached_len=cached_len_msg,
                        q_at_scheduling=q_at_sched_msg,
                        jain_control=jain_control_msg,
                        jain_prompt=jain_prompt_msg,
                        p99_ttft_ms=p99_ttft_ms_msg,
                        aimd_violated=aimd_violated_msg,
                        aimd_violation_reason=aimd_violation_reason_msg,
                        aimd_step=aimd_step_msg,
                    )
                )

                # --- NEW: record first-token time on prefill completion ---
                if batch.is_prefill and req.uid not in self._first_token_time:
                    self._first_token_time[req.uid] = now

                # --- NEW: deduct output-token cost from deficit (paper line 26).
                # Runs for every req in every batch (prefill produces the first
                # token too). Must happen before the finished check so that
                # requests completing this step are still counted.
                if self.prefill_manager.policy in ("dlpm", "adaptive_dlpm"):
                    if req.uid in self._req_meta:
                        _client_id = self._req_meta[req.uid][0]
                    else:
                        _client_id = str(req.uid)
                    self.prefill_manager.deficit_state.deduct_decode(_client_id, 1)

                if finished and req not in self.finished_reqs:
                    self.decode_manager.remove_req(req)
                    self._free_req_resources(req)
                    new_finished_reqs.add(req)

                    # --- NEW: record completed request to telemetry + file log ---
                    if req.uid in self._req_meta:
                        client_id, arrival_time, orig_prompt_len, cached_len, q_at_sched = self._req_meta.pop(req.uid)
                        first_tok = self._first_token_time.pop(req.uid, now)
                        ttft_s = first_tok - arrival_time
                        output_tokens = len(req.input_ids) - orig_prompt_len
                        tpot_ms = (
                            (now - first_tok) * 1000.0 / (output_tokens - 1)
                            if output_tokens > 1 else 0.0
                        )
                        self.telemetry.record(CompletedReqRecord(
                            client_id=client_id,
                            arrival_time=arrival_time,
                            ttft=ttft_s,
                            prompt_len=orig_prompt_len,
                            cached_len=cached_len,
                            output_tokens=output_tokens,
                        ))
                        if self._req_logger is not None:
                            self._req_logger.log_request(
                                req_id=req.uid,
                                client_id=client_id,
                                arrival_time=arrival_time,
                                ttft_ms=ttft_s * 1000.0,
                                tpot_ms=tpot_ms,
                                prompt_len=orig_prompt_len,
                                cached_len=cached_len,
                                q_at_scheduling=q_at_sched,
                            )

                elif batch.is_prefill:
                    self.cache_manager.cache_req(req, finished=False)

        self.finished_reqs = new_finished_reqs
        self.send_result(reply)

    def _process_one_msg(self, msg: BaseBackendMsg) -> None:
        if isinstance(msg, BatchBackendMsg):
            for msg in msg.data:
                self._process_one_msg(msg)
        elif isinstance(msg, ExitMsg):
            raise KeyboardInterrupt
        elif isinstance(msg, UserMsg):
            logger.debug_rank0("Received user msg: %s", msg)
            input_len, max_seq_len = len(msg.input_ids), self.engine.max_seq_len
            max_output_len = max_seq_len - input_len
            if max_output_len <= 0:
                return logger.warning_rank0(
                    f"Input sequence length {input_len} exceeds {max_seq_len}, "
                    f"request {msg.uid} is dropped."
                )
            if msg.sampling_params.max_tokens > max_output_len:
                msg.sampling_params.max_tokens = max_output_len
                logger.warning_rank0(
                    f"Adjust max_tokens to {max_output_len} for request {msg.uid}."
                )
            # --- NEW: store metadata for telemetry before adding to queue ---
            client_id = msg.client_id if msg.client_id else str(msg.uid)
            # orig_prompt_len captured now; cached_len and q_at_scheduling filled at scheduling
            self._req_meta[msg.uid] = (client_id, time.perf_counter(), len(msg.input_ids), 0, 0.0)
            self.prefill_manager.add_one_req(msg)
        elif isinstance(msg, ResetBackendMsg):
            logger.info_rank0("Resetting AIMD experiment state (scope=%s)", msg.scope)
            self.reset_experiment_state()
        elif isinstance(msg, AbortBackendMsg):
            logger.debug_rank0("Aborting request %d", msg.uid)
            self._req_meta.pop(msg.uid, None)
            self._first_token_time.pop(msg.uid, None)
            req_to_free = self.prefill_manager.abort_req(msg.uid)
            req_to_free = req_to_free or self.decode_manager.abort_req(msg.uid)
            if req_to_free is not None:
                self._free_req_resources(req_to_free)
        else:
            logger.error(f"Unknown message type: {type(msg)}")
            raise NotImplementedError

    def _free_req_resources(self, req: Req) -> None:
        self.table_manager.free(req.table_idx)
        self.cache_manager.cache_req(req, finished=True)

    def _prepare_batch(self, batch: Batch) -> ForwardInput:
        self.engine.graph_runner.pad_batch(batch)
        self.cache_manager.allocate_paged(batch.reqs)
        batch.positions = _make_positions(batch, self.device)
        input_mapping = _make_input_tuple(batch, self.device)
        write_mapping = _make_write_tuple(batch, self.device)
        batch.out_loc = self.engine.page_table[input_mapping]
        self.engine.attn_backend.prepare_metadata(batch)
        return ForwardInput(
            batch=batch,
            sample_args=self.engine.sampler.prepare(batch),
            input_tuple=input_mapping,
            write_tuple=write_mapping,
        )

    def _schedule_next_batch(self) -> ForwardInput | None:
        batch = (
            self.prefill_manager.schedule_next_batch(self.prefill_budget)
            or self.decode_manager.schedule_next_batch()
        )
        if batch is None:
            return None
        # Fix: update cached_len in _req_meta now that PrefillAdder has resolved
        # the cache match. cached_len was stored as 0 at arrival time because the
        # radix-tree lookup only happens during scheduling.
        if batch.is_prefill:
            q_now = self.controller.get_Q() if self.controller is not None else 0.0
            for req in batch.reqs:
                if not isinstance(req, ChunkedReq) and req.uid in self._req_meta:
                    client_id, arrival_time, orig_prompt_len, _, _ = self._req_meta[req.uid]
                    self._req_meta[req.uid] = (client_id, arrival_time, orig_prompt_len, req.cached_len, q_now)
        return self._prepare_batch(batch)

    def _forward(self, forward_input: ForwardInput) -> ForwardOutput:
        batch, sample_args, input_mapping, output_mapping = forward_input
        batch.input_ids = self.token_pool[input_mapping]
        forward_output = self.engine.forward_batch(batch, sample_args)
        self.token_pool[output_mapping] = forward_output.next_tokens_gpu
        self.decode_manager.filter_reqs(forward_input.batch.reqs)
        return forward_output


def _make_positions(batch: Batch, device: torch.device) -> torch.Tensor:
    needed_size = sum(r.extend_len for r in batch.padded_reqs)
    indices_host = torch.empty(needed_size, dtype=torch.int32, pin_memory=True)
    offset = 0
    for req in batch.padded_reqs:
        length = req.extend_len
        torch.arange(
            req.cached_len,
            req.device_len,
            dtype=torch.int32,
            out=indices_host[offset : offset + length],
        )
        offset += length
    return indices_host.to(device, non_blocking=True)


def _make_input_tuple(batch: Batch, device: torch.device) -> Indice2D:
    mapping_host = torch.empty(len(batch.positions), dtype=torch.int64, pin_memory=True)
    offset = 0
    for req in batch.padded_reqs:
        length = req.extend_len
        mapping_host[offset : offset + length].fill_(req.table_idx)
        offset += length
    return mapping_host.to(device, non_blocking=True), batch.positions.to(torch.int64)


def _make_write_tuple(batch: Batch, device: torch.device) -> Indice2D:
    mapping_list = [req.table_idx for req in batch.reqs]
    mapping_host = torch.tensor(mapping_list, dtype=torch.int64, pin_memory=True)
    write_list = [(req.device_len if req.can_decode else -1) for req in batch.reqs]
    write_host = torch.tensor(write_list, dtype=torch.int64, pin_memory=True)
    return mapping_host.to(device, non_blocking=True), write_host.to(device, non_blocking=True)
