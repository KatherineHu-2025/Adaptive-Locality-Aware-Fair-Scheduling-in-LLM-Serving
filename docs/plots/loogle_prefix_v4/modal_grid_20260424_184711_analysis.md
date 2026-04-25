# Analysis: modal_grid_20260424_184711

## Run Context
- Results folder: `results/modal_grid_20260424_184711`
- Exact command used:

```cmd
set AIMD_MULT_FACTOR=0.65 && python benchmark_modal_service_loogle_prefix_grid.py --request-counts 4000 --loogle-prefix-dominant-fraction 0.5 --loogle-prefix-mix-mode chunked --loogle-prefix-chunk-size 40 --max-concurrency 8 --aimd-jain-threshold 0.70 --rates 4 --static-q-values 4000 --aimd-ttft-slo-ms 4500 --stop-service-at-end --loogle-prefix-strict-cold
```

## v4 Standalone Summary
- Policies: adaptive_dlpm, dlpm_q4000, lpm, fcfs
- Request count per policy: 4000 (adaptive successful: 3971/4000)
- Throughput leader: `dlpm_q4000` (33.890 tok/s)
- Best overall TTFT P99: `fcfs` (4369.574 ms)
- Best dominant TTFT P99: `dlpm_q4000` (1928.097 ms)
- Worst cold TTFT P99: `adaptive_dlpm` (6110.291 ms)

## v4 vs v3 (direct comparison)
Reference v3 folder: `results/modal_grid_20260424_001827`

### Adaptive DLPM
- Throughput: 34.630 -> 32.935 tok/s (down ~4.9%)
- TTFT P50: 1342.664 -> 1375.405 ms (slightly worse)
- TTFT P99: 4801.150 -> 6527.214 ms (worse by ~35.9%)
- Success count: 2000/2000 -> 3971/4000 (29 failures in v4)
- Dominant TTFT P99: 2800.138 -> 6900.288 ms (much worse)
- Cold TTFT P99: 5224.436 -> 6110.291 ms (worse)
- Median adaptive Q: 3550 -> 16000 (much higher)
- AIMD violation rows: 793/7999 (~9.9%) -> 211/15970 (~1.3%)

### Static policies
- `dlpm_q4000`: throughput slightly down, TTFT P99 slightly improved
- `fcfs`: throughput slightly up, TTFT P99 roughly flat/slightly worse
- `lpm`: throughput slightly down, TTFT P99 slightly worse

## Interpretation
The v4 tuning (`AIMD_MULT_FACTOR=0.65`, relaxed Jain/TTFT thresholds) appears to have made adaptive DLPM less reactive (fewer violations, higher sustained Q), but in this run it harmed adaptive tail behavior and reliability.

In other words, adaptive likely stayed at high Q too often for this workload phase, which increased queueing pressure and produced:
- higher dominant and cold P99 TTFT,
- lower adaptive throughput,
- and non-zero failures.

## Is this the ideal behavior?
Short answer: **No** for the adaptive objective you were targeting.

If your goal is for adaptive DLPM to be competitive with static Q=4000 on throughput while improving/maintaining tail fairness, this v4 result is a regression relative to v3.

What looks good:
- Reduced control thrash (fewer violation-triggered events).

What looks bad:
- Tail latency got materially worse for adaptive (especially dominant stream),
- Adaptive lost throughput vs v3,
- Adaptive introduced failures.

## Suggested next tuning step
To move back toward a better tradeoff, tighten control modestly from v4:
1. Keep `AIMD_MULT_FACTOR=0.65`.
2. Lower `--aimd-ttft-slo-ms` from 4500 to around 4000-4200.
3. Raise `--aimd-jain-threshold` from 0.70 back toward 0.72.

This should keep Q from pinning too high while avoiding the harsher 0.5 multiplicative drops.
