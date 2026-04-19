"""
workload/client.py — Async workload client for Adaptive DLPM experiments.

Replays a list of RequestSpec objects against a running mini-sglang server,
injecting requests according to a Gamma process arrival model and recording
per-request metrics to a JSONL log file.

Gamma process inter-arrival times
----------------------------------
Inter-arrival time ~ Gamma(shape=k, scale=1 / (rate * k))

  k < 1  →  bursty (high variance, occasional bursts)
  k = 1  →  Poisson / memoryless (exponential inter-arrivals)
  k > 1  →  regular / smooth (low variance)

The mean inter-arrival is always 1/rate regardless of k.

Arrival mode
------------
    global      → one Gamma process for all requests in list order
    per-client  → one Gamma process per client_id, merged by timestamp

Usage (Python API)
------------------
    import asyncio
    from workload.dataset import load_synthetic
    from workload.client import replay

    specs = load_synthetic(dominant_reqs=100, cold_reqs=20)
    results = asyncio.run(replay(
        specs=specs,
        server_url="http://127.0.0.1:19190",
        arrival_mode="global",
        rate=3.0,
        k=1.0,
        output_path="results/run_001.jsonl",
        policy="adaptive_dlpm",
    ))

Usage (CLI)
-----------
    # Local minisgl server
    python -m workload.client \\
        --server http://127.0.0.1:19190 \\
        --dataset synthetic \\
        --arrival-mode global \\
        --rate 3.0 --k 1.0 \\
        --policy adaptive_dlpm \\
        --timeout 120 --max-concurrency 64 \\
        --output results/run_001.jsonl

    # Modal-hosted endpoint (single-GPU friendly settings)
    python -m workload.client \\
        --server https://<your-modal-url> \\
        --dataset synthetic \\
        --arrival-mode per-client \\
        --rate 1.0 --k 1.0 \\
        --policy adaptive_dlpm \\
        --timeout 600 --max-concurrency 2 \\
        --dominant-reqs 20 --cold-reqs 5 \\
        --output results/run_modal_test.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np

# Make workload/ importable when running as __main__
sys.path.insert(0, str(Path(__file__).parent.parent))

from workload.dataset import RequestSpec, load_loogle, load_synthetic

try:
    import aiohttp
except ImportError:
    raise ImportError("pip install aiohttp")


_STREAM_META_PREFIX = "__MINISGL_META__ "


# ---------------------------------------------------------------------------
# Per-request result
# ---------------------------------------------------------------------------

@dataclass
class RequestResult:
    req_id: str
    client_id: str
    arrival_time: float        # seconds since replay start (wall clock)
    ttft_ms: float             # time-to-first-token in ms (-1 if failed)
    tpot_ms: float             # time-per-output-token in ms (-1 if 0/1 tokens)
    prompt_len: int            # word-count estimate of prompt length
    output_tokens: int         # actual tokens received
    expected_output_len: int
    policy: str
    success: bool
    error: str = ""
    # Server-side fields (populated if server returns them; otherwise -1)
    cached_len: int = -1
    Q_at_scheduling: float = -1.0
    jain_control: float = -1.0
    jain_prompt: float = -1.0
    p99_ttft_window_ms: float = -1.0
    aimd_violated: bool = False
    aimd_violation_reason: str = "none"
    aimd_step: int = -1


# ---------------------------------------------------------------------------
# Gamma inter-arrival generator
# ---------------------------------------------------------------------------

def gamma_interarrivals(n: int, rate: float, k: float, seed: int = 42) -> np.ndarray:
    """
    Generate n inter-arrival times from Gamma(shape=k, scale=1/(rate*k)).
    Mean inter-arrival = 1/rate for any k.

    Parameters
    ----------
    n     : number of inter-arrival intervals (= number of requests)
    rate  : target arrival rate in requests/second
    k     : shape parameter (k=1 → Poisson, k<1 → bursty, k>1 → regular)
    seed  : random seed for reproducibility
    """
    rng = np.random.default_rng(seed)
    scale = 1.0 / (rate * k)
    return rng.gamma(shape=k, scale=scale, size=n)


def build_arrival_plan(
    specs: List[RequestSpec],
    rate: float,
    k: float,
    seed: int,
    arrival_mode: str,
) -> List[tuple[float, RequestSpec]]:
    """
    Build absolute arrival times for each request.

    arrival_mode="global":
        One Gamma process over all requests in list order.

    arrival_mode="per-client":
        One Gamma process per client_id, then merge by timestamp.
        The total target rate is split evenly across active clients.
    """
    if arrival_mode == "global":
        interarrivals = gamma_interarrivals(len(specs), rate=rate, k=k, seed=seed)
        scheduled = np.cumsum(interarrivals)
        return list(zip(scheduled.tolist(), specs))

    if arrival_mode != "per-client":
        raise ValueError(f"Unknown arrival mode: {arrival_mode}")

    by_client: dict[str, List[RequestSpec]] = {}
    for spec in specs:
        by_client.setdefault(spec.client_id, []).append(spec)

    n_clients = max(1, len(by_client))
    per_client_rate = rate / n_clients

    merged: List[tuple[float, RequestSpec]] = []
    for idx, (_, client_specs) in enumerate(by_client.items()):
        client_seed = seed + idx * 10007
        interarrivals = gamma_interarrivals(
            len(client_specs),
            rate=per_client_rate,
            k=k,
            seed=client_seed,
        )
        scheduled = np.cumsum(interarrivals)
        merged.extend(zip(scheduled.tolist(), client_specs))

    merged.sort(key=lambda x: x[0])
    return merged


# ---------------------------------------------------------------------------
# Single request coroutine
# ---------------------------------------------------------------------------

async def _send_one(
    session: aiohttp.ClientSession,
    spec: RequestSpec,
    server_url: str,
    policy: str,
    t0: float,           # replay wall-clock start time
    timeout: float = 120.0,
) -> RequestResult:
    """Send one request and return a RequestResult."""
    req_id = str(uuid.uuid4())[:8]
    arrival = time.perf_counter() - t0

    payload = {
        "prompt": spec.prompt,
        "max_tokens": spec.expected_output_len,
        "client_id": spec.client_id,
    }

    first_token_time: Optional[float] = None
    last_token_time: Optional[float] = None
    output_tokens = 0
    cached_len = -1
    q_at_scheduling = -1.0
    jain_control = -1.0
    jain_prompt = -1.0
    p99_ttft_window_ms = -1.0
    aimd_violated = False
    aimd_violation_reason = "none"
    aimd_step = -1
    error = ""

    try:
        async with session.post(
            f"{server_url}/generate",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                return RequestResult(
                    req_id=req_id, client_id=spec.client_id,
                    arrival_time=arrival, ttft_ms=-1, tpot_ms=-1,
                    prompt_len=len(spec.prompt.split()),
                    output_tokens=0, expected_output_len=spec.expected_output_len,
                    policy=policy, success=False,
                    error=f"HTTP {resp.status}: {body[:200]}",
                )

            # Parse SSE stream: "data: <token>", "data: [DONE]", or metadata.
            async for raw_line in resp.content:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                token = line[len("data:"):].strip()
                if token == "[DONE]":
                    break

                if token.startswith(_STREAM_META_PREFIX):
                    try:
                        meta_payload = json.loads(token[len(_STREAM_META_PREFIX):])
                        cached_len = int(meta_payload.get("cached_len", -1))
                        q_at_scheduling = float(meta_payload.get("Q_at_scheduling", -1.0))
                        jain_control = float(meta_payload.get("jain_control", -1.0))
                        jain_prompt = float(meta_payload.get("jain_prompt", -1.0))
                        p99_ttft_window_ms = float(meta_payload.get("p99_ttft_ms", -1.0))
                        aimd_violated = bool(meta_payload.get("aimd_violated", False))
                        aimd_violation_reason = str(meta_payload.get("aimd_violation_reason", "none"))
                        aimd_step = int(meta_payload.get("aimd_step", -1))
                    except (TypeError, ValueError, json.JSONDecodeError):
                        # Ignore malformed metadata and keep sentinel defaults.
                        pass
                    continue

                now = time.perf_counter()
                if first_token_time is None:
                    first_token_time = now
                last_token_time = now
                output_tokens += 1

    except asyncio.TimeoutError:
        error = "timeout"
    except Exception as e:
        error = str(e)[:200]

    now = time.perf_counter()
    ft = first_token_time or now
    lt = last_token_time or now

    ttft_ms = (ft - (t0 + arrival)) * 1000.0
    tpot_ms = ((lt - ft) / max(output_tokens - 1, 1)) * 1000.0 if output_tokens > 1 else -1.0

    return RequestResult(
        req_id=req_id,
        client_id=spec.client_id,
        arrival_time=arrival,
        ttft_ms=ttft_ms if first_token_time else -1.0,
        tpot_ms=tpot_ms,
        prompt_len=len(spec.prompt.split()),
        output_tokens=output_tokens,
        expected_output_len=spec.expected_output_len,
        policy=policy,
        success=first_token_time is not None,
        error=error,
        cached_len=cached_len,
        Q_at_scheduling=q_at_scheduling,
        jain_control=jain_control,
        jain_prompt=jain_prompt,
        p99_ttft_window_ms=p99_ttft_window_ms,
        aimd_violated=aimd_violated,
        aimd_violation_reason=aimd_violation_reason,
        aimd_step=aimd_step,
    )


# ---------------------------------------------------------------------------
# Sequential per-client coroutine
# ---------------------------------------------------------------------------

async def _run_client_sequential(
    specs: List[RequestSpec],
    session: "aiohttp.ClientSession",
    server_url: str,
    policy: str,
    t0: float,
    timeout: float,
    results: List["RequestResult"],
    out_file,
    initial_delay: float = 0.0,
) -> None:
    """
    Send one client's requests strictly in order, waiting for each response
    before sending the next.  All clients run this coroutine concurrently,
    so inter-client parallelism is preserved while intra-client ordering is
    enforced.

    initial_delay — seconds to wait before sending the first turn.  Derived
    from the conversation's rescaled tstamp so that different clients start
    at staggered times, matching the paper's timestamp-rescaling approach.

    This models the paper's multi-turn workload: turn N+1 can only be
    submitted after the server has responded to turn N, ensuring the turn-N
    prefix is in the cache when turn N+1 arrives.
    """
    if initial_delay > 0.0:
        await asyncio.sleep(initial_delay)
    for spec in specs:
        result = await _send_one(session, spec, server_url, policy, t0, timeout)
        results.append(result)
        if out_file:
            out_file.write(json.dumps(asdict(result)) + "\n")
            out_file.flush()
        status = "OK" if result.success else f"FAIL({result.error[:40]})"
        print(
            f"[{result.arrival_time:6.2f}s] {result.client_id:<20} "
            f"ttft={result.ttft_ms:7.1f}ms  tokens={result.output_tokens:4d}  {status}"
        )


# ---------------------------------------------------------------------------
# Main replay function
# ---------------------------------------------------------------------------

async def replay(
    specs: List[RequestSpec],
    server_url: str,
    rate: float,
    k: float = 1.0,
    policy: str = "adaptive_dlpm",
    output_path: Optional[str] = None,
    seed: int = 42,
    timeout: float = 120.0,
    max_concurrency: int = 64,
    arrival_mode: str = "global",
) -> List[RequestResult]:
    """
    Replay a list of RequestSpec objects against the server using a
    Gamma process arrival model.

    Parameters
    ----------
    specs           : requests to send (from load_chatbot_arena / load_loogle /
                      load_synthetic)
    server_url      : base URL of the mini-sglang server
    rate            : target arrival rate (requests/second)
    k               : Gamma shape (k=1 Poisson, k<1 bursty, k>1 regular)
    policy          : label written into the log (matches MINISGL_POLICY on
                      the server — the client doesn't set it, just records it)
    output_path     : if given, write one JSON line per result to this file
    seed            : random seed for Gamma inter-arrivals (default 42)
    timeout         : per-request HTTP timeout in seconds
    max_concurrency : maximum simultaneous in-flight requests (ignored for
                      sequential mode — one connection per client)
    arrival_mode    : "global"     — one Gamma process over all requests
                      "per-client" — one Gamma process per client_id, merged
                      "sequential" — one coroutine per client; turns sent in
                                     order, each waiting for the previous
                                     response (models real multi-turn chat)

    Returns
    -------
    List[RequestResult] in completion order.
    """
    if not specs:
        return []

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        out_file = open(output_path, "w")
    else:
        out_file = None

    results: List[RequestResult] = []

    # ------------------------------------------------------------------
    # Sequential mode: each client's requests are sent in order, waiting
    # for each response before sending the next.  All clients run their
    # coroutines concurrently, so inter-client parallelism is preserved.
    # This models the paper's multi-turn workload (Fig. 6d) where turn
    # N+1 is only submitted after the server responds to turn N, ensuring
    # the prefix is cached when the next turn arrives.
    # ------------------------------------------------------------------
    if arrival_mode == "sequential":
        by_client: dict[str, List[RequestSpec]] = {}
        for spec in specs:
            by_client.setdefault(spec.client_id, []).append(spec)

        # Rescale per-client start times so the mean inter-client arrival
        # rate matches `rate`.  Each client's raw start time is the
        # arrival_time stored on its first RequestSpec (set by the dataset
        # loader from the real tstamp, relative to the earliest conversation).
        # If no client has a non-zero start time (e.g. synthetic / LooGLE),
        # scale_factor stays 1.0 and all clients start at t=0.
        raw_starts = sorted(
            cspecs[0].arrival_time
            for cspecs in by_client.values()
            if cspecs[0].arrival_time > 0.0
        )
        if len(raw_starts) >= 2 and rate > 0.0:
            interarrivals = [
                b - a for a, b in zip([0.0] + raw_starts[:-1], raw_starts)
            ]
            mean_interarrival = sum(interarrivals) / len(interarrivals)
            # scale_factor s.t. rescaled mean inter-arrival = 1/rate
            scale_factor = mean_interarrival * rate
        else:
            scale_factor = 1.0

        n_clients = max(len(by_client), 1)
        connector = aiohttp.TCPConnector(limit=n_clients)
        async with aiohttp.ClientSession(connector=connector) as session:
            t0 = time.perf_counter()
            tasks = [
                asyncio.create_task(
                    _run_client_sequential(
                        cspecs, session, server_url, policy, t0, timeout, results, out_file,
                        initial_delay=cspecs[0].arrival_time / scale_factor,
                    )
                )
                for cspecs in by_client.values()
            ]
            await asyncio.gather(*tasks)

        if out_file:
            out_file.close()
        return results

    # ------------------------------------------------------------------
    # Gamma-arrival modes: "global" and "per-client"
    # ------------------------------------------------------------------
    arrival_plan = build_arrival_plan(
        specs=specs,
        rate=rate,
        k=k,
        seed=seed,
        arrival_mode=arrival_mode,
    )
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _throttled(spec: RequestSpec, session: aiohttp.ClientSession, t0: float):
        async with semaphore:
            result = await _send_one(session, spec, server_url, policy, t0, timeout)
        results.append(result)
        if out_file:
            out_file.write(json.dumps(asdict(result)) + "\n")
            out_file.flush()
        status = "OK" if result.success else f"FAIL({result.error[:40]})"
        print(
            f"[{result.arrival_time:6.2f}s] {result.client_id:<20} "
            f"ttft={result.ttft_ms:7.1f}ms  tokens={result.output_tokens:4d}  {status}"
        )

    connector = aiohttp.TCPConnector(limit=max_concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        t0 = time.perf_counter()
        tasks = []
        for scheduled_at, spec in arrival_plan:
            now = time.perf_counter() - t0
            delay = max(0.0, scheduled_at - now)
            if delay > 0:
                await asyncio.sleep(delay)
            tasks.append(asyncio.create_task(_throttled(spec, session, t0)))

        await asyncio.gather(*tasks)

    if out_file:
        out_file.close()

    return results


# ---------------------------------------------------------------------------
# Active-window helper
# ---------------------------------------------------------------------------

def _active_window(results: List[RequestResult]) -> tuple:
    """
    Return (t_start, t_end) of the interval when ALL clients are simultaneously
    active, following the paper's Jain and throughput measurement convention.

        t_start = max(each client's earliest arrival_time)   ← last client joins
        t_end   = min(each client's latest completion_time)  ← first client finishes
        completion_time = arrival_time + ttft_ms / 1000.0

    Only successful requests are used. Returns (0.0, inf) when fewer than 2
    clients are present (single-client runs have no meaningful active window).
    """
    from collections import defaultdict
    successful = [r for r in results if r.success]
    by_client: dict = defaultdict(list)
    for r in successful:
        by_client[r.client_id].append(r)
    if len(by_client) < 2:
        return (0.0, float("inf"))
    t_start = max(min(r.arrival_time for r in reqs) for reqs in by_client.values())
    t_end = min(
        max(r.arrival_time + r.ttft_ms / 1000.0 for r in reqs)
        for reqs in by_client.values()
    )
    return (t_start, max(t_start, t_end))


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------

def print_summary(results: List[RequestResult]) -> None:
    """Print a brief summary table after a replay run."""
    if not results:
        print("No results.")
        return

    from collections import defaultdict

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    ttfts = sorted(r.ttft_ms for r in successful)

    def pct(lst, p):
        if not lst:
            return float("nan")
        return lst[max(0, int(p * len(lst)) - 1)]

    total_wall = max(r.arrival_time for r in results) if results else 0
    total_tokens = sum(r.output_tokens for r in successful)

    print("\n" + "=" * 60)
    print(f"Requests:     {len(results)}  ({len(successful)} OK, {len(failed)} failed)")
    print(f"Throughput:   {total_tokens / max(total_wall, 1e-9):.1f} tokens/sec  (overall)")
    if ttfts:
        print(f"TTFT P50:     {pct(ttfts, 0.50):.1f} ms")
        print(f"TTFT P99:     {pct(ttfts, 0.99):.1f} ms")

    # Active-window throughput and Jain — paper-faithful metrics computed over
    # the interval when all clients are simultaneously active (§6.1).
    t_start, t_end = _active_window(results)
    active_duration = max(t_end - t_start, 1e-9)
    active_reqs = [
        r for r in successful
        if t_start <= r.arrival_time
        and r.arrival_time + r.ttft_ms / 1000.0 <= t_end
    ]
    active_tokens = sum(r.output_tokens for r in active_reqs)
    if total_wall > 0 and t_end < float("inf"):
        print(f"Throughput:   {active_tokens / active_duration:.1f} tokens/sec  "
              f"(active window {t_start:.1f}s–{t_end:.1f}s, {len(active_reqs)} reqs)")

    # Per-client breakdown
    by_client: dict = defaultdict(list)
    for r in successful:
        by_client[r.client_id].append(r.ttft_ms)

    if len(by_client) > 1:
        print("\nPer-client median TTFT:")
        for cid, ttft_list in sorted(by_client.items()):
            med = sorted(ttft_list)[len(ttft_list) // 2]
            print(f"  {cid:<30} {med:8.1f} ms  ({len(ttft_list)} reqs)")

    # Jain — overall (all completed requests)
    def _jain(service_vals):
        x = list(service_vals)
        if len(x) < 2 or sum(xi ** 2 for xi in x) == 0:
            return float("nan")
        return sum(x) ** 2 / (len(x) * sum(xi ** 2 for xi in x))

    # paper formula (§3): service_i = extend_tokens×1 + output_tokens×2
    # extend_tokens = prompt_len - cached_len (cached tokens cost nothing to recompute).
    # cached_len is -1 when the server did not return it; fall back to prompt_len in that case.
    def _extend(r: RequestResult) -> int:
        if r.cached_len >= 0:
            return max(r.prompt_len - r.cached_len, 0)
        return r.prompt_len

    overall_service = {
        cid: sum(_extend(r) + 2 * r.output_tokens for r in successful if r.client_id == cid)
        for cid in by_client
    }
    print(f"\nJain (overall, extend+2×output):        {_jain(overall_service.values()):.4f}")

    # Jain — active window only
    active_by_client: dict = defaultdict(list)
    for r in active_reqs:
        active_by_client[r.client_id].append(r)
    if len(active_by_client) >= 2:
        active_service = {
            cid: sum(_extend(r) + 2 * r.output_tokens for r in reqs)
            for cid, reqs in active_by_client.items()
        }
        print(f"Jain (active window, extend+2×output):  {_jain(active_service.values()):.4f}")

    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args():
    p = argparse.ArgumentParser(description="Replay workload against mini-sglang")
    p.add_argument("--server",  default="http://127.0.0.1:19190")
    p.add_argument("--dataset", choices=["synthetic", "loogle", "chatbot_arena"],
                   default="synthetic")
    p.add_argument("--arrival-mode", choices=["global", "per-client", "sequential"], default="global",
                   help=(
                       "Arrival process mode: "
                       "'global' = one Gamma process for all requests; "
                       "'per-client' = one Gamma process per client, merged by timestamp; "
                       "'sequential' = turns sent in order per client, waiting for each response "
                       "(recommended for chatbot_arena and loogle to model real prefix-cache reuse)"
                   ))
    p.add_argument("--rate",    type=float, default=2.0,
                   help="Target arrival rate (req/sec)")
    p.add_argument("--k",       type=float, default=1.0,
                   help="Gamma shape: 1=Poisson, <1=bursty, >1=regular")
    p.add_argument("--policy",  default="adaptive_dlpm",
                   help="Label for the log (must match MINISGL_POLICY on server)")
    p.add_argument("--output",  default=None,
                   help="Path to write JSONL results (default: results/<dataset>_<policy>.jsonl)")
    p.add_argument("--max-reqs", type=int, default=100)
    p.add_argument("--seed",    type=int, default=42)
    p.add_argument("--dominant-reqs", type=int, default=80)
    p.add_argument("--cold-reqs",     type=int, default=20)
    p.add_argument("--num-dominant-clients", type=int, default=1,
                   help="Number of distinct dominant client IDs (each shares the same system prompt)")
    p.add_argument("--num-cold-clients", type=int, default=1,
                   help="Number of distinct cold client IDs (each sends unique prompts)")
    p.add_argument("--timeout", type=float, default=120.0,
                   help="Per-request HTTP timeout in seconds")
    p.add_argument("--max-concurrency", type=int, default=64,
                   help="Maximum simultaneous in-flight requests")
    p.add_argument("--min-turns", type=int, default=1,
                   help="chatbot_arena only: skip conversations with fewer turns than this")
    p.add_argument("--loogle-max-input-tokens", type=int, default=26000,
                   help="loogle only: conservative estimated input-token cap; set <=0 to disable truncation")
    return p.parse_args()


async def _main():
    args = _parse_args()

    if args.dataset == "synthetic":
        specs = load_synthetic(
            dominant_reqs=args.dominant_reqs,
            cold_reqs=args.cold_reqs,
            num_dominant_clients=args.num_dominant_clients,
            num_cold_clients=args.num_cold_clients,
        )
    elif args.dataset == "loogle":
        # one_per_doc=False: keep all QA pairs per document so that multiple
        # questions from the same doc share the long document prefix — matching
        # the paper's Long-Context QA workload (Fig. 6a: Long Doc → Q1A1, Q2A2, Q3A3).
        loogle_cap = args.loogle_max_input_tokens if args.loogle_max_input_tokens > 0 else None
        specs = load_loogle(max_docs=args.max_reqs, one_per_doc=False, max_input_tokens=loogle_cap)
    elif args.dataset == "chatbot_arena":
        from workload.dataset import load_chatbot_arena
        specs = load_chatbot_arena(max_conversations=args.max_reqs, min_turns=args.min_turns)
    else:
        raise ValueError(f"Unknown dataset: {args.dataset}")

    output = args.output or f"results/{args.dataset}_{args.policy}.jsonl"

    print(
        f"Replaying {len(specs)} requests  arrival_mode={args.arrival_mode}  "
        f"rate={args.rate} req/s  k={args.k}"
    )
    print(f"Server: {args.server}  Policy label: {args.policy}")
    print(f"Output: {output}\n")

    results = await replay(
        specs=specs,
        server_url=args.server,
        rate=args.rate,
        k=args.k,
        policy=args.policy,
        output_path=output,
        seed=args.seed,
        timeout=args.timeout,
        max_concurrency=args.max_concurrency,
        arrival_mode=args.arrival_mode,
    )
    print_summary(results)


if __name__ == "__main__":
    asyncio.run(_main())
