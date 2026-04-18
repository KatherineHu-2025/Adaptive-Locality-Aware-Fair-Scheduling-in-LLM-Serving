"""
Plot paper figures from benchmark_modal_service_grid.py output.

Usage:
    python plot_main_comparison.py docs/plots/main_comparison/modal_grid_20260417_015219

Generates in --output-dir:
  fig1_ttft_bars.png      — overall TTFT P50/P99 bar chart by policy
  fig2_per_client.png     — dominant vs cold client TTFT P99 (fairness figure)
  fig3_pareto.png         — dominant TTFT P99 vs cold TTFT P99 per policy
  fig4_throughput.png     — throughput by policy
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


# ---------------------------------------------------------------------------
# Policy display config
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

def _pct(vals: list[float], p: float) -> float:
    sv = sorted(v for v in vals if not math.isnan(v))
    if not sv:
        return float("nan")
    return sv[max(0, math.ceil(p * len(sv)) - 1)]


def fix_policy_label(policy: str, output_file: str) -> str:
    """Derive dlpm_q{N} label from the output filename for dlpm variants."""
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
            rows.append(row)
    return rows


def load_per_client_stats(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Read per-request JSONLs and split TTFT by client type (dominant/cold)."""
    out = []
    for row in rows:
        path = Path(row["output_file"])
        if not path.exists():
            continue
        dom, cold = [], []
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if not r.get("success"):
                    continue
                ttft = float(r.get("ttft_ms", -1))
                if ttft < 0:
                    continue
                cid = str(r.get("client_id", ""))
                if "dominant" in cid:
                    dom.append(ttft)
                elif "cold" in cid:
                    cold.append(ttft)
        out.append({
            "policy": row["policy"],
            "rate": row["rate"],
            "k": row["k"],
            "dom_p50": _pct(dom, 0.50),
            "dom_p99": _pct(dom, 0.99),
            "cold_p50": _pct(cold, 0.50),
            "cold_p99": _pct(cold, 0.99),
            "n_dom": len(dom),
            "n_cold": len(cold),
        })
    return out


def _sort_policies(policies: list[str]) -> list[str]:
    order = {p: i for i, p in enumerate(POLICY_ORDER)}
    return sorted(policies, key=lambda p: order.get(p, 99))


def _bar_positions(n_policies: int, n_groups: int, bar_width: float = 0.12):
    """Return (group_centers, offsets) for grouped bar chart."""
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
                matching = [r[metric] for r in rows if r["policy"] == policy and r["rate"] == cond[0] and r["k"] == cond[1]]
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
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig1] {out_path}")


# ---------------------------------------------------------------------------
# Figure 2: Per-client TTFT — dominant vs cold side by side
# ---------------------------------------------------------------------------

def fig2_per_client(pc: list[dict], out_path: Path, dpi: int) -> None:
    conditions = sorted({(r["rate"], r["k"]) for r in pc})
    policies = _sort_policies(list({r["policy"] for r in pc}))
    n_cond = len(conditions)
    n_pol = len(policies)
    bar_w = 0.1

    fig, axes = plt.subplots(1, n_cond, figsize=(8 * n_cond, 6), dpi=dpi, sharey=False)
    if n_cond == 1:
        axes = [axes]

    for ax, (rate, k) in zip(axes, conditions):
        subset = [r for r in pc if r["rate"] == rate and r["k"] == k]
        by_pol = {r["policy"]: r for r in subset}

        x = np.arange(n_pol)
        w = bar_w
        dom_p99 = [by_pol.get(p, {}).get("dom_p99", float("nan")) for p in policies]
        cold_p99 = [by_pol.get(p, {}).get("cold_p99", float("nan")) for p in policies]

        ax.bar(x - w / 2, dom_p99, width=w, label="Dominant clients", alpha=0.85,
               color=[POLICY_COLORS.get(p, "gray") for p in policies])
        ax.bar(x + w / 2, cold_p99, width=w, label="Cold clients", alpha=0.55,
               color=[POLICY_COLORS.get(p, "gray") for p in policies],
               hatch="//", edgecolor="black", linewidth=0.5)

        ax.set_xticks(x)
        ax.set_xticklabels([POLICY_LABELS.get(p, p) for p in policies], fontsize=8)
        ax.set_ylabel("TTFT P99 (ms)")
        ax.set_title(f"Per-Client TTFT P99  (rate={rate:.1f} req/s, k={k:.1f})")
        ax.grid(True, axis="y", alpha=0.3)
        ax.set_ylim(bottom=0)

        # Annotate cold/dominant ratio
        for xi, (dp, cp) in enumerate(zip(dom_p99, cold_p99)):
            if not (math.isnan(dp) or math.isnan(cp) or dp == 0):
                ratio = cp / dp
                ax.text(xi, max(dp, cp) * 1.02, f"×{ratio:.1f}", ha="center", fontsize=7, color="dimgray")

    from matplotlib.patches import Patch
    legend_elems = [
        Patch(facecolor="dimgray", alpha=0.85, label="Dominant clients (P99)"),
        Patch(facecolor="dimgray", alpha=0.55, hatch="//", label="Cold clients (P99)"),
    ]
    fig.legend(handles=legend_elems, loc="upper center", ncol=2, frameon=True, fontsize=10)
    fig.suptitle("Dominant vs Cold Client TTFT P99 — Fairness Comparison", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig2] {out_path}")


# ---------------------------------------------------------------------------
# Figure 3: Pareto — dominant TTFT P99 vs cold TTFT P99
# ---------------------------------------------------------------------------

def fig3_pareto(pc: list[dict], out_path: Path, dpi: int, pareto_max: float | None = None) -> None:
    policies = _sort_policies(list({r["policy"] for r in pc}))
    conditions = sorted({(r["rate"], r["k"]) for r in pc})
    markers = ["o", "s", "^", "D", "P", "X"]
    cond_markers = {c: markers[i % len(markers)] for i, c in enumerate(conditions)}

    fig, ax = plt.subplots(figsize=(9, 7), dpi=dpi)

    for policy in policies:
        for cond in conditions:
            pts = [r for r in pc if r["policy"] == policy and r["rate"] == cond[0] and r["k"] == cond[1]]
            if not pts:
                continue
            r = pts[0]
            dom_p99 = r["dom_p99"]
            cold_p99 = r["cold_p99"]
            if math.isnan(dom_p99) or math.isnan(cold_p99):
                continue
            if pareto_max is not None and (dom_p99 > pareto_max or cold_p99 > pareto_max):
                continue
            ax.scatter(
                dom_p99, cold_p99,
                color=POLICY_COLORS.get(policy, "gray"),
                marker=cond_markers[cond],
                s=90, alpha=0.85, zorder=3,
            )
            ax.annotate(
                POLICY_LABELS.get(policy, policy).replace("\n", " "),
                (dom_p99, cold_p99),
                textcoords="offset points", xytext=(6, 4),
                fontsize=7, color=POLICY_COLORS.get(policy, "gray"),
            )

    # Diagonal reference line (perfect fairness = cold P99 == dominant P99)
    lims = [
        min(ax.get_xlim()[0], ax.get_ylim()[0]),
        max(ax.get_xlim()[1], ax.get_ylim()[1]),
    ]
    ax.plot(lims, lims, "--", color="lightgray", linewidth=1, zorder=0, label="cold = dominant (perfect fairness)")

    ax.set_xlabel("Dominant Client TTFT P99 (ms)", fontsize=11)
    ax.set_ylabel("Cold Client TTFT P99 (ms)", fontsize=11)
    ax.set_title("Fairness Tradeoff: Dominant vs Cold Client TTFT P99\n"
                 "(ideal policy: bottom-left corner)", fontsize=12)
    ax.grid(True, alpha=0.3)

    # Legend for conditions
    from matplotlib.lines import Line2D
    cond_legend = [
        Line2D([0], [0], marker=cond_markers[c], color="dimgray", linestyle="none",
               markersize=7, label=f"rate={c[0]:.1f}, k={c[1]:.1f}")
        for c in conditions
    ]
    # Legend for policies
    pol_legend = [
        Line2D([0], [0], marker="o", color=POLICY_COLORS.get(p, "gray"), linestyle="none",
               markersize=8, label=POLICY_LABELS.get(p, p).replace("\n", " "))
        for p in policies
    ]
    ax.legend(handles=pol_legend + cond_legend, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig3] {out_path}")


# ---------------------------------------------------------------------------
# Figure 4: Throughput comparison
# ---------------------------------------------------------------------------

def fig4_throughput(rows: list[dict], out_path: Path, dpi: int) -> None:
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
    ax.set_title("Throughput by Policy and Load Condition")
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", ncol=3, fontsize=9, frameon=True)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig4] {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Plot paper figures from main comparison benchmark")
    parser.add_argument("folder", help="Benchmark result folder (contains summary.csv)")
    parser.add_argument("--output-dir", default="docs/plots/main_comparison",
                        help="Directory to write plot PNGs")
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--pareto-max", type=float, default=None,
                        help="Exclude points where dom or cold P99 exceeds this value (ms) from fig3")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        raise SystemExit(f"Folder not found: {folder}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[load] {folder / 'summary.csv'}")
    rows = load_summary(folder)
    print(f"[load] {len(rows)} rows, policies: {sorted({r['policy'] for r in rows})}")

    print("[load] reading per-request JSONLs for per-client stats...")
    pc = load_per_client_stats(rows)
    print(f"[load] per-client stats: {len(pc)} rows")

    prefix = folder.name
    fig1_ttft_bars(rows, out_dir / f"{prefix}_fig1_ttft_bars.png", args.dpi)
    fig2_per_client(pc, out_dir / f"{prefix}_fig2_per_client.png", args.dpi)
    fig3_pareto(pc, out_dir / f"{prefix}_fig3_pareto.png", args.dpi, pareto_max=args.pareto_max)
    fig4_throughput(rows, out_dir / f"{prefix}_fig4_throughput.png", args.dpi)

    print("\n=== Done ===")
    print(f"Output: {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
