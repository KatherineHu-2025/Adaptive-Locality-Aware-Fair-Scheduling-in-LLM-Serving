"""
Benchmark driver for Modal hosted minisgl service.

What this script does:
1) Deploys run_modal_service.py (optionally once per policy).
2) Waits for /healthz.
3) Runs workload.client across a grid of rates, k values, policies, and request counts.
4) Summarizes each run and writes CSV + JSON outputs.

Dataset behavior:
- synthetic: request_count is split into dominant/cold by --cold-fraction.
- loogle/chatbot_arena: request_count is passed as --max-reqs to workload.client.

Example:
    python benchmark_modal_service_grid.py \
      --policies adaptive_dlpm,lpm,dlpm \
      --rates 0.5,1.0,1.5 \
      --ks 0.5,1.0 \
      --request-counts 25,50 \
      --arrival-mode per-client \
      --max-concurrency 2 \
      --timeout 600
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest


MODAL_URL_RE = re.compile(r"https://[a-zA-Z0-9\-\.]+\.modal\.run")
MODAL_URL_FUZZY_RE = re.compile(r"https://(?:[a-zA-Z0-9\-\.]|\s)+?\.modal\.\s*r\s*u\s*n")
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-9;]*[A-Za-z]")


def safe_for_console(text: str) -> str:
    """Make text safe to print on consoles with limited encodings (e.g., cp1252)."""
    encoding = sys.stdout.encoding or "utf-8"
    return text.encode(encoding, errors="backslashreplace").decode(encoding, errors="replace")


def parse_float_list(text: str) -> list[float]:
    return [float(x.strip()) for x in text.split(",") if x.strip()]


def parse_int_list(text: str) -> list[int]:
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def parse_str_list(text: str) -> list[str]:
    return [x.strip() for x in text.split(",") if x.strip()]


def run_cmd(cmd: list[str], env: dict[str, str] | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
    cmd_env = os.environ.copy()
    if env:
        cmd_env.update(env)

    # Normalize encoding for child Python CLIs (including modal) across platforms.
    # This avoids Unicode output issues on Windows and keeps behavior consistent on macOS/Linux.
    cmd_env.setdefault("PYTHONUTF8", "1")
    cmd_env.setdefault("PYTHONIOENCODING", "utf-8")

    return subprocess.run(
        cmd,
        env=cmd_env,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        capture_output=capture,
    )


def find_modal_url(output: str) -> str | None:
    clean = ANSI_ESCAPE_RE.sub("", output)

    matches = MODAL_URL_RE.findall(clean)
    if not matches:
        fuzzy_matches = MODAL_URL_FUZZY_RE.findall(clean)
        for candidate in fuzzy_matches:
            # Handle soft-wrapped URLs from rich/terminal output.
            normalized = re.sub(r"\s+", "", candidate)
            if MODAL_URL_RE.fullmatch(normalized):
                matches.append(normalized)

    if not matches:
        return None
    # Prefer non-dev URL when both are present.
    matches_sorted = sorted(matches, key=lambda u: ("-dev.modal.run" in u, len(u)))
    return matches_sorted[0]


def deploy_service(service_name: str, policy: str, use_dummy: bool) -> str:
    env = os.environ.copy()
    env["MODAL_MINISGL_POLICY"] = policy
    env["MODAL_MINISGL_DUMMY_WEIGHT"] = "1" if use_dummy else "0"

    cmd = [
        sys.executable,
        "-m",
        "modal",
        "deploy",
        "run_modal_service.py",
        "--name",
        service_name,
    ]
    print(f"\n[deploy] policy={policy} dummy={use_dummy} name={service_name}")
    res = run_cmd(cmd, env=env, capture=True)
    combined = (res.stdout or "") + "\n" + (res.stderr or "")
    tail = safe_for_console(combined[-2000:])

    if res.returncode != 0:
        raise RuntimeError(f"Modal deploy failed (policy={policy}).\n{tail}")

    base_url = find_modal_url(combined)
    if not base_url:
        raise RuntimeError(
            "Could not parse modal URL from deploy output.\n"
            "Run this manually and copy URL if needed:\n"
            f"{' '.join(cmd)}\n"
            f"Deploy output tail:\n{tail}"
        )

    print(f"[deploy] url={base_url}")
    return base_url


def wait_for_health(base_url: str, timeout_sec: int = 600) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    last_err: str | None = None
    url = f"{base_url.rstrip('/')}/healthz"

    while time.time() < deadline:
        try:
            req = urlrequest.Request(url, method="GET")
            with urlrequest.urlopen(req, timeout=8) as resp:
                payload = resp.read().decode("utf-8", errors="replace")
                data = json.loads(payload)
                if data.get("ok"):
                    return data
                last_err = f"health ok=false: {data}"
        except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_err = str(exc)
        time.sleep(4)

    raise RuntimeError(f"Health check timed out for {url}. Last error: {last_err}")


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return float("nan")
    idx = max(0, math.ceil(p * len(sorted_values)) - 1)
    return sorted_values[idx]


def summarize_jsonl(
    path: Path,
    policy: str,
    dataset: str,
    rate: float,
    k: float,
    request_count: int,
    dominant: int,
    cold: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    success = [r for r in rows if r.get("success")]
    failed = [r for r in rows if not r.get("success")]

    ttfts = sorted(float(r["ttft_ms"]) for r in success if float(r.get("ttft_ms", -1)) >= 0)
    total_wall = max((float(r.get("arrival_time", 0.0)) for r in rows), default=0.0)
    total_tokens = sum(int(r.get("output_tokens", 0)) for r in success)

    by_client_tokens: dict[str, int] = {}
    for r in success:
        cid = str(r.get("client_id", ""))
        by_client_tokens[cid] = by_client_tokens.get(cid, 0) + int(r.get("output_tokens", 0))

    jain = float("nan")
    x = list(by_client_tokens.values())
    if len(x) >= 2 and sum(v * v for v in x) > 0:
        jain = (sum(x) ** 2) / (len(x) * sum(v * v for v in x))

    return {
        "policy": policy,
        "dataset": dataset,
        "rate": rate,
        "k": k,
        "request_count": request_count,
        "dominant_reqs": dominant,
        "cold_reqs": cold,
        "total_requests": len(rows),
        "success_count": len(success),
        "failed_count": len(failed),
        "success_rate": (len(success) / len(rows)) if rows else 0.0,
        "throughput_tok_per_sec": total_tokens / max(total_wall, 1e-9),
        "ttft_p50_ms": percentile(ttfts, 0.50),
        "ttft_p95_ms": percentile(ttfts, 0.95),
        "ttft_p99_ms": percentile(ttfts, 0.99),
        "ttft_mean_ms": statistics.fmean(ttfts) if ttfts else float("nan"),
        "jain_index": jain,
        "run_error": "",
        "output_file": str(path),
    }


def make_failed_row(
    policy: str,
    dataset: str,
    rate: float,
    k: float,
    request_count: int,
    dominant: int,
    cold: int,
    output_file: Path,
    run_error: str,
) -> dict[str, Any]:
    """Return a consistent summary row for workload runs that failed before JSONL output was written."""
    return {
        "policy": policy,
        "dataset": dataset,
        "rate": rate,
        "k": k,
        "request_count": request_count,
        "dominant_reqs": dominant,
        "cold_reqs": cold,
        "total_requests": 0,
        "success_count": 0,
        "failed_count": 0,
        "success_rate": 0.0,
        "throughput_tok_per_sec": float("nan"),
        "ttft_p50_ms": float("nan"),
        "ttft_p95_ms": float("nan"),
        "ttft_p99_ms": float("nan"),
        "ttft_mean_ms": float("nan"),
        "jain_index": float("nan"),
        "run_error": run_error,
        "output_file": str(output_file),
    }


def format_run_error(res: subprocess.CompletedProcess[str], tail_chars: int = 4000) -> str:
    combined = ((res.stdout or "") + "\n" + (res.stderr or "")).strip()
    if not combined:
        return "workload.client failed with no stdout/stderr output"
    return safe_for_console(combined[-tail_chars:])


def stop_service(service_name: str) -> None:
    cmd = [sys.executable, "-m", "modal", "app", "stop", service_name]
    print(f"[stop] {' '.join(cmd)}")
    run_cmd(cmd, capture=False)


def run_client_once(
    base_url: str,
    policy: str,
    dataset: str,
    rate: float,
    k: float,
    request_count: int,
    dominant_reqs: int,
    cold_reqs: int,
    arrival_mode: str,
    timeout: float,
    max_concurrency: int,
    seed: int,
    out_file: Path,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        "-m",
        "workload.client",
        "--server",
        base_url,
        "--dataset",
        dataset,
        "--arrival-mode",
        arrival_mode,
        "--rate",
        str(rate),
        "--k",
        str(k),
        "--policy",
        policy,
        "--timeout",
        str(timeout),
        "--max-concurrency",
        str(max_concurrency),
        "--max-reqs",
        str(request_count),
        "--seed",
        str(seed),
        "--output",
        str(out_file),
    ]

    if dataset == "synthetic":
        cmd.extend([
            "--dominant-reqs",
            str(dominant_reqs),
            "--cold-reqs",
            str(cold_reqs),
        ])

    print("[run]", " ".join(cmd))
    return run_cmd(cmd, capture=True)


def write_outputs(rows: list[dict[str, Any]], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "summary.json"
    csv_path = out_dir / "summary.csv"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)

    if rows:
        fieldnames = list(rows[0].keys())
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Modal service across policy/rate/k/request grids")
    parser.add_argument("--service-name", default="adaptive-dlpm-scheduler-service")
    parser.add_argument("--policies", default="adaptive_dlpm,lpm,dlpm")
    parser.add_argument("--rates", default="0.5,1.0,1.5")
    parser.add_argument("--ks", default="0.5,1.0")
    parser.add_argument("--request-counts", default="25,50")
    parser.add_argument(
        "--dataset",
        choices=["synthetic", "loogle", "chatbot_arena"],
        default="synthetic",
        help=(
            "Workload dataset for workload.client. "
            "For non-synthetic datasets, request-count values are used as --max-reqs."
        ),
    )
    parser.add_argument("--cold-fraction", type=float, default=0.2)
    parser.add_argument("--arrival-mode", choices=["global", "per-client"], default="per-client")
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--max-concurrency", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--use-dummy-weight", action="store_true", help="Use dummy weights in service (fast but gibberish text)")
    parser.add_argument("--stop-service-at-end", action="store_true")
    parser.add_argument("--reuse-existing-url", default="", help="Skip deploy and benchmark this existing service URL")
    parser.add_argument("--output-root", default="results")
    args = parser.parse_args()

    policies = parse_str_list(args.policies)
    rates = parse_float_list(args.rates)
    ks = parse_float_list(args.ks)
    request_counts = parse_int_list(args.request_counts)

    if args.reuse_existing_url and len(policies) > 1:
        raise SystemExit(
            "--reuse-existing-url points to a single deployed server policy. "
            "Use one policy at a time with --reuse-existing-url, or remove it to auto-deploy per policy."
        )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.output_root) / f"modal_grid_{ts}"
    run_dir = out_dir / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[dict[str, Any]] = []

    try:
        if args.reuse_existing_url:
            base_url = args.reuse_existing_url.rstrip("/")
            health = wait_for_health(base_url)
            print(f"[health] reuse url ok: {health}")
            expected_policy = policies[0] if policies else ""
            reported_policy = str(health.get("policy", ""))
            if expected_policy and reported_policy and reported_policy != expected_policy:
                raise SystemExit(
                    f"--reuse-existing-url policy mismatch: requested '{expected_policy}', "
                    f"but endpoint reports '{reported_policy}' in /healthz."
                )

            for policy, rate, kval, req_count in itertools.product(policies, rates, ks, request_counts):
                if args.dataset == "synthetic":
                    cold = int(round(req_count * args.cold_fraction))
                    cold = min(max(cold, 1), req_count - 1)
                    dominant = req_count - cold
                else:
                    cold = 0
                    dominant = 0

                out_file = run_dir / f"{policy}_r{rate}_k{kval}_n{req_count}.jsonl"
                res = run_client_once(
                    base_url=base_url,
                    policy=policy,
                    dataset=args.dataset,
                    rate=rate,
                    k=kval,
                    request_count=req_count,
                    dominant_reqs=dominant,
                    cold_reqs=cold,
                    arrival_mode=args.arrival_mode,
                    timeout=args.timeout,
                    max_concurrency=args.max_concurrency,
                    seed=args.seed,
                    out_file=out_file,
                )

                if res.returncode != 0 or not out_file.exists():
                    run_error = format_run_error(res)
                    print(
                        f"[error] policy={policy} rate={rate} k={kval} n={req_count} "
                        f"return_code={res.returncode}; output not available"
                    )
                    print(run_error)
                    if args.dataset == "chatbot_arena":
                        print(
                            "[hint] chatbot_arena is a gated HF dataset; authenticate first "
                            "(e.g., `huggingface-cli login` or set HUGGINGFACE_HUB_TOKEN)."
                        )
                    row = make_failed_row(
                        policy,
                        args.dataset,
                        rate,
                        kval,
                        req_count,
                        dominant,
                        cold,
                        out_file,
                        run_error,
                    )
                else:
                    row = summarize_jsonl(
                        out_file,
                        policy,
                        args.dataset,
                        rate,
                        kval,
                        req_count,
                        dominant,
                        cold,
                    )
                row["return_code"] = res.returncode
                row["server_url"] = base_url
                summaries.append(row)
                print(
                    f"[done] policy={policy} rate={rate} k={kval} n={req_count} "
                    f"success={row['success_count']}/{row['total_requests']} "
                    f"p50={row['ttft_p50_ms']:.1f}ms p99={row['ttft_p99_ms']:.1f}ms"
                )
        else:
            for policy in policies:
                # Force a fresh app session for each policy so deploy-time env changes are applied.
                stop_service(args.service_name)
                base_url = deploy_service(
                    service_name=args.service_name,
                    policy=policy,
                    use_dummy=args.use_dummy_weight,
                ).rstrip("/")
                health = wait_for_health(base_url)
                print(f"[health] {policy}: {health}")
                reported_policy = str(health.get("policy", ""))
                if reported_policy and reported_policy != policy:
                    raise RuntimeError(
                        f"Deployed policy mismatch: expected '{policy}', got '{reported_policy}'. "
                        "Try a unique --service-name or stop the app and retry."
                    )

                for rate, kval, req_count in itertools.product(rates, ks, request_counts):
                    if args.dataset == "synthetic":
                        cold = int(round(req_count * args.cold_fraction))
                        cold = min(max(cold, 1), req_count - 1)
                        dominant = req_count - cold
                    else:
                        cold = 0
                        dominant = 0

                    out_file = run_dir / f"{policy}_r{rate}_k{kval}_n{req_count}.jsonl"
                    res = run_client_once(
                        base_url=base_url,
                        policy=policy,
                        dataset=args.dataset,
                        rate=rate,
                        k=kval,
                        request_count=req_count,
                        dominant_reqs=dominant,
                        cold_reqs=cold,
                        arrival_mode=args.arrival_mode,
                        timeout=args.timeout,
                        max_concurrency=args.max_concurrency,
                        seed=args.seed,
                        out_file=out_file,
                    )

                    if res.returncode != 0 or not out_file.exists():
                        run_error = format_run_error(res)
                        print(
                            f"[error] policy={policy} rate={rate} k={kval} n={req_count} "
                            f"return_code={res.returncode}; output not available"
                        )
                        print(run_error)
                        if args.dataset == "chatbot_arena":
                            print(
                                "[hint] chatbot_arena is a gated HF dataset; authenticate first "
                                "(e.g., `huggingface-cli login` or set HUGGINGFACE_HUB_TOKEN)."
                            )
                        row = make_failed_row(
                            policy,
                            args.dataset,
                            rate,
                            kval,
                            req_count,
                            dominant,
                            cold,
                            out_file,
                            run_error,
                        )
                    else:
                        row = summarize_jsonl(
                            out_file,
                            policy,
                            args.dataset,
                            rate,
                            kval,
                            req_count,
                            dominant,
                            cold,
                        )
                    row["return_code"] = res.returncode
                    row["server_url"] = base_url
                    summaries.append(row)
                    print(
                        f"[done] policy={policy} rate={rate} k={kval} n={req_count} "
                        f"success={row['success_count']}/{row['total_requests']} "
                        f"p50={row['ttft_p50_ms']:.1f}ms p99={row['ttft_p99_ms']:.1f}ms"
                    )

        json_path, csv_path = write_outputs(summaries, out_dir)

        print("\n=== Benchmark Complete ===")
        print(f"runs: {len(summaries)}")
        print(f"json: {json_path}")
        print(f"csv : {csv_path}")

        ok_runs = [r for r in summaries if r.get("success_count", 0) > 0]
        if ok_runs:
            best = min(ok_runs, key=lambda r: (r.get("ttft_p99_ms", float("inf")), -r.get("throughput_tok_per_sec", 0.0)))
            print(
                "best (by p99 then throughput): "
                f"policy={best['policy']} rate={best['rate']} k={best['k']} n={best['request_count']} "
                f"p99={best['ttft_p99_ms']:.1f}ms throughput={best['throughput_tok_per_sec']:.1f} tok/s"
            )

    finally:
        if args.stop_service_at_end and not args.reuse_existing_url:
            stop_service(args.service_name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
