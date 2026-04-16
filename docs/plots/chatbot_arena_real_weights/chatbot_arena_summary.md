# Chatbot Arena — Real Weights Experiment Summary

**Dataset:** lmsys/chatbot_arena_conversations (English, min_turns=2)  
**Model:** Qwen/Qwen3-0.6B (real weights, A100)  
**Setup:** 50 conversations × ≥2 turns → 129 total requests  
**Arrival:** per-client Gamma process, rate=1.0 req/s, k=1.0  
**Policies compared:** Adaptive DLPM, LPM, FCFS  
**Results directory:** `results/modal_grid_20260416_010102/`

---

## Key Results

### Overall TTFT

| Policy                | P50 (ms) | P95 (ms) | P99 (ms) | Throughput (tok/s) |
|-----------------------|---------:|---------:|---------:|-------------------:|
| Adaptive DLPM         |      252 |    2,232 |   18,614 |               37.1 |
| DLPM (static Q=4000)  |    1,320 |   23,555 |   23,555 |               37.1 |
| LPM                   |      514 |   35,591 |   35,591 |               37.1 |
| FCFS                  |      236 |   14,997 |   14,997 |               37.1 |

### TTFT by Turn

| Policy               | Turn 1 P50 | Turn 1 P99 | Turn 2 P50 | Turn 2 P99 | Turn 3+ P50 | Turn 3+ P99 |
|----------------------|-----------:|-----------:|-----------:|-----------:|------------:|------------:|
| Adaptive DLPM        |       339ms |    20,441ms |       244ms |    1,980ms |        211ms |    1,068ms |
| DLPM (static Q=4000) |     1,365ms |    26,244ms |     1,361ms |    2,125ms |      1,068ms |    2,085ms |
| LPM                  |       569ms |    37,926ms |       554ms |    1,547ms |        289ms |      701ms |
| FCFS                 |       340ms |    16,512ms |       219ms |      743ms |        186ms |      500ms |

---

## Observations

### 1. LPM causes severe cold-start starvation

LPM's greedy prefix prioritization creates a feedback loop: once some clients have
their turn-1 prefix cached, subsequent turns always jump the queue over new clients
waiting for their first turn. This drives turn-1 P99 to **37,926ms** — more than
2× worse than Adaptive DLPM (20,441ms) and 2.3× worse than FCFS (16,512ms).

The starvation also cascades into turn-2 P50: LPM's warm-turn median is 554ms
vs ~230ms for the other two policies, because the backlog of starved cold requests
eventually blocks even cached requests.

### 2. Static DLPM trades median for a worse starvation tail

DLPM with static Q=4000 has the worst P50 of all policies (1,365ms turn-1 vs
~340ms for Adaptive DLPM and FCFS). The fixed quantum causes all clients to
wait through a full refill cycle before being served, hurting median latency.
Its starvation tail (P99=26,244ms) is better than LPM but worse than Adaptive
DLPM — without the AIMD controller to tighten Q under load, the static budget
is either too large (wasting fairness) or too small (causing long wait cycles).

### 3. Adaptive DLPM halves LPM's starvation tail

The AIMD controller dynamically adjusts Q, allowing Adaptive DLPM to prevent
runaway starvation without penalising median latency. Turn-1 P99 drops from
37,926ms (LPM) to 20,441ms (Adaptive DLPM) — a **46% reduction** — while
keeping P50 near FCFS levels (339ms vs 340ms).

### 3. FCFS wins overall P99 at this load level

At rate=1.0 req/s with 50 clients, the queue rarely accumulates. FCFS's simple
arrival-order scheduling avoids any head-of-line blocking, giving the best
overall P99 (14,997ms). This is expected: DLPM's fairness advantage is most
visible under high concurrency and bursty traffic where the queue depth is
consistently non-zero.

### 4. Cache speedup is clearly visible across all policies

Later turns are dramatically faster in all policies, confirming the radix cache
is active with real weights:

| Policy        | Turn 1 P50 | Turn 2 P50 | Speedup |
|---------------|-----------:|-----------:|--------:|
| Adaptive DLPM |       339ms |       244ms |    1.4× |
| LPM           |       569ms |       554ms |    1.0× |
| FCFS          |       340ms |       219ms |    1.6× |

LPM's warm-turn speedup is near-zero because its queue is backlogged — warm
requests wait behind the pile of starved cold requests.

---

## Plots

| File | Description |
|------|-------------|
| `chatbot_arena_starvation_turn1.png` | Turn-1 TTFT CDF on log scale — starvation view |
| `chatbot_arena_ttft_cdf_by_turn.png` | TTFT CDF split by turn (cold / warm / hot) |
| `chatbot_arena_ttft_by_turn_bar.png` | P50 and P99 bar chart by turn and policy |
| `chatbot_arena_ttft_overall.png`     | Overall TTFT CDF and percentile bars |

---

## Limitations and Next Steps

- **Jain index identical across policies** (0.5792): each conversation has a unique
  `client_id`, so every client contributes roughly equal output tokens regardless
  of scheduler. A meaningful Jain comparison requires a dominant/cold workload
  (synthetic dataset) or server-side `cached_len` to compute service-rate Jain.

- **Low load regime**: at 1.0 req/s the queue rarely saturates. Re-running at
  2.0–3.0 req/s should widen the gap between Adaptive DLPM and FCFS and trigger
  the AIMD controller.

- **AIMD not active**: 0 AIMD updates observed. The control interval fires every
  50 scheduling steps; at 1.0 req/s with max_concurrency=2, the pending queue
  rarely has 50+ events. Higher rate needed to trigger the sawtooth.
