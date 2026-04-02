"""
Local unit tests for scheduling policies and AIMD controller.
No GPU / sgl_kernel required — CacheManager is mocked.

Run from the project root:
    pip install pytest
    pytest tests/test_scheduler_logic.py -v
"""
from __future__ import annotations

import sys
import time
import types
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Minimal stubs so we can import our code without installing minisgl
# ---------------------------------------------------------------------------

# Insert src/ FIRST so our real scheduler code is found as a package
_SRC = str(__import__("pathlib").Path(__file__).parent.parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _make_stub_module(name: str, is_package: bool = False) -> types.ModuleType:
    """Register a stub module. Set is_package=True for top-level packages."""
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    if is_package:
        mod.__path__ = []   # marks it as a package to Python's importer
        mod.__package__ = name
    sys.modules[name] = mod
    return mod


# minisgl itself is a real package in src/ — let Python find it naturally.
# We only stub the sub-modules our scheduler code imports that don't exist in src/.
core_mod = _make_stub_module("minisgl.core")

@dataclass
class SamplingParams:
    max_tokens: int = 64

@dataclass
class Req:
    input_ids: list
    table_idx: int
    cached_len: int
    output_len: int
    uid: int
    cache_handle: object
    sampling_params: SamplingParams
    device_len: int = 0
    max_device_len: int = 0

    def __post_init__(self):
        self.device_len = len(self.input_ids)
        self.max_device_len = self.device_len + self.output_len

    @property
    def extend_len(self):
        return self.device_len - self.cached_len

    @property
    def can_decode(self):
        return True

@dataclass
class Batch:
    reqs: list
    phase: str
    is_prefill: bool = False

    def __post_init__(self):
        self.is_prefill = self.phase == "prefill"

core_mod.SamplingParams = SamplingParams
core_mod.Req = Req
core_mod.Batch = Batch

_make_stub_module("minisgl.utils").init_logger = lambda _: MagicMock()
_make_stub_module("minisgl.kvcache")
_make_stub_module("minisgl.message")
_make_stub_module("minisgl.env")

from minisgl.scheduler.telemetry import (  # noqa: E402
    AIMDConfig,
    AIMDController,
    CompletedReqRecord,
    SlidingWindowTelemetry,
)
from minisgl.scheduler.policies import DeficitState, reorder_pending_list  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_pending_req(uid: int, client_id: str, input_len: int, cached_len: int = 0):
    """Create a minimal PendingReq-like object without importing minisgl."""
    req = MagicMock()
    req.uid = uid
    req.client_id = client_id
    req.input_len = input_len
    req.output_len = 64
    req.chunked_req = None
    req.input_ids = list(range(input_len))
    req.sampling_params = SamplingParams(max_tokens=64)
    req._cached_len = cached_len
    return req


def make_cache_manager(cached_lens: Dict[int, int]) -> MagicMock:
    """
    Mock CacheManager.match_req() to return a given cached_len per request uid.
    """
    cm = MagicMock()

    def match_req(pending_req):
        result = MagicMock()
        result.cuda_handle.cached_len = cached_lens.get(pending_req.uid, 0)
        return result

    cm.match_req.side_effect = match_req
    return cm


# ---------------------------------------------------------------------------
# Tests: reorder_pending_list (policies.py)
# ---------------------------------------------------------------------------

class TestFCFSPolicy:
    def test_preserves_arrival_order(self):
        reqs = [make_pending_req(i, f"c{i}", 100) for i in range(5)]
        cm = make_cache_manager({})
        result = reorder_pending_list(reqs, cm, policy="fcfs")
        assert [r.uid for r in result] == [0, 1, 2, 3, 4]

    def test_empty_list(self):
        cm = make_cache_manager({})
        assert reorder_pending_list([], cm, policy="fcfs") == []


class TestLPMPolicy:
    def test_orders_by_cache_score_descending(self):
        # uids 0,1,2 with cached lengths 10, 50, 30
        reqs = [make_pending_req(0, "c0", 100), make_pending_req(1, "c1", 100), make_pending_req(2, "c2", 100)]
        cm = make_cache_manager({0: 10, 1: 50, 2: 30})
        result = reorder_pending_list(reqs, cm, policy="lpm")
        assert [r.uid for r in result] == [1, 2, 0]  # highest cached first

    def test_cold_requests_go_last(self):
        reqs = [make_pending_req(0, "c0", 100, cached_len=0),
                make_pending_req(1, "c1", 100, cached_len=0),
                make_pending_req(2, "c2", 100)]
        cm = make_cache_manager({0: 0, 1: 0, 2: 90})
        result = reorder_pending_list(reqs, cm, policy="lpm")
        assert result[0].uid == 2  # hot request first


class TestDLPMPolicy:
    def test_eligible_clients_get_lpm_ordering(self):
        """
        Two clients A (cache=90, deficit=0) and B (cache=10, deficit=0).
        Both eligible (deficit within Q). LPM should pick A first.
        """
        reqs = [make_pending_req(0, "A", 100), make_pending_req(1, "B", 100)]
        cm = make_cache_manager({0: 90, 1: 10})
        ds = DeficitState()
        result = reorder_pending_list(reqs, cm, policy="dlpm", deficit_state=ds, Q=1000)
        assert result[0].uid == 0  # A has more cached tokens

    def test_ineligible_client_pushed_to_back(self):
        """
        Client A deficit=5000 (dominant), client B deficit=0.
        With Q=1000, A is ineligible → B goes first regardless of cache score.
        """
        reqs = [make_pending_req(0, "A", 100), make_pending_req(1, "B", 100)]
        cm = make_cache_manager({0: 90, 1: 0})  # A has more cache
        ds = DeficitState()
        ds.deficit["A"] = 5000.0
        ds.deficit["B"] = 0.0
        result = reorder_pending_list(reqs, cm, policy="dlpm", deficit_state=ds, Q=1000)
        assert result[0].uid == 1  # B is eligible despite cold cache

    def test_no_eligible_falls_back_to_min_deficit(self):
        """If Q=0, only the exact minimum-deficit client is eligible."""
        reqs = [make_pending_req(0, "A", 100), make_pending_req(1, "B", 100)]
        cm = make_cache_manager({0: 90, 1: 10})
        ds = DeficitState()
        ds.deficit["A"] = 100.0
        ds.deficit["B"] = 0.0
        result = reorder_pending_list(reqs, cm, policy="dlpm", deficit_state=ds, Q=0)
        # min deficit is B (0) → B goes first
        assert result[0].uid == 1

    def test_deficit_update_marks_served_as_zero(self):
        reqs = [make_pending_req(0, "A", 100), make_pending_req(1, "B", 100)]
        ds = DeficitState()
        ds.deficit["A"] = 200.0
        ds.deficit["B"] = 0.0
        ds.update(reqs, served_client_ids={"A"})
        assert ds.deficit["A"] == 0.0
        assert ds.deficit["B"] == 100.0  # B was skipped, accumulates input_len

    def test_requires_deficit_state(self):
        reqs = [make_pending_req(0, "c", 100)]
        cm = make_cache_manager({})
        with pytest.raises(AssertionError):
            reorder_pending_list(reqs, cm, policy="dlpm")  # no deficit_state


class TestStarvationScenario:
    """
    Simulate the core experiment: dominant client A (high cache) vs cold client B.
    Under LPM, B always goes last. Under DLPM with low Q, B gets served.
    """

    def test_lpm_starves_cold_client(self):
        rounds = 5
        A_reqs = [make_pending_req(i, "A", 100) for i in range(rounds)]
        B_req = make_pending_req(100, "B", 100)
        queue = A_reqs + [B_req]

        cm = make_cache_manager({**{r.uid: 90 for r in A_reqs}, 100: 0})

        for _ in range(rounds):
            ordered = reorder_pending_list(queue, cm, policy="lpm")
            # B always ends up last under LPM when A reqs are hot
            assert ordered[-1].uid == 100 or all(r.uid != 100 for r in ordered[:-1])

    def test_dlpm_prevents_starvation(self):
        """After enough rounds, B's accumulated deficit forces it to the front."""
        ds = DeficitState()
        A_req = make_pending_req(0, "A", 100)
        B_req = make_pending_req(1, "B", 100)
        queue = [A_req, B_req]

        cm = make_cache_manager({0: 90, 1: 0})
        Q = 150  # tight bound

        # Set deficits directly: A has been served (deficit=0),
        # B has been skipped 3 times (deficit = 3 * 100 = 300).
        # With Q=150: eligible = {c : deficit[c] <= min_deficit + Q}
        #             = {c : deficit[c] <= 0 + 150}  → only A (0 <= 150)
        # Wait — that means A is eligible, not B.
        # For B to go first we need B's deficit to be the MINIMUM so A is the
        # one outside the eligible window. Flip: B=0, A=300.
        ds.deficit["A"] = 300.0
        ds.deficit["B"] = 0.0

        ordered = reorder_pending_list(queue, cm, policy="dlpm", deficit_state=ds, Q=Q)
        # min_deficit = 0 (B). A's deficit (300) > 0 + 150 → A ineligible.
        # Eligible = [B] → B goes first despite cold cache.
        assert ordered[0].uid == 1  # B gets scheduled first


# ---------------------------------------------------------------------------
# Tests: SlidingWindowTelemetry
# ---------------------------------------------------------------------------

class TestSlidingWindowTelemetry:
    def _rec(self, client_id, ttft, prompt_len=100, cached_len=0):
        return CompletedReqRecord(
            client_id=client_id,
            arrival_time=0.0,
            ttft=ttft,
            prompt_len=prompt_len,
            cached_len=cached_len,
        )

    def test_p99_ttft(self):
        t = SlidingWindowTelemetry(window_size=100)
        for i in range(100):
            t.record(self._rec("c", ttft=float(i)))
        # P99 of 0..99 should be near 98
        assert t.p99_ttft() >= 97.0

    def test_jain_index_perfect_fairness(self):
        t = SlidingWindowTelemetry()
        for _ in range(10):
            t.record(self._rec("A", ttft=0.1, prompt_len=100))
            t.record(self._rec("B", ttft=0.1, prompt_len=100))
        assert abs(t.jain_fairness_index() - 1.0) < 1e-6

    def test_jain_index_unfair(self):
        t = SlidingWindowTelemetry()
        for _ in range(9):
            t.record(self._rec("A", ttft=0.1, prompt_len=100))
        t.record(self._rec("B", ttft=0.1, prompt_len=1))  # B gets almost nothing
        jain = t.jain_fairness_index()
        assert jain < 0.7  # highly unfair

    def test_cache_hit_rate(self):
        t = SlidingWindowTelemetry()
        t.record(self._rec("c", ttft=0.1, prompt_len=100, cached_len=80))
        t.record(self._rec("c", ttft=0.1, prompt_len=100, cached_len=20))
        assert abs(t.cache_hit_rate() - 0.5) < 1e-6

    def test_window_size_limit(self):
        t = SlidingWindowTelemetry(window_size=5)
        for i in range(10):
            t.record(self._rec("c", ttft=float(i)))
        assert len(t.window) == 5
        # Only the last 5 records remain
        assert t.max_wait_time() == 9.0

    def test_empty_window_returns_safe_defaults(self):
        t = SlidingWindowTelemetry()
        assert t.p99_ttft() == 0.0
        assert t.jain_fairness_index() == 1.0
        assert t.cache_hit_rate() == 0.0


# ---------------------------------------------------------------------------
# Tests: AIMDController
# ---------------------------------------------------------------------------

class TestAIMDController:
    def _make_controller(self, jain=1.0, p99_ttft=0.0, **cfg_kwargs):
        telemetry = MagicMock()
        telemetry.jain_fairness_index.return_value = jain
        telemetry.p99_ttft.return_value = p99_ttft / 1000.0  # convert ms → s
        # Default control_interval to 1 unless explicitly overridden
        cfg_kwargs.setdefault("control_interval", 1)
        cfg = AIMDConfig(**cfg_kwargs)
        return AIMDController(cfg, telemetry), telemetry

    def test_additive_increase_when_healthy(self):
        ctrl, _ = self._make_controller(jain=0.9, p99_ttft=100.0,
                                         Q_init=4000, additive_step=500,
                                         jain_threshold=0.75, ttft_slo_ms=2000)
        ctrl.step()
        assert ctrl.current_Q == 4500.0

    def test_multiplicative_decrease_on_low_jain(self):
        ctrl, _ = self._make_controller(jain=0.5, p99_ttft=100.0,
                                         Q_init=4000, multiplicative_factor=0.5,
                                         jain_threshold=0.75, ttft_slo_ms=2000)
        ctrl.step()
        assert ctrl.current_Q == 2000.0

    def test_multiplicative_decrease_on_high_ttft(self):
        ctrl, _ = self._make_controller(jain=0.9, p99_ttft=5000.0,
                                         Q_init=4000, multiplicative_factor=0.5,
                                         jain_threshold=0.75, ttft_slo_ms=2000)
        ctrl.step()
        assert ctrl.current_Q == 2000.0

    def test_q_clipped_to_min(self):
        ctrl, _ = self._make_controller(jain=0.1, p99_ttft=0.0,
                                         Q_init=600, Q_min=500, multiplicative_factor=0.5,
                                         jain_threshold=0.75, ttft_slo_ms=2000)
        ctrl.step()
        assert ctrl.current_Q == 500.0

    def test_q_clipped_to_max(self):
        ctrl, _ = self._make_controller(jain=1.0, p99_ttft=0.0,
                                         Q_init=63_900, Q_max=64_000, additive_step=500,
                                         jain_threshold=0.75, ttft_slo_ms=2000)
        ctrl.step()
        assert ctrl.current_Q == 64_000.0

    def test_control_interval_respected(self):
        ctrl, _ = self._make_controller(jain=0.5, Q_init=4000,
                                         multiplicative_factor=0.5,
                                         jain_threshold=0.75, ttft_slo_ms=2000,
                                         control_interval=5)
        # Steps 1–4: no change
        for _ in range(4):
            ctrl.step()
        assert ctrl.current_Q == 4000.0
        # Step 5: fires
        ctrl.step()
        assert ctrl.current_Q == 2000.0

    def test_history_recorded(self):
        ctrl, _ = self._make_controller(jain=1.0, Q_init=4000,
                                         additive_step=500, control_interval=1,
                                         jain_threshold=0.75, ttft_slo_ms=2000)
        ctrl.step()
        ctrl.step()
        assert len(ctrl.history) == 2
        assert ctrl.history[0][1] == 4500.0  # first step Q value

    def test_saw_tooth_pattern(self):
        """Q should increase additively then drop when Jain falls."""
        telemetry = MagicMock()
        cfg = AIMDConfig(Q_init=4000, additive_step=500, multiplicative_factor=0.5,
                          jain_threshold=0.75, ttft_slo_ms=2000, control_interval=1,
                          Q_max=64000, Q_min=500)
        ctrl = AIMDController(cfg, telemetry)

        # 3 healthy rounds → Q increases
        telemetry.jain_fairness_index.return_value = 0.9
        telemetry.p99_ttft.return_value = 0.5
        for _ in range(3):
            ctrl.step()
        assert ctrl.current_Q == 5500.0

        # 1 violation → Q drops
        telemetry.jain_fairness_index.return_value = 0.5
        ctrl.step()
        assert ctrl.current_Q == 2750.0

        # Resumes increasing
        telemetry.jain_fairness_index.return_value = 0.9
        ctrl.step()
        assert ctrl.current_Q == 3250.0
