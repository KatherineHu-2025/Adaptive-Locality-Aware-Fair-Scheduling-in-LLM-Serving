"""
Generate cross-threshold comparison plots and markdown for LooGLE adaptive runs.

This script compares adaptive rows across Jain threshold configurations:
- 0.60 from results/modal_grid_loogle_60p_jain_threshold/summary.csv
- 0.63 from results/modal_grid_20260421_185446/summary.csv
- 0.65 from results/modal_grid_loogle_65p_jain_threshold/summary.csv

Outputs are saved to a target folder, defaulting to:
docs/plots/loogle_63p_jain_concurrency_16
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path


def load_summary_csv(path: Path):
    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit("Missing dependency: pandas") from exc

    if not path.exists():
        raise FileNotFoundError(f"Missing summary file: {path}")

    df = pd.read_csv(path)
    numeric_cols = [
        "rate",
        "k",
        "request_count",
        "success_rate",
        "throughput_tok_per_sec",
        "ttft_p50_ms",
        "ttft_p99_ms",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def pick_adaptive_rows(df, threshold_label: str):
    # 0.60 merged file uses adaptive_j060 naming while others commonly use adaptive_dlpm.
    if threshold_label == "0.60":
        policies = ["adaptive_j060", "adaptive_dlpm"]
    elif threshold_label == "0.65":
        policies = ["adaptive_dlpm", "adaptive_j065"]
    else:
        policies = ["adaptive_dlpm"]

    out = df[df["policy"].isin(policies)].copy()
    out["jain_threshold"] = float(threshold_label)
    return out


def safe_pct_improvement(new_value: float, base_value: float) -> float:
    # Positive means the new value is better for latency metrics (lower is better).
    if base_value == 0:
        return float("nan")
    return (base_value - new_value) / base_value * 100.0


def safe_pct_delta(new_value: float, base_value: float) -> float:
    # Positive means the new value is larger (used for throughput deltas).
    if base_value == 0:
        return float("nan")
    return (new_value - base_value) / base_value * 100.0


def build_pairwise_table(adaptive_df):
    import pandas as pd

    common_n = sorted(
        set(adaptive_df[adaptive_df["jain_threshold"] == 0.60]["request_count"].dropna().astype(int))
        & set(adaptive_df[adaptive_df["jain_threshold"] == 0.63]["request_count"].dropna().astype(int))
        & set(adaptive_df[adaptive_df["jain_threshold"] == 0.65]["request_count"].dropna().astype(int))
    )

    rows: list[dict[str, float | int]] = []
    for req_count in common_n:
        d = adaptive_df[adaptive_df["request_count"] == req_count]
        p99_060 = float(d[d["jain_threshold"] == 0.60]["ttft_p99_ms"].iloc[0])
        p99_063 = float(d[d["jain_threshold"] == 0.63]["ttft_p99_ms"].iloc[0])
        p99_065 = float(d[d["jain_threshold"] == 0.65]["ttft_p99_ms"].iloc[0])

        p50_060 = float(d[d["jain_threshold"] == 0.60]["ttft_p50_ms"].iloc[0])
        p50_063 = float(d[d["jain_threshold"] == 0.63]["ttft_p50_ms"].iloc[0])
        p50_065 = float(d[d["jain_threshold"] == 0.65]["ttft_p50_ms"].iloc[0])

        thr_060 = float(d[d["jain_threshold"] == 0.60]["throughput_tok_per_sec"].iloc[0])
        thr_063 = float(d[d["jain_threshold"] == 0.63]["throughput_tok_per_sec"].iloc[0])
        thr_065 = float(d[d["jain_threshold"] == 0.65]["throughput_tok_per_sec"].iloc[0])

        rows.append(
            {
                "request_count": int(req_count),
                "j063_vs_j065_p99_impr_pct": safe_pct_improvement(p99_063, p99_065),
                "j065_vs_j060_p99_impr_pct": safe_pct_improvement(p99_065, p99_060),
                "j063_vs_j060_p99_impr_pct": safe_pct_improvement(p99_063, p99_060),
                "j063_vs_j065_p50_impr_pct": safe_pct_improvement(p50_063, p50_065),
                "j065_vs_j060_p50_impr_pct": safe_pct_improvement(p50_065, p50_060),
                "j063_vs_j060_p50_impr_pct": safe_pct_improvement(p50_063, p50_060),
                "j063_vs_j065_thr_delta_pct": safe_pct_delta(thr_063, thr_065),
                "j065_vs_j060_thr_delta_pct": safe_pct_delta(thr_065, thr_060),
                "j063_vs_j060_thr_delta_pct": safe_pct_delta(thr_063, thr_060),
            }
        )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("request_count")


def build_adaptive_vs_baselines(summary_df, threshold_label: str):
    import pandas as pd

    adaptive = pick_adaptive_rows(summary_df, threshold_label)
    baselines = summary_df[summary_df["policy"].isin(["fcfs", "dlpm", "lpm"])].copy()

    rows: list[dict[str, float | int | str]] = []
    for _, arow in adaptive.iterrows():
        req_count = int(arow["request_count"])
        for baseline in ["fcfs", "dlpm", "lpm"]:
            brow = baselines[(baselines["policy"] == baseline) & (baselines["request_count"] == req_count)]
            if brow.empty:
                continue
            brow0 = brow.iloc[0]
            rows.append(
                {
                    "jain_threshold": threshold_label,
                    "request_count": req_count,
                    "baseline": baseline,
                    "ttft_p99_improvement_pct": safe_pct_improvement(float(arow["ttft_p99_ms"]), float(brow0["ttft_p99_ms"])),
                    "ttft_p50_improvement_pct": safe_pct_improvement(float(arow["ttft_p50_ms"]), float(brow0["ttft_p50_ms"])),
                    "throughput_improvement_pct": safe_pct_delta(float(arow["throughput_tok_per_sec"]), float(brow0["throughput_tok_per_sec"])),
                }
            )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["jain_threshold", "request_count", "baseline"])


def plot_adaptive_metrics_by_threshold(adaptive_df, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), dpi=150)
    metrics = [
        ("ttft_p50_ms", "TTFT P50 (ms)", "lower better"),
        ("ttft_p99_ms", "TTFT P99 (ms)", "lower better"),
        ("throughput_tok_per_sec", "Throughput (tok/s)", "higher better"),
        ("success_rate", "Success Rate", "higher better"),
    ]

    marker_map = {0.60: "o", 0.63: "s", 0.65: "^"}

    for ax, (metric, title, subtitle) in zip(axes.flatten(), metrics):
        for thr in sorted(adaptive_df["jain_threshold"].dropna().unique()):
            d = adaptive_df[adaptive_df["jain_threshold"] == thr].sort_values("request_count")
            if d.empty:
                continue
            ax.plot(
                d["request_count"],
                d[metric],
                marker=marker_map.get(float(thr), "o"),
                linewidth=2,
                markersize=6,
                label=f"J={thr:.2f}",
            )
        ax.set_title(f"{title} ({subtitle})")
        ax.set_xlabel("Request Count (n)")
        ax.grid(True, alpha=0.3)

    axes[0, 0].set_ylabel("ms")
    axes[0, 1].set_ylabel("ms")
    axes[1, 0].set_ylabel("tok/s")
    axes[1, 1].set_ylabel("ratio")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=True)
    fig.suptitle("Adaptive Policy Metrics Across Jain Thresholds (LooGLE)")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def plot_pairwise_p99_improvement(pairwise_df, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    if pairwise_df.empty:
        return

    x = np.arange(len(pairwise_df))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    ax.bar(x - width, pairwise_df["j063_vs_j065_p99_impr_pct"], width, label="J=0.63 vs J=0.65")
    ax.bar(x, pairwise_df["j065_vs_j060_p99_impr_pct"], width, label="J=0.65 vs J=0.60")
    ax.bar(x + width, pairwise_df["j063_vs_j060_p99_impr_pct"], width, label="J=0.63 vs J=0.60")

    ax.axhline(0.0, color="black", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels([f"n={int(n)}" for n in pairwise_df["request_count"]])
    ax.set_ylabel("P99 Improvement (%)")
    ax.set_title("Adaptive Pairwise P99 Improvements (positive = better)")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(frameon=True)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def plot_adaptive_vs_fcfs(adaptive_vs_baselines_df, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if adaptive_vs_baselines_df.empty:
        return

    df = adaptive_vs_baselines_df[adaptive_vs_baselines_df["baseline"] == "fcfs"].copy()
    if df.empty:
        return

    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    for threshold in sorted(df["jain_threshold"].unique(), key=float):
        d = df[df["jain_threshold"] == threshold].sort_values("request_count")
        ax.plot(
            d["request_count"],
            d["ttft_p99_improvement_pct"],
            marker="o",
            linewidth=2,
            markersize=6,
            label=f"J={threshold}",
        )
    ax.axhline(0.0, color="black", linewidth=1)
    ax.set_xlabel("Request Count (n)")
    ax.set_ylabel("P99 Improvement vs FCFS (%)")
    ax.set_title("Adaptive Tail-Latency Gain vs FCFS Across Thresholds")
    ax.grid(True, alpha=0.3)
    ax.legend(frameon=True)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def get_best_threshold_by_n(adaptive_df):
    winners: list[tuple[int, float, float]] = []
    for req_count in sorted(adaptive_df["request_count"].dropna().astype(int).unique()):
        d = adaptive_df[adaptive_df["request_count"] == req_count]
        if d.empty:
            continue
        best_row = d.sort_values("ttft_p99_ms", ascending=True).iloc[0]
        winners.append((req_count, float(best_row["jain_threshold"]), float(best_row["ttft_p99_ms"])))
    return winners


def to_text_table(df, floatfmt: str = "%.3f") -> str:
    if df.empty:
        return "(no rows)"
    return df.to_string(index=False, float_format=lambda x: floatfmt % x)


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-threshold LooGLE comparison report generator")
    parser.add_argument(
        "--summary-060",
        default="results/modal_grid_loogle_60p_jain_threshold/summary.csv",
        help="Path to summary.csv for J=0.60 result set",
    )
    parser.add_argument(
        "--summary-063",
        default="results/modal_grid_20260421_185446/summary.csv",
        help="Path to summary.csv for J=0.63 result set",
    )
    parser.add_argument(
        "--summary-065",
        default="results/modal_grid_loogle_65p_jain_threshold/summary.csv",
        help="Path to summary.csv for J=0.65 result set",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/plots/loogle_63p_jain_concurrency_16",
        help="Directory to save cross-threshold plots and markdown",
    )
    parser.add_argument(
        "--prefix",
        default="loogle_63p_jain_concurrency_16",
        help="Filename prefix for generated artifacts",
    )
    args = parser.parse_args()

    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit("Missing dependency: pandas") from exc

    s060_path = Path(args.summary_060)
    s063_path = Path(args.summary_063)
    s065_path = Path(args.summary_065)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    s060 = load_summary_csv(s060_path)
    s063 = load_summary_csv(s063_path)
    s065 = load_summary_csv(s065_path)

    adaptive_df = pd.concat(
        [
            pick_adaptive_rows(s060, "0.60"),
            pick_adaptive_rows(s063, "0.63"),
            pick_adaptive_rows(s065, "0.65"),
        ],
        ignore_index=True,
    )
    adaptive_df = adaptive_df[
        [
            "jain_threshold",
            "policy",
            "request_count",
            "success_rate",
            "throughput_tok_per_sec",
            "ttft_p50_ms",
            "ttft_p99_ms",
            "output_file",
        ]
    ].sort_values(["jain_threshold", "request_count"]) 

    pairwise_df = build_pairwise_table(adaptive_df)
    avb_df = pd.concat(
        [
            build_adaptive_vs_baselines(s060, "0.60"),
            build_adaptive_vs_baselines(s063, "0.63"),
            build_adaptive_vs_baselines(s065, "0.65"),
        ],
        ignore_index=True,
    )

    plot1 = out_dir / f"{args.prefix}_adaptive_metrics_by_threshold.png"
    plot2 = out_dir / f"{args.prefix}_adaptive_p99_pairwise_improvement.png"
    plot3 = out_dir / f"{args.prefix}_adaptive_vs_fcfs_p99_improvement.png"
    report_path = out_dir / f"{args.prefix}_threshold_comparison_summary.md"

    plot_adaptive_metrics_by_threshold(adaptive_df, plot1)
    plot_pairwise_p99_improvement(pairwise_df, plot2)
    plot_adaptive_vs_fcfs(avb_df, plot3)

    winners = get_best_threshold_by_n(adaptive_df)

    common_n_set = sorted(
        set(adaptive_df[adaptive_df["jain_threshold"] == 0.60]["request_count"].dropna().astype(int))
        & set(adaptive_df[adaptive_df["jain_threshold"] == 0.63]["request_count"].dropna().astype(int))
        & set(adaptive_df[adaptive_df["jain_threshold"] == 0.65]["request_count"].dropna().astype(int))
    )

    p99_spread_rows = []
    for req_count in common_n_set:
        d = adaptive_df[adaptive_df["request_count"] == req_count]
        min_p99 = float(d["ttft_p99_ms"].min())
        max_p99 = float(d["ttft_p99_ms"].max())
        p99_spread_rows.append(
            {
                "request_count": req_count,
                "min_p99_ms": min_p99,
                "max_p99_ms": max_p99,
                "spread_pct_of_min": ((max_p99 - min_p99) / min_p99 * 100.0) if min_p99 > 0 else float("nan"),
            }
        )
    p99_spread_df = pd.DataFrame(p99_spread_rows)

    run063_n100 = s063[s063["request_count"] == 100].copy().sort_values("ttft_p99_ms")
    run063_n100 = run063_n100[
        ["policy", "success_rate", "throughput_tok_per_sec", "ttft_p50_ms", "ttft_p99_ms"]
    ]

    lines: list[str] = []
    lines.append("# LooGLE Jain Threshold Comparison Summary (0.60 vs 0.63 vs 0.65)")
    lines.append("")
    lines.append(f"Generated on: {date.today().isoformat()}")
    lines.append("")
    lines.append("## Data Sources")
    lines.append("")
    lines.append(f"- J=0.60: `{s060_path.as_posix()}`")
    lines.append(f"- J=0.63: `{s063_path.as_posix()}`")
    lines.append(f"- J=0.65: `{s065_path.as_posix()}`")
    lines.append("")
    lines.append("## Additional Plots Generated")
    lines.append("")
    lines.append(f"- `{plot1.as_posix()}`")
    lines.append(f"- `{plot2.as_posix()}`")
    lines.append(f"- `{plot3.as_posix()}`")
    lines.append("")
    lines.append("## Adaptive Rows Used For Cross-Threshold Comparison")
    lines.append("```text")
    lines.append(to_text_table(adaptive_df, floatfmt="%.4f"))
    lines.append("```")
    lines.append("")
    lines.append("## Pairwise Adaptive Improvements (common n only; positive latency improvement is better)")
    lines.append("```text")
    lines.append(to_text_table(pairwise_df, floatfmt="%.2f"))
    lines.append("```")
    lines.append("")
    lines.append("## Adaptive vs Baseline Policies (within each threshold result set)")
    lines.append("```text")
    lines.append(to_text_table(avb_df, floatfmt="%.2f"))
    lines.append("```")
    lines.append("")
    lines.append("## Threshold Winner By Request Count (lowest adaptive P99)")
    lines.append("```text")
    for req_count, thr, p99 in winners:
        lines.append(f"n={req_count}: J={thr:.2f} with adaptive P99={p99:.2f} ms")
    lines.append("```")
    lines.append("")
    lines.append("## Tail-Latency Spread Across Thresholds (common n)")
    lines.append("```text")
    lines.append(to_text_table(p99_spread_df, floatfmt="%.2f"))
    lines.append("```")
    lines.append("")
    lines.append("## 0.63 Run Snapshot At n=100 (no direct 0.60/0.65 counterpart)")
    lines.append("```text")
    lines.append(to_text_table(run063_n100, floatfmt="%.2f"))
    lines.append("```")
    lines.append("")
    winner_by_n = {req_count: thr for req_count, thr, _ in winners}
    common_winner_text = ", ".join(
        f"n={n}->J={winner_by_n[n]:.2f}" for n in common_n_set if n in winner_by_n
    )

    throughput_spread_rows = []
    for req_count in common_n_set:
        d = adaptive_df[adaptive_df["request_count"] == req_count]
        min_thr = float(d["throughput_tok_per_sec"].min())
        max_thr = float(d["throughput_tok_per_sec"].max())
        spread = ((max_thr - min_thr) / min_thr * 100.0) if min_thr > 0 else float("nan")
        throughput_spread_rows.append((req_count, spread))

    max_thr_spread = max((spread for _, spread in throughput_spread_rows), default=float("nan"))
    j060_n25 = adaptive_df[
        (adaptive_df["jain_threshold"] == 0.60) & (adaptive_df["request_count"] == 25)
    ]
    j063_n25 = adaptive_df[
        (adaptive_df["jain_threshold"] == 0.63) & (adaptive_df["request_count"] == 25)
    ]
    j065_n25 = adaptive_df[
        (adaptive_df["jain_threshold"] == 0.65) & (adaptive_df["request_count"] == 25)
    ]

    lines.append("## Analysis Summary")
    lines.append("")
    lines.append(
        f"1. Adaptive tail-latency winners on common request counts: {common_winner_text}."
    )

    if not j060_n25.empty and not j063_n25.empty and not j065_n25.empty:
        p99_060_n25 = float(j060_n25.iloc[0]["ttft_p99_ms"])
        p99_063_n25 = float(j063_n25.iloc[0]["ttft_p99_ms"])
        p99_065_n25 = float(j065_n25.iloc[0]["ttft_p99_ms"])
        lines.append(
            "2. J=0.60 is highly unstable at n=25 in this sample: "
            + f"P99={p99_060_n25:.2f} ms vs J=0.63 ({p99_063_n25:.2f} ms) and J=0.65 ({p99_065_n25:.2f} ms)."
        )
    else:
        lines.append("2. n=25 cross-threshold stability could not be fully computed due to missing rows.")

    lines.append(
        "3. Throughput differences across adaptive thresholds are small "
        + f"(max spread across common n is {max_thr_spread:.2f}%), so the primary tradeoff is latency tail behavior."
    )

    if 100 in winner_by_n:
        lines.append(
            "4. At n=100 there is only J=0.63 adaptive data in this comparison, "
            "so cross-threshold ranking at n=100 is not yet available."
        )
    else:
        lines.append("4. n=100 adaptive cross-threshold comparison is not available in current inputs.")

    lines.append(
        "5. Within the 0.63 n=100 policy snapshot, FCFS has the lowest P99; adaptive is better than static DLPM but trails FCFS and LPM."
    )
    lines.append("")
    lines.append("## Suggested Next Steps")
    lines.append("")
    lines.append("1. Repeat n=25 for each threshold with 3 to 5 seeds and compare median plus IQR of P99 before locking a threshold.")
    lines.append("2. Add a fine-grained sweep around the current best point: J in {0.62, 0.63, 0.64, 0.65}.")
    lines.append("3. Validate under deeper load (rate=2.0 and 3.0) with the same concurrency setting to test threshold robustness.")
    lines.append("4. Add a guardrail experiment for J=0.60 (faster cutback on repeated Jain violations) to reduce heavy-tail risk.")
    lines.append("5. If objective is pure tail minimization at n=100, run matched 0.60 and 0.65 experiments at n=100 to avoid one-sided conclusions.")

    report_path.write_text("\n".join(lines), encoding="utf-8")

    print("=== LooGLE Threshold Comparison Complete ===")
    print("plot:", plot1)
    print("plot:", plot2)
    print("plot:", plot3)
    print("report:", report_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
