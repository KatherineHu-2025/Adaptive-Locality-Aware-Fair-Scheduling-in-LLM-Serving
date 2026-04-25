# Analysis: modal_grid_20260425_010727

## Run Context
- Results folder: `results/modal_grid_20260425_010727`
- Exact plot command used:

```cmd
venv\Scripts\python.exe plot_benchmark_result.py results\modal_grid_20260425_010727 --output-dir docs\plots\loogle_prefix_v7
```

## v7 Standalone Summary
- Policies: adaptive_dlpm, dlpm_q1000, dlpm_q4000, dlpm_q16000, lpm, fcfs
- Request count per policy: 1500, all successful
- Throughput leader: lpm (34.324 tok/s)
- Best overall TTFT P99: fcfs (4398.107 ms)
- Best dominant TTFT P99: dlpm_q1000 (1656.684 ms)
- Adaptive DLPM median Q: 2500
- Adaptive AIMD violation rows: 730 / 9000 (~8.1%)

## Comparison Across Versions (v3-v7)
Reference folders:
- v3: `results/modal_grid_20260424_001827`
- v4: `results/modal_grid_20260424_184711`
- v5: `results/modal_grid_20260424_212104`
- v6: `results/modal_grid_20260424_235859`
- v7: `results/modal_grid_20260425_010727`

### Adaptive DLPM Throughput
- v3: 34.630 tok/s
- v4: 32.935 tok/s
- v5: 34.433 tok/s
- v6: 34.670 tok/s
- v7: 33.618 tok/s

Interpretation:
- v7 throughput regressed versus v5/v6 and is closer to v4 than to the best runs.

### Adaptive DLPM TTFT P99
- v3: 4801.150 ms
- v4: 6527.214 ms
- v5: 4907.639 ms
- v6: 4714.167 ms
- v7: 4740.193 ms

Interpretation:
- v7 tail latency is better than v3/v5 and dramatically better than v4.
- v7 is slightly worse than v6 on overall adaptive TTFT P99 (+26 ms), so it is close but not a new best.

### Adaptive DLPM Dominant TTFT P99
- v3: 2800.138 ms
- v4: 6900.288 ms
- v5: 2071.080 ms
- v6: 2574.866 ms
- v7: 2444.245 ms

Interpretation:
- v7 is a clear dominant-tail improvement over v3/v4/v6.
- v5 remains best on dominant-tail latency.

### Adaptive DLPM Cold TTFT P99
- v3: 5224.436 ms
- v4: 6110.291 ms
- v5: 5437.096 ms
- v6: 4884.052 ms
- v7: 5310.311 ms

Interpretation:
- v7 cold tail regressed from v6 and is only slightly better than v3.
- This suggests the new setting leaned back toward dominant-client preference.

### Adaptive Median Q (AIMD)
- v3: 3550
- v4: 16000
- v5: 1700
- v6: 2200
- v7: 2500

Interpretation:
- v7 stays in a moderate Q range, avoiding v4-like runaway behavior.

## Static Policy Comparison in v7
- `lpm` is best throughput and gives strong overall TTFT P99 (4524 ms).
- `fcfs` remains the best overall tail-latency reference (4398 ms), but at lower throughput.
- `dlpm_q1000` gives the best dominant TTFT P99 and competitive throughput.
- `adaptive_dlpm` is no longer leading either throughput or overall/cold tail in v7.

## Is This Ideal Behavior?
Short answer: **no, v7 is not the ideal point yet**.

What is good:
- Dominant tail remains strong and improved vs v3/v6.
- Overall adaptive TTFT P99 is stable and near the best adaptive runs.
- Q dynamics appear controlled (no extreme runaway Q behavior).

What is not ideal:
- Throughput dropped versus v5/v6.
- Cold TTFT P99 regressed from v6.
- Adaptive does not lead any of the top-level metrics in this run.

## Practical Conclusion
- If your target is dominant-client responsiveness with acceptable global tail, v7 is reasonable.
- If your target is balanced dominant and cold behavior with top throughput, v6 still looks like the stronger tradeoff than v7.

## Generated Artifacts
- `docs/plots/loogle_prefix_v7/modal_grid_20260425_010727_throughput_vs_rate.png`
- `docs/plots/loogle_prefix_v7/modal_grid_20260425_010727_ttft_p99_vs_rate.png`
- `docs/plots/loogle_prefix_v7/modal_grid_20260425_010727_ttft_request_hist.png`
- `docs/plots/loogle_prefix_v7/modal_grid_20260425_010727_request_total_hist.png`
- `docs/plots/loogle_prefix_v7/modal_grid_20260425_010727_subset_breakdown.png`
- `docs/plots/loogle_prefix_v7/modal_grid_20260425_010727_aimd_overview.png`
- `docs/plots/loogle_prefix_v7/modal_grid_20260425_010727_summary.md`
