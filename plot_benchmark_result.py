"""
Plot and summarize benchmark outputs from benchmark_modal_service_grid.py.

This script reads a benchmark result folder (e.g. results/modal_grid_20260414_200819),
loads summary.csv, and generates several plots plus a short textual summary.

Usage:
    python plot_benchmark_result.py results/modal_grid_20260414_200819

    # You can also pass just the folder name under results/
    python plot_benchmark_result.py modal_grid_20260414_200819

    # Custom output directory / prefix
    python plot_benchmark_result.py modal_grid_20260414_200819 --output-dir docs/plots --prefix baseline_fcfs_lpm
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


def resolve_input_folder(folder_arg: str) -> Path:
    p = Path(folder_arg)
    candidates = [p, Path("results") / folder_arg]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        f"Could not find benchmark folder '{folder_arg}'. Tried: "
        + ", ".join(str(c) for c in candidates)
    )


def fix_policy_label(policy: str, output_file: str) -> str:
    """Split static DLPM rows by Q value encoded in their run filename."""
    if str(policy) == "dlpm":
        m = re.search(r"dlpm_q(\d+)_", Path(str(output_file)).name)
        if m:
            return f"dlpm_q{m.group(1)}"
    return str(policy)


def load_summary_csv(folder: Path):
    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: pandas. Use your project venv, e.g. 'venv\\Scripts\\python.exe plot_benchmark_result.py ...'"
        ) from exc

    summary_csv = folder / "summary.csv"
    if not summary_csv.exists():
        raise FileNotFoundError(f"Missing file: {summary_csv}")

    df = pd.read_csv(summary_csv)
    required_cols = {
        "policy",
        "rate",
        "k",
        "request_count",
        "throughput_tok_per_sec",
        "ttft_p50_ms",
        "ttft_p99_ms",
        "success_rate",
    }
    missing = sorted(required_cols - set(df.columns))
    if missing:
        raise ValueError(f"summary.csv is missing required columns: {missing}")

    if "output_file" in df.columns:
        df["policy"] = [
            fix_policy_label(policy, output_file)
            for policy, output_file in zip(df["policy"], df["output_file"])
        ]

    # Ensure numeric columns are numeric for sorting/plotting.
    numeric_cols = [
        "rate",
        "k",
        "request_count",
        "throughput_tok_per_sec",
        "ttft_p50_ms",
        "ttft_p99_ms",
        "success_rate",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def resolve_output_jsonl_path(folder: Path, output_file: str) -> Path | None:
    if not output_file:
        return None

    raw = str(output_file).strip()
    normalized = raw.replace("\\", "/")
    base_name = Path(normalized).name

    candidates = [
        Path(raw),
        Path(normalized),
        folder / raw,
        folder / normalized,
        folder / base_name,
        folder / "runs" / base_name,
        Path.cwd() / raw,
        Path.cwd() / normalized,
    ]

    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def load_request_logs(df, folder: Path):
    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: pandas. Use your project venv, e.g. 'venv\\Scripts\\python.exe plot_benchmark_result.py ...'"
        ) from exc

    if "output_file" not in df.columns:
        return pd.DataFrame()

    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        run_path = resolve_output_jsonl_path(folder, str(row.get("output_file", "")))
        if run_path is None:
            continue

        try:
            with run_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    payload = json.loads(line)
                    payload["run_file"] = str(run_path)
                    payload["run_name"] = run_path.name
                    payload["policy"] = row.get("policy", payload.get("policy", ""))
                    payload["rate"] = row.get("rate")
                    payload["k"] = row.get("k")
                    payload["request_count"] = row.get("request_count")
                    records.append(payload)
        except (OSError, json.JSONDecodeError):
            continue

    if not records:
        return pd.DataFrame()

    req_df = pd.DataFrame.from_records(records)

    numeric_cols = [
        "arrival_time",
        "ttft_ms",
        "tpot_ms",
        "prompt_len",
        "output_tokens",
        "cached_len",
        "Q_at_scheduling",
        "jain_control",
        "jain_prompt",
        "p99_ttft_window_ms",
        "aimd_step",
        "rate",
        "k",
        "request_count",
    ]
    for col in numeric_cols:
        if col not in req_df.columns:
            req_df[col] = float("nan")
        req_df[col] = pd.to_numeric(req_df[col], errors="coerce")

    if "success" in req_df.columns:
        req_df["success"] = req_df["success"].apply(_as_bool)
    else:
        req_df["success"] = False

    if "aimd_violated" in req_df.columns:
        req_df["aimd_violated"] = req_df["aimd_violated"].apply(_as_bool)
    else:
        req_df["aimd_violated"] = False

    if "aimd_violation_reason" not in req_df.columns:
        req_df["aimd_violation_reason"] = ""

    req_df = req_df.sort_values(["run_file", "arrival_time"], kind="stable")
    req_df["request_idx"] = req_df.groupby("run_file").cumcount() + 1

    return req_df


def plot_metric_vs_rate(df, metric: str, ylabel: str, title: str, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    policies = sorted(df["policy"].dropna().unique())
    ks = sorted(df["k"].dropna().unique())
    request_counts = sorted(df["request_count"].dropna().unique())

    color_map = {policy: f"C{i}" for i, policy in enumerate(policies)}
    marker_cycle = ["o", "s", "^", "D", "P", "X", "v"]
    marker_map = {k: marker_cycle[i % len(marker_cycle)] for i, k in enumerate(ks)}

    fig, axes = plt.subplots(1, len(request_counts), figsize=(7 * len(request_counts), 5), dpi=150)
    if len(request_counts) == 1:
        axes = [axes]

    for ax, req_count in zip(axes, request_counts):
        d_req = df[df["request_count"] == req_count]
        for policy in policies:
            for kval in ks:
                d = d_req[(d_req["policy"] == policy) & (d_req["k"] == kval)].sort_values("rate")
                if d.empty:
                    continue
                ax.plot(
                    d["rate"],
                    d[metric],
                    color=color_map[policy],
                    marker=marker_map[kval],
                    linewidth=2,
                    markersize=5,
                    label=f"{policy}, k={kval:g}",
                )

        ax.set_title(f"n={int(req_count)}")
        ax.set_xlabel("Arrival Rate (req/s)")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)

    handles, labels = axes[0].get_legend_handles_labels()
    # De-duplicate legend labels while preserving order.
    unique: dict[str, Any] = {}
    for h, l in zip(handles, labels):
        if l not in unique:
            unique[l] = h

    fig.suptitle(title)
    fig.legend(unique.values(), unique.keys(), loc="upper center", ncol=min(4, len(unique)), frameon=True)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def plot_pareto(df, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    policies = sorted(df["policy"].dropna().unique())
    request_counts = sorted(df["request_count"].dropna().unique())

    color_map = {policy: f"C{i}" for i, policy in enumerate(policies)}
    marker_cycle = ["o", "s", "^", "D", "P", "X", "v"]
    marker_map = {n: marker_cycle[i % len(marker_cycle)] for i, n in enumerate(request_counts)}

    fig, (ax_linear, ax_log) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)

    for policy in policies:
        for n in request_counts:
            d = df[(df["policy"] == policy) & (df["request_count"] == n)]
            if d.empty:
                continue
            label = f"{policy}, n={int(n)}"
            ax_linear.scatter(
                d["throughput_tok_per_sec"],
                d["ttft_p99_ms"],
                label=label,
                color=color_map[policy],
                marker=marker_map[n],
                alpha=0.8,
                s=48,
            )
            ax_log.scatter(
                d["throughput_tok_per_sec"],
                d["ttft_p99_ms"],
                label=label,
                color=color_map[policy],
                marker=marker_map[n],
                alpha=0.8,
                s=48,
            )

    # Clip linear axis to reduce outlier domination, while log panel shows full range.
    y95 = float(df["ttft_p99_ms"].quantile(0.95))
    if y95 > 0:
        ax_linear.set_ylim(0, y95 * 1.2)

    ax_linear.set_title("Throughput vs TTFT P99 (Linear Y)")
    ax_linear.set_xlabel("Throughput (tokens/sec)")
    ax_linear.set_ylabel("TTFT P99 (ms)")
    ax_linear.grid(True, alpha=0.3)

    ax_log.set_title("Throughput vs TTFT P99 (Log Y, Full Range)")
    ax_log.set_xlabel("Throughput (tokens/sec)")
    ax_log.set_ylabel("TTFT P99 (ms)")
    ax_log.set_yscale("log")
    ax_log.grid(True, alpha=0.3)

    handles, labels = ax_linear.get_legend_handles_labels()
    unique: dict[str, Any] = {}
    for h, l in zip(handles, labels):
        if l not in unique:
            unique[l] = h

    fig.legend(unique.values(), unique.keys(), loc="upper center", ncol=min(4, len(unique)), frameon=True)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def plot_ttft_percentile_histograms(df, out_path: Path) -> bool:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    policies = sorted(df["policy"].dropna().unique())
    if not policies:
        return False

    fig, (ax_p50, ax_p99) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)
    colors = {policy: f"C{i}" for i, policy in enumerate(policies)}

    has_data = False
    for policy in policies:
        p50_vals = df.loc[df["policy"] == policy, "ttft_p50_ms"].dropna().tolist()
        p99_vals = df.loc[df["policy"] == policy, "ttft_p99_ms"].dropna().tolist()

        if p50_vals:
            ax_p50.hist(p50_vals, bins=min(20, max(6, len(p50_vals))), alpha=0.45, color=colors[policy], label=policy)
            has_data = True
        if p99_vals:
            ax_p99.hist(p99_vals, bins=min(20, max(6, len(p99_vals))), alpha=0.45, color=colors[policy], label=policy)
            has_data = True

    if not has_data:
        plt.close(fig)
        return False

    ax_p50.set_title("TTFT P50 Distribution Across Runs")
    ax_p50.set_xlabel("TTFT P50 (ms)")
    ax_p50.set_ylabel("Count")
    ax_p50.grid(True, axis="y", alpha=0.3)

    ax_p99.set_title("TTFT P99 Distribution Across Runs")
    ax_p99.set_xlabel("TTFT P99 (ms)")
    ax_p99.set_ylabel("Count")
    ax_p99.grid(True, axis="y", alpha=0.3)
    ax_p99.set_xscale("log")

    handles, labels = ax_p50.get_legend_handles_labels()
    unique: dict[str, Any] = {}
    for h, l in zip(handles, labels):
        if l not in unique:
            unique[l] = h
    if unique:
        fig.legend(unique.values(), unique.keys(), loc="upper center", ncol=min(4, len(unique)), frameon=True)

    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return True


def plot_ttft_request_histograms(req_df, out_path: Path) -> bool:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if req_df.empty:
        return False

    ok = req_df[(req_df["success"] == True) & (req_df["ttft_ms"] >= 0)].copy()
    if ok.empty:
        return False

    policies = sorted(ok["policy"].dropna().unique())
    if not policies:
        return False

    policy_vals: dict[str, list[float]] = {
        policy: ok.loc[ok["policy"] == policy, "ttft_ms"].dropna().tolist() for policy in policies
    }
    all_vals = [v for vals in policy_vals.values() for v in vals]
    if not all_vals:
        return False

    global_min = float(min(all_vals))
    global_max = float(max(all_vals))
    if global_max <= global_min:
        global_max = global_min + 1.0

    bins_n = min(35, max(8, len(all_vals) // 20))
    step = (global_max - global_min) / bins_n
    bin_edges = [global_min + i * step for i in range(bins_n + 1)]

    n = len(policies)
    cols = 2
    rows = math.ceil(n / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(14, max(4 * rows, 5)), dpi=150)
    if rows == 1 and cols == 1:
        axes = [[axes]]
    elif rows == 1:
        axes = [axes]

    flat_axes = [ax for row_axes in axes for ax in row_axes]
    max_bin_count = 0.0

    for i, policy in enumerate(policies):
        ax = flat_axes[i]
        vals = policy_vals[policy]
        if not vals:
            ax.text(0.5, 0.5, "No TTFT samples", ha="center", va="center")
            ax.set_title(f"{policy} TTFT")
            continue

        counts, _, _ = ax.hist(vals, bins=bin_edges, color=f"C{i}", alpha=0.75)
        if len(counts) > 0:
            max_bin_count = max(max_bin_count, float(max(counts)))
        p50 = float(sorted(vals)[max(0, math.ceil(0.50 * len(vals)) - 1)])
        p99 = float(sorted(vals)[max(0, math.ceil(0.99 * len(vals)) - 1)])
        ax.axvline(p50, color="black", linestyle="--", linewidth=1.5, label=f"P50={p50:.1f} ms")
        ax.axvline(p99, color="red", linestyle=":", linewidth=1.5, label=f"P99={p99:.1f} ms")
        ax.set_title(f"{policy} TTFT Distribution")
        ax.set_xlabel("TTFT (ms)")
        ax.set_ylabel("Count")
        ax.grid(True, axis="y", alpha=0.3)
        ax.legend(loc="best")

    for j in range(len(policies), len(flat_axes)):
        flat_axes[j].axis("off")

    if max_bin_count <= 0:
        max_bin_count = 1.0
    for i in range(len(policies)):
        ax = flat_axes[i]
        ax.set_xlim(global_min, global_max)
        ax.set_ylim(0, max_bin_count * 1.10)

    fig.suptitle("Request-Level TTFT Histograms with P50/P99")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return True


def plot_aimd_overview(req_df, out_path: Path) -> bool:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if req_df.empty:
        return False

    adaptive = req_df[req_df["policy"] == "adaptive_dlpm"].copy()
    if adaptive.empty:
        return False

    fig, (ax_q, ax_sig) = plt.subplots(2, 1, figsize=(14, 10), dpi=150)

    run_meta = (
        adaptive.groupby("run_file", as_index=False)
        .agg(
            rows=("run_file", "count"),
            rate=("rate", "max"),
            k=("k", "max"),
            request_count=("request_count", "max"),
        )
        .sort_values(["rate", "request_count", "k", "rows"])
    )
    if run_meta.empty:
        plt.close(fig)
        return False

    run_meta = run_meta.tail(6)
    q_has_points = False
    for i, row in run_meta.iterrows():
        run_file = str(row["run_file"])
        d = adaptive[(adaptive["run_file"] == run_file) & (adaptive["Q_at_scheduling"] >= 0)].copy()
        if d.empty:
            continue
        d = d.sort_values(["arrival_time", "request_idx"], kind="stable")
        x = d["request_idx"].tolist()
        y = d["Q_at_scheduling"].tolist()
        label = f"r={row['rate']:g}, k={row['k']:g}, n={int(row['request_count'])}"
        ax_q.plot(x, y, linewidth=1.8, alpha=0.9, label=label)

        if "aimd_violated" in d.columns:
            vx = [xi for xi, v in zip(x, d["aimd_violated"].tolist()) if bool(v)]
            vy = [yi for yi, v in zip(y, d["aimd_violated"].tolist()) if bool(v)]
            if vx:
                ax_q.scatter(vx, vy, color="tab:red", s=16, alpha=0.75)
        q_has_points = True

    ax_q.set_title("Adaptive DLPM: Q Changes Over Time")
    ax_q.set_xlabel("Request Index")
    ax_q.set_ylabel("Q_at_scheduling")
    ax_q.grid(True, alpha=0.3)
    if q_has_points:
        ax_q.legend(loc="best", fontsize=9)
    else:
        ax_q.text(0.5, 0.5, "No adaptive Q samples", ha="center", va="center")

    rep = run_meta.iloc[-1]
    rep_file = str(rep["run_file"])
    rep_df = adaptive[adaptive["run_file"] == rep_file].copy().sort_values(["arrival_time", "request_idx"], kind="stable")
    x_rep = rep_df["request_idx"].tolist()

    has_signal = False
    if "jain_control" in rep_df.columns:
        y_jain = rep_df["jain_control"].tolist()
        if any(not math.isnan(v) and v >= 0 for v in y_jain):
            ax_sig.plot(x_rep, y_jain, color="tab:green", linewidth=1.8, label="jain_control")
            has_signal = True

    if "p99_ttft_window_ms" in rep_df.columns:
        y_p99w = rep_df["p99_ttft_window_ms"].tolist()
        if any(not math.isnan(v) and v >= 0 for v in y_p99w):
            ax_sig_right = ax_sig.twinx()
            ax_sig_right.plot(x_rep, y_p99w, color="tab:orange", linewidth=1.4, linestyle="--", label="p99_ttft_window_ms")
            ax_sig_right.set_ylabel("p99_ttft_window_ms")
            lines_l, labels_l = ax_sig.get_legend_handles_labels()
            lines_r, labels_r = ax_sig_right.get_legend_handles_labels()
            ax_sig.legend(lines_l + lines_r, labels_l + labels_r, loc="best")
            has_signal = True

    ax_sig.set_title(
        f"Adaptive DLPM Signals (Representative Run: r={rep['rate']:g}, k={rep['k']:g}, n={int(rep['request_count'])})"
    )
    ax_sig.set_xlabel("Request Index")
    ax_sig.set_ylabel("jain_control")
    ax_sig.grid(True, alpha=0.3)
    if not has_signal:
        ax_sig.text(0.5, 0.5, "No Jain/p99 signal samples", ha="center", va="center")
    elif not ax_sig.get_legend_handles_labels()[0]:
        ax_sig.legend(loc="best")

    fig.suptitle("Adaptive DLPM AIMD Overview")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return True


def plot_aimd_violation_reasons(req_df, out_path: Path) -> bool:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if req_df.empty or "aimd_violation_reason" not in req_df.columns:
        return False

    violated = req_df[req_df["aimd_violated"] == True].copy()
    if violated.empty:
        return False

    reason = violated["aimd_violation_reason"].fillna("unknown").astype(str).str.strip().str.lower()
    reason = reason[reason != ""]
    if reason.empty:
        return False

    counts = reason.value_counts().head(10)
    if counts.empty:
        return False

    fig, ax = plt.subplots(1, 1, figsize=(10, 5), dpi=150)
    ax.barh(list(reversed(counts.index.tolist())), list(reversed(counts.values.tolist())), color="tab:red", alpha=0.8)
    ax.set_title("Top AIMD Violation Reasons")
    ax.set_xlabel("Count")
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return True


def _slug_value(value: Any) -> str:
    text = str(value)
    out = []
    for ch in text:
        if ch.isalnum() or ch in {"-", "_", "."}:
            out.append(ch)
        else:
            out.append("_")
    return "".join(out)


def plot_all_aimd_traces(req_df, out_dir: Path, prefix: str) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if req_df.empty:
        return []

    adaptive = req_df[req_df["policy"] == "adaptive_dlpm"].copy()
    if adaptive.empty:
        return []

    grouped = (
        adaptive.groupby("run_file", as_index=False)
        .agg(rate=("rate", "max"), request_count=("request_count", "max"), k=("k", "max"), rows=("run_file", "count"))
        .sort_values(["rate", "request_count", "k", "rows"])
    )
    if grouped.empty:
        return []

    trace_paths: list[Path] = []
    trace_dir = out_dir / f"{prefix}_aimd_traces"
    trace_dir.mkdir(parents=True, exist_ok=True)

    for idx, (_, row) in enumerate(grouped.iterrows(), start=1):
        run_file = str(row["run_file"])
        d = adaptive[adaptive["run_file"] == run_file].copy().sort_values(["arrival_time", "request_idx"], kind="stable")
        if d.empty:
            continue

        fig, (ax_q, ax_sig) = plt.subplots(2, 1, figsize=(13, 8), dpi=150)

        x = d["request_idx"].tolist()
        q = d["Q_at_scheduling"].tolist() if "Q_at_scheduling" in d.columns else []
        jain = d["jain_control"].tolist() if "jain_control" in d.columns else []
        p99w = d["p99_ttft_window_ms"].tolist() if "p99_ttft_window_ms" in d.columns else []

        if q and any(not math.isnan(v) and v >= 0 for v in q):
            ax_q.plot(x, q, color="tab:blue", linewidth=1.8, label="Q_at_scheduling")
            vio_mask = d["aimd_violated"].tolist() if "aimd_violated" in d.columns else [False] * len(x)
            vio_x = [xi for xi, violated in zip(x, vio_mask) if bool(violated)]
            vio_q = [qi for qi, violated in zip(q, vio_mask) if bool(violated)]
            if vio_x:
                ax_q.scatter(vio_x, vio_q, color="tab:red", s=16, alpha=0.8, label="AIMD violation")
            ax_q.legend(loc="best")
        else:
            ax_q.text(0.5, 0.5, "No Q samples", ha="center", va="center")
        ax_q.set_title("Q changes over time")
        ax_q.set_xlabel("Request Index")
        ax_q.set_ylabel("Q")
        ax_q.grid(True, alpha=0.3)

        has_signal = False
        jain_ok = [v for v in jain if not math.isnan(v) and v >= 0]
        p99_ok = [v for v in p99w if not math.isnan(v) and v >= 0]
        if jain_ok:
            ax_sig.plot(x, jain, color="tab:green", linewidth=1.6, label="jain_control")
            has_signal = True
        if p99_ok:
            ax_sig_right = ax_sig.twinx()
            ax_sig_right.plot(x, p99w, color="tab:orange", linewidth=1.4, linestyle="--", label="p99_ttft_window_ms")
            ax_sig_right.set_ylabel("p99_ttft_window_ms")
            lines_l, labels_l = ax_sig.get_legend_handles_labels()
            lines_r, labels_r = ax_sig_right.get_legend_handles_labels()
            ax_sig.legend(lines_l + lines_r, labels_l + labels_r, loc="best")
            has_signal = True
        elif jain_ok:
            ax_sig.legend(loc="best")

        if not has_signal:
            ax_sig.text(0.5, 0.5, "No Jain/p99 window samples", ha="center", va="center")
        ax_sig.set_title("AIMD signals")
        ax_sig.set_xlabel("Request Index")
        ax_sig.set_ylabel("jain_control")
        ax_sig.grid(True, alpha=0.3)

        run_name = Path(run_file).name
        rate_slug = _slug_value(f"{row['rate']:g}")
        k_slug = _slug_value(f"{row['k']:g}")
        n_slug = _slug_value(int(row["request_count"]))
        trace_path = trace_dir / f"trace_{idx:03d}_r{rate_slug}_k{k_slug}_n{n_slug}.png"

        fig.suptitle(
            f"Adaptive AIMD Trace: {run_name} (r={row['rate']:g}, k={row['k']:g}, n={int(row['request_count'])})"
        )
        fig.tight_layout(rect=[0, 0, 1, 0.95])
        fig.savefig(trace_path, bbox_inches="tight")
        plt.close(fig)
        trace_paths.append(trace_path)

    return trace_paths


def build_summary_markdown(df, folder: Path, req_df=None) -> str:
    # Use medians (robust to outliers) plus means for context.
    med = (
        df.groupby("policy")[["throughput_tok_per_sec", "ttft_p50_ms", "ttft_p99_ms"]]
        .median()
        .round(3)
    )
    mean = (
        df.groupby("policy")[["throughput_tok_per_sec", "ttft_p50_ms", "ttft_p99_ms"]]
        .mean()
        .round(3)
    )

    best_thr = df.loc[df.groupby("policy")["throughput_tok_per_sec"].idxmax()][
        ["policy", "rate", "k", "request_count", "throughput_tok_per_sec", "ttft_p99_ms"]
    ]
    best_p99 = df.loc[df.groupby("policy")["ttft_p99_ms"].idxmin()][
        ["policy", "rate", "k", "request_count", "throughput_tok_per_sec", "ttft_p50_ms", "ttft_p99_ms"]
    ]

    high_load = (
        df[df["rate"] == df["rate"].max()]
        .groupby("policy")[["throughput_tok_per_sec", "ttft_p50_ms", "ttft_p99_ms"]]
        .median()
        .round(3)
    )

    outlier_rows = df[df["ttft_p99_ms"] > 10_000][
        ["policy", "rate", "k", "request_count", "ttft_p99_ms", "output_file"]
    ]

    lines: list[str] = []
    lines.append(f"# Benchmark Summary: {folder.name}")
    lines.append("")
    lines.append(f"Rows: {len(df)}")
    lines.append(f"Policies: {', '.join(sorted(df['policy'].dropna().unique()))}")
    lines.append("")

    lines.append("## Policy Medians")
    lines.append("```text")
    lines.append(med.to_string())
    lines.append("```")
    lines.append("")

    lines.append("## Policy Means")
    lines.append("```text")
    lines.append(mean.to_string())
    lines.append("```")
    lines.append("")

    lines.append("## Best Throughput Row Per Policy")
    lines.append("```text")
    lines.append(best_thr.to_string(index=False))
    lines.append("```")
    lines.append("")

    lines.append("## Best (Lowest) TTFT P99 Row Per Policy")
    lines.append("```text")
    lines.append(best_p99.to_string(index=False))
    lines.append("```")
    lines.append("")

    lines.append("## High-Load (Max Rate) Median by Policy")
    lines.append("```text")
    lines.append(high_load.to_string())
    lines.append("```")
    lines.append("")

    if len(outlier_rows) > 0:
        lines.append("## Severe TTFT P99 Outliers (> 10,000 ms)")
        lines.append("```text")
        lines.append(outlier_rows.to_string(index=False))
        lines.append("```")
        lines.append("")

    if req_df is not None and not getattr(req_df, "empty", True):
        lines.append("## Request-Level Telemetry Coverage")
        total_rows = int(len(req_df))
        q_rows = int((req_df["Q_at_scheduling"] >= 0).sum()) if "Q_at_scheduling" in req_df.columns else 0
        jain_rows = int((req_df["jain_control"] >= 0).sum()) if "jain_control" in req_df.columns else 0
        violated_rows = int((req_df["aimd_violated"] == True).sum()) if "aimd_violated" in req_df.columns else 0
        lines.append("```text")
        lines.append(f"total_request_rows: {total_rows}")
        lines.append(f"rows_with_Q_at_scheduling: {q_rows}")
        lines.append(f"rows_with_jain_control: {jain_rows}")
        lines.append(f"rows_with_aimd_violated=true: {violated_rows}")
        lines.append("```")
        lines.append("")

        if "Q_at_scheduling" in req_df.columns:
            q_med = (
                req_df[
                    (req_df["policy"] == "adaptive_dlpm")
                    & (req_df["Q_at_scheduling"] >= 0)
                ]["Q_at_scheduling"]
                .median()
            )
            if not math.isnan(float(q_med)):
                lines.append("## Adaptive DLPM Median Q_at_scheduling")
                lines.append("```text")
                lines.append(f"adaptive_dlpm: {float(q_med):.2f}")
                lines.append("```")
                lines.append("")

        if "run_file" in req_df.columns:
            n_adaptive_runs = int(req_df[req_df["policy"] == "adaptive_dlpm"]["run_file"].nunique())
            lines.append("## Adaptive AIMD Trace Coverage")
            lines.append("```text")
            lines.append(f"adaptive_runs_found: {n_adaptive_runs}")
            lines.append("one trace PNG is generated for each adaptive run")
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot and summarize benchmark_modal_service_grid.py outputs")
    parser.add_argument("folder", help="Benchmark folder path or name (e.g. modal_grid_20260414_200819)")
    parser.add_argument("--output-dir", default="docs/plots", help="Directory for generated plots and summary")
    parser.add_argument("--prefix", default="", help="Output filename prefix (default: input folder name)")
    args = parser.parse_args()

    folder = resolve_input_folder(args.folder)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.prefix.strip() or folder.name

    df = load_summary_csv(folder)
    req_df = load_request_logs(df, folder)

    throughput_plot = out_dir / f"{prefix}_throughput_vs_rate.png"
    p99_plot = out_dir / f"{prefix}_ttft_p99_vs_rate.png"
    pareto_plot = out_dir / f"{prefix}_pareto.png"
    ttft_percentile_hist_plot = out_dir / f"{prefix}_ttft_percentile_hist.png"
    ttft_request_hist_plot = out_dir / f"{prefix}_ttft_request_hist.png"
    aimd_overview_plot = out_dir / f"{prefix}_aimd_overview.png"
    aimd_reasons_plot = out_dir / f"{prefix}_aimd_violation_reasons.png"
    aimd_trace_dir = out_dir / f"{prefix}_aimd_traces"
    summary_md = out_dir / f"{prefix}_summary.md"

    plot_metric_vs_rate(
        df=df,
        metric="throughput_tok_per_sec",
        ylabel="Throughput (tokens/sec)",
        title=f"Throughput vs Rate by Policy/K ({folder.name})",
        out_path=throughput_plot,
    )
    plot_metric_vs_rate(
        df=df,
        metric="ttft_p99_ms",
        ylabel="TTFT P99 (ms)",
        title=f"TTFT P99 vs Rate by Policy/K ({folder.name})",
        out_path=p99_plot,
    )
    plot_pareto(df=df, out_path=pareto_plot)
    made_ttft_percentile_hist = plot_ttft_percentile_histograms(df=df, out_path=ttft_percentile_hist_plot)
    made_ttft_request_hist = plot_ttft_request_histograms(req_df=req_df, out_path=ttft_request_hist_plot)
    made_aimd_overview = plot_aimd_overview(req_df=req_df, out_path=aimd_overview_plot)
    made_aimd_reasons = plot_aimd_violation_reasons(req_df=req_df, out_path=aimd_reasons_plot)
    aimd_trace_paths = plot_all_aimd_traces(req_df=req_df, out_dir=out_dir, prefix=prefix)

    summary = build_summary_markdown(df, folder, req_df=req_df)
    summary_md.write_text(summary, encoding="utf-8")

    print("=== Benchmark Plotting Complete ===")
    print("input folder:", folder)
    print("throughput plot:", throughput_plot)
    print("p99 plot:", p99_plot)
    print("pareto plot:", pareto_plot)
    print("ttft percentile histogram:", ttft_percentile_hist_plot if made_ttft_percentile_hist else "(skipped: no data)")
    print("ttft request histogram:", ttft_request_hist_plot if made_ttft_request_hist else "(skipped: no request TTFT data)")
    print("aimd overview:", aimd_overview_plot if made_aimd_overview else "(skipped: no AIMD metadata)")
    print("aimd violation reasons:", aimd_reasons_plot if made_aimd_reasons else "(skipped: no violation reason data)")
    if aimd_trace_paths:
        print("aimd per-run traces dir:", aimd_trace_dir)
        print("aimd per-run traces count:", len(aimd_trace_paths))
    else:
        print("aimd per-run traces:", "(skipped: no adaptive AIMD run)")
    print("summary markdown:", summary_md)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
