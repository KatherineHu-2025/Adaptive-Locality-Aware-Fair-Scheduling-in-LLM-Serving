# LooGLE Prefix Analysis: modal_grid_20260423_183127

## Run Context
- Command: `python benchmark_modal_service_loogle_prefix_grid.py --request-counts 400 --loogle-prefix-dominant-fraction 0.5 --loogle-prefix-mix-mode chunked --loogle-prefix-chunk-size 40 --max-concurrency 5 --aimd-jain-threshold 0.68 --rates 2 --stop-service-at-end`
- Folder: `results/modal_grid_20260423_183127/`
- Output plots: `docs/plots/loogle_prefix/`

## What changed in the plots
- Static DLPM runs are now separated by Q value in the plot labels, so the curves and bars no longer collapse into one generic `dlpm` bucket.
- The folder now includes a dedicated `subset_breakdown` figure showing overall, dominant, and cold metrics for throughput, TTFT p50, and TTFT p99.

## Key ranking from this run
Overall, the ordering does not match your target yet.

- Best overall TTFT p99: `dlpm_q16000` at about 16.4 s
- Best dominant-client TTFT p99: `dlpm_q8000` at about 2.8 s
- Worst cold-client TTFT p99: `fcfs` at about 24.9 s

The important takeaway is that LPM is not the best policy in this run. It is better than FCFS, but static DLPM variants are still ahead on the key latency metrics, especially on the dominant client.

## Why this is happening
- The current "cold" requests are still only partially cold from the cache's point of view: they use different clients and different documents, but they still begin with real LooGLE context text, so the prefix cache can match a lot of material.
- The dominant fraction is still large enough that FCFS can ride a long run of dominant traffic and get some prefix benefit even without being locality-aware.
- The result is that the workload still favors cache reuse strongly enough that several DLPM settings beat LPM on latency.

## What to do next
1. Turn on strict cold.
   - The implementation prepends a unique cold-only marker before each cold prompt, so the first shared prefix tokens are no longer the same across cold requests.
   - That keeps the semantic structure of the task but prevents the cache from reusing the dominant prefix for cold rows.

2. Lower the dominant fraction again.
   - Try `0.35` to `0.45`.
   - This should reduce FCFS's ability to coast on a long dominant streak while still leaving enough repeated-context traffic for locality-aware schedulers to matter.

3. Keep chunked mixing, but reduce the chunk size.
   - Try `10` or `20` instead of `40`.
   - Smaller chunks make the workload more adversarial and reduce long same-class stretches.

4. Sweep a smaller but sharper grid.
   - Suggested next sweep: dominant fraction in `{0.35, 0.4, 0.45}` crossed with chunk size in `{10, 20}`.
   - Keep `--max-concurrency` the same unless you also raise the server-side batch capacity.

5. Consider two dominant clients only if you want more contention, not if you want a cleaner LPM win.
   - Two dominant clients can increase queue pressure, but if you split the dominant share evenly, each client is less dominant and the effect may weaken the locality gap.
   - If you try it, keep the two dominant clients on the same shared context so the cache still has a strong repeated-prefix signal.

6. Treat max-concurrency as a queue-depth knob.
   - Higher client concurrency usually helps the scheduler show its ordering advantage because more requests are waiting at once.
   - Too low can starve the queue and hide policy differences; too high can just inflate latency without improving ranking.
   - For this kind of benchmark, I would test `8`, `12`, and `16` rather than moving wildly.

## Concurrency note
- `--max-concurrency` only controls the client-side in-flight limit.
- The Modal UI showing many pending requests and only a few running is usually the backend scheduler admitting work in small batches, not a Modal bug.
- If you want more simultaneous active requests, the real limit is on the server side, not the client flag alone.

## Bottom line
This run is useful for showing that FCFS is the worst, but it does not yet produce the ranking you want. The next best move is to make the cold side truly cold and lower the dominant fraction a bit, then rerun the same sweep.
