# LooGLE Prefix Mix: Paper-Oriented Summary (v3-v7)

## Scope
This note summarizes the latest run (`v7`) and compares it with prior tuned runs (`v3`-`v6`) for paper writing.

Reference folders:
- `results/modal_grid_20260424_001827` (v3)
- `results/modal_grid_20260424_184711` (v4)
- `results/modal_grid_20260424_212104` (v5)
- `results/modal_grid_20260424_235859` (v6)
- `results/modal_grid_20260425_010727` (v7)

## Main Message
Adaptive DLPM in v7 remains competitive but does not represent the best overall operating point discovered so far. Relative to v6, v7 improves dominant-tail latency but loses both throughput and cold-tail latency.

## Key Quantitative Comparison (Adaptive DLPM)
- Throughput (tok/s):
  - v3: 34.630
  - v4: 32.935
  - v5: 34.433
  - v6: 34.670
  - v7: 33.618
- Overall TTFT P99 (ms):
  - v3: 4801
  - v4: 6527
  - v5: 4908
  - v6: 4714
  - v7: 4740
- Dominant TTFT P99 (ms):
  - v3: 2800
  - v4: 6900
  - v5: 2071
  - v6: 2575
  - v7: 2444
- Cold TTFT P99 (ms):
  - v3: 5224
  - v4: 6110
  - v5: 5437
  - v6: 4884
  - v7: 5310
- Adaptive median Q:
  - v3: 3550
  - v4: 16000
  - v5: 1700
  - v6: 2200
  - v7: 2500

## Interpretation for the Paper
- Best balanced adaptive point among these runs is still v6.
- v7 demonstrates a different tradeoff point:
  - better dominant-tail than v6,
  - but weaker cold-tail and lower throughput.
- This supports the paper claim that controller settings move the Pareto point between locality bias (dominant wins) and fairness to cold clients.

## Suggested Figures to Include
- Throughput/latency frontier:
  - `docs/plots/loogle_prefix_v7/modal_grid_20260425_010727_pareto.png`
- Tail behavior by policy:
  - `docs/plots/loogle_prefix_v7/modal_grid_20260425_010727_ttft_p99_vs_rate.png`
  - `docs/plots/loogle_prefix_v7/modal_grid_20260425_010727_subset_breakdown.png`
- Distribution evidence (scheduler vs end-to-end):
  - `docs/plots/loogle_prefix_v7/modal_grid_20260425_010727_ttft_request_hist.png`
  - `docs/plots/loogle_prefix_v7/modal_grid_20260425_010727_request_total_hist.png`
- Controller dynamics:
  - `docs/plots/loogle_prefix_v7/modal_grid_20260425_010727_aimd_overview.png`

## Recommended Narrative Snippet
Under the LooGLE prefix-mix workload, adaptive DLPM remains robust across tuning sweeps but exhibits a clear tradeoff surface. The v6 configuration provides the strongest balance between throughput and tail fairness, while v7 shifts toward stronger dominant-client latency at the cost of cold-client tail and aggregate throughput. This trend is consistent with the controller's Q operating region and violation activity, and illustrates that adaptive scheduling should be tuned as a policy knob, not treated as a single fixed operating point.

## Bottom Line
For final paper plots and main-table reporting, use v6 as the primary adaptive point and present v7 as an ablation showing the dominant-vs-cold tradeoff.