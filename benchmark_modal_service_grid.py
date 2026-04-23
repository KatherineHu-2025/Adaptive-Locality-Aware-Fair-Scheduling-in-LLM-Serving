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
- loogle_prefix: request_count is split into dominant/cold by --loogle-prefix-dominant-fraction.

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
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest


def _find_modal_python() -> str:
    """Return the Python executable that has modal installed."""
    try:
        subprocess.run([sys.executable, "-c", "import modal"], check=True, capture_output=True)
        return sys.executable
    except subprocess.CalledProcessError:
        pass
    modal_bin = shutil.which("modal")
    if modal_bin:
        bin_dir = Path(modal_bin).parent
        for name in ("python3", "python"):
            candidate = bin_dir / name
            if candidate.exists():
                try:
                    subprocess.run([str(candidate), "-c", "import modal"], check=True, capture_output=True)
                    return str(candidate)
                except subprocess.CalledProcessError:
                    pass
    return sys.executable


MODAL_PYTHON = _find_modal_python()

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


def deploy_service(service_name: str, policy: str, use_dummy: bool, extra_env: dict[str, str] | None = None) -> str:
    env = os.environ.copy()
    env["MODAL_MINISGL_POLICY"] = policy
    env["MODAL_MINISGL_DUMMY_WEIGHT"] = "1" if use_dummy else "0"
    if extra_env:
        env.update(extra_env)

    cmd = [
        MODAL_PYTHON,
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


def reset_experiment_state(base_url: str, timeout_sec: float = 60.0, attempts: int = 3) -> dict[str, Any]:
    """Reset service-side scheduler experiment state so each run starts clean."""
    url = f"{base_url.rstrip('/')}/reset_experiment"
    payload = json.dumps({"scope": "experiment"}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    last_err: str | None = None

    for attempt in range(1, max(1, attempts) + 1):
        try:
            req = urlrequest.Request(url, data=payload, headers=headers, method="POST")
            with urlrequest.urlopen(req, timeout=timeout_sec) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                data = json.loads(body) if body else {}
                if isinstance(data, dict) and data.get("ok", True):
                    return data
                last_err = f"reset ok=false: {data}"
        except urlerror.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
            if exc.code == 404:
                raise RuntimeError(
                    "Server does not expose /reset_experiment (HTTP 404). "
                    "Redeploy using the current run_modal_service.py before benchmarking."
                ) from exc
            last_err = f"HTTP {exc.code}: {body[:300]}"
        except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_err = str(exc)

        if attempt < attempts:
            time.sleep(1.0)

    raise RuntimeError(f"Failed to reset experiment state via {url}. Last error: {last_err}")


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
    dominant_client_prefix: str = "client_dominant",
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
    request_total_ms = sorted(
        float(r.get("request_total_ms", -1.0))
        for r in success
        if float(r.get("request_total_ms", -1.0)) >= 0
    )
    # Backward-compatible fallback for older logs that do not include request_total_ms.
    if not request_total_ms:
        request_total_ms = sorted(
            float(r.get("ttft_ms", -1.0))
            + max(int(r.get("output_tokens", 0)) - 1, 0) * max(float(r.get("tpot_ms", -1.0)), 0.0)
            for r in success
            if float(r.get("ttft_ms", -1.0)) >= 0
        )

    dominant_success = [
        r for r in success if str(r.get("client_id", "")).startswith(dominant_client_prefix)
    ] if dominant_client_prefix else []
    dominant_ttfts = sorted(
        float(r.get("ttft_ms", -1.0)) for r in dominant_success if float(r.get("ttft_ms", -1.0)) >= 0
    )
    dominant_request_total_ms = sorted(
        float(r.get("request_total_ms", -1.0))
        for r in dominant_success
        if float(r.get("request_total_ms", -1.0)) >= 0
    )
    if not dominant_request_total_ms:
        dominant_request_total_ms = sorted(
            float(r.get("ttft_ms", -1.0))
            + max(int(r.get("output_tokens", 0)) - 1, 0) * max(float(r.get("tpot_ms", -1.0)), 0.0)
            for r in dominant_success
            if float(r.get("ttft_ms", -1.0)) >= 0
        )

    total_wall = max((float(r.get("arrival_time", 0.0)) for r in rows), default=0.0)
    total_tokens = sum(int(r.get("output_tokens", 0)) for r in success)

    # Jain Fairness Index — paper formula (§3, following VTC):
    #   service_i = extend_tokens × 1 + output_tokens × 2
    # extend_tokens = prompt_len - cached_len (cached tokens cost nothing to recompute).
    # cached_len is -1 when the server did not return it; fall back to prompt_len in that case.
    by_client_service: dict[str, int] = {}
    by_client_output: dict[str, int] = {}
    for r in success:
        cid = str(r.get("client_id", ""))
        out_tok = int(r.get("output_tokens", 0))
        prompt_tok = int(r.get("prompt_len", 0))
        cached_tok = int(r.get("cached_len", -1))
        extend_tok = max(prompt_tok - cached_tok, 0) if cached_tok >= 0 else prompt_tok
        service_tok = extend_tok + out_tok * 2
        by_client_service[cid] = by_client_service.get(cid, 0) + service_tok
        by_client_output[cid] = by_client_output.get(cid, 0) + out_tok

    def _jain(vals: list[int]) -> float:
        if len(vals) < 2 or sum(v * v for v in vals) == 0:
            return float("nan")
        return (sum(vals) ** 2) / (len(vals) * sum(v * v for v in vals))

    jain = _jain(list(by_client_service.values()))
    jain_output = _jain(list(by_client_output.values()))

    # Active-window metrics — paper convention: measure throughput and Jain
    # only during the interval when ALL clients are simultaneously active.
    #   t_start = max(each client's earliest arrival_time)
    #   t_end   = min(each client's latest completion_time)
    # completion_time = arrival_time + ttft_ms / 1000
    by_client_arrivals: dict[str, list[float]] = {}
    by_client_completions: dict[str, list[float]] = {}
    for r in success:
        cid = str(r.get("client_id", ""))
        arr = float(r.get("arrival_time", 0.0))
        ttft_s = float(r.get("ttft_ms", 0.0)) / 1000.0
        by_client_arrivals.setdefault(cid, []).append(arr)
        by_client_completions.setdefault(cid, []).append(arr + ttft_s)

    n_clients = len(by_client_arrivals)
    if n_clients >= 2:
        t_start = max(min(v) for v in by_client_arrivals.values())
        t_end = min(max(v) for v in by_client_completions.values())
        active_dur = max(t_end - t_start, 1e-9)

        active_service: dict[str, int] = {}
        active_output: dict[str, int] = {}
        active_tokens = 0
        for r in success:
            arr = float(r.get("arrival_time", 0.0))
            ttft_s = float(r.get("ttft_ms", 0.0)) / 1000.0
            if t_start <= arr and arr + ttft_s <= t_end:
                cid = str(r.get("client_id", ""))
                out_tok = int(r.get("output_tokens", 0))
                prompt_tok = int(r.get("prompt_len", 0))
                cached_tok = int(r.get("cached_len", -1))
                extend_tok = max(prompt_tok - cached_tok, 0) if cached_tok >= 0 else prompt_tok
                active_tokens += out_tok
                active_service[cid] = active_service.get(cid, 0) + extend_tok + out_tok * 2
                active_output[cid] = active_output.get(cid, 0) + out_tok

        throughput_active = active_tokens / active_dur
        jain_active = _jain(list(active_service.values()))
        jain_active_output = _jain(list(active_output.values()))
    else:
        throughput_active = float("nan")
        jain_active = float("nan")
        jain_active_output = float("nan")

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
        "throughput_active_tok_per_sec": throughput_active,   # active-window only
        "ttft_p50_ms": percentile(ttfts, 0.50),
        "ttft_p95_ms": percentile(ttfts, 0.95),
        "ttft_p99_ms": percentile(ttfts, 0.99),
        "ttft_mean_ms": statistics.fmean(ttfts) if ttfts else float("nan"),
        "request_total_p50_ms": percentile(request_total_ms, 0.50),
        "request_total_p95_ms": percentile(request_total_ms, 0.95),
        "request_total_p99_ms": percentile(request_total_ms, 0.99),
        "request_total_mean_ms": statistics.fmean(request_total_ms) if request_total_ms else float("nan"),
        "dominant_client_prefix": dominant_client_prefix,
        "dominant_success_count": len(dominant_success),
        "dominant_ttft_p50_ms": percentile(dominant_ttfts, 0.50),
        "dominant_ttft_p99_ms": percentile(dominant_ttfts, 0.99),
        "dominant_request_total_p50_ms": percentile(dominant_request_total_ms, 0.50),
        "dominant_request_total_p99_ms": percentile(dominant_request_total_ms, 0.99),
        "jain_index": jain,                   # paper metric, all requests
        "jain_index_active": jain_active,     # paper metric, active window only
        "jain_output_tokens": jain_output,    # output-only, all requests
        "jain_output_active": jain_active_output,  # output-only, active window
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
    dominant_client_prefix: str = "client_dominant",
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
        "throughput_active_tok_per_sec": float("nan"),
        "ttft_p50_ms": float("nan"),
        "ttft_p95_ms": float("nan"),
        "ttft_p99_ms": float("nan"),
        "ttft_mean_ms": float("nan"),
        "request_total_p50_ms": float("nan"),
        "request_total_p95_ms": float("nan"),
        "request_total_p99_ms": float("nan"),
        "request_total_mean_ms": float("nan"),
        "dominant_client_prefix": dominant_client_prefix,
        "dominant_success_count": 0,
        "dominant_ttft_p50_ms": float("nan"),
        "dominant_ttft_p99_ms": float("nan"),
        "dominant_request_total_p50_ms": float("nan"),
        "dominant_request_total_p99_ms": float("nan"),
        "jain_index": float("nan"),
        "jain_index_active": float("nan"),
        "jain_output_tokens": float("nan"),
        "jain_output_active": float("nan"),
        "run_error": run_error,
        "output_file": str(output_file),
    }


def format_run_error(res: subprocess.CompletedProcess[str], tail_chars: int = 4000) -> str:
    combined = ((res.stdout or "") + "\n" + (res.stderr or "")).strip()
    if not combined:
        return "workload.client failed with no stdout/stderr output"
    return safe_for_console(combined[-tail_chars:])


def dominant_summary_suffix(row: dict[str, Any]) -> str:
    parts: list[str] = []
    dom_ttft = row.get("dominant_ttft_p50_ms", float("nan"))
    dom_total = row.get("dominant_request_total_p50_ms", float("nan"))
    if isinstance(dom_ttft, (int, float)) and not math.isnan(float(dom_ttft)):
        parts.append(f"dom_ttft_p50={float(dom_ttft):.1f}ms")
    if isinstance(dom_total, (int, float)) and not math.isnan(float(dom_total)):
        parts.append(f"dom_e2e_p50={float(dom_total):.1f}ms")
    return (" " + " ".join(parts)) if parts else ""


def stop_service(service_name: str) -> None:
    cmd = [MODAL_PYTHON, "-m", "modal", "app", "stop", service_name]
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
    min_turns: int = 1,
    num_dominant_clients: int = 1,
    num_cold_clients: int = 1,
    loogle_max_input_tokens: int = 26000,
    loogle_prefix_max_docs: int = 500,
    loogle_prefix_dominant_client_id: str = "client_dominant",
    loogle_prefix_cold_client_prefix: str = "client_cold",
    loogle_prefix_mix_mode: str = "interleave",
    loogle_prefix_chunk_size: int = 20,
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

    if dataset in ("synthetic", "loogle_prefix"):
        cmd.extend([
            "--dominant-reqs",
            str(dominant_reqs),
            "--cold-reqs",
            str(cold_reqs),
        ])

    if dataset == "synthetic":
        cmd.extend([
            "--num-dominant-clients",
            str(num_dominant_clients),
            "--num-cold-clients",
            str(num_cold_clients),
        ])

    if dataset in ("loogle", "loogle_prefix"):
        cmd.extend([
            "--loogle-max-input-tokens",
            str(loogle_max_input_tokens),
        ])

    if dataset == "loogle_prefix":
        cmd.extend([
            "--loogle-prefix-max-docs",
            str(loogle_prefix_max_docs),
            "--loogle-prefix-dominant-client-id",
            loogle_prefix_dominant_client_id,
            "--loogle-prefix-cold-client-prefix",
            loogle_prefix_cold_client_prefix,
            "--loogle-prefix-mix-mode",
            loogle_prefix_mix_mode,
            "--loogle-prefix-chunk-size",
            str(loogle_prefix_chunk_size),
        ])

    if dataset == "chatbot_arena" and min_turns > 1:
        cmd.extend(["--min-turns", str(min_turns)])

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
        choices=["synthetic", "loogle", "loogle_prefix", "chatbot_arena"],
        default="synthetic",
        help=(
            "Workload dataset for workload.client. "
            "For non-synthetic datasets, request-count values are used as --max-reqs."
        ),
    )
    parser.add_argument("--cold-fraction", type=float, default=0.2)
    parser.add_argument("--loogle-prefix-dominant-fraction", type=float, default=0.8,
                        help="loogle_prefix only: fraction of requests assigned to dominant repeated-context client")
    parser.add_argument("--loogle-max-input-tokens", type=int, default=26000,
                        help="loogle/loogle_prefix: conservative estimated input-token cap; set <=0 to disable truncation")
    parser.add_argument("--loogle-prefix-max-docs", type=int, default=500,
                        help="loogle_prefix only: cap on distinct docs sampled from LooGLE")
    parser.add_argument("--dominant-client-prefix", default="client_dominant",
                        help="Prefix used to identify dominant client rows in summary metrics")
    parser.add_argument("--loogle-prefix-cold-client-prefix", default="client_cold",
                        help="loogle_prefix only: client ID prefix for cold/new-context requests")
    parser.add_argument("--loogle-prefix-mix-mode", choices=["interleave", "random", "chunked"], default="interleave",
                        help="loogle_prefix only: request ordering strategy for dominant/cold mix")
    parser.add_argument("--loogle-prefix-chunk-size", type=int, default=20,
                        help="loogle_prefix only: chunk size used when mix mode is 'chunked'")
    parser.add_argument("--arrival-mode", choices=["global", "per-client", "sequential"], default="per-client")
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--max-concurrency", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-turns", type=int, default=1,
                        help="chatbot_arena only: skip conversations with fewer turns than this (default 1 = all)")
    parser.add_argument("--use-dummy-weight", action="store_true", help="Use dummy weights in service (fast but gibberish text)")
    parser.add_argument("--stop-service-at-end", action="store_true")
    parser.add_argument("--reuse-existing-url", default="", help="Skip deploy and benchmark this existing service URL")
    parser.add_argument("--output-root", default="results")
    parser.add_argument("--num-dominant-clients", type=int, default=1,
                        help="Number of distinct dominant client IDs sharing the same system prompt")
    parser.add_argument("--num-cold-clients", type=int, default=1,
                        help="Number of distinct cold client IDs with unique prompts")
    # Static DLPM Q grid: deploys dlpm once per Q value with Q_MIN=Q_MAX=Q_INIT=Q
    parser.add_argument("--static-q-values", default="",
                        help="Comma-separated Q values for static dlpm deployments (e.g. 1200,4000,8000). "
                             "Ignored for lpm and adaptive_dlpm. Creates one deployment per value.")
    # Adaptive DLPM knobs passed as deploy-time env vars
    parser.add_argument("--aimd-jain-threshold", default="0.75",
                        help="Jain fairness threshold for adaptive_dlpm (AIMD_JAIN_THRESHOLD)")
    parser.add_argument("--aimd-q-init", default="4000",
                        help="Initial Q for adaptive_dlpm (AIMD_Q_INIT)")
    parser.add_argument("--aimd-q-min", default="1200",
                        help="Q lower bound for adaptive_dlpm (AIMD_Q_MIN)")
    parser.add_argument("--aimd-q-max", default="16000",
                        help="Q upper bound for adaptive_dlpm (AIMD_Q_MAX)")
    args = parser.parse_args()

    policies = parse_str_list(args.policies)
    rates = parse_float_list(args.rates)
    ks = parse_float_list(args.ks)
    request_counts = parse_int_list(args.request_counts)
    static_q_values = parse_int_list(args.static_q_values) if args.static_q_values else []

    # Expand policies into (policy, run_label, extra_deploy_env) tuples.
    # dlpm expands into one entry per static Q value; other policies get one entry.
    policy_runs: list[tuple[str, str, dict[str, str]]] = []
    for policy in policies:
        if policy == "dlpm" and static_q_values:
            for q in static_q_values:
                policy_runs.append((
                    policy,
                    f"dlpm_q{q}",
                    {"AIMD_Q_INIT": str(q), "AIMD_Q_MIN": str(q), "AIMD_Q_MAX": str(q)},
                ))
        elif policy == "adaptive_dlpm":
            policy_runs.append((
                policy,
                "adaptive_dlpm",
                {
                    "AIMD_JAIN_THRESHOLD": args.aimd_jain_threshold,
                    "AIMD_Q_INIT": args.aimd_q_init,
                    "AIMD_Q_MIN": args.aimd_q_min,
                    "AIMD_Q_MAX": args.aimd_q_max,
                },
            ))
        else:
            policy_runs.append((policy, policy, {}))

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

            for (policy, run_label, _), rate, kval, req_count in itertools.product(policy_runs, rates, ks, request_counts):
                if args.dataset == "synthetic":
                    cold = int(round(req_count * args.cold_fraction))
                    cold = min(max(cold, 1), req_count - 1)
                    dominant = req_count - cold
                elif args.dataset == "loogle_prefix":
                    dominant = int(round(req_count * args.loogle_prefix_dominant_fraction))
                    dominant = min(max(dominant, 1), req_count - 1)
                    cold = req_count - dominant
                else:
                    cold = 0
                    dominant = 0

                out_file = run_dir / f"{run_label}_r{rate}_k{kval}_n{req_count}.jsonl"
                reset_experiment_state(base_url)
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
                    min_turns=args.min_turns,
                    num_dominant_clients=args.num_dominant_clients,
                    num_cold_clients=args.num_cold_clients,
                    loogle_max_input_tokens=args.loogle_max_input_tokens,
                    loogle_prefix_max_docs=args.loogle_prefix_max_docs,
                    loogle_prefix_dominant_client_id=args.dominant_client_prefix,
                    loogle_prefix_cold_client_prefix=args.loogle_prefix_cold_client_prefix,
                    loogle_prefix_mix_mode=args.loogle_prefix_mix_mode,
                    loogle_prefix_chunk_size=args.loogle_prefix_chunk_size,
                )

                if res.returncode != 0 or not out_file.exists():
                    run_error = format_run_error(res)
                    print(
                        f"[error] policy={run_label} rate={rate} k={kval} n={req_count} "
                        f"return_code={res.returncode}; output not available"
                    )
                    print(run_error)
                    if args.dataset == "chatbot_arena":
                        print(
                            "[hint] chatbot_arena is a gated HF dataset; authenticate first "
                            "(e.g., `huggingface-cli login` or set HUGGINGFACE_HUB_TOKEN)."
                        )
                    row = make_failed_row(
                        run_label,
                        args.dataset,
                        rate,
                        kval,
                        req_count,
                        dominant,
                        cold,
                        out_file,
                        run_error,
                        dominant_client_prefix=args.dominant_client_prefix,
                    )
                else:
                    row = summarize_jsonl(
                        out_file,
                        run_label,
                        args.dataset,
                        rate,
                        kval,
                        req_count,
                        dominant,
                        cold,
                        dominant_client_prefix=args.dominant_client_prefix,
                    )
                row["return_code"] = res.returncode
                row["server_url"] = base_url
                summaries.append(row)
                print(
                    f"[done] policy={run_label} rate={rate} k={kval} n={req_count} "
                    f"success={row['success_count']}/{row['total_requests']} "
                    f"p50={row['ttft_p50_ms']:.1f}ms p99={row['ttft_p99_ms']:.1f}ms"
                    f"{dominant_summary_suffix(row)}"
                )
        else:
            for policy, run_label, extra_env in policy_runs:
                # Force a fresh app session for each policy so deploy-time env changes are applied.
                stop_service(args.service_name)
                base_url = deploy_service(
                    service_name=args.service_name,
                    policy=policy,
                    use_dummy=args.use_dummy_weight,
                    extra_env=extra_env,
                ).rstrip("/")
                health = wait_for_health(base_url)
                print(f"[health] {run_label}: {health}")
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
                    elif args.dataset == "loogle_prefix":
                        dominant = int(round(req_count * args.loogle_prefix_dominant_fraction))
                        dominant = min(max(dominant, 1), req_count - 1)
                        cold = req_count - dominant
                    else:
                        cold = 0
                        dominant = 0

                    out_file = run_dir / f"{run_label}_r{rate}_k{kval}_n{req_count}.jsonl"
                    reset_experiment_state(base_url)
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
                        min_turns=args.min_turns,
                        num_dominant_clients=args.num_dominant_clients,
                        num_cold_clients=args.num_cold_clients,
                        loogle_max_input_tokens=args.loogle_max_input_tokens,
                        loogle_prefix_max_docs=args.loogle_prefix_max_docs,
                        loogle_prefix_dominant_client_id=args.dominant_client_prefix,
                        loogle_prefix_cold_client_prefix=args.loogle_prefix_cold_client_prefix,
                        loogle_prefix_mix_mode=args.loogle_prefix_mix_mode,
                        loogle_prefix_chunk_size=args.loogle_prefix_chunk_size,
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
                            dominant_client_prefix=args.dominant_client_prefix,
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
                            dominant_client_prefix=args.dominant_client_prefix,
                        )
                    row["return_code"] = res.returncode
                    row["server_url"] = base_url
                    summaries.append(row)
                    print(
                        f"[done] policy={policy} rate={rate} k={kval} n={req_count} "
                        f"success={row['success_count']}/{row['total_requests']} "
                        f"p50={row['ttft_p50_ms']:.1f}ms p99={row['ttft_p99_ms']:.1f}ms"
                        f"{dominant_summary_suffix(row)}"
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
