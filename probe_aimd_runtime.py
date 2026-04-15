"""
Run a single short adaptive-DLPM probe and verify AIMD runtime behavior.

What this script is for:
- Quick validation that AIMD is active on a currently running service.
- Runs one workload.client invocation and compares /aimd before vs after.
- Produces a run-local AIMD trace so Q movement is scoped to this run only.
- Prints a verdict: no updates, updates-with-constant-Q, or updates-with-Q-change.

How to run:
1) Basic probe:
        python probe_aimd_runtime.py --server https://<your-modal-url>

2) Probe with custom load shape:
        python probe_aimd_runtime.py \
                --server https://<your-modal-url> \
                --rate 3.0 \
                --k 0.5 \
                --dominant-reqs 60 \
                --cold-reqs 40 \
                --arrival-mode per-client \
                --max-concurrency 4 \
                --timeout 600 \
                --output results/probe_custom.jsonl \
                --aimd-output results/probe_custom_aimd_run.json

Key command-line flags:
- Target/output:
    --server, --output, --aimd-output

- Workload shape:
    --rate, --k, --dominant-reqs, --cold-reqs,
    --arrival-mode, --max-concurrency, --timeout, --seed

Difference vs run_aimd_ab_test_v2.py:
- This script does not deploy or compare strict-vs-relaxed cases; it probes one
    already-deployed endpoint and reports run-local AIMD movement.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path
from urllib import parse, request


def fetch_json(url: str) -> dict:
    req = request.Request(url, method="GET")
    with request.urlopen(req, timeout=20) as resp:
        payload = resp.read().decode("utf-8", errors="replace")
    return json.loads(payload)


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    idx = max(0, math.ceil(p * len(sorted_vals)) - 1)
    return sorted_vals[idx]


def summarize(rows: list[dict]) -> dict:
    success = [r for r in rows if r.get("success")]
    ttfts = sorted(float(r.get("ttft_ms", -1.0)) for r in success if float(r.get("ttft_ms", -1.0)) >= 0.0)
    total_wall = max((float(r.get("arrival_time", 0.0)) for r in rows), default=0.0)
    total_tokens = sum(int(r.get("output_tokens", 0)) for r in success)

    return {
        "total_requests": len(rows),
        "success_count": len(success),
        "failed_count": len(rows) - len(success),
        "success_rate": (len(success) / len(rows)) if rows else 0.0,
        "ttft_p50_ms": percentile(ttfts, 0.50),
        "ttft_p99_ms": percentile(ttfts, 0.99),
        "throughput_tok_per_sec": total_tokens / max(total_wall, 1e-9),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe adaptive AIMD runtime behavior with one short workload run")
    parser.add_argument("--server", required=True, help="Modal base URL, e.g. https://xxx.modal.run")
    parser.add_argument("--rate", type=float, default=1.5)
    parser.add_argument("--k", type=float, default=0.5)
    parser.add_argument("--dominant-reqs", type=int, default=30)
    parser.add_argument("--cold-reqs", type=int, default=20)
    parser.add_argument("--arrival-mode", choices=["global", "per-client"], default="per-client")
    parser.add_argument("--max-concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="results/probe_aimd_runtime.jsonl")
    parser.add_argument(
        "--aimd-output",
        default="",
        help=(
            "Optional path to save AIMD records for this run only. "
            "Default: <output_stem>_aimd_run.json"
        ),
    )
    args = parser.parse_args()

    base = args.server.rstrip("/")
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    health_before = fetch_json(f"{base}/healthz")
    aimd_before = fetch_json(f"{base}/aimd?{parse.urlencode({'limit': 5})}")

    before_count = int(aimd_before.get("count", 0)) if aimd_before.get("ok", False) else 0
    before_q = None
    records_before = aimd_before.get("records") or []
    if records_before:
        before_q = records_before[-1].get("Q")

    cmd = [
        sys.executable,
        "-m",
        "workload.client",
        "--server",
        base,
        "--dataset",
        "synthetic",
        "--arrival-mode",
        args.arrival_mode,
        "--rate",
        str(args.rate),
        "--k",
        str(args.k),
        "--policy",
        "adaptive_dlpm",
        "--timeout",
        str(args.timeout),
        "--max-concurrency",
        str(args.max_concurrency),
        "--dominant-reqs",
        str(args.dominant_reqs),
        "--cold-reqs",
        str(args.cold_reqs),
        "--seed",
        str(args.seed),
        "--output",
        str(out_path),
    ]

    print("[probe] running:", " ".join(cmd))
    res = subprocess.run(cmd, text=True, check=False)

    health_after = fetch_json(f"{base}/healthz")
    aimd_after = fetch_json(f"{base}/aimd?{parse.urlencode({'limit': 20})}")

    after_count = int(aimd_after.get("count", 0)) if aimd_after.get("ok", False) else 0
    after_q = None
    records_after = aimd_after.get("records") or []
    if records_after:
        after_q = records_after[-1].get("Q")

    delta_updates = max(0, after_count - before_count)

    # Fetch a wider tail so we can isolate this run's records even if history exists.
    tail_limit = max(50, delta_updates + 10)
    aimd_tail = fetch_json(f"{base}/aimd?{parse.urlencode({'limit': tail_limit})}")
    tail_records = aimd_tail.get("records") or []

    if delta_updates > 0 and delta_updates <= len(tail_records):
        run_records = tail_records[-delta_updates:]
    elif delta_updates > 0:
        # History window is truncated; best-effort fallback to all fetched records.
        run_records = tail_records
    else:
        run_records = []

    q_values_recent = [rec.get("Q") for rec in records_after if rec.get("Q") is not None]
    unique_q_recent = sorted(set(float(q) for q in q_values_recent)) if q_values_recent else []

    q_values_run = [rec.get("Q") for rec in run_records if rec.get("Q") is not None]
    unique_q_run = sorted(set(float(q) for q in q_values_run)) if q_values_run else []

    rows = read_jsonl(out_path)
    summary = summarize(rows)

    aimd_out_path = Path(args.aimd_output) if args.aimd_output else out_path.with_name(f"{out_path.stem}_aimd_run.json")
    aimd_out_path.parent.mkdir(parents=True, exist_ok=True)
    aimd_artifact = {
        "server": base,
        "aimd_updates_before": before_count,
        "aimd_updates_after": after_count,
        "aimd_delta_updates": delta_updates,
        "aimd_q_before": before_q,
        "aimd_q_after": after_q,
        "aimd_unique_q_run": unique_q_run,
        "records": run_records,
    }
    aimd_out_path.write_text(json.dumps(aimd_artifact, indent=2), encoding="utf-8")

    print("\n=== Probe Summary ===")
    print("workload return code:", res.returncode)
    print("health before:", health_before)
    print("health after:", health_after)
    print("aimd updates before:", before_count)
    print("aimd updates after:", after_count)
    print("aimd delta updates:", delta_updates)
    print("aimd Q before:", before_q)
    print("aimd Q after:", after_q)
    print("aimd unique Q in recent sample:", unique_q_recent)
    print("aimd unique Q during this run:", unique_q_run)
    print("aimd run trace:", str(aimd_out_path))
    print("workload summary:", summary)

    if delta_updates <= 0:
        print("\n[verdict] No AIMD updates observed. Likely control interval too large or run too short.")
    elif len(unique_q_run) >= 2:
        print("\n[verdict] AIMD is active and Q changed during this run.")
    else:
        print("\n[verdict] AIMD updates observed, but Q stayed constant during this run (possible saturation at bounds).")

    return res.returncode


if __name__ == "__main__":
    raise SystemExit(main())
