# LooGLE Starvation v4: Paper Summary

## Scope and Goal
This summary captures the v4 starvation-focused LooGLE-prefix experiment and what it shows about Adaptive DLPM relative to FCFS, LPM, and static DLPM variants.

Primary question:
- Under mixed dominant/cold traffic, does Adaptive DLPM control starvation risk while preserving throughput?

## Experimental Method
Workload and setup:
- Dataset: `loogle_prefix`
- Rate / K: `rate=5`, `k=1.0`
- Request count: `1800`
- Max concurrency: `8`
- Mix: `dominant_fraction=0.85`, `chunked`, `chunk_size=180`, `strict_cold=true`
- Token cap: `--loogle-max-input-tokens 12000`
- Timeout: `2400`

Policies evaluated (merged 6-policy view):
- `adaptive_dlpm`
- `fcfs`
- `lpm`
- `dlpm_q1200`
- `dlpm_q4000`
- `dlpm_q8000`

Data sources:
- `results/modal_grid_20260426_000325`
- `results/modal_grid_20260426_005716`
- merged into `results/modal_grid_20260426_v4_merged`

## Evaluation Protocol
Metrics used:
- Throughput (tokens/sec)
- TTFT P50/P95/P99 overall
- TTFT subgroup tails for `dominant` vs `cold`
- Success rate

Why subgroup metrics matter:
- Overall latency can hide starvation; starvation appears as inflated cold-client tails relative to dominant clients.

## Results (Key Evidence)
From `results/modal_grid_20260426_v4_merged/summary.csv` and `docs/plots/loogle_starvation_v4/loogle_starvation_v4_summary.md`.

Overall TTFT P99 (lower is better):
1. adaptive_dlpm: `661.8 ms`
2. dlpm_q1200: `682.8 ms`
3. dlpm_q8000: `700.4 ms`
4. dlpm_q4000: `713.3 ms`
5. fcfs: `1098.4 ms`
6. lpm: `1264.2 ms`

Throughput:
- All policies are tightly clustered around `46 tok/s`.
- Conclusion: ranking differences are latency/scheduling effects, not throughput differences.

Cold-client TTFT P99:
1. dlpm_q1200: `916.0 ms`
2. dlpm_q8000: `961.4 ms`
3. adaptive_dlpm: `1010.3 ms`
4. dlpm_q4000: `1103.0 ms`
5. fcfs: `1144.0 ms`
6. lpm: `1805.5 ms` (worst)

Dominant-client TTFT P99:
1. adaptive_dlpm: `554.0 ms`
2. dlpm_q1200: `604.9 ms`
3. dlpm_q8000: `634.8 ms`
4. dlpm_q4000: `639.9 ms`
5. fcfs: `1080.4 ms`
6. lpm: `1096.3 ms`

## What This Shows About Adaptive DLPM
1. Adaptive DLPM is the best overall tail policy in this v4 setting.
2. Adaptive strongly outperforms LPM on cold-tail latency (anti-starvation signal).
3. Adaptive is not best on cold-tail P99 vs every static Q (q1200 and q8000 are lower), but remains the strongest balanced policy across overall and dominant/cold views.
4. FCFS is not the top fairness policy in this high-dominant/high-locality regime.

Balanced interpretation for paper:
- Adaptive DLPM provides the best overall tail-latency/throughput operating point.
- LPM exhibits the clearest cold-tail weakness in this run.
- Static Q can beat Adaptive on one subgroup metric, but Adaptive is more robust across views.

## Recommended Plots to Include in Paper
1. `docs/plots/loogle_starvation_v4/loogle_starvation_v4_ttft_p99_vs_rate.png`
- Illustrates overall tail ranking across policies.
- Use this as the primary policy comparison figure.

2. `docs/plots/loogle_starvation_v4/loogle_starvation_v4_subset_breakdown.png`
- Shows dominant vs cold subgroup behavior.
- Critical for starvation claims; highlights LPM cold-tail degradation.

3. `docs/plots/loogle_starvation_v4/loogle_starvation_v4_pareto.png`
- Shows latency-throughput tradeoff frontier.
- Supports claim that Adaptive is strong without throughput loss.

4. `docs/plots/loogle_starvation_v4/loogle_starvation_v4_throughput_vs_rate.png`
- Confirms throughput parity among policies.
- Prevents misinterpretation that latency gains come from reduced work.

5. `docs/plots/loogle_starvation_v4/loogle_starvation_v4_ttft_percentile_hist.png`
- Shows distribution shape beyond single P99 points.
- Useful to show tail heaviness patterns.

6. `docs/plots/loogle_starvation_v4/loogle_starvation_v4_aimd_overview.png`
- Shows adaptive controller operating region/Q behavior.
- Supports controller interpretability discussion.

## Suggested Paper Claim (Concise)
In the v4 LooGLE-prefix stress setting, Adaptive DLPM achieves the best overall TTFT tail while maintaining throughput parity with all baselines. LPM has the worst cold-client tail, indicating starvation risk under locality-heavy scheduling. Static DLPM at specific Q values can outperform Adaptive on a single subgroup tail metric, but Adaptive provides the strongest overall robust operating point across aggregate and subgroup views.
