# Adaptive DLPM: Dynamic Locality-Aware Fair Scheduling in Multi-Tenant LLM Serving

**CMU 15-442/642 Final Project**  
Katherine Hu (yangh3) · Emily Ho (emilyho) · Quinn Zhu (annz)

---

## Overview

Pure locality-aware scheduling (LPM) in multi-tenant LLM serving starves clients whose requests don't match the current KV cache — especially new or low-traffic clients. DLPM ([arXiv 2501.14312](https://arxiv.org/abs/2501.14312)) fixes this with per-client deficit tracking and a fairness quantum **Q**, but Q is static and must be tuned manually per workload.

We extend DLPM with an **AIMD-based adaptive controller** that tunes Q dynamically at runtime:
- **Additive increase** when Jain Fairness Index is healthy → chase more locality/throughput
- **Multiplicative decrease** when fairness drops or P99 TTFT spikes → enforce stricter fairness

Built on top of [mini-sglang](https://github.com/sgl-project/mini-sglang).

---

## Repository Structure

```
.
├── src/minisgl/               # Our scheduler modifications (applied on top of mini-sglang)
│   ├── scheduler/
│   │   ├── policies.py        # LPM / DLPM / Adaptive DLPM / FCFS reordering logic
│   │   ├── telemetry.py       # SlidingWindowTelemetry + AIMDController
│   │   ├── prefill.py         # Modified PrefillManager (policy dispatch + deficit tracking)
│   │   ├── scheduler.py       # Modified Scheduler (telemetry wiring + AIMD instantiation)
│   │   └── utils.py           # Modified PendingReq (+ client_id, arrival_time)
│   └── message/
│       └── backend.py         # Modified UserMsg (+ client_id)
├── tests/
│   └── test_scheduler_logic.py  # 25 unit tests (no GPU required)
├── apply_patches.sh           # Copies src/ into a cloned mini-sglang repo
├── run_modal.py               # Modal cloud runner for GPU experiments
├── requirements.txt
└── implementation_plan.md     # Detailed step-by-step implementation plan
```

---

## Setup

### 1. Clone this repo

```bash
git clone <this-repo-url>
cd <repo-name>
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Run local unit tests (no GPU needed)

Tests cover all scheduling logic: LPM ordering, DLPM starvation prevention, deficit updates, Jain Index calculation, AIMD saw-tooth behavior.

```bash
pytest tests/test_scheduler_logic.py -v
```

Expected: **25 passed**.

### 4. Set up mini-sglang (requires Linux + CUDA GPU)

Clone mini-sglang and apply our patches:

```bash
git clone https://github.com/sgl-project/mini-sglang
pip install -e ./mini-sglang
bash apply_patches.sh ./mini-sglang
```

### 5. Run on GPU via Modal

```bash
# One-time Modal setup
pip install modal
modal setup

# Run unit tests on A100
modal run run_modal.py

# Smoke test (starts server with dummy weights)
modal run run_modal.py --smoke-test

# Run experiments
modal run run_modal.py --experiment starvation
modal run run_modal.py --experiment workload_shift
modal run run_modal.py --experiment pareto
modal run run_modal.py --all
```

---

## Switching Policies

All policy settings are controlled via environment variables — no code changes needed:

```bash
# Baseline: Longest Prefix Match
MINISGL_POLICY=lpm python -m minisgl --model <model>

# Static DLPM (set Q manually)
MINISGL_POLICY=dlpm MINISGL_STATIC_Q=8000 python -m minisgl --model <model>

# Adaptive DLPM (our contribution)
MINISGL_POLICY=adaptive_dlpm python -m minisgl --model <model>

# FCFS (related-work reference)
MINISGL_POLICY=fcfs python -m minisgl --model <model>
```

### AIMD Hyperparameters (all have sensible defaults)

| Variable | Default | Meaning |
|---|---|---|
| `AIMD_Q_MIN` | 500 | Minimum Q (strictest fairness) |
| `AIMD_Q_MAX` | 64000 | Maximum Q (near-pure LPM) |
| `AIMD_Q_INIT` | 4000 | Starting Q |
| `AIMD_JAIN_THRESHOLD` | 0.75 | Jain index below this → tighten |
| `AIMD_TTFT_SLO_MS` | 2000 | P99 TTFT (ms) above this → tighten |
| `AIMD_ADDITIVE_STEP` | 500 | Tokens added to Q per healthy step |
| `AIMD_MULT_FACTOR` | 0.5 | Q multiplier on violation |
| `AIMD_CONTROL_INTERVAL` | 50 | Scheduling steps between controller updates |
| `MINISGL_TELEMETRY_WINDOW` | 200 | Sliding window size (requests) |

---

## How It Works

### Scheduling Hook

mini-sglang's `PrefillManager.schedule_next_batch()` iterates the waiting queue in FIFO order. We inject our policy by **reordering the queue before PrefillAdder runs** — all memory allocation logic is unchanged.

```
Incoming request → PendingReq (+ client_id, arrival_time)
                        ↓
              reorder_pending_list()   ← policy decision
              [LPM / DLPM / Adaptive]
                        ↓
                  PrefillAdder         ← unchanged mini-sglang logic
                        ↓
               DeficitState.update()   ← track which clients were served
                        ↓
            SlidingWindowTelemetry     ← record TTFT, Jain, cache hit rate
                        ↓
              AIMDController.step()    ← adjust Q for next round
```

### DLPM Deficit Logic

```
eligible = {req : deficit[req.client_id] <= min_deficit_across_all_waiting + Q}
among eligible: pick requests with longest cached prefix (LPM)
ineligible requests: stay in queue (fairness enforced)
after each round: served clients → deficit = 0; skipped clients → deficit += prompt_len
```

---

## Evaluation Plan

**Baselines:** LPM · Static DLPM (Q ∈ {500, 2000, 8000, 32000}) · Adaptive DLPM  
**Datasets:** Chatbot Arena traces · LooGLE (long-context QA)  
**Arrival process:** Gamma process  
**Metrics:** Throughput · Jain Fairness Index · P50/P99 TTFT · TPOT · Cache Hit Rate · Max Wait Time  

**Key experiments:**
1. **Starvation** — dominant client vs. cold client at fixed load
2. **Workload shift** — homogeneous → diverse traffic at t=60s (Adaptive DLPM should auto-adjust Q)
3. **Pareto sweep** — all policies plotted on Throughput vs. Jain frontier

---

## References

- DLPM paper: [Locality-aware Fair Scheduling in LLM Serving](https://arxiv.org/abs/2501.14312) (arXiv 2501.14312)
- mini-sglang: [github.com/sgl-project/mini-sglang](https://github.com/sgl-project/mini-sglang)
- k-LPM: arXiv 2502.04677
- AIMD: Clipper (Crankshaw et al., 2017)
