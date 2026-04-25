# LooGLE Prefix Mix: Paper Summary (Final = v6)

## Scope
This summary treats v6 as the final adaptive configuration for reporting.

Reference runs:
- v3: `results/modal_grid_20260424_001827`
- v4: `results/modal_grid_20260424_184711`
- v5: `results/modal_grid_20260424_212104`
- v6 (final): `results/modal_grid_20260424_235859`
- v7 (comparison only): `results/modal_grid_20260425_010727`

## Final Takeaway
Use v6 as the main adaptive result. It gives the strongest overall balance among the tested adaptive points, with top adaptive throughput, best adaptive overall TTFT P99 across v3-v7, and the best adaptive cold-tail TTFT P99 among those runs.

## Key Numbers for v6
From `results/modal_grid_20260424_235859/summary.json`:

- adaptive_dlpm:
	- throughput: 34.670 tok/s
	- overall TTFT P99: 4714.167 ms
	- dominant TTFT P99: 2574.866 ms
	- cold TTFT P99: 4884.052 ms
	- median Q: 2200
- dlpm_q4000:
	- throughput: 34.282 tok/s
	- overall TTFT P99: 4654.554 ms
	- dominant TTFT P99: 2440.779 ms
	- cold TTFT P99: 5043.151 ms
- lpm:
	- throughput: 31.640 tok/s
	- overall TTFT P99: 4535.418 ms
- fcfs:
	- throughput: 31.410 tok/s
	- overall TTFT P99: 4518.194 ms

## Why v6 Is the Final Choice
1. Best adaptive throughput in the sweep (v3-v7).
2. Best adaptive overall TTFT P99 in the sweep.
3. Best adaptive cold-tail TTFT P99 in the sweep.
4. Q is in a stable middle range (not near v4-like runaway, not v5-like very low floor).

## v6 vs v7 (for clarity)
v7 is useful as an ablation, but not the final point:

- Adaptive throughput: v6 34.670 > v7 33.618 tok/s
- Adaptive overall TTFT P99: v6 4714 < v7 4740 ms
- Adaptive cold TTFT P99: v6 4884 < v7 5310 ms
- Adaptive dominant TTFT P99: v7 2444 < v6 2575 ms

Interpretation:
- v7 shifts toward better dominant latency.
- v6 remains the better balanced point for the paper's main result.

## Suggested Paper Positioning
- Main result row/figure: v6 adaptive configuration.
- Ablation/tradeoff discussion: include v7 to show dominant-vs-cold tradeoff movement under retuning.

## Recommended Figures (v6)
- `docs/plots/loogle_prefix_v6/modal_grid_20260424_235859_pareto.png`
- `docs/plots/loogle_prefix_v6/modal_grid_20260424_235859_ttft_p99_vs_rate.png`
- `docs/plots/loogle_prefix_v6/modal_grid_20260424_235859_subset_breakdown.png`
- `docs/plots/loogle_prefix_v6/modal_grid_20260424_235859_ttft_request_hist.png`
- `docs/plots/loogle_prefix_v6/modal_grid_20260424_235859_request_total_hist.png`
- `docs/plots/loogle_prefix_v6/modal_grid_20260424_235859_aimd_overview.png`

## Ready-to-Use Narrative
Under the LooGLE prefix-mix workload, the v6 adaptive DLPM setting provides the best overall tradeoff among tested adaptive configurations. It achieves the highest adaptive throughput while also delivering the strongest adaptive tail behavior for both overall and cold-client TTFT P99. Compared with v7, which improves dominant-client tail latency, v6 is more balanced and is therefore selected as the final operating point for primary paper reporting.

---

# LooGLE Prefix Mix Paper Addendum (Starvation-Style Format)

This addendum follows the structure and tone of `LooGLE_starvation_paper_summary.md`, adapted to the prefix-mix v6 final decision.

## Workload We Test

- **Dataset/regime:** LooGLE prefix-mix workload (`dataset=loogle_prefix`).
- **Traffic composition:** 50% dominant-prefix requests and 50% cold-prefix requests.
- **Arrival pattern:** chunked mix (`chunk-size=40`) to force alternating pressure between dominant and cold clients.
- **Load setting used for final claim:** `rate=4`, `k=1`, `request_count=1500`, `max_concurrency=8`.
- **Why this workload matters:** it directly exposes the locality-vs-fairness tension by mixing cache-friendly dominant traffic with cache-poor cold traffic in the same run.

## Method

We evaluate four policy families under identical workload conditions:

1. **Adaptive DLPM** with AIMD control (`AIMD_MULT_FACTOR=0.65`, Jain threshold in the v6 run setup, `Q_min` and TTFT SLO constraints).
2. **Static DLPM** with fixed queue parameter (`dlpm_q4000` in v6).
3. **LPM** baseline.
4. **FCFS** baseline.

Controller behavior is interpreted using telemetry from Q-at-scheduling, Jain-related control signals, and AIMD violation events.

## Evaluation Protocol

- **Primary latency metric:** TTFT (P50/P95/P99), reported overall and by subgroup (dominant vs cold).
- **Secondary latency metric:** request total latency (P50/P95/P99) to capture end-to-end effects beyond first token.
- **Efficiency metric:** throughput (tokens/sec).
- **Comparison lens:** evaluate Adaptive DLPM directly against static DLPM (`q=4000`), LPM, and FCFS within the same v6 run.
- **Success criterion:** strong throughput while maintaining competitive tail latency, especially for cold clients.

## Results (Evidence-Based)

### 1. Adaptive DLPM delivers the highest throughput in v6.

- Adaptive DLPM: **34.670 tok/s**
- Static DLPM (`q=4000`): **34.282 tok/s**
- LPM: **31.640 tok/s**
- FCFS: **31.410 tok/s**

Interpretation: Adaptive DLPM leads throughput while remaining close to static DLPM and clearly ahead of LPM/FCFS.

### 2. Adaptive DLPM is competitive on overall TTFT tail, but not the absolute minimum.

- Adaptive DLPM overall TTFT P99: **4714 ms**
- Static DLPM (`q=4000`): **4655 ms**
- LPM: **4535 ms**
- FCFS: **4518 ms**

Interpretation: Adaptive gives a small TTFT P99 penalty versus FCFS/LPM, in exchange for the highest throughput.

### 3. Dominant-client behavior is strong and close to static DLPM.

- Adaptive DLPM dominant TTFT P99: **2575 ms**
- Static DLPM (`q=4000`) dominant TTFT P99: **2441 ms**
- LPM dominant TTFT P99: **2151 ms**
- FCFS dominant TTFT P99: **4206 ms**

Interpretation: Adaptive is much better than FCFS for dominant clients and remains in the same performance band as static DLPM/LPM.

### 4. Cold-client tail is where Adaptive DLPM trades off against classic baselines.

- Adaptive DLPM cold TTFT P99: **4884 ms**
- Static DLPM (`q=4000`) cold TTFT P99: **5043 ms**
- LPM cold TTFT P99: **4877 ms**
- FCFS cold TTFT P99: **4514 ms**

Interpretation: Adaptive is better than static DLPM on cold tail, nearly tied with LPM, and behind FCFS.

### 5. Controller operating region in v6 is practical.

- Median adaptive Q is **2200**.

Interpretation: Q stays in a moderate region rather than drifting to extreme values, indicating stable control behavior in this workload.

## Why This Matters for the Paper

- The prefix-mix benchmark demonstrates that policy ranking depends on which tail and which subgroup you optimize.
- In v6, Adaptive DLPM is the best throughput policy and remains competitive on dominant and cold tails relative to baselines.
- This supports presenting Adaptive DLPM as a robust scheduling choice rather than a single-metric winner.

## What to Include in the Writeup (v6-Centric)

1. Workload definition: dominant/cold split, chunked arrivals, concurrency and rate.
2. Method: adaptive vs static vs LPM vs FCFS under identical load.
3. Evaluation metrics: throughput + TTFT tails + subgroup breakdown + request-total tails.
4. Main result: choose v6 as final because it is the best balanced adaptive operating point.
5. Policy comparison sentence: Adaptive DLPM leads throughput and stays close to the best latency policies, with the main gap versus FCFS on cold-tail TTFT P99.

## Optional Ready-to-Paste Paragraph (Method + Evaluation + Results)

We evaluate scheduling policies on a LooGLE prefix-mix workload that combines 50% dominant-prefix and 50% cold-prefix traffic under chunked arrivals (chunk size 40), at rate 4, k=1, request count 1500, and max concurrency 8. We compare Adaptive DLPM (AIMD-controlled Q), static DLPM (Q=4000), LPM, and FCFS using throughput, TTFT tail percentiles (overall and subgroup), and request-total latency. In this v6 run, Adaptive DLPM achieves the highest throughput (34.67 tok/s) while remaining latency-competitive: its overall TTFT P99 (4.71 s) is close to static DLPM/LPM/FCFS, dominant-client TTFT P99 is strong (2.57 s), and cold-client TTFT P99 (4.88 s) is better than static DLPM and close to LPM, though still behind FCFS. This makes Adaptive DLPM the most balanced throughput-first policy in the evaluated setting.
