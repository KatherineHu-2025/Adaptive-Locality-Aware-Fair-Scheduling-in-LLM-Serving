# A/B Experiment: Strict vs Relaxed Jain Threshold

**Run command:**
```bash
python run_aimd_ab_test_v2.py \
  --server https://yangh3--adaptive-dlpm-scheduler-service-hosted-minisgl-app.modal.run \
  --output-dir docs/plots/ab_test_realigned_jain \
  --strict-jain-threshold 0.90 \
  --relaxed-jain-threshold 0.75 \
  --num-dominant-clients 4 \
  --num-cold-clients 4 \
  --max-concurrency 16 \
  --phase-a-rate 2.0 \
  --phase-b-rate 4.0
```

**Workload:** 4 dominant clients (shared system prompt, high cache hit rate) + 4 cold clients (unique prompts, always cold-start). Two-phase load: Phase A at 2.0 req/s (light), Phase B at 4.0 req/s (heavy).

---

## What this experiment proves

This is a **hyperparameter sensitivity study** for the Adaptive DLPM Jain threshold — not the main Adaptive vs Static DLPM comparison. It demonstrates:

1. The AIMD control loop is functional (sawtooth visible in the relaxed case)
2. An over-strict threshold saturates Q at Q_MIN, destroying cache efficiency for everyone
3. A well-calibrated threshold lets Q operate dynamically, achieving significantly better latency

---

## Results Summary

| Metric | Strict (0.90) | Relaxed (0.75) |
|--------|--------------|----------------|
| Throughput | ~230 tok/s | ~230 tok/s |
| TTFT P50 | 7824 ms | **783 ms** (10× better) |
| TTFT P99 | 9750 ms | **5232 ms** (1.9× better) |
| Phase A TTFT P99 | 8900 ms | **1050 ms** (8.5× better) |
| Phase B TTFT P99 | 9750 ms | **5232 ms** (1.9× better) |
| Q range | 1200–2800 (mostly at floor) | 1200–5250 (clear sawtooth) |

---

## Plot Descriptions

### `plot_relaxed_v2.png` — Relaxed threshold (0.75)

The most important plot. Six panels:

- **Q Trajectory (top-left):** Clear AIMD sawtooth — Q climbs additively during Phase A (light load), then drops multiplicatively when Phase B violations fire. Q operates between 1200 and 5250, confirming the control loop is closed and responsive to load changes.
- **AIMD Signals (top-right):** Jain (control) oscillates above and below the 0.75 threshold. p99_ttft_ms stays low (~11–17 ms in the AIMD window), meaning the server itself is fast — the high client-side TTFT comes from queuing, not compute.
- **Q vs AIMD p99 TTFT (mid-left):** Scatter of Q values vs server-side p99 TTFT. Shows that higher Q correlates with slightly higher server-side latency (dominant clients get more budget), but the relationship is bounded.
- **TTFT (mid-right):** Per-request TTFT over time. P50=783 ms, P99=3232 ms. The rolling mean rises during Phase B then stabilizes — no runaway starvation.
- **Throughput Trend (bottom-left):** Cumulative throughput ~230 tok/s, stable across both phases.
- **TTFT Distribution (bottom-right):** Left-skewed with most requests under 2000 ms and a moderate tail.

---

### `plot_strict_v2.png` — Strict threshold (0.90)

- **Q Trajectory (top-left):** Q crashes to Q_MIN=1200 within the first few steps and stays there almost the entire run. The 0.90 threshold sits above the workload's natural Jain floor (~0.82), so violations fire almost continuously. q_max=2800 (one brief escape), direction_changes=3.
- **AIMD Signals (top-right):** Jain (control) oscillates between ~0.3–0.9 but spends most time below the 0.90 threshold line. Violations are nearly constant.
- **TTFT (mid-right):** P50=7824 ms, P99=9750 ms — 10× worse than relaxed. Bimodal distribution: dominant clients complete quickly (cache hits), cold clients queue for 8–10 seconds.
- **TTFT Distribution (bottom-right):** Heavy right tail with many requests at 7000–10000 ms, confirming severe cold-client starvation.

**Interpretation:** Forcing Q to Q_MIN=1200 eliminates the LPM (cache-greedy) advantage entirely. The scheduler can no longer batch cache-hitting requests efficiently, so every prefill is effectively a cold start. This increases total prefill work and causes deep queuing for all clients — including cold ones.

---

### `plot_ab_compare_v2.png` — Side-by-side comparison

Four bar charts comparing strict (blue) vs relaxed (orange):

- **Overall Throughput:** Identical (~230 tok/s). The scheduler choice does not change how many tokens the GPU processes — only how those tokens are distributed over time.
- **Overall TTFT P50:** Strict 7824 ms vs Relaxed 783 ms. The median request under strict waits 10× longer for its first token.
- **Overall TTFT P99:** Strict 9750 ms vs Relaxed 5232 ms.
- **Phase TTFT P99:** Strict is worse in both Phase A and Phase B independently, ruling out the phase transition as a confound.

---

## Limitations

- This is **not** the core paper experiment. It compares two Adaptive DLPM configurations, not Adaptive DLPM vs Static DLPM vs LPM.
- The strict case's poor performance reflects a misconfigured threshold (0.90 > natural Jain floor), not a fundamental flaw in strict fairness enforcement.
- Next step: run all five cases (LPM, Static DLPM at Q=1200/4000/8000, Adaptive DLPM) through the same two-phase workload to demonstrate Pareto-dominance.
