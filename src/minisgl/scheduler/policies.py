"""
Scheduling policies for Adaptive DLPM.

Provides a `reorder_pending_list()` function that, given the current
pending_list and cache state, returns a reordered list according to the
selected policy. The existing PrefillAdder logic is unchanged — we only
control which order requests are offered to it.

Policies
--------
lpm            Longest Prefix Match — greedy cache-locality maximizer (baseline)
dlpm           Deficit Longest Prefix Match — static Q (DLPM paper, §3)
adaptive_dlpm  DLPM with Q tuned by AIMDController at runtime (our contribution)
fcfs           First-Come-First-Serve — arrival-time order (related-work reference)
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from .cache import CacheManager
    from .telemetry import AIMDController, SlidingWindowTelemetry
    from .utils import PendingReq

# Supported policy names
VALID_POLICIES = {"lpm", "dlpm", "adaptive_dlpm", "fcfs"}


# ---------------------------------------------------------------------------
# Per-client deficit state (lives in Scheduler / PrefillManager)
# ---------------------------------------------------------------------------

@dataclass
class DeficitState:
    """
    Tracks per-client deficit for DLPM.

    deficit[client_id] = cumulative prompt tokens that were NOT served to this
    client across all past scheduling rounds (opportunity cost). Clients whose
    deficit is within Q of the minimum-deficit client are eligible for prefix-
    locality-based selection.
    """
    deficit: Dict[str, float] = field(default_factory=lambda: defaultdict(float))

    def update(
        self,
        pending_list: List[PendingReq],
        served_client_ids: set,
    ) -> None:
        """
        Called after each scheduling round.
        Clients whose request was NOT served accumulate deficit equal to their
        prompt length (tokens they deserved but didn't get).
        Served clients have their deficit reset to 0.
        """
        for req in pending_list:
            if req.client_id in served_client_ids:
                self.deficit[req.client_id] = 0.0
            else:
                self.deficit[req.client_id] += req.input_len

    def min_deficit(self, client_ids) -> float:
        if not client_ids:
            return 0.0
        return min(self.deficit[c] for c in client_ids)


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _get_cached_len(pending_req: PendingReq, cache_manager: CacheManager) -> int:
    """
    Read-only radix tree lookup for a pending request.
    Returns the number of tokens already in the KV cache.
    Does NOT lock the cache handle — locking happens later in PrefillAdder.
    """
    match_result = cache_manager.match_req(pending_req)
    return match_result.cuda_handle.cached_len


# ---------------------------------------------------------------------------
# Main reorder function
# ---------------------------------------------------------------------------

def reorder_pending_list(
    pending_list: List[PendingReq],
    cache_manager: CacheManager,
    policy: str,
    deficit_state: Optional[DeficitState] = None,
    Q: float = 0.0,
) -> List[PendingReq]:
    """
    Return a reordered copy of `pending_list` according to `policy`.
    The original list is NOT mutated; PrefillManager.schedule_next_batch()
    assigns the result back to self.pending_list before calling PrefillAdder.

    Parameters
    ----------
    pending_list    : current FIFO queue of waiting requests
    cache_manager   : used to score cache hits (read-only)
    policy          : one of VALID_POLICIES
    deficit_state   : required for "dlpm" and "adaptive_dlpm"
    Q               : DLPM quantum (ignored for "lpm" / "fcfs")
    """
    if not pending_list:
        return pending_list

    if policy == "fcfs":
        # Already in arrival order — no change needed
        return list(pending_list)

    # Score every pending request by its cache hit length
    scores: Dict[int, int] = {
        req.uid: _get_cached_len(req, cache_manager)
        for req in pending_list
    }

    if policy == "lpm":
        return sorted(pending_list, key=lambda r: scores[r.uid], reverse=True)

    if policy in ("dlpm", "adaptive_dlpm"):
        assert deficit_state is not None, "DeficitState required for DLPM policies"
        waiting_clients = {req.client_id for req in pending_list}
        min_def = deficit_state.min_deficit(waiting_clients)

        # Eligible: clients within Q of the minimum-deficit client
        eligible = [
            req for req in pending_list
            if deficit_state.deficit[req.client_id] <= min_def + Q
        ]
        ineligible = [
            req for req in pending_list
            if deficit_state.deficit[req.client_id] > min_def + Q
        ]

        if not eligible:
            # Fallback: serve the most-starved client (min deficit)
            eligible = sorted(
                pending_list,
                key=lambda r: deficit_state.deficit[r.client_id],
            )
            ineligible = []

        # Among eligible: LPM ordering; among ineligible: preserve FIFO
        eligible_sorted = sorted(eligible, key=lambda r: scores[r.uid], reverse=True)
        return eligible_sorted + ineligible

    raise ValueError(f"Unknown policy: {policy!r}. Valid: {VALID_POLICIES}")
