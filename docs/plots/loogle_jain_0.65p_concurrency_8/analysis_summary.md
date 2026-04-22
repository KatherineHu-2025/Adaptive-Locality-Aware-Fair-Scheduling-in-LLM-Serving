# LooGLE Jain=0.65 Concurrency=8 Analysis Summary

Source results: `results/modal_grid_20260421_171114/summary.csv`
Output folder: `docs/plots/loogle_jain_0.65p_concurrency_8/`
Run settings: `dataset=loogle`, `rate=1.0`, `k=1.0`, `max_concurrency=8`, `n in {25,50}`.

## Best-by-N (lower is better for TTFT, higher is better for throughput)

**TTFT P99 winners**
```text
 request_count policy  ttft_p99_ms
            25   fcfs     14329.73
            50   fcfs      2341.15
```

**TTFT P50 winners**
```text
 request_count policy  ttft_p50_ms
            25   fcfs       224.94
            50   fcfs       265.08
```

**Throughput winners**
```text
 request_count policy  throughput_tok_per_sec
            25   fcfs                  8.1679
            50    lpm                  9.2170
```

## Severe TTFT P99 Outliers (> 10,000 ms)
```text
       policy  request_count  ttft_p99_ms                                                               output_file
adaptive_dlpm             25     17473.62 results\modal_grid_20260421_171114\runs\adaptive_dlpm_r1.0_k1.0_n25.jsonl
         dlpm             25     19557.98    results\modal_grid_20260421_171114\runs\dlpm_q4000_r1.0_k1.0_n25.jsonl
         dlpm             50    382237.76    results\modal_grid_20260421_171114\runs\dlpm_q4000_r1.0_k1.0_n50.jsonl
         fcfs             25     14329.73          results\modal_grid_20260421_171114\runs\fcfs_r1.0_k1.0_n25.jsonl
          lpm             25     37645.74           results\modal_grid_20260421_171114\runs\lpm_r1.0_k1.0_n25.jsonl
```

## Adaptive AIMD Behavior (Jain=0.65, concurrency=8)

n=25: violation_rate=45.70%  Q_min=1200.0  Q_max=4000.0  Q_unique=6  reasons={'none': 101, 'jain': 85}
n=50: violation_rate=100.00%  Q_min=1200.0  Q_max=1200.0  Q_unique=1  reasons={'jain': 383}

## Key Findings

1. With higher concurrency, FCFS is the P99 winner at both n=25 and n=50; adaptive is second-best at n=50 and avoids the extreme DLPM tail.
2. DLPM Q=4000 shows a catastrophic tail at n=50 (P99 >> 100k ms), indicating the fixed Q is too small under heavier queue pressure.
3. Adaptive (J=0.65) maintains competitive P50/P99 at n=50 while keeping throughput near the other policies, but still shows heavy AIMD violation at this load.

## Recommended Next Steps

1. Increase `max_concurrency` further (e.g., 16) at n=50 to see whether adaptive improves relative to FCFS when queues are deeper.
2. Re-run with `arrival_mode=sequential` for LooGLE to emulate multi-turn behavior and compare against this per-client Gamma mode.
3. If DLPM continues to blow up at Q=4000, test higher static Q (e.g., 8000/16000) under concurrency=8 for a fair baseline.
4. If AIMD remains always violating at n=50, try a small threshold sweep (0.62–0.66) while keeping concurrency=8 to check if non-violation intervals appear.