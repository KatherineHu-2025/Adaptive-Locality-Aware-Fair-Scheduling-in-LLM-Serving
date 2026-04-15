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


def build_summary_markdown(df, folder: Path) -> str:
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

    throughput_plot = out_dir / f"{prefix}_throughput_vs_rate.png"
    p99_plot = out_dir / f"{prefix}_ttft_p99_vs_rate.png"
    pareto_plot = out_dir / f"{prefix}_pareto.png"
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

    summary = build_summary_markdown(df, folder)
    summary_md.write_text(summary, encoding="utf-8")

    print("=== Benchmark Plotting Complete ===")
    print("input folder:", folder)
    print("throughput plot:", throughput_plot)
    print("p99 plot:", p99_plot)
    print("pareto plot:", pareto_plot)
    print("summary markdown:", summary_md)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
