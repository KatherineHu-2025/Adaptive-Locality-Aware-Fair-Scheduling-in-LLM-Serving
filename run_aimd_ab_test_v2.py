"""
Run a full strict-vs-relaxed AIMD A/B experiment and generate artifacts/plots.

What this script is for:
- End-to-end A/B comparison of adaptive DLPM with two Jain thresholds.
- Per-case deployment on Modal, health wait, optional warmup, and probe execution.
- Optional two-phase load profile (A then B) for longer-run AIMD behavior checks.
- Writes merged request logs, run-scoped AIMD traces, /aimd tail snapshots, and plots.

How to run:
1) Full A/B run (deploy + probes + plots):
        python run_aimd_ab_test_v2.py --server https://<your-modal-url>

2) Rebuild plots from existing artifacts only (no deploy/probe):
        python run_aimd_ab_test_v2.py --plot-only --server https://<your-modal-url>

3) Single-phase run (disable two-phase sawtooth flow):
        python run_aimd_ab_test_v2.py --server https://<your-modal-url> --disable-two-phase-sawtooth

Key command-line flags:
- Core target:
    --server, --app-name, --output-dir

- Strict vs relaxed threshold knobs:
    --strict-jain-threshold, --relaxed-jain-threshold

- Probe/load shape knobs:
    --arrival-mode, --max-concurrency, --timeout, --seed
    --phase-a-rate, --phase-a-k, --phase-a-dominant-reqs, --phase-a-cold-reqs
    --phase-b-rate, --phase-b-k, --phase-b-dominant-reqs, --phase-b-cold-reqs
    --disable-two-phase-sawtooth

- Warmup knobs:
    --disable-warmup, --warmup-rate, --warmup-k,
    --warmup-dominant-reqs, --warmup-cold-reqs,
    --warmup-max-concurrency, --warmup-timeout

- AIMD/deploy env overrides:
    --control-interval, --q-init, --q-min, --q-max,
    --additive-step, --mult-factor, --ttft-slo-ms,
    --telemetry-window, --aimd-debug-log-path

- Plot controls:
    --plot-only, --disable-plots, --plot-dpi

Difference vs probe_aimd_runtime.py:
- This script orchestrates full A/B deployment flow (strict + relaxed), while
    probe_aimd_runtime.py runs one short workload probe against an already-live server.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics as st
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib import request


def run_cmd(cmd: list[str], env: dict[str, str] | None = None, allow_fail: bool = False) -> int:
    print("$", " ".join(cmd))
    res = subprocess.run(cmd, env=env, check=False)
    if res.returncode != 0 and not allow_fail:
        raise RuntimeError(f"Command failed ({res.returncode}): {' '.join(cmd)}")
    return res.returncode


def fetch_json(url: str, timeout: float = 30.0) -> dict[str, Any]:
    req = request.Request(url, method="GET")
    with request.urlopen(req, timeout=timeout) as resp:
        payload = resp.read().decode("utf-8", errors="replace")
    return json.loads(payload)


def wait_for_health(base_url: str, startup_timeout: float, poll_interval: float, request_timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + startup_timeout
    url = f"{base_url.rstrip('/')}/healthz"
    last_err = ""

    while time.monotonic() < deadline:
        try:
            data = fetch_json(url, timeout=request_timeout)
            if data.get("ok"):
                return data
            last_err = f"health ok=false: {data}"
        except Exception as exc:
            last_err = str(exc)

        print(f"[health-wait] not ready yet; retrying in {poll_interval:.1f}s ({last_err[:180]})")
        time.sleep(poll_interval)

    raise TimeoutError(
        f"Timed out waiting for health at {url} after {startup_timeout:.0f}s. Last error: {last_err}"
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in rows if r.get("success")]
    ttfts = sorted(float(r.get("ttft_ms", -1.0)) for r in ok if float(r.get("ttft_ms", -1.0)) >= 0.0)
    total_wall = max((float(r.get("arrival_time", 0.0)) for r in rows), default=0.0)
    total_tokens = sum(int(r.get("output_tokens", 0)) for r in ok)

    return {
        "rows": len(rows),
        "ok": len(ok),
        "throughput_tok_per_sec": total_tokens / max(total_wall, 1e-9),
        "ttft_p50_ms": percentile(ttfts, 0.50),
        "ttft_p95_ms": percentile(ttfts, 0.95),
        "ttft_p99_ms": percentile(ttfts, 0.99),
    }


def summarize_jsonl(path: Path) -> dict[str, Any]:
    return summarize_rows(read_jsonl(path))


def read_aimd_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("records", []) if isinstance(payload, dict) else []


def detect_sawtooth(records: list[dict[str, Any]]) -> dict[str, Any]:
    q_values = [float(r.get("Q")) for r in records if r.get("Q") is not None]
    deltas = [q_values[i] - q_values[i - 1] for i in range(1, len(q_values))]
    dirs = [1 if d > 0 else -1 for d in deltas if d != 0]
    direction_changes = sum(1 for i in range(1, len(dirs)) if dirs[i] != dirs[i - 1])
    has_up = any(d > 0 for d in deltas)
    has_down = any(d < 0 for d in deltas)
    sawtooth_like = has_up and has_down and direction_changes >= 1

    return {
        "num_updates": len(q_values),
        "q_min": min(q_values) if q_values else None,
        "q_max": max(q_values) if q_values else None,
        "has_up": has_up,
        "has_down": has_down,
        "direction_changes": direction_changes,
        "sawtooth_like": sawtooth_like,
    }


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return float("nan")


def _stitch_time_series(times: list[float]) -> list[float]:
    """Stitch per-phase time series that may reset to 0 between phases."""
    stitched: list[float] = []
    offset = 0.0
    prev = None
    for t in times:
        if math.isnan(t):
            stitched.append(float("nan"))
            continue
        if prev is not None and t < prev:
            offset += prev
        stitched_t = t + offset
        stitched.append(stitched_t)
        prev = t
    return stitched


def _rolling_mean(values: list[float], window: int) -> list[float]:
    out: list[float] = []
    for i in range(len(values)):
        left = max(0, i - window + 1)
        chunk = values[left : i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def _extract_phase_summaries(case: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    aimd_path = Path(case["aimd_run"])
    if not aimd_path.exists():
        return {}, {}
    try:
        payload = json.loads(aimd_path.read_text(encoding="utf-8"))
    except Exception:
        return {}, {}
    if not isinstance(payload, dict):
        return {}, {}
    phase_a = payload.get("phase_a", {})
    phase_b = payload.get("phase_b", {})
    return phase_a.get("summary", {}) if isinstance(phase_a, dict) else {}, phase_b.get("summary", {}) if isinstance(phase_b, dict) else {}


def plot_case_figure(case: dict[str, Any], output_dir: Path, dpi: int) -> Path | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[plot] matplotlib unavailable; skipping case plot for {case['label']}: {exc}")
        return None

    label = str(case["label"])
    rows = read_jsonl(Path(case["jsonl"]))
    aimd_records = read_aimd_records(Path(case["aimd_run"]))

    fig, axes = plt.subplots(3, 2, figsize=(15, 13), dpi=dpi)
    ax_q, ax_aimd, ax_q_ttft, ax_ttft, ax_thr, ax_ttft_hist = axes.ravel()

    if aimd_records:
        q_vals = [_safe_float(r.get("Q")) for r in aimd_records]
        t_vals = [_safe_float(r.get("t")) for r in aimd_records]
        if all(math.isnan(v) for v in t_vals):
            x_vals = [float(i) for i in range(1, len(q_vals) + 1)]
            ax_q.set_xlabel("AIMD Update Index")
            ax_aimd.set_xlabel("AIMD Update Index")
        else:
            t0 = next((v for v in t_vals if not math.isnan(v)), 0.0)
            x_vals = [0.0 if math.isnan(v) else (v - t0) for v in t_vals]
            ax_q.set_xlabel("Time Since First AIMD Update (s)")
            ax_aimd.set_xlabel("Time Since First AIMD Update (s)")

        ax_q.plot(x_vals, q_vals, color="tab:blue", linewidth=2, label="Q")
        violated_x = [x_vals[i] for i, r in enumerate(aimd_records) if bool(r.get("violated"))]
        violated_q = [q_vals[i] for i, r in enumerate(aimd_records) if bool(r.get("violated"))]
        if violated_x:
            ax_q.scatter(violated_x, violated_q, color="tab:red", s=16, label="Violation", alpha=0.8)

        saw = detect_sawtooth(aimd_records)
        ax_q.set_title(f"{label.upper()} Q Trajectory")
        ax_q.set_ylabel("Q")
        ax_q.grid(True, alpha=0.3)
        ax_q.legend(loc="best")
        ax_q.text(
            0.01,
            0.02,
            (
                f"q_min={saw.get('q_min')}  q_max={saw.get('q_max')}\n"
                f"up={saw.get('has_up')}  down={saw.get('has_down')}  changes={saw.get('direction_changes')}"
            ),
            transform=ax_q.transAxes,
            fontsize=9,
            bbox={"facecolor": "white", "alpha": 0.7, "edgecolor": "none"},
        )

        jain_vals = [_safe_float(r.get("jain")) for r in aimd_records]
        p99_vals = [_safe_float(r.get("p99_ttft_ms")) for r in aimd_records]
        ln1 = ax_aimd.plot(x_vals, jain_vals, color="tab:green", linewidth=2, label="AIMD Jain")
        try:
            threshold = float(case["jain_threshold"])
            ax_aimd.axhline(threshold, color="tab:green", linestyle="--", alpha=0.6, label="Jain Threshold")
        except Exception:
            pass
        ax_aimd.set_ylabel("Jain")
        ax_aimd.set_title(f"{label.upper()} AIMD Signals")
        ax_aimd.grid(True, alpha=0.3)

        ax_aimd_right = ax_aimd.twinx()
        ln2 = ax_aimd_right.plot(
            x_vals,
            p99_vals,
            color="tab:orange",
            linewidth=1.8,
            label="AIMD p99_ttft_ms",
        )
        ax_aimd_right.set_ylabel("AIMD p99_ttft_ms")
        lines = ln1 + ln2
        labels = [ln.get_label() for ln in lines]
        ax_aimd.legend(lines, labels, loc="best")

        scatter_points: list[tuple[float, float, bool]] = []
        for i, q in enumerate(q_vals):
            p99 = p99_vals[i] if i < len(p99_vals) else float("nan")
            if math.isnan(q) or math.isnan(p99):
                continue
            scatter_points.append((q, p99, bool(aimd_records[i].get("violated"))))

        viol_q = [q for q, p99, violated in scatter_points if violated]
        viol_p99 = [p99 for q, p99, violated in scatter_points if violated]
        ok_q = [q for q, p99, violated in scatter_points if not violated]
        ok_p99 = [p99 for q, p99, violated in scatter_points if not violated]

        if ok_q:
            ax_q_ttft.scatter(ok_q, ok_p99, color="tab:blue", alpha=0.7, s=26, label="No violation")
        if viol_q:
            ax_q_ttft.scatter(viol_q, viol_p99, color="tab:red", alpha=0.8, s=30, label="Violation")
        if scatter_points:
            ax_q_ttft.set_title(f"{label.upper()} Q vs AIMD p99 TTFT")
            ax_q_ttft.set_xlabel("Q")
            ax_q_ttft.set_ylabel("AIMD p99_ttft_ms")
            ax_q_ttft.grid(True, alpha=0.3)
            ax_q_ttft.legend(loc="best")
        else:
            ax_q_ttft.set_title(f"{label.upper()} Q vs AIMD p99 TTFT")
            ax_q_ttft.text(0.5, 0.5, "No valid Q/p99 points", ha="center", va="center")
    else:
        ax_q.set_title(f"{label.upper()} Q Trajectory")
        ax_q.text(0.5, 0.5, "No AIMD records", ha="center", va="center")
        ax_aimd.set_title(f"{label.upper()} AIMD Signals")
        ax_aimd.text(0.5, 0.5, "No AIMD records", ha="center", va="center")
        ax_q_ttft.set_title(f"{label.upper()} Q vs AIMD p99 TTFT")
        ax_q_ttft.text(0.5, 0.5, "No AIMD records", ha="center", va="center")

    ok_rows = [r for r in rows if r.get("success")]
    ttft_vals = [_safe_float(r.get("ttft_ms")) for r in ok_rows]
    ttft_vals = [v for v in ttft_vals if not math.isnan(v)]
    if ttft_vals:
        req_idx = list(range(1, len(ttft_vals) + 1))
        roll = _rolling_mean(ttft_vals, window=min(10, len(ttft_vals)))
        ax_ttft.plot(req_idx, ttft_vals, color="tab:purple", alpha=0.35, linewidth=1, label="Per-request TTFT")
        ax_ttft.plot(req_idx, roll, color="tab:purple", linewidth=2.2, label="Rolling mean")
        p50 = percentile(sorted(ttft_vals), 0.50)
        p99 = percentile(sorted(ttft_vals), 0.99)
        ax_ttft.axhline(p50, color="tab:gray", linestyle="--", alpha=0.6, label=f"P50={p50:.1f} ms")
        ax_ttft.axhline(p99, color="tab:red", linestyle=":", alpha=0.6, label=f"P99={p99:.1f} ms")
        ax_ttft.set_title(f"{label.upper()} TTFT")
        ax_ttft.set_xlabel("Successful Request Index")
        ax_ttft.set_ylabel("TTFT (ms)")
        ax_ttft.grid(True, alpha=0.3)
        ax_ttft.legend(loc="best")
    else:
        ax_ttft.set_title(f"{label.upper()} TTFT")
        ax_ttft.text(0.5, 0.5, "No TTFT samples", ha="center", va="center")

    if ttft_vals:
        bins = min(30, max(8, len(ttft_vals) // 5))
        ax_ttft_hist.hist(ttft_vals, bins=bins, color="tab:purple", alpha=0.75)
        ax_ttft_hist.set_title(f"{label.upper()} TTFT Distribution")
        ax_ttft_hist.set_xlabel("TTFT (ms)")
        ax_ttft_hist.set_ylabel("Count")
        ax_ttft_hist.grid(True, axis="y", alpha=0.3)
    else:
        ax_ttft_hist.set_title(f"{label.upper()} TTFT Distribution")
        ax_ttft_hist.text(0.5, 0.5, "No TTFT samples", ha="center", va="center")

    if ok_rows:
        arrival_vals = [_safe_float(r.get("arrival_time")) for r in ok_rows]
        stitched_arrival = _stitch_time_series(arrival_vals)
        output_tokens = [int(r.get("output_tokens", 0)) for r in ok_rows]
        cum_tokens = 0
        cumulative_thr: list[float] = []
        req_idx = list(range(1, len(ok_rows) + 1))
        for t, tok in zip(stitched_arrival, output_tokens):
            cum_tokens += tok
            denom = t if not math.isnan(t) and t > 1e-9 else len(cumulative_thr) + 1.0
            cumulative_thr.append(cum_tokens / denom)

        ax_thr.plot(req_idx, cumulative_thr, color="tab:cyan", linewidth=2, label="Cumulative throughput")
        ax_thr.set_title(f"{label.upper()} Throughput Trend")
        ax_thr.set_xlabel("Successful Request Index")
        ax_thr.set_ylabel("Tokens/sec")
        ax_thr.grid(True, alpha=0.3)
        ax_thr.legend(loc="best")
    else:
        ax_thr.set_title(f"{label.upper()} Throughput Trend")
        ax_thr.text(0.5, 0.5, "No throughput samples", ha="center", va="center")

    fig.tight_layout()
    out_path = output_dir / f"plot_{label}_v2.png"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_ab_comparison(strict: dict[str, Any], relaxed: dict[str, Any], output_dir: Path, dpi: int) -> Path | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[plot] matplotlib unavailable; skipping comparison plot: {exc}")
        return None

    strict_summary = strict.get("summary", {})
    relaxed_summary = relaxed.get("summary", {})

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), dpi=dpi)
    ax_thr, ax_p50, ax_p99, ax_phase = axes.ravel()

    labels = ["strict", "relaxed"]
    thr_vals = [_safe_float(strict_summary.get("throughput_tok_per_sec")), _safe_float(relaxed_summary.get("throughput_tok_per_sec"))]
    p50_vals = [_safe_float(strict_summary.get("ttft_p50_ms")), _safe_float(relaxed_summary.get("ttft_p50_ms"))]
    p99_vals = [_safe_float(strict_summary.get("ttft_p99_ms")), _safe_float(relaxed_summary.get("ttft_p99_ms"))]

    ax_thr.bar(labels, thr_vals, color=["tab:blue", "tab:orange"])
    ax_thr.set_title("Overall Throughput")
    ax_thr.set_ylabel("Tokens/sec")
    ax_thr.grid(True, axis="y", alpha=0.3)

    ax_p50.bar(labels, p50_vals, color=["tab:blue", "tab:orange"])
    ax_p50.set_title("Overall TTFT P50")
    ax_p50.set_ylabel("ms")
    ax_p50.grid(True, axis="y", alpha=0.3)

    ax_p99.bar(labels, p99_vals, color=["tab:blue", "tab:orange"])
    ax_p99.set_title("Overall TTFT P99")
    ax_p99.set_ylabel("ms")
    ax_p99.grid(True, axis="y", alpha=0.3)

    strict_a, strict_b = _extract_phase_summaries(strict)
    relaxed_a, relaxed_b = _extract_phase_summaries(relaxed)
    phase_names = ["A", "B"]
    strict_phase_p99 = [_safe_float(strict_a.get("ttft_p99_ms")), _safe_float(strict_b.get("ttft_p99_ms"))]
    relaxed_phase_p99 = [_safe_float(relaxed_a.get("ttft_p99_ms")), _safe_float(relaxed_b.get("ttft_p99_ms"))]
    x = [0, 1]
    w = 0.38
    ax_phase.bar([v - w / 2 for v in x], strict_phase_p99, width=w, label="strict", color="tab:blue")
    ax_phase.bar([v + w / 2 for v in x], relaxed_phase_p99, width=w, label="relaxed", color="tab:orange")
    ax_phase.set_xticks(x, phase_names)
    ax_phase.set_title("Phase TTFT P99")
    ax_phase.set_ylabel("ms")
    ax_phase.grid(True, axis="y", alpha=0.3)
    ax_phase.legend(loc="best")

    fig.tight_layout()
    out_path = output_dir / "plot_ab_compare_v2.png"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


def generate_plots(strict: dict[str, Any], relaxed: dict[str, Any], args: argparse.Namespace) -> list[Path]:
    out: list[Path] = []
    strict_plot = plot_case_figure(strict, args.output_dir, args.plot_dpi)
    if strict_plot:
        out.append(strict_plot)
    relaxed_plot = plot_case_figure(relaxed, args.output_dir, args.plot_dpi)
    if relaxed_plot:
        out.append(relaxed_plot)
    compare_plot = plot_ab_comparison(strict, relaxed, args.output_dir, args.plot_dpi)
    if compare_plot:
        out.append(compare_plot)
    return out


def load_existing_case(label: str, jain_threshold: str, args: argparse.Namespace) -> dict[str, Any]:
    jsonl_path = args.output_dir / f"probe_{label}_jain_v2.jsonl"
    aimd_run_path = args.output_dir / f"probe_{label}_jain_v2_aimd_run.json"
    aimd_tail_path = args.output_dir / f"aimd_{label}_tail_v2.json"

    if not jsonl_path.exists():
        raise FileNotFoundError(f"Missing existing artifact: {jsonl_path}")
    if not aimd_run_path.exists():
        raise FileNotFoundError(f"Missing existing artifact: {aimd_run_path}")

    return {
        "label": label,
        "jain_threshold": jain_threshold,
        "health": {},
        "summary": summarize_jsonl(jsonl_path),
        "sawtooth": detect_sawtooth(read_aimd_records(aimd_run_path)),
        "warmup_jsonl": "",
        "jsonl": str(jsonl_path),
        "aimd_run": str(aimd_run_path),
        "aimd_tail": str(aimd_tail_path),
    }


def run_warmup(label: str, args: argparse.Namespace) -> Path:
    """Issue a small synthetic load to warm model/container before measured probe."""
    warmup_out = args.output_dir / f"warmup_{label}_v2.jsonl"
    warmup_cmd = [
        sys.executable,
        "-m",
        "workload.client",
        "--server",
        args.server,
        "--dataset",
        "synthetic",
        "--arrival-mode",
        args.arrival_mode,
        "--rate",
        str(args.warmup_rate),
        "--k",
        str(args.warmup_k),
        "--policy",
        "adaptive_dlpm",
        "--timeout",
        str(args.warmup_timeout),
        "--max-concurrency",
        str(args.warmup_max_concurrency),
        "--dominant-reqs",
        str(args.warmup_dominant_reqs),
        "--cold-reqs",
        str(args.warmup_cold_reqs),
        "--seed",
        str(args.seed),
        "--output",
        str(warmup_out),
    ]
    run_cmd(warmup_cmd)
    return warmup_out


def run_probe(
    label: str,
    suffix: str,
    args: argparse.Namespace,
    rate: float,
    k: float,
    dominant_reqs: int,
    cold_reqs: int,
) -> tuple[Path, Path, dict[str, Any]]:
    out_jsonl = args.output_dir / f"probe_{label}_{suffix}_v2.jsonl"
    out_aimd_run = args.output_dir / f"probe_{label}_{suffix}_v2_aimd_run.json"

    probe_cmd = [
        sys.executable,
        "probe_aimd_runtime.py",
        "--server",
        args.server,
        "--rate",
        str(rate),
        "--k",
        str(k),
        "--dominant-reqs",
        str(dominant_reqs),
        "--cold-reqs",
        str(cold_reqs),
        "--arrival-mode",
        args.arrival_mode,
        "--max-concurrency",
        str(args.max_concurrency),
        "--timeout",
        str(args.timeout),
        "--seed",
        str(args.seed),
        "--output",
        str(out_jsonl),
        "--aimd-output",
        str(out_aimd_run),
    ]
    run_cmd(probe_cmd)
    return out_jsonl, out_aimd_run, summarize_jsonl(out_jsonl)


def run_case(
    label: str,
    jain_threshold: str,
    args: argparse.Namespace,
    base_env: dict[str, str],
) -> dict[str, Any]:
    print(f"\n=== CASE: {label.upper()} (AIMD_JAIN_THRESHOLD={jain_threshold}) ===")

    env = base_env.copy()
    env["AIMD_JAIN_THRESHOLD"] = jain_threshold

    run_cmd([sys.executable, "-m", "modal", "app", "stop", args.app_name], allow_fail=True)

    run_cmd(
        [sys.executable, "-m", "modal", "deploy", "run_modal_service.py", "--name", args.app_name],
        env=env,
    )

    health = wait_for_health(
        base_url=args.server,
        startup_timeout=args.startup_timeout,
        poll_interval=args.health_poll_interval,
        request_timeout=args.health_request_timeout,
    )
    print("health:", health)

    warmup_out = None
    if args.enable_warmup:
        print(
            "[warmup] Running pre-probe warmup "
            f"(dominant={args.warmup_dominant_reqs}, cold={args.warmup_cold_reqs}, "
            f"rate={args.warmup_rate}, k={args.warmup_k})"
        )
        warmup_out = run_warmup(label=label, args=args)
        print("[warmup] output:", warmup_out)

    out_jsonl = args.output_dir / f"probe_{label}_jain_v2.jsonl"
    out_aimd_run = args.output_dir / f"probe_{label}_jain_v2_aimd_run.json"

    sawtooth: dict[str, Any] = {}

    if args.enable_two_phase_sawtooth:
        print(
            "[probe] Two-phase run enabled: "
            f"A(rate={args.phase_a_rate},k={args.phase_a_k},n={args.phase_a_dominant_reqs + args.phase_a_cold_reqs}) -> "
            f"B(rate={args.phase_b_rate},k={args.phase_b_k},n={args.phase_b_dominant_reqs + args.phase_b_cold_reqs})"
        )

        phase_a_jsonl, phase_a_aimd, phase_a_summary = run_probe(
            label=label,
            suffix="phase_a",
            args=args,
            rate=args.phase_a_rate,
            k=args.phase_a_k,
            dominant_reqs=args.phase_a_dominant_reqs,
            cold_reqs=args.phase_a_cold_reqs,
        )
        phase_b_jsonl, phase_b_aimd, phase_b_summary = run_probe(
            label=label,
            suffix="phase_b",
            args=args,
            rate=args.phase_b_rate,
            k=args.phase_b_k,
            dominant_reqs=args.phase_b_dominant_reqs,
            cold_reqs=args.phase_b_cold_reqs,
        )

        combined_rows = read_jsonl(phase_a_jsonl) + read_jsonl(phase_b_jsonl)
        with out_jsonl.open("w", encoding="utf-8") as f:
            for row in combined_rows:
                f.write(json.dumps(row) + "\n")

        phase_a_records = read_aimd_records(phase_a_aimd)
        phase_b_records = read_aimd_records(phase_b_aimd)
        combined_records = phase_a_records + phase_b_records
        sawtooth = detect_sawtooth(combined_records)

        out_aimd_payload = {
            "mode": "two-phase",
            "phase_a": {
                "params": {
                    "rate": args.phase_a_rate,
                    "k": args.phase_a_k,
                    "dominant_reqs": args.phase_a_dominant_reqs,
                    "cold_reqs": args.phase_a_cold_reqs,
                },
                "summary": phase_a_summary,
                "records": phase_a_records,
            },
            "phase_b": {
                "params": {
                    "rate": args.phase_b_rate,
                    "k": args.phase_b_k,
                    "dominant_reqs": args.phase_b_dominant_reqs,
                    "cold_reqs": args.phase_b_cold_reqs,
                },
                "summary": phase_b_summary,
                "records": phase_b_records,
            },
            "sawtooth": sawtooth,
            "records": combined_records,
        }
        out_aimd_run.write_text(json.dumps(out_aimd_payload, indent=2), encoding="utf-8")
        summary = summarize_rows(combined_rows)

        print("phase A summary:", {k: round(v, 3) if isinstance(v, float) else v for k, v in phase_a_summary.items()})
        print("phase B summary:", {k: round(v, 3) if isinstance(v, float) else v for k, v in phase_b_summary.items()})
        print("sawtooth analysis:", sawtooth)
    else:
        phase_jsonl, phase_aimd, _ = run_probe(
            label=label,
            suffix="single",
            args=args,
            rate=args.rate,
            k=args.k,
            dominant_reqs=args.dominant_reqs,
            cold_reqs=args.cold_reqs,
        )
        combined_rows = read_jsonl(phase_jsonl)
        with out_jsonl.open("w", encoding="utf-8") as f:
            for row in combined_rows:
                f.write(json.dumps(row) + "\n")
        out_aimd_run.write_text(Path(phase_aimd).read_text(encoding="utf-8"), encoding="utf-8")
        sawtooth = detect_sawtooth(read_aimd_records(Path(phase_aimd)))
        summary = summarize_rows(combined_rows)

    aimd_tail = fetch_json(
        f"{args.server.rstrip('/')}/aimd?limit={args.aimd_limit}",
        timeout=max(30.0, args.health_request_timeout),
    )
    out_aimd_tail = args.output_dir / f"aimd_{label}_tail_v2.json"
    out_aimd_tail.write_text(json.dumps(aimd_tail, indent=2), encoding="utf-8")

    print("summary:", {k: round(v, 3) if isinstance(v, float) else v for k, v in summary.items()})
    print("probe output:", out_jsonl)
    print("aimd run trace:", out_aimd_run)
    print("aimd tail snapshot:", out_aimd_tail)

    return {
        "label": label,
        "jain_threshold": jain_threshold,
        "health": health,
        "summary": summary,
        "sawtooth": sawtooth,
        "warmup_jsonl": str(warmup_out) if warmup_out else "",
        "jsonl": str(out_jsonl),
        "aimd_run": str(out_aimd_run),
        "aimd_tail": str(out_aimd_tail),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run strict vs relaxed AIMD probe A/B test (v2)")
    parser.add_argument("--server", required=True, help="Modal endpoint URL (https://...modal.run)")
    parser.add_argument("--app-name", default="adaptive-dlpm-scheduler-service")
    parser.add_argument("--output-dir", default="results")

    parser.add_argument("--rate", type=float, default=2.0)
    parser.add_argument("--k", type=float, default=0.5)
    parser.add_argument("--dominant-reqs", type=int, default=30)
    parser.add_argument("--cold-reqs", type=int, default=20)
    parser.add_argument("--arrival-mode", choices=["global", "per-client"], default="per-client")
    parser.add_argument("--max-concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--aimd-limit", type=int, default=200)
    parser.add_argument(
        "--startup-timeout",
        type=float,
        default=900.0,
        help="Seconds to wait for /healthz after each deploy.",
    )
    parser.add_argument(
        "--health-poll-interval",
        type=float,
        default=5.0,
        help="Polling interval (seconds) for /healthz readiness checks.",
    )
    parser.add_argument(
        "--health-request-timeout",
        type=float,
        default=30.0,
        help="Per-request timeout (seconds) for health checks.",
    )

    parser.add_argument("--strict-jain-threshold", default="0.95")
    parser.add_argument("--relaxed-jain-threshold", default="0.50")

    parser.add_argument(
        "--disable-two-phase-sawtooth",
        action="store_true",
        help="Run a single measured probe per case instead of the two-phase sawtooth test.",
    )
    parser.add_argument("--phase-a-rate", type=float, default=1.0)
    parser.add_argument("--phase-a-k", type=float, default=1.0)
    parser.add_argument("--phase-a-dominant-reqs", type=int, default=60)
    parser.add_argument("--phase-a-cold-reqs", type=int, default=40)
    parser.add_argument("--phase-b-rate", type=float, default=3.0)
    parser.add_argument("--phase-b-k", type=float, default=0.5)
    parser.add_argument("--phase-b-dominant-reqs", type=int, default=60)
    parser.add_argument("--phase-b-cold-reqs", type=int, default=40)

    parser.add_argument(
        "--disable-warmup",
        action="store_true",
        help="Disable pre-probe warmup load.",
    )
    parser.add_argument("--warmup-dominant-reqs", type=int, default=2)
    parser.add_argument("--warmup-cold-reqs", type=int, default=2)
    parser.add_argument("--warmup-rate", type=float, default=1.0)
    parser.add_argument("--warmup-k", type=float, default=1.0)
    parser.add_argument("--warmup-max-concurrency", type=int, default=2)
    parser.add_argument("--warmup-timeout", type=float, default=300.0)

    parser.add_argument(
        "--disable-plots",
        action="store_true",
        help="Disable generation of matplotlib PNG charts at the end of the run.",
    )
    parser.add_argument(
        "--plot-dpi",
        type=int,
        default=140,
        help="DPI for generated plot PNGs.",
    )
    parser.add_argument(
        "--plot-only",
        action="store_true",
        help="Generate plots from existing results artifacts and skip deploy/probe execution.",
    )

    # Shared AIMD/deploy settings to keep A/B comparison controlled.
    parser.add_argument("--dummy-weight", default="1")
    parser.add_argument("--control-interval", default="5")
    parser.add_argument("--q-init", default="4000")
    parser.add_argument("--q-min", default="1200")
    parser.add_argument("--q-max", default="16000")
    parser.add_argument("--additive-step", default="250")
    parser.add_argument("--mult-factor", default="0.7")
    parser.add_argument("--ttft-slo-ms", default="900")
    parser.add_argument("--telemetry-window", default="60")
    parser.add_argument("--aimd-debug-log-path", default="/tmp/minisgl_aimd_history.jsonl")

    args = parser.parse_args()
    args.enable_warmup = not args.disable_warmup
    args.enable_two_phase_sawtooth = not args.disable_two_phase_sawtooth
    args.enable_plots = not args.disable_plots
    args.output_dir = Path(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.plot_only:
        if not args.enable_plots:
            raise SystemExit("--plot-only requires plots to be enabled. Remove --disable-plots.")

        strict = load_existing_case("strict", args.strict_jain_threshold, args)
        relaxed = load_existing_case("relaxed", args.relaxed_jain_threshold, args)

        print("\n=== PLOT-ONLY MODE (v2) ===")
        print("strict summary:", {k: round(v, 3) if isinstance(v, float) else v for k, v in strict["summary"].items()})
        print("relaxed summary:", {k: round(v, 3) if isinstance(v, float) else v for k, v in relaxed["summary"].items()})

        plot_paths = generate_plots(strict, relaxed, args)
        if plot_paths:
            print("\n=== PLOTS GENERATED ===")
            for path in plot_paths:
                print(path)
            return 0

        raise SystemExit("No plots were generated. Check matplotlib installation and artifact files.")

    expected_fragment = f"--{args.app_name}-hosted-minisgl-app.modal.run"
    if expected_fragment not in args.server:
        raise SystemExit(
            "Server URL does not match app name. "
            f"Expected URL containing '{expected_fragment}', got '{args.server}'."
        )

    base_env = os.environ.copy()
    base_env.update(
        {
            "MODAL_MINISGL_POLICY": "adaptive_dlpm",
            "MODAL_MINISGL_DUMMY_WEIGHT": args.dummy_weight,
            "AIMD_CONTROL_INTERVAL": args.control_interval,
            "AIMD_Q_INIT": args.q_init,
            "AIMD_Q_MIN": args.q_min,
            "AIMD_Q_MAX": args.q_max,
            "AIMD_ADDITIVE_STEP": args.additive_step,
            "AIMD_MULT_FACTOR": args.mult_factor,
            "AIMD_TTFT_SLO_MS": args.ttft_slo_ms,
            "MINISGL_TELEMETRY_WINDOW": args.telemetry_window,
            "AIMD_DEBUG_LOG_PATH": args.aimd_debug_log_path,
        }
    )

    strict = run_case("strict", args.strict_jain_threshold, args, base_env)
    relaxed = run_case("relaxed", args.relaxed_jain_threshold, args, base_env)

    print("\n=== A/B COMPLETE (v2) ===")
    print("strict summary:", {k: round(v, 3) if isinstance(v, float) else v for k, v in strict["summary"].items()})
    print("relaxed summary:", {k: round(v, 3) if isinstance(v, float) else v for k, v in relaxed["summary"].items()})

    try:
        strict_saw = json.loads(Path(strict["aimd_run"]).read_text(encoding="utf-8")).get("sawtooth", {})
        relaxed_saw = json.loads(Path(relaxed["aimd_run"]).read_text(encoding="utf-8")).get("sawtooth", {})
        if strict_saw or relaxed_saw:
            print("strict sawtooth:", strict_saw)
            print("relaxed sawtooth:", relaxed_saw)
    except Exception:
        pass

    if args.enable_plots:
        plot_paths = generate_plots(strict, relaxed, args)
        if plot_paths:
            print("\n=== PLOTS GENERATED ===")
            for path in plot_paths:
                print(path)
        else:
            print("\n=== PLOTS SKIPPED ===")
            print("No plots were generated (matplotlib may be unavailable or no data found).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
