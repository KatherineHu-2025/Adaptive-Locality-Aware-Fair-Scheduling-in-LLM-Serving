"""
Sliding-window telemetry and AIMD controller for Adaptive DLPM.

SlidingWindowTelemetry tracks the last N completed requests and computes
real-time metrics (P99 TTFT, Jain Fairness Index, cache hit rate) used by
the AIMD controller to dynamically adjust the DLPM quantum Q.
"""

from __future__ import annotations

import csv
import json
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
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

    # Optional: append JSONL records of Q updates for runtime debugging.
    debug_log_path: str = ""


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

        if self.config.debug_log_path:
            try:
                with open(self.config.debug_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "t": time.perf_counter(),
                        "step": self._step_count,
                        "Q": float(new_Q),
                        "jain": float(jain),
                        "p99_ttft_ms": float(p99_ms),
                        "violated": bool(violated),
                    }) + "\n")
            except Exception:
                # Never break scheduler progress due to debug logging.
                pass

    def get_Q(self) -> float:
        return self.current_Q


# ---------------------------------------------------------------------------
# File-based request and Q-trajectory logger
# ---------------------------------------------------------------------------

class RequestLogger:
    """
    Writes per-request metrics to a JSONL file and Q trajectory to a CSV.

    Activated by setting the MINISGL_LOG_DIR environment variable.
    Creates:
      {log_dir}/requests_{policy}_{timestamp}.jsonl  — one line per request
      {log_dir}/q_trajectory_{timestamp}.csv         — Q history (adaptive_dlpm)
    """

    def __init__(self, log_dir: str, policy: str) -> None:
        os.makedirs(log_dir, exist_ok=True)
        ts = int(time.time())
        self._policy = policy
        req_path = os.path.join(log_dir, f"requests_{policy}_{ts}.jsonl")
        self._req_file = open(req_path, "w", buffering=1)  # line-buffered
        self._q_path = os.path.join(log_dir, f"q_trajectory_{ts}.csv")

    def log_request(
        self,
        req_id: int,
        client_id: str,
        arrival_time: float,
        ttft_ms: float,
        tpot_ms: float,
        prompt_len: int,
        cached_len: int,
        q_at_scheduling: float,
    ) -> None:
        record = {
            "req_id": req_id,
            "client_id": client_id,
            "arrival_time": arrival_time,
            "ttft_ms": round(ttft_ms, 3),
            "tpot_ms": round(tpot_ms, 3),
            "prompt_len": prompt_len,
            "cached_len": cached_len,
            "cache_hit_rate": round(cached_len / prompt_len, 4) if prompt_len > 0 else 0.0,
            "policy": self._policy,
            "Q_at_scheduling": q_at_scheduling,
        }
        self._req_file.write(json.dumps(record) + "\n")

    def flush_q_history(self, history: List[Tuple[float, float, float, float]]) -> None:
        """Write Q trajectory to CSV. history entries: (wall_time, Q, jain, p99_ttft_ms)."""
        if not history:
            return
        with open(self._q_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["wall_time", "Q", "jain_index", "p99_ttft_ms"])
            writer.writerows(history)

    def close(self) -> None:
        self._req_file.close()
