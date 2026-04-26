# LooGLE Starvation Analysis (V1 - Merged)

Date: 2026-04-25

**Merged from:**
- `results/modal_grid_20260425_142407/` (static DLPM: q1200, q4000, q8000)
- `results/modal_grid_20260425_145946/` (adaptive_dlpm, fcfs, lpm)

## TL;DR: This Is NOT The Starvation Behavior You Want

**Your goal:** 
- FCFS and Adaptive do BEST (lowest P99)
- LPM does WORST (highest P99, demonstrates starvation)

**Actual results:**
- LPM does BEST (P99: 2751 ms at n=50)
- FCFS does WORST (P99: 29143 ms at n=25, 3263 ms at n=50)
- Adaptive is middle-bad (P99: 3138 ms at n=50)

✗ **This is the OPPOSITE of ideal.** LPM is winning, not losing.

---

## Policy Comparison: Median P99 Tail Latency

Ranked best → worst on tail latency:
```text
1. lpm              10818.4 ms  ← should be WORST but is BEST
2. dlpm              12772.6 ms
3. adaptive_dlpm     15471.9 ms
4. fcfs              16203.2 ms  ← should be BEST but is WORST
```

### At n=50 (Less Outlier-Prone)
Ranked best → worst:
```text
1. lpm              2751.1 ms   ← BEST
2. dlpm_q8000       3118.9 ms
3. adaptive_dlpm    3137.8 ms
4. dlpm_q4000       3352.6 ms
5. fcfs             3263.2 ms   ← WORST
```

### At n=25 (Outlier-Heavy)
Ranked worst → best via P99:
```text
1. fcfs             29143.2 ms  ← severe tail outlier (worst)
2. adaptive_dlpm    27806.0 ms
3. dlpm_q1200       28374.1 ms
4. dlpm_q8000       24405.9 ms
5. dlpm_q4000       22182.9 ms
6. lpm              18885.7 ms  ← best on P99 here too
```

---

## Throughput (All Tied)
```text
All policies:   ~36.87-36.90 tok/s at n=50
                ~32.67-32.76 tok/s at n=25
```
Throughput penalty is negligible across all policies.

---

## Why LPM Is Winning (Not Starvation)

**Plain `loogle` dataset has no explicit hot-cold split.**

- All requests are drawn from a mixed-distribution workload with no dominant prefix cache reuse pattern.
- **LPM (Length-Prepared-First)** is greedy for short-latency requests, which helps in a uniform workload:
  - Shorter TTFT for short responses (P50: 870 ms, the best)
  - Overall lower scheduling overhead.
- Without explicit competing hot/cold traffic, LPM doesn't show classic starvation (cold clients getting starved indefinitely).
- **FCFS** does worse because it processes requests in order without any optimization for latency, and at high concurrency (n=25 outliers), long-context requests block the queue.

**Starvation** only emerges in a **two-tier workload:**
- **Tier 1 (hot/dominant):** Short prefixes, high reuse → LPM loves these
- **Tier 2 (cold):** Long prefixes, low reuse → LPM deprioritizes these

When Tier 2 requests are delayed indefinitely by Tier 1, that's starvation. With uniform `loogle`, there's no Tier 2 to starve.

---

## Why Adaptive Didn't Win

Adaptive DLPM uses Q (prefix-cache threshold) controlled by AIMD based on Jain index violations.

**In this run:**
- Adaptive Q clamped at Q_MIN = 1200 (from `--aimd-jain-threshold 0.63`)
- Only 481 out of 3414 requests triggered violations (14%), so Q had little room to grow.
- With Q_MIN so restrictive, prefixing is disabled for nearly all requests → behaves like FCFS.
- Hence adaptive performed similar to FCFS (both worse than LPM).

---

## Comparison: Static Qs

Best static DLPM Q **varies by load:**
- **n=25:** `dlpm_q4000` wins (P99: 22182 ms) — but all static Qs are bad (20k+ ms P99)
- **n=50:** `dlpm_q8000` wins (P99: 3118 ms)

This reinforces the **Q brittleness** problem: no single Q works across n=25 and n=50.

---

## Verdict: Not Ideal for Your Goal

| Desired Behavior | Actual Result | Status |
|---|---|---|
| FCFS best on P99 | FCFS worst (16203 ms median, 29143 ms outlier at n=25) | ✗ Failed |
| Adaptive best on P99 | Adaptive middle-bad (15471 ms median) | ✗ Failed |
| LPM worst on P99 | LPM best (10818 ms median, 2751 ms at n=50) | ✗ Failed |

---

## How to Fix: Use `loogle_prefix` for Explicit Starvation

To observe **true starvation**, you need:
1. **Explicit dominant/cold split** in client traffic.
2. **LPM should over-favor dominant prefix traffic** and starve cold clients.
3. **Adaptive should dynamically reduce Q** to protect cold clients.
4. **FCFS should give fair service** to both groups.

### Recommended Next Run

```bash
set AIMD_MULT_FACTOR=0.65 && python benchmark_modal_service_loogle_prefix_grid.py \
  --request-counts 1500 \
  --loogle-prefix-dominant-fraction 0.5 \
  --loogle-prefix-mix-mode chunked \
  --loogle-prefix-chunk-size 40 \
  --max-concurrency 8 \
  --aimd-jain-threshold 0.63 \
  --rates 4 \
  --static-q-values 1200,4000,8000 \
  --aimd-ttft-slo-ms 4000 \
  --stop-service-at-end \
  --loogle-prefix-strict-cold
```

**Why this fixes it:**
- **`--loogle-prefix-dominant-fraction 0.5`** → 50% requests are hot (prefix cache reused), 50% cold (unique prefixes).
- **`--loogle-prefix-mix-mode chunked`** → Cold requests arrive in bursts, not interleaved. This creates queue depth and forces scheduling decisions.
- **LPM will deprioritize cold bursts** while favoring hot clients → visible cold-client starvation (long tails).
- **Adaptive can reduce Q** when Jain index drops (fairness violated) → protect cold clients.
- **FCFS treats both equally** → should show consistent, fair latency across both groups.

### Tuning Knobs If Starvation Signal Is Still Weak

1. **Lower `--loogle-prefix-dominant-fraction`** to `0.3` or `0.2` → More cold requests = stronger starvation pressure.
2. **Increase `--max-concurrency`** to `12` or `16` → Deeper queue = more scheduling choices available.
3. **Increase `--rates`** to `5` or `6` req/s → Higher load intensifies starvation.
4. **Increase `--request-counts`** to `2000` or `4000` → Longer run = more tail data.
5. **Adjust `--aimd-jain-threshold`** in `{0.60, 0.65}` to see if Q control becomes more responsive.

---

## Files in This Directory

- `loogle_starvation_v1_summary.md` — Auto-generated benchmark summary (merged data)
- `loogle_starvation_v1_pareto.png` — Pareto frontier by rate/k
- `loogle_starvation_v1_ttft_p99_vs_rate.png` — P99 tail latency across policies
- `loogle_starvation_v1_throughput_vs_rate.png` — Throughput comparison
- `loogle_starvation_v1_ttft_percentile_hist.png` — Percentile histograms
- `loogle_starvation_v1_ttft_request_hist.png` — TTFT by request index
- `loogle_starvation_v1_request_total_hist.png` — End-to-end request latency
- `loogle_starvation_v1_aimd_overview.png` — Adaptive DLPM Q trajectory
- `loogle_starvation_v1_aimd_violation_reasons.png` — AIMD violation breakdown
- `loogle_starvation_v1_aimd_traces/` — Per-run Q traces
- `analysis_summary.md` — This file

---

## Next Steps

1. **Run the recommended `loogle_prefix` command** above.
2. **Plot and analyze the new results** to confirm starvation pattern (LPM worst, FCFS/Adaptive best).
3. **Sweep `--loogle-prefix-dominant-fraction`** and `--max-concurrency`** to calibrate starvation strength if needed.
