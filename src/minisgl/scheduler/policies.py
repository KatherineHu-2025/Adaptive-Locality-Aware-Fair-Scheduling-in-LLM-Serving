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
    Tracks per-client deficit counter for DLPM (Algorithm 1 in the paper).

    q[client_id] is the remaining service budget for each client in the
    current cycle.  Mirrors the paper's q_i:
      - Initialised to 0 when a client first appears.
      - A request from client i is eligible to be scheduled when q_i > 0.
      - After a prefill step: q_i -= w_e * extend_length(r)  (paper line 23)
      - After each decode step: q_i -= w_q * output_tokens   (paper line 26)
      - When ALL active clients have q_i <= 0, every client is replenished
        by Q^u (CHECKREFILL, paper lines 3-8).

    We_e = 1, w_q = 2 following OpenAI pricing as in the paper (§3).
    """
    q: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    W_E: float = 1.0   # weight for extend (non-cached prefill) tokens
    W_Q: float = 2.0   # weight for output tokens

    def register(self, client_id: str) -> None:
        """Called when a new client is first seen (paper line 12)."""
        if client_id not in self.q:
            self.q[client_id] = 0.0

    def needs_refill(self, active_client_ids: set) -> bool:
        """True when all active clients have q_i <= 0 (CHECKREFILL condition)."""
        return all(self.q[c] <= 0 for c in active_client_ids)

    def refill(self, active_client_ids: set, Q: float) -> None:
        """Replenish every exhausted client by Q (CHECKREFILL body, paper line 7)."""
        for c in active_client_ids:
            if self.q[c] <= 0:
                self.q[c] += Q

    def deduct_prefill(self, client_id: str, extend_len: int) -> None:
        """Deduct extend-token cost after a request is added to the batch (paper line 23)."""
        self.q[client_id] -= self.W_E * extend_len

    def deduct_decode(self, client_id: str, output_tokens: int) -> None:
        """Deduct output-token cost after each decode step (paper line 26)."""
        self.q[client_id] -= self.W_Q * output_tokens

    def is_eligible(self, client_id: str) -> bool:
        """A client may be scheduled when q_i > 0 (paper line 21)."""
        return self.q[client_id] > 0


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

        # Ensure every waiting client is registered (paper line 12)
        for req in pending_list:
            deficit_state.register(req.client_id)

        active_clients = {req.client_id for req in pending_list}

        # CHECKREFILL: if no active client has q_i > 0, replenish all (paper lines 3-8)
        if deficit_state.needs_refill(active_clients):
            deficit_state.refill(active_clients, Q)

        # Eligible = clients with q_i > 0 (paper line 21)
        eligible = [req for req in pending_list if deficit_state.is_eligible(req.client_id)]
        ineligible = [req for req in pending_list if not deficit_state.is_eligible(req.client_id)]

        # Among eligible: LPM ordering (paper line 16: SORTBYPREFIX)
        # Among ineligible: preserve FIFO (they will be served after the next refill)
        eligible_sorted = sorted(eligible, key=lambda r: scores[r.uid], reverse=True)
        return eligible_sorted + ineligible

    raise ValueError(f"Unknown policy: {policy!r}. Valid: {VALID_POLICIES}")
