"""
Plot paper figures from chatbot_arena benchmark results.

Usage:
    python plot_chatbot_comparison.py docs/plots/chatbot_comparison/modal_grid_20260417_124839

Generates in --output-dir:
  fig1_ttft_bars.png      — overall TTFT P50/P99 bar chart by policy
  fig2_tail_scatter.png   — P50 vs P99 scatter (tail factor) per policy/condition
  fig3_throughput.png     — throughput by policy
  fig4_jain.png           — Jain fairness index by policy
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


# ---------------------------------------------------------------------------
# Policy display config (mirrors plot_main_comparison.py)
# ---------------------------------------------------------------------------

POLICY_ORDER = ["fcfs", "lpm", "dlpm_q1200", "dlpm_q4000", "dlpm_q8000", "adaptive_dlpm"]

POLICY_COLORS = {
    "fcfs":          "#7f8c8d",
    "lpm":           "#e74c3c",
    "dlpm_q1200":    "#aed6f1",
    "dlpm_q4000":    "#2980b9",
    "dlpm_q8000":    "#1a5276",
    "adaptive_dlpm": "#27ae60",
}

POLICY_LABELS = {
    "fcfs":          "FCFS",
    "lpm":           "LPM",
    "dlpm_q1200":    "Static DLPM\nQ=1200",
    "dlpm_q4000":    "Static DLPM\nQ=4000",
    "dlpm_q8000":    "Static DLPM\nQ=8000",
    "adaptive_dlpm": "Adaptive\nDLPM",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fix_policy_label(policy: str, output_file: str) -> str:
    if policy == "dlpm":
        m = re.search(r"dlpm_q(\d+)_", Path(output_file).name)
        if m:
            return f"dlpm_q{m.group(1)}"
    return policy


def load_summary(folder: Path) -> list[dict[str, Any]]:
    rows = []
    with (folder / "summary.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["policy"] = fix_policy_label(row["policy"], row.get("output_file", ""))
            row["rate"] = float(row["rate"])
            row["k"] = float(row["k"])
            row["throughput_tok_per_sec"] = float(row["throughput_tok_per_sec"])
            row["ttft_p50_ms"] = float(row["ttft_p50_ms"])
            row["ttft_p99_ms"] = float(row["ttft_p99_ms"])
            row["ttft_mean_ms"] = float(row["ttft_mean_ms"])
            jain = row.get("jain_index", "")
            try:
                row["jain_index"] = float(jain)
            except (ValueError, TypeError):
                row["jain_index"] = float("nan")
            rows.append(row)
    return rows


def _sort_policies(policies: list[str]) -> list[str]:
    order = {p: i for i, p in enumerate(POLICY_ORDER)}
    return sorted(policies, key=lambda p: order.get(p, 99))


def _bar_positions(n_policies: int, n_groups: int, bar_width: float = 0.12):
    offsets = np.linspace(-(n_policies - 1) / 2, (n_policies - 1) / 2, n_policies) * bar_width
    centers = np.arange(n_groups)
    return centers, offsets


# ---------------------------------------------------------------------------
# Figure 1: Overall TTFT bar chart (P50 and P99)
# ---------------------------------------------------------------------------

def fig1_ttft_bars(rows: list[dict], out_path: Path, dpi: int) -> None:
    conditions = sorted({(r["rate"], r["k"]) for r in rows})
    policies = _sort_policies(list({r["policy"] for r in rows}))
    n_cond = len(conditions)
    n_pol = len(policies)
    bar_w = 0.12

    fig, axes = plt.subplots(1, 2, figsize=(16, 6), dpi=dpi)

    for ax, metric, title in [
        (axes[0], "ttft_p50_ms", "TTFT P50 by Policy and Load Condition"),
        (axes[1], "ttft_p99_ms", "TTFT P99 by Policy and Load Condition"),
    ]:
        centers, offsets = _bar_positions(n_pol, n_cond, bar_w)
        for pi, policy in enumerate(policies):
            vals = []
            for cond in conditions:
                matching = [r[metric] for r in rows
                            if r["policy"] == policy and r["rate"] == cond[0] and r["k"] == cond[1]]
                vals.append(matching[0] if matching else float("nan"))
            ax.bar(
                centers + offsets[pi],
                vals,
                width=bar_w,
                color=POLICY_COLORS.get(policy, "tab:gray"),
                label=POLICY_LABELS.get(policy, policy),
                alpha=0.88,
            )

        ax.set_xticks(centers)
        ax.set_xticklabels([f"rate={r:.1f}\nk={k:.1f}" for r, k in conditions], fontsize=9)
        ax.set_ylabel("TTFT (ms)")
        ax.set_title(title)
        ax.grid(True, axis="y", alpha=0.3)
        ax.set_ylim(bottom=0)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=min(6, n_pol), frameon=True, fontsize=9)
    fig.suptitle("Chatbot Arena — TTFT by Policy", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig1] {out_path}")


# ---------------------------------------------------------------------------
# Figure 2: P50 vs P99 scatter — tail factor per policy/condition
# ---------------------------------------------------------------------------

def fig2_tail_scatter(rows: list[dict], out_path: Path, dpi: int) -> None:
    policies = _sort_policies(list({r["policy"] for r in rows}))
    conditions = sorted({(r["rate"], r["k"]) for r in rows})
    markers = ["o", "s", "^", "D"]
    cond_markers = {c: markers[i % len(markers)] for i, c in enumerate(conditions)}

    fig, ax = plt.subplots(figsize=(9, 7), dpi=dpi)

    for policy in policies:
        for cond in conditions:
            pts = [r for r in rows if r["policy"] == policy and r["rate"] == cond[0] and r["k"] == cond[1]]
            if not pts:
                continue
            r = pts[0]
            p50 = r["ttft_p50_ms"]
            p99 = r["ttft_p99_ms"]
            if math.isnan(p50) or math.isnan(p99):
                continue
            ax.scatter(
                p50, p99,
                color=POLICY_COLORS.get(policy, "gray"),
                marker=cond_markers[cond],
                s=90, alpha=0.85, zorder=3,
            )
            ax.annotate(
                POLICY_LABELS.get(policy, policy).replace("\n", " "),
                (p50, p99),
                textcoords="offset points", xytext=(6, 4),
                fontsize=7, color=POLICY_COLORS.get(policy, "gray"),
            )

    # Diagonal: P99 == P50 (no tail)
    lims = [
        min(ax.get_xlim()[0], ax.get_ylim()[0]),
        max(ax.get_xlim()[1], ax.get_ylim()[1]),
    ]
    ax.plot(lims, lims, "--", color="lightgray", linewidth=1, zorder=0, label="P99 = P50 (no tail)")

    ax.set_xlabel("TTFT P50 (ms)", fontsize=11)
    ax.set_ylabel("TTFT P99 (ms)", fontsize=11)
    ax.set_title("Tail Latency: P50 vs P99 per Policy\n"
                 "(ideal policy: bottom-left, close to diagonal)", fontsize=12)
    ax.grid(True, alpha=0.3)

    from matplotlib.lines import Line2D
    cond_legend = [
        Line2D([0], [0], marker=cond_markers[c], color="dimgray", linestyle="none",
               markersize=7, label=f"rate={c[0]:.1f}, k={c[1]:.1f}")
        for c in conditions
    ]
    pol_legend = [
        Line2D([0], [0], marker="o", color=POLICY_COLORS.get(p, "gray"), linestyle="none",
               markersize=8, label=POLICY_LABELS.get(p, p).replace("\n", " "))
        for p in policies
    ]
    ax.legend(handles=pol_legend + cond_legend, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig2] {out_path}")


# ---------------------------------------------------------------------------
# Figure 3: Throughput comparison
# ---------------------------------------------------------------------------

def fig3_throughput(rows: list[dict], out_path: Path, dpi: int) -> None:
    conditions = sorted({(r["rate"], r["k"]) for r in rows})
    policies = _sort_policies(list({r["policy"] for r in rows}))
    n_cond = len(conditions)
    n_pol = len(policies)
    bar_w = 0.12

    fig, ax = plt.subplots(figsize=(12, 5), dpi=dpi)
    centers, offsets = _bar_positions(n_pol, n_cond, bar_w)

    for pi, policy in enumerate(policies):
        vals = []
        for cond in conditions:
            matching = [r["throughput_tok_per_sec"] for r in rows
                        if r["policy"] == policy and r["rate"] == cond[0] and r["k"] == cond[1]]
            vals.append(matching[0] if matching else float("nan"))
        ax.bar(
            centers + offsets[pi], vals, width=bar_w,
            color=POLICY_COLORS.get(policy, "tab:gray"),
            label=POLICY_LABELS.get(policy, policy).replace("\n", " "),
            alpha=0.88,
        )

    ax.set_xticks(centers)
    ax.set_xticklabels([f"rate={r:.1f}, k={k:.1f}" for r, k in conditions], fontsize=9)
    ax.set_ylabel("Throughput (tokens/sec)")
    ax.set_title("Chatbot Arena — Throughput by Policy and Load Condition")
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", ncol=3, fontsize=9, frameon=True)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig3] {out_path}")


# ---------------------------------------------------------------------------
# Figure 4: Jain fairness index
# ---------------------------------------------------------------------------

def fig4_jain(rows: list[dict], out_path: Path, dpi: int) -> None:
    conditions = sorted({(r["rate"], r["k"]) for r in rows})
    policies = _sort_policies(list({r["policy"] for r in rows}))
    n_cond = len(conditions)
    n_pol = len(policies)
    bar_w = 0.12

    fig, ax = plt.subplots(figsize=(12, 5), dpi=dpi)
    centers, offsets = _bar_positions(n_pol, n_cond, bar_w)

    for pi, policy in enumerate(policies):
        vals = []
        for cond in conditions:
            matching = [r["jain_index"] for r in rows
                        if r["policy"] == policy and r["rate"] == cond[0] and r["k"] == cond[1]]
            vals.append(matching[0] if matching else float("nan"))
        ax.bar(
            centers + offsets[pi], vals, width=bar_w,
            color=POLICY_COLORS.get(policy, "tab:gray"),
            label=POLICY_LABELS.get(policy, policy).replace("\n", " "),
            alpha=0.88,
        )

    ax.axhline(1.0, color="black", linewidth=0.8, linestyle="--", label="Perfect fairness (1.0)")
    ax.set_xticks(centers)
    ax.set_xticklabels([f"rate={r:.1f}, k={k:.1f}" for r, k in conditions], fontsize=9)
    ax.set_ylabel("Jain Fairness Index")
    ax.set_title("Chatbot Arena — Jain Fairness Index by Policy and Load Condition")
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(0, 1.1)
    ax.legend(loc="lower right", ncol=3, fontsize=9, frameon=True)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig4] {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Plot figures from chatbot_arena benchmark")
    parser.add_argument("folder", help="Benchmark result folder (contains summary.csv)")
    parser.add_argument("--output-dir", default="docs/plots/chatbot_comparison",
                        help="Directory to write plot PNGs")
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        raise SystemExit(f"Folder not found: {folder}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[load] {folder / 'summary.csv'}")
    rows = load_summary(folder)
    print(f"[load] {len(rows)} rows, policies: {sorted({r['policy'] for r in rows})}")

    prefix = folder.name
    fig1_ttft_bars(rows, out_dir / f"{prefix}_fig1_ttft_bars.png", args.dpi)
    fig2_tail_scatter(rows, out_dir / f"{prefix}_fig2_tail_scatter.png", args.dpi)
    fig3_throughput(rows, out_dir / f"{prefix}_fig3_throughput.png", args.dpi)
    fig4_jain(rows, out_dir / f"{prefix}_fig4_jain.png", args.dpi)

    print("\n=== Done ===")
    print(f"Output: {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
