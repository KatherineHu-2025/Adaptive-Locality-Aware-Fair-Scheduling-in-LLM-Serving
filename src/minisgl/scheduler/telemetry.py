"""
Sliding-window telemetry and AIMD controller for Adaptive DLPM.

SlidingWindowTelemetry tracks the last N completed requests and computes
real-time metrics (P99 TTFT, Jain Fairness Index, cache hit rate) used by
the AIMD controller to dynamically adjust the DLPM quantum Q.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Telemetry record: one entry per completed request
# ---------------------------------------------------------------------------

@dataclass
class CompletedReqRecord:
    client_id: str
    arrival_time: float   # perf_counter at submission
    ttft: float           # seconds from arrival to first output token
    prompt_len: int       # total input tokens
    cached_len: int       # tokens matched in radix cache at scheduling time


# ---------------------------------------------------------------------------
# Sliding-window telemetry
# ---------------------------------------------------------------------------

class SlidingWindowTelemetry:
    """
    Thread-safe (GIL-protected) rolling window over the last `window_size`
    completed requests. Computes metrics consumed by AIMDController.
    """

    def __init__(self, window_size: int = 200) -> None:
        self.window: deque[CompletedReqRecord] = deque(maxlen=window_size)

    def record(self, rec: CompletedReqRecord) -> None:
        self.window.append(rec)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def p99_ttft(self) -> float:
        """99th-percentile TTFT in seconds. Returns 0 if window is empty."""
        if not self.window:
            return 0.0
        ttfts = sorted(r.ttft for r in self.window)
        idx = max(0, int(0.99 * len(ttfts)) - 1)
        return ttfts[idx]

    def jain_fairness_index(self) -> float:
        """
        Jain's Fairness Index over per-client prompt tokens in the window.
        J = (Σ x_i)² / (n · Σ x_i²),  range [1/n, 1],  1 = perfectly fair.
        Returns 1.0 if fewer than 2 distinct clients are present.
        """
        if not self.window:
            return 1.0
        client_tokens: Dict[str, int] = defaultdict(int)
        for r in self.window:
            client_tokens[r.client_id] += r.prompt_len
        x = list(client_tokens.values())
        n = len(x)
        if n < 2:
            return 1.0
        sum_x = sum(x)
        sum_x2 = sum(xi * xi for xi in x)
        if sum_x2 == 0:
            return 1.0
        return (sum_x ** 2) / (n * sum_x2)

    def cache_hit_rate(self) -> float:
        """Fraction of prompt tokens served from the radix cache."""
        if not self.window:
            return 0.0
        total_prompt = sum(r.prompt_len for r in self.window)
        total_cached = sum(r.cached_len for r in self.window)
        return total_cached / total_prompt if total_prompt > 0 else 0.0

    def max_wait_time(self) -> float:
        """Maximum TTFT (seconds) in the window — direct starvation signal."""
        if not self.window:
            return 0.0
        return max(r.ttft for r in self.window)


# ---------------------------------------------------------------------------
# AIMD controller
# ---------------------------------------------------------------------------

@dataclass
class AIMDConfig:
    # Q bounds (tokens)
    Q_min: float = 500
    Q_max: float = 64_000
    Q_init: float = 4_000

    # Trigger thresholds
    jain_threshold: float = 0.75   # Jain index below this → tighten fairness
    ttft_slo_ms: float = 2_000.0   # P99 TTFT (ms) above this → tighten fairness

    # AIMD step sizes
    additive_step: float = 500.0          # tokens added to Q each healthy step
    multiplicative_factor: float = 0.5   # Q multiplied by this on violation

    # How often to re-evaluate (every N calls to step())
    control_interval: int = 50


class AIMDController:
    """
    Additive-Increase / Multiplicative-Decrease controller for DLPM's Q.

    Call step() once per scheduling iteration. Q is updated every
    `config.control_interval` steps based on live telemetry.
    """

    def __init__(self, config: AIMDConfig, telemetry: SlidingWindowTelemetry) -> None:
        self.config = config
        self.telemetry = telemetry
        self.current_Q: float = config.Q_init
        self._step_count: int = 0
        # History for plotting: list of (wall_time, Q, jain, p99_ttft_ms)
        self.history: List[Tuple[float, float, float, float]] = []

    def step(self) -> None:
        """Called once per scheduling step. Updates Q every control_interval steps."""
        self._step_count += 1
        if self._step_count % self.config.control_interval != 0:
            return

        jain = self.telemetry.jain_fairness_index()
        p99_ms = self.telemetry.p99_ttft() * 1000.0

        violated = jain < self.config.jain_threshold or p99_ms > self.config.ttft_slo_ms

        if violated:
            new_Q = max(self.config.Q_min, self.current_Q * self.config.multiplicative_factor)
        else:
            new_Q = min(self.config.Q_max, self.current_Q + self.config.additive_step)

        self.current_Q = new_Q
        self.history.append((time.perf_counter(), new_Q, jain, p99_ms))

    def get_Q(self) -> float:
        return self.current_Q
