# LooGLE Paper Summary (What to Include)

This summary focuses on what LooGLE contributes to the paper, what it demonstrates about Adaptive DLPM, and which plots/data belong in the final writeup. It uses the latest LooGLE analyses and run summaries in this repo.

## Why LooGLE Matters (vs Synthetic and Chatbot Arena)

- LooGLE is a cold-prefix stress test: long contexts, low prefix reuse across documents, short answers. It highlights fairness and starvation risks when cache locality is weak.
- Synthetic lets you shape dominant/cold traffic patterns, but it is not real text and can over-fit to your workload model.
- Chatbot Arena is multi-turn and locality-rich, which is where LPM can shine but also starve cold clients. LooGLE provides the counter-regime where locality is weak and static tuning can fail.

Conclusion to include: LooGLE validates robustness and failure modes in the cold-prefix regime. It is a necessary complement to synthetic and Chatbot Arena because it tests adaptive behavior when locality is minimal and long-prefill dominates.

## Key LooGLE Conclusions to Include (Evidence-Based)

1. **Static DLPM is brittle on long-context, cold-prefix workloads.**
   - In real-weights LooGLE, static DLPM (Q=4000) shows catastrophic tail (P99 ~148s) while other policies stay below ~25s.
   - This is a strong negative result that motivates Adaptive DLPM or per-workload Q tuning.

2. **Adaptive DLPM avoids catastrophic tails and is a robust middle ground.**
   - In multiple LooGLE slices, adaptive consistently avoids the worst DLPM tail while keeping throughput similar to FCFS/LPM.
   - It is not always the lowest P99, but it suppresses extreme failures in the cold-prefix regime.

3. **LooGLE reveals the limit of fairness control under cold-prefix traffic.**
   - In the rate=1.0, k=1.0 baseline, AIMD is often fully violated (Jain-driven) and Q clamps to Q_min, showing that the controller cannot open up locality when fairness is always violated.
   - This is an honest limitation you can report and use to motivate workload-dependent tuning or alternate fairness thresholds.

4. **Threshold sensitivity is real: no single Jain threshold is universally best.**
   - J=0.65 is best at n=50 in the 0.60/0.63/0.65 sweep, but J=0.63 performs better at n=25 and n=100.
   - J=0.60 can be unstable (extreme tail outlier at n=25), which argues against overly relaxed thresholds in this workload.

5. **Under higher concurrency, FCFS often wins P99, while LPM can collapse.**
   - With max_concurrency=8, FCFS is the P99 winner at both n=25 and n=50; DLPM can blow up at n=50 (P99 >> 100k ms).
   - Adaptive remains competitive and avoids the worst DLPM failure.

## Static DLPM Q Sweep vs Adaptive (Final LooGLE Run)

Source: results/modal_grid_loogle_final_results/summary.csv (merged with modal_grid_20260421_185446 and the static Q sweep)

All values are `rate=1.0, k=1.0`; Adaptive is J=0.63 (same run set as FCFS/LPM).

### n=25

| Policy | Q | Throughput (tok/s) | P50 (ms) | P99 (ms) |
|---|---:|---:|---:|---:|
| DLPM | 1000 | 8.17 | 13075.24 | 29679.21 |
| DLPM | 2000 | 8.17 | 510.90 | 24205.37 |
| DLPM | 4000 | 8.17 | 578.51 | 29347.32 |
| DLPM | 8000 | 8.17 | 11711.60 | 168522.25 |
| DLPM | 16000 | 8.17 | 550.20 | 23576.37 |
| DLPM | 32000 | 8.17 | 1863.22 | 24080.49 |
| Adaptive (J=0.63) | — | 8.17 | 573.04 | 18220.36 |

Takeaway (n=25): best static P99 is DLPM Q=16000 (23576 ms), but Adaptive (18220 ms) is still better on P99 by ~29%. Static Q is highly unstable across values (e.g., Q=8000 is catastrophic).

### n=50

| Policy | Q | Throughput (tok/s) | P50 (ms) | P99 (ms) |
|---|---:|---:|---:|---:|
| DLPM | 1000 | 9.22 | 3964.12 | 15883.49 |
| DLPM | 2000 | 9.22 | 630.47 | 2885.95 |
| DLPM | 4000 | 9.22 | 941.44 | 57694.08 |
| DLPM | 8000 | 9.22 | 1534.70 | 151516.06 |
| DLPM | 16000 | 9.22 | 645.40 | 2888.50 |
| DLPM | 32000 | 9.22 | 1301.18 | 12103.15 |
| Adaptive (J=0.63) | — | 9.22 | 698.13 | 3274.94 |

Takeaway (n=50): best static P99 is DLPM Q=2000 (2885 ms), beating Adaptive (3275 ms) by ~11.9% while keeping throughput identical. Static Q performance is highly sensitive and no single Q dominates both n=25 and n=50.

**Overall message:** static DLPM can beat Adaptive at a specific Q and n, but it is brittle; Adaptive provides more stable tail behavior across n and avoids catastrophic failures seen at other Q values.

## What Plots/Data to Include in the Paper

### Must-Include LooGLE Figures

1. **Real-weights LooGLE tail comparison (log CDF + Pareto)**
   - Source: docs/plots/loogle_real_weights/loogle_comparison_ttft_log.png
   - Why: shows static DLPM catastrophic tail and adaptive robustness in real weights.

2. **Updated LooGLE baseline slice (rate=1, k=1, n=25/50)**
   - Source: docs/plots/loogle_updated_benchmark_and_plot/
   - Why: provides a clean, controlled baseline and reveals AIMD clamping.

3. **Jain-threshold sweep comparison**
   - Source: docs/plots/loogle_63p_jain_concurrency_16/loogle_63p_jain_concurrency_16_threshold_comparison_summary.md
   - Use the threshold comparison plots:
     - loogle_63p_jain_concurrency_16_adaptive_metrics_by_threshold.png
     - loogle_63p_jain_concurrency_16_adaptive_p99_pairwise_improvement.png
   - Why: shows adaptive sensitivity and supports the threshold selection argument.

4. **Concurrency=8 stress test summary**
   - Source: docs/plots/loogle_jain_0.65p_concurrency_8/
   - Use: throughput/P99 plots plus AIMD traces and analysis_summary.md
   - Why: highlights FCFS P99 dominance, DLPM tail failure, adaptive robustness under queue pressure.

### Optional (If Space Allows)

- LooGLE grid (rate/k sweep) summary in docs/plots/loogle_grid_results/loogle_analysis_summary.md
- Adaptive AIMD traces to show clamping vs variation:
  - loogle_updated_benchmark_and_plot_aimd_traces/trace_001_r1_k1_n25.png
  - loogle_updated_benchmark_and_plot_aimd_traces/trace_002_r1_k1_n50.png

## What To Say About Adaptive DLPM on LooGLE (Paper Text)

Suggested phrasing:

- "On LooGLE, static DLPM with fixed Q fails catastrophically under long-context, cold-prefix traffic. Adaptive DLPM avoids these extreme tails while preserving throughput, demonstrating robustness across regimes where locality is weak."
- "Adaptive DLPM is not always the latency-optimal policy on LooGLE (FCFS often wins P99), but it consistently prevents the pathological tails that appear with static Q and sometimes with LPM under higher concurrency."
- "Threshold sensitivity is significant: in our sweep, J=0.65 is best at n=50, while J=0.63 is better at n=25 and n=100, and J=0.60 is unstable. This motivates tuning or adaptive thresholding by workload."

## Evidence That Supports the "Greatness" of Adaptive DLPM

Use these evidence points to support strong claims (without overstating):

1. **Robustness:** avoids catastrophic tail latency where static DLPM fails (e.g., P99 ~148s at Q=4000 on real-weights LooGLE).
2. **No throughput penalty:** throughput is usually tied across policies in LooGLE, so adaptive does not sacrifice throughput while preventing extremes.
3. **Middle-ground tradeoff:** adaptive often beats LPM and DLPM on tail latency under pressure, even when FCFS wins absolute P99.
4. **Interpretability:** AIMD traces show when the controller clamps and why, giving a clear handle for tuning.

If you want a stronger "wins P50, loses P99" narrative, LooGLE alone is not ideal; use a custom hot/cold LooGLE variant or synthetic workload for that pattern, and use LooGLE to show robustness in the cold-prefix regime.

## Additional Results That Would Strengthen the Paper

These are high-value experiments that are missing or incomplete:

1. **Static Q sweep on LooGLE (Q=1000/2000/4000/8000/16000/32000)**
   - Completed at rate=1.0, k=1.0, n=25/50 under concurrency=16.
   - Use this sweep to identify the best static frontier and position adaptive relative to it.

2. **Higher load runs (rate=2.0/3.0) with concurrency ≥ 8**
   - Needed to show adaptive behavior under deeper queues.

3. **Completion-time metric (not just TTFT)**
   - Under chunked prefill, TTFT underestimates starvation. Completion time or time-in-queue should be reported.

4. **Multi-seed repeats for n=50 and n=100**
   - Needed to reduce variance and avoid conclusions from single-run tails.

5. **Custom hot/cold LooGLE variant**
   - If you want the P50 locality win vs P99 fairness win story, you need explicit prefix skew and cold arrivals.

6. **Sequential arrival-mode runs for LooGLE**
   - More realistic for multi-turn per-doc behavior and cache reuse.

## Most Recent LooGLE Runs to Cite

- LooGLE 0.63, concurrency=16, n=25/50/100:
  - results/modal_grid_20260421_185446
  - docs/plots/loogle_63p_jain_concurrency_16/

- LooGLE static Q sweep (final merged set, includes adaptive + baselines + dlpm_q*):
   - results/modal_grid_loogle_final_results/
   - docs/results/loogle_final_results/

- LooGLE 0.65, concurrency=8, n=25/50:
  - results/modal_grid_20260421_171114
  - docs/plots/loogle_jain_0.65p_concurrency_8/

- LooGLE 0.60 and 0.65 threshold sweep comparison:
  - docs/plots/loogle_63p_jain_concurrency_16/loogle_63p_jain_concurrency_16_threshold_comparison_summary.md

- LooGLE baseline refresh (rate=1, k=1, n=25/50):
  - results/modal_grid_20260419_160306
  - docs/plots/loogle_updated_benchmark_and_plot/

- LooGLE real-weights comparison:
  - docs/plots/loogle_real_weights/loogle_comparison_summary.md
