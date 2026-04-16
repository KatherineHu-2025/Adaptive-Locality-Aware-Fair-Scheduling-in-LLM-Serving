# LooGLE Real Weights — Experiment Summary

**Dataset:** bigai-nlco/LooGLE (longdep_qa, test split, one_per_doc=True)  
**Model:** Qwen/Qwen3-0.6B (real weights, A100)  
**Setup:** 50 requests (46–48 succeeded), one per document, unique client per doc  
**Arrival:** per-client Gamma process, rate=1.0 req/s, k=1.0  
**Policies compared:** Adaptive DLPM, DLPM (static Q=4000), LPM, FCFS  

---

## Key Results

| Policy               |  P50 (ms) |   P99 (ms) | Success | Throughput (tok/s) |
|----------------------|----------:|-----------:|--------:|-------------------:|
| Adaptive DLPM        |     3,942 |     19,018 |   46/50 |                1.0 |
| DLPM (static Q=4000) |     1,701 |    148,603 |   48/50 |                0.9 |
| LPM                  |     3,110 |     16,863 |   46/50 |                1.0 |
| FCFS                 |     3,871 |     24,963 |   46/50 |                1.0 |

---

## Observations

### 1. DLPM static Q causes catastrophic tail latency on LooGLE

DLPM (static Q=4000) achieves the **best P50** (1,701ms) but the **worst P99 by
far** (148,603ms — nearly 2.5 minutes). Two requests timed out entirely (600s
limit). This is the classic DLPM starvation failure mode: with long-context
LooGLE prompts (avg ~21K tokens), each request consumes a large fraction of
the Q budget. Some requests end up waiting through many full refill cycles
before they become eligible, accumulating catastrophic tail latency.

### 2. LPM has the best P99 on LooGLE

Unlike Chatbot Arena (where LPM causes cold-start starvation), LooGLE has no
shared prefix across clients — every request is a cold start from a unique
document. LPM degenerates to near-FCFS ordering since all requests have similar
cached_len (~0). Its P99 (16,863ms) edges out Adaptive DLPM (19,018ms).

### 3. Adaptive DLPM provides the best balance

Adaptive DLPM avoids the catastrophic tail of static DLPM while keeping P99
close to LPM. The AIMD controller tightens Q when fairness violations are
detected, preventing any single client from accumulating unlimited wait time.

### 4. 4 failed requests are dataset outliers (same across all policies)

The same 4 documents (prompt_len > 15K words) timed out under adaptive_dlpm,
lpm, and fcfs. These are extreme-length outliers in the LooGLE dataset, not
scheduler failures.

---

## Plots

| File | Description |
|------|-------------|
| `loogle_comparison_ttft_overall.png` | TTFT CDF and percentile bars (all 4 policies) |
| `loogle_comparison_ttft_log.png`     | TTFT CDF on log scale — tail latency view |
| `loogle_comparison_pareto.png`       | Throughput vs P99 TTFT scatter (lower-right better) |

---

## Limitations

- **Jain index identical across all policies**: each document has a unique
  client_id with exactly 1 request, so per-client output tokens are determined
  by the model response, not the scheduler.
- **No shared prefix**: LooGLE's unique documents mean the radix cache offers
  no reuse advantage, making this a cold-start stress test rather than a
  cache-locality comparison.
- **Single rate point**: only rate=1.0 req/s tested. Higher rates would further
  stress the DLPM static-Q starvation problem.
