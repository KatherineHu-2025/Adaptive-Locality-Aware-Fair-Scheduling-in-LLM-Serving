# Analysis: modal_grid_20260424_235859

## Run Context
- Results folder: `results/modal_grid_20260424_235859`
- Exact command used:

```cmd
set AIMD_MULT_FACTOR=0.65 && python benchmark_modal_service_loogle_prefix_grid.py --request-counts 1500 --loogle-prefix-dominant-fraction 0.5 --loogle-prefix-mix-mode chunked --loogle-prefix-chunk-size 40 --max-concurrency 8 --aimd-jain-threshold 0.72 --rates 4 --static-q-values 4000 --aimd-ttft-slo-ms 4000 --aimd-q-min 2200 --stop-service-at-end --loogle-prefix-strict-cold
```

## v6 Standalone Summary
- Policies: adaptive_dlpm, dlpm_q4000, lpm, fcfs
- Request count per policy: 1500, all successful
- Throughput leader: adaptive_dlpm (34.670 tok/s)
- Best overall TTFT P99: fcfs (4518.194 ms)
- Best dominant TTFT P99: adaptive_dlpm (2574.866 ms)
- Worst cold TTFT P99: adaptive_dlpm (4884.052 ms)

## Comparison Across Versions
Reference folders:
- v3: `results/modal_grid_20260424_001827`
- v4: `results/modal_grid_20260424_184711`
- v5: `results/modal_grid_20260424_212104`
- v6: `results/modal_grid_20260424_235859`

### Adaptive DLPM throughput
- v3: 34.630 tok/s
- v4: 32.935 tok/s
- v5: 34.433 tok/s
- v6: 34.670 tok/s
- v6 is the best throughput of the four.

### Adaptive DLPM TTFT P99
- v3: 4801.150 ms
- v4: 6527.214 ms
- v5: 4907.639 ms
- v6: 4714.167 ms
- v6 is the best adaptive TTFT P99 of the four.

### Adaptive DLPM median Q
- v3: 3550
- v4: 16000
- v5: 1700
- v6: 2200
- v6 sits between v5 and v3, which looks much more reasonable than v4.

### Adaptive DLPM violation rate
- v3: 793 / 7999 (~9.9%)
- v4: 211 / 15970 (~1.3%)
- v5: 763 / 6000 (~12.7%)
- v6: 1142 / 6000 (~19.0%)
- v6 is more reactive than v5, which likely helped dominant behavior and overall throughput, but it also means the controller is still quite active.

## Dominant vs Cold Behavior
### Dominant TTFT P99
- v3: 2800.138 ms
- v4: 6900.288 ms
- v5: 2071.080 ms
- v6: 2574.866 ms

### Cold TTFT P99
- v3: 5224.436 ms
- v4: 6110.291 ms
- v5: 5437.096 ms
- v6: 4884.052 ms

Interpretation:
- v6 improves cold tail over v3/v4/v5, which is a good sign.
- v6 is worse than v5 on dominant tail, but still much better than v3 and far better than v4.
- This run is the best cold-tail result you have seen so far for adaptive DLPM, while keeping throughput high.

## Static Policy Comparison in v6
- `dlpm_q4000` still gives strong throughput (34.282 tok/s) and the best dominant TTFT P99 among the policies in this run (2440.779 ms).
- `lpm` has the best overall TTFT P99 in v6 (4535.418 ms), but throughput is lower than adaptive and dlpm_q4000.
- `fcfs` remains the best overall tail-latency reference in the earlier runs, but in v6 its throughput is the weakest of the four.

## Is This the Ideal Behavior?
Short answer: **closer, but still not fully ideal**.

What looks good:
- adaptive DLPM now has the best throughput of all tested versions.
- adaptive DLPM improved cold tail relative to v3/v4/v5.
- adaptive DLPM remains clearly competitive on dominant client latency.
- Q is no longer pinned at the extremes seen in earlier runs.

What still looks imperfect:
- adaptive still has the worst cold TTFT P99 among policies in this v6 run.
- the control loop is fairly active, so there may still be some oscillation.
- overall TTFT P99 is still best under `fcfs` or `lpm`, not adaptive.

## Practical Conclusion
If your goal is:
- maximize throughput and dominant-client locality, v6 is strong.
- improve cold-tail fairness enough that adaptive no longer looks obviously worse than the baselines, v6 is an improvement over earlier versions.

If your goal is the strictest definition of “ideal,” meaning:
- adaptive should win or at least not lose on cold TTFT P99,
- while keeping dominant TTFT P99 strong,
- then you are close, but not there yet.

## Suggested Next Direction
The most promising next adjustment is to make adaptive a bit less reactive on cold-tail spikes while keeping dominant locality benefits:
1. Keep `AIMD_MULT_FACTOR=0.65`.
2. Lower Jain slightly only if needed; do not tighten aggressively yet.
3. Consider increasing `--aimd-q-min` only modestly, or try a slightly higher `--aimd-ttft-slo-ms` if you want to reduce overreaction.

## Generated Artifacts
- `docs/plots/loogle_prefix_v6/modal_grid_20260424_235859_throughput_vs_rate.png`
- `docs/plots/loogle_prefix_v6/modal_grid_20260424_235859_ttft_p99_vs_rate.png`
- `docs/plots/loogle_prefix_v6/modal_grid_20260424_235859_ttft_request_hist.png`
- `docs/plots/loogle_prefix_v6/modal_grid_20260424_235859_request_total_hist.png`
- `docs/plots/loogle_prefix_v6/modal_grid_20260424_235859_aimd_overview.png`
- `docs/plots/loogle_prefix_v6/modal_grid_20260424_235859_summary.md`
