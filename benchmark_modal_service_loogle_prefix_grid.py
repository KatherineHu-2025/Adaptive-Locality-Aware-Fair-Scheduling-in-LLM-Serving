"""
Dedicated benchmark runner for a prefix-favoring LooGLE workload.

Scenario
--------
- One dominant client repeatedly queries the SAME long document context
  (high prefix reuse potential).
- Cold requests use fresh contexts from different documents/clients.

This script is a thin wrapper around benchmark_modal_service_grid.py with
--dataset loogle_prefix and defaults tuned for this workload.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run prefix-favoring LooGLE benchmark grid (dominant repeated-context client + cold fresh contexts)"
    )
    parser.add_argument("--service-name", default="adaptive-dlpm-scheduler-service")
    parser.add_argument("--policies", default="adaptive_dlpm,lpm,fcfs,dlpm")
    parser.add_argument("--rates", default="1.0")
    parser.add_argument("--ks", default="1.0")
    parser.add_argument("--request-counts", default="200,400")
    parser.add_argument("--static-q-values", default="1000,2000,4000,8000,16000,32000")
    parser.add_argument("--arrival-mode", choices=["global", "per-client", "sequential"], default="global")
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--max-concurrency", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-root", default="results")
    parser.add_argument("--loogle-prefix-dominant-fraction", type=float, default=0.8)
    parser.add_argument("--loogle-max-input-tokens", type=int, default=26000)
    parser.add_argument("--loogle-prefix-max-docs", type=int, default=500)
    parser.add_argument("--dominant-client-prefix", default="client_dominant")
    parser.add_argument("--loogle-prefix-cold-client-prefix", default="client_cold")
    parser.add_argument("--loogle-prefix-mix-mode", choices=["interleave", "random", "chunked"], default="chunked")
    parser.add_argument("--loogle-prefix-chunk-size", type=int, default=20)

    parser.add_argument("--aimd-jain-threshold", default="0.82")
    parser.add_argument("--aimd-q-init", default="4000")
    parser.add_argument("--aimd-q-min", default="1200")
    parser.add_argument("--aimd-q-max", default="16000")

    parser.add_argument("--reuse-existing-url", default="")
    parser.add_argument("--use-dummy-weight", action="store_true")
    parser.add_argument("--stop-service-at-end", action="store_true")

    args = parser.parse_args()

    script_path = Path(__file__).resolve().parent / "benchmark_modal_service_grid.py"
    cmd = [
        sys.executable,
        str(script_path),
        "--dataset",
        "loogle_prefix",
        "--service-name",
        args.service_name,
        "--policies",
        args.policies,
        "--rates",
        args.rates,
        "--ks",
        args.ks,
        "--request-counts",
        args.request_counts,
        "--static-q-values",
        args.static_q_values,
        "--arrival-mode",
        args.arrival_mode,
        "--timeout",
        str(args.timeout),
        "--max-concurrency",
        str(args.max_concurrency),
        "--seed",
        str(args.seed),
        "--output-root",
        args.output_root,
        "--loogle-prefix-dominant-fraction",
        str(args.loogle_prefix_dominant_fraction),
        "--loogle-max-input-tokens",
        str(args.loogle_max_input_tokens),
        "--loogle-prefix-max-docs",
        str(args.loogle_prefix_max_docs),
        "--dominant-client-prefix",
        args.dominant_client_prefix,
        "--loogle-prefix-cold-client-prefix",
        args.loogle_prefix_cold_client_prefix,
        "--loogle-prefix-mix-mode",
        args.loogle_prefix_mix_mode,
        "--loogle-prefix-chunk-size",
        str(args.loogle_prefix_chunk_size),
        "--aimd-jain-threshold",
        args.aimd_jain_threshold,
        "--aimd-q-init",
        args.aimd_q_init,
        "--aimd-q-min",
        args.aimd_q_min,
        "--aimd-q-max",
        args.aimd_q_max,
    ]

    if args.reuse_existing_url:
        cmd.extend(["--reuse-existing-url", args.reuse_existing_url])
    if args.use_dummy_weight:
        cmd.append("--use-dummy-weight")
    if args.stop_service_at_end:
        cmd.append("--stop-service-at-end")

    print("[run]", " ".join(cmd))
    res = subprocess.run(cmd, check=False)
    return int(res.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
