# LooGLE Grid Benchmark Summary

Date: 2026-04-15  
Source run folder: results/modal_grid_20260415_130050

## Workload and Configuration

- Benchmark driver: benchmark_modal_service_grid.py
- Dataset: loogle
- Policies: fcfs, lpm, adaptive_dlpm
- Arrival rates: 1.0, 2.0, 3.0 req/s
- Gamma k: 0.5, 1.0
- Request count: 30 (`max-reqs` for real-trace datasets)
- Arrival mode: per-client
- Timeout: 600 s
- Total rows: 18 (6 per policy)

## Headline Findings

1. Throughput differences are small; adaptive_dlpm has the highest median throughput, fcfs is a close second, lpm is slightly behind.
2. FCFS consistently delivers the best TTFT P50 and usually best TTFT P99 at matched `(rate, k)`.
3. LPM does not show a clear locality-driven throughput win on this LooGLE slice, but it has one strong P99 case at `(rate=1.0, k=1.0)`.
4. Tail metrics are dominated by timeout-clamped outliers (`~600,000 ms`) in many rows, especially at `k=0.5`.

## Core Metrics (Policy Medians)

| Policy | Throughput (tok/s) | TTFT P50 (ms) | TTFT P99 (ms) | Total Success |
|---|---:|---:|---:|---:|
| adaptive_dlpm | 0.665 | 2857.901 | 599852.846 | 168/180 (93.33%) |
| fcfs | 0.657 | 2337.134 | 352746.313 | 163/180 (90.56%) |
| lpm | 0.651 | 4107.824 | 303682.903 | 163/180 (90.56%) |

Interpretation of medians:
- Throughput: adaptive_dlpm is best, but by a narrow margin over fcfs (about 1.3%).
- TTFT P50: fcfs is clearly best; lpm is the slowest at median.
- TTFT P99: median values are heavily skewed by timeout-level outliers, so this column alone should not drive conclusions.

## Pairwise Wins Across 6 Matched `(rate, k)` Combinations

- Best throughput wins: adaptive_dlpm 4, fcfs 2, lpm 0
- Best TTFT P50 wins: fcfs 5, adaptive_dlpm 1, lpm 0
- Best TTFT P99 wins: fcfs 4, adaptive_dlpm 1, lpm 1

This shows a stable pattern: adaptive_dlpm slightly leads on throughput while fcfs dominates latency.

## Stratified View by Arrival Burstiness

`k=0.5` (burstier arrivals):
- Throughput median: adaptive_dlpm (0.691) > fcfs (0.680) > lpm (0.674)
- TTFT P50 median: fcfs (2219.657 ms) < adaptive_dlpm (2870.852 ms) << lpm (4109.623 ms)
- TTFT P99 median: all policies near timeout scale (`~596k-600k ms`)

`k=1.0` (Poisson baseline):
- Throughput median: fcfs (0.652) ~= adaptive_dlpm (0.649) > lpm (0.640)
- TTFT P50 median: fcfs (2383.678 ms) < adaptive_dlpm (2844.951 ms) << lpm (4106.025 ms)
- TTFT P99 median: fcfs (4041.267 ms) < adaptive_dlpm (4733.143 ms) < lpm (7298.023 ms)

In the non-bursty slice (`k=1.0`), fcfs is the clean latency winner and remains competitive on throughput.

## Outliers and Caveats

1. Many rows have `ttft_p99_ms` close to `600,000 ms`, matching the 600 s run timeout scale.
2. Because of those timeout-clamped tails, means and unfiltered P99 medians can be misleading.
3. Success rates are below 100% in all policies, so some throughput/latency values are conditioned on partial completion.
4. Jain index is tightly clustered (`~0.288-0.312`) and low across all rows; in this run it is not strongly discriminative between policies.

## What Property This Sweep Is Testing

This LooGLE grid is primarily a **fairness-vs-locality stress test** under long-context, mostly cold-prefix traffic:

1. Can locality-first policies (LPM) improve efficiency without hurting fairness/latency too much?
2. Can fairness-aware policies (Adaptive DLPM) protect tail behavior and completion under bursty arrivals?
3. Do policy orderings stay stable across `k=0.5` (bursty) and `k=1.0` (Poisson baseline)?

### Was It Successful?

Partially.

- Successful as a stress diagnostic: it clearly exposed severe tail instability/timeouts.
- Not fully successful as a clean fairness-vs-locality validation: timeout-clamped tails dominate P99 in many rows, which blurs policy separation.
- Practical conclusion: this run identifies an important bottleneck regime, but does not by itself conclusively validate the Adaptive DLPM fairness hypothesis on LooGLE.

## Why LooGLE Throughput Is Tiny (<1 tok/s) vs Chatbot Arena (~40+ tok/s)

Short answer: this is mostly a **metric/data regime effect**, not a simple bug.

1. Throughput here is computed as:
	- `sum(output_tokens of successful requests) / max(arrival_time)`
2. In the client, `arrival_time` is recorded when a request actually starts sending (`time.perf_counter() - t0`), and that happens inside the semaphore-gated section (`max_concurrency`). So it includes queueing delay under client-side backpressure.
3. LooGLE has extremely long prompts and short answers in this run:
	- Across the 18 LooGLE runs: mean `prompt_len` ~15,752.9 and mean successful `output_tokens` ~15.2.
	- Across the 18 Chatbot Arena runs: mean `prompt_len` ~19.2 and mean successful `output_tokens` ~131.8.
4. Long prefill + short decode means you spend a lot of wall-clock time per request but earn few output tokens, which drives output-token throughput down.
5. Partial failures and timeout-heavy tails further reduce the numerator (successful output tokens) and enlarge effective wall time.

So the low LooGLE throughput is expected under this metric definition and workload shape; it does **not** necessarily mean the server is "broken."

If you want cross-dataset comparability, add one or more of:

1. request/s and success/s,
2. output-token throughput on successful-window only,
3. prefill-oriented metric (e.g., estimated prompt tokens/s),
4. per-request latency distributions stratified by prompt length bins.

## What This Means For Us

1. For LooGLE in this configuration, prioritizing locality (LPM) does not translate into a practical throughput advantage.
2. FCFS is the strongest latency baseline and is nearly tied for throughput, making it a robust default for user-facing responsiveness.
3. Adaptive DLPM is promising when throughput and completion rate matter, but tail stability needs tuning before claiming end-to-end superiority.
4. The main bottleneck signal here is timeout-driven tail behavior, not just scheduler ordering.

## Recommended Next Pass

1. Keep `rate=1,2,3`, but add one repeat per point to separate scheduler effects from run-to-run timeout noise.
2. Add a timeout/termination diagnostic table per run (how many requests hit timeout) alongside TTFT.
3. For adaptive_dlpm, run a small ablation on AIMD knobs (`Q_INIT`, `Q_MIN`, `Q_MAX`, `JAIN_THRESHOLD`, `TTFT_SLO_MS`) to reduce catastrophic tail events.
4. Report both full P99 and a trimmed tail metric (for example, excluding timeout-clamped requests) to make policy comparisons more actionable.
