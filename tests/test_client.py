"""
Tests for workload/client.py

No server required — the HTTP layer is mocked.

Run:
    pytest tests/test_client.py -v
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from workload.client import (
    RequestResult,
    gamma_interarrivals,
    print_summary,
    replay,
)
from workload.dataset import RequestSpec


# ---------------------------------------------------------------------------
# gamma_interarrivals
# ---------------------------------------------------------------------------

class TestGammaInterarrivals:
    def test_length(self):
        arr = gamma_interarrivals(10, rate=2.0, k=1.0)
        assert len(arr) == 10

    def test_all_positive(self):
        arr = gamma_interarrivals(100, rate=3.0, k=0.5)
        assert (arr > 0).all()

    def test_mean_close_to_one_over_rate(self):
        # With enough samples, mean ≈ 1/rate regardless of k
        for k in [0.5, 1.0, 2.0]:
            arr = gamma_interarrivals(10_000, rate=4.0, k=k, seed=0)
            assert abs(arr.mean() - 1 / 4.0) < 0.05, f"k={k} mean={arr.mean():.3f}"

    def test_reproducible_with_seed(self):
        a = gamma_interarrivals(5, rate=1.0, k=1.0, seed=42)
        b = gamma_interarrivals(5, rate=1.0, k=1.0, seed=42)
        np.testing.assert_array_equal(a, b)

    def test_different_seeds_differ(self):
        a = gamma_interarrivals(5, rate=1.0, k=1.0, seed=1)
        b = gamma_interarrivals(5, rate=1.0, k=1.0, seed=2)
        assert not np.array_equal(a, b)

    def test_bursty_higher_variance_than_regular(self):
        bursty  = gamma_interarrivals(10_000, rate=1.0, k=0.3, seed=0)
        regular = gamma_interarrivals(10_000, rate=1.0, k=5.0, seed=0)
        assert bursty.std() > regular.std()


# ---------------------------------------------------------------------------
# Helpers to mock aiohttp
# ---------------------------------------------------------------------------

def _make_sse_body(tokens: list[str]) -> bytes:
    lines = [f"data: {t}\n".encode() for t in tokens]
    lines.append(b"data: [DONE]\n")
    return b"".join(lines)


def _mock_session(tokens: list[str], status: int = 200):
    """
    Build a mock aiohttp.ClientSession whose POST returns an SSE stream.
    """
    # Build a fake async iterator over the SSE lines
    sse_lines = [f"data: {t}\n".encode() for t in tokens] + [b"data: [DONE]\n"]

    async def fake_aiter():
        for line in sse_lines:
            yield line

    resp = MagicMock()
    resp.status = status
    resp.content.__aiter__ = lambda _: fake_aiter()
    resp.text = AsyncMock(return_value="error body")

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.post = MagicMock(return_value=cm)

    connector = MagicMock()
    connector.__aenter__ = AsyncMock(return_value=session)
    connector.__aexit__ = AsyncMock(return_value=False)

    return session


# ---------------------------------------------------------------------------
# replay()
# ---------------------------------------------------------------------------

class TestReplay:
    def _specs(self, n=3):
        return [
            RequestSpec(client_id=f"c{i}", prompt=f"prompt {i}",
                        expected_output_len=4)
            for i in range(n)
        ]

    def test_returns_one_result_per_spec(self):
        specs = self._specs(3)
        session = _mock_session(["tok1", "tok2", "tok3"])

        async def run():
            with patch("aiohttp.ClientSession", return_value=MagicMock(
                __aenter__=AsyncMock(return_value=session),
                __aexit__=AsyncMock(return_value=False),
            )), patch("aiohttp.TCPConnector", return_value=MagicMock()):
                return await replay(specs, "http://localhost:19190",
                                    rate=10.0, policy="lpm")

        results = asyncio.run(run())
        assert len(results) == 3

    def test_empty_specs_returns_empty(self):
        results = asyncio.run(replay([], "http://localhost:19190", rate=1.0))
        assert results == []

    def test_result_fields_populated(self):
        specs = self._specs(1)
        session = _mock_session(["a", "b", "c"])

        async def run():
            with patch("aiohttp.ClientSession", return_value=MagicMock(
                __aenter__=AsyncMock(return_value=session),
                __aexit__=AsyncMock(return_value=False),
            )), patch("aiohttp.TCPConnector", return_value=MagicMock()):
                return await replay(specs, "http://localhost:19190",
                                    rate=10.0, policy="dlpm")

        results = asyncio.run(run())
        r = results[0]
        assert r.client_id == "c0"
        assert r.policy == "dlpm"
        assert r.output_tokens == 3
        assert r.success is True

    def test_writes_jsonl_output(self, tmp_path):
        specs = self._specs(2)
        session = _mock_session(["tok"])
        out = str(tmp_path / "out.jsonl")

        async def run():
            with patch("aiohttp.ClientSession", return_value=MagicMock(
                __aenter__=AsyncMock(return_value=session),
                __aexit__=AsyncMock(return_value=False),
            )), patch("aiohttp.TCPConnector", return_value=MagicMock()):
                return await replay(specs, "http://localhost:19190",
                                    rate=10.0, output_path=out)

        asyncio.run(run())
        lines = Path(out).read_text().strip().splitlines()
        assert len(lines) == 2
        row = json.loads(lines[0])
        assert "ttft_ms" in row
        assert "client_id" in row

    def test_failed_request_marked_unsuccessful(self):
        specs = self._specs(1)
        session = _mock_session([], status=500)

        async def run():
            with patch("aiohttp.ClientSession", return_value=MagicMock(
                __aenter__=AsyncMock(return_value=session),
                __aexit__=AsyncMock(return_value=False),
            )), patch("aiohttp.TCPConnector", return_value=MagicMock()):
                return await replay(specs, "http://localhost:19190", rate=10.0)

        results = asyncio.run(run())
        assert results[0].success is False
        assert results[0].ttft_ms == -1.0


# ---------------------------------------------------------------------------
# print_summary (smoke test — just ensure it doesn't crash)
# ---------------------------------------------------------------------------

class TestPrintSummary:
    def _result(self, client_id, ttft_ms, output_tokens=10, success=True):
        return RequestResult(
            req_id="x", client_id=client_id,
            arrival_time=0.0, ttft_ms=ttft_ms, tpot_ms=5.0,
            prompt_len=100, output_tokens=output_tokens,
            expected_output_len=10, policy="lpm",
            success=success,
        )

    def test_no_crash_on_empty(self, capsys):
        print_summary([])
        assert "No results" in capsys.readouterr().out

    def test_no_crash_on_results(self, capsys):
        results = [
            self._result("alice", 200.0, 10),
            self._result("bob",   800.0, 5),
        ]
        print_summary(results)
        out = capsys.readouterr().out
        assert "Jain" in out
        assert "alice" in out
        assert "bob" in out

    def test_jain_printed_for_multi_client(self, capsys):
        results = [self._result("A", 100), self._result("B", 200)]
        print_summary(results)
        assert "Jain" in capsys.readouterr().out
