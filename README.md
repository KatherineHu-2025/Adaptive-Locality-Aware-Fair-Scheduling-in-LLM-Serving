# Adaptive DLPM: Dynamic Locality-Aware Fair Scheduling in Multi-Tenant LLM Serving

**CMU 15-442/642 Final Project**  
Katherine Hu (yangh3) · Emily Ho (emilyho) · Quinn Zhu (annz)

---

## What This Project Does (Plain English)

Imagine an LLM server (like the backend behind ChatGPT) handling requests from multiple users at once. The server can answer faster if part of your prompt was already processed before and saved in a cache (called the **KV cache**). A greedy scheduler always picks requests that get the best cache hit — but this is unfair to new or less-frequent users whose prompts don't match anything in the cache. They can wait forever.

**DLPM** (Deficit Longest Prefix Match) fixes this by tracking a "deficit" per client — how many tokens they've been denied service — and refusing to serve cache-friendly requests until fairer clients are given a turn. It uses a tunable parameter **Q** to control how aggressively it enforces fairness vs. chasing cache hits.

**Our contribution: Adaptive DLPM.** Instead of tuning Q by hand, we add an AIMD controller (the same idea behind TCP congestion control) that automatically:
- **Increases Q** (allows more cache-chasing) when fairness looks healthy
- **Decreases Q** (enforces stricter fairness) when a client is being starved or latency spikes

Built on top of [mini-sglang](https://github.com/sgl-project/mini-sglang), a stripped-down LLM serving system from the SGLang team.

---

## Repository Structure

```
.
├── src/minisgl/                   # All our code changes (applied on top of mini-sglang)
│   ├── scheduler/
│   │   ├── policies.py            # LPM / DLPM / Adaptive DLPM / FCFS scheduling logic
│   │   ├── telemetry.py           # Sliding-window metrics + AIMD controller
│   │   ├── prefill.py             # Hooks our policy into mini-sglang's request batching
│   │   ├── scheduler.py           # Wires telemetry and AIMD into the scheduler lifecycle
│   │   └── utils.py               # Adds client_id and arrival_time to each request
│   ├── message/
│   │   ├── backend.py             # Adds client_id to messages sent to the scheduler
│   │   └── tokenizer.py           # Adds client_id to tokenizer messages
│   ├── tokenizer/
│   │   └── server.py              # Passes client_id through the tokenizer worker
│   └── server/
│       └── api_server.py          # Accepts client_id in HTTP request body
├── tests/
│   └── test_scheduler_logic.py    # 25 unit tests (no GPU required)
├── apply_patches.sh               # Copies src/ files into a cloned mini-sglang repo
├── run_modal.py                   # Runs tests and experiments on a GPU via Modal cloud
├── requirements.txt               # Python dependencies
└── implementation_plan.md         # Detailed step-by-step implementation notes
```

### What mini-sglang is (and why we don't commit it)

mini-sglang is a separate open-source project we depend on. We clone it separately and apply our changes on top via `apply_patches.sh`. It is excluded from this repo (see `.gitignore`). Our actual code lives entirely in `src/`.

---

## How a Request Flows Through the System

```
Client HTTP POST  {"prompt": "...", "client_id": "alice"}
        │
        ▼
  api_server.py        reads client_id from HTTP body
        │
        ▼
  tokenizer/server.py  tokenizes text → token IDs; carries client_id along
        │
        ▼
  scheduler/prefill.py reorders the waiting queue using our policy (LPM/DLPM/Adaptive)
        │
        ▼
  GPU forward pass     processes the batch
        │
        ▼
  telemetry.py         records TTFT, cache hit rate, Jain fairness index
        │
        ▼
  AIMDController       every 50 steps: adjust Q up or down based on metrics
```

`client_id` is what lets the scheduler know which user each request belongs to. Without it, everyone is treated as the same anonymous user and fairness tracking doesn't work.

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

Expected: **25 passed**. These run purely in Python — no GPU, no mini-sglang install needed.

### 4. Set up mini-sglang (Linux + CUDA GPU only)

> **Note:** mini-sglang requires Linux with a CUDA-capable GPU (like an A100). It does not install on Mac. Use Modal (Step 5) for GPU testing.

```bash
git clone https://github.com/sgl-project/mini-sglang
pip install -e ./mini-sglang
bash apply_patches.sh ./mini-sglang
```

`apply_patches.sh` copies all 9 modified files from `src/` into the cloned repo. Run it again after any edit to `src/`.

### 5. Run on GPU via Modal

[Modal](https://modal.com) gives us an A100 in the cloud. It handles the Linux + CUDA requirement automatically.

```bash
# One-time setup
pip install modal
modal setup          # opens browser to authenticate

# Run unit tests on A100
modal run run_modal.py

# Smoke test: start server with dummy weights, send one request
modal run run_modal.py --smoke-test
modal run run_modal.py --smoke-test --policy dlpm
modal run run_modal.py --smoke-test --policy adaptive_dlpm

# Run experiments (see Experiments section below)
modal run run_modal.py --experiment starvation
modal run run_modal.py --experiment workload_shift
modal run run_modal.py --experiment pareto
modal run run_modal.py --all
```

---

## Development Workflow

**The key rule:** `src/` is the source of truth. Always edit files there.

```
Edit src/minisgl/...
       │
       ├── Local tests (fast, no GPU)
       │     pytest tests/test_scheduler_logic.py -v
       │
       └── GPU tests (after edits)
             bash apply_patches.sh ./mini-sglang   # copies src/ → mini-sglang/
             modal run run_modal.py --smoke-test
```

Local tests import directly from `src/` — no patching needed for them. Only GPU/Modal runs need the patch step.

---

## Switching Policies

All policy settings are controlled via environment variables — no code changes needed:

```bash
# Baseline: Longest Prefix Match (greedy cache hits, can starve clients)
MINISGL_POLICY=lpm python -m minisgl --model <model>

# Static DLPM (set Q manually — larger Q = more cache-friendly, less fair)
MINISGL_POLICY=dlpm MINISGL_STATIC_Q=8000 python -m minisgl --model <model>

# Adaptive DLPM (our contribution — Q adjusts automatically)
MINISGL_POLICY=adaptive_dlpm python -m minisgl --model <model>

# FCFS: First-Come-First-Served (arrival order, ignores cache)
MINISGL_POLICY=fcfs python -m minisgl --model <model>
```

### Identifying Clients

To enable per-client fairness tracking, send a `client_id` in the HTTP request body:

```bash
curl -X POST http://localhost:19190/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello world", "max_tokens": 50, "client_id": "alice"}'
```

If `client_id` is omitted, each request is treated as its own unique client (fairness tracking still works, but won't group requests from the same user together).

---

## AIMD Hyperparameters

All have sensible defaults. Override via environment variables for ablation studies.

| Variable | Default | Meaning |
|---|---|---|
| `AIMD_Q_MIN` | 500 | Minimum Q — strictest fairness |
| `AIMD_Q_MAX` | 64000 | Maximum Q — near-pure LPM (max cache hits) |
| `AIMD_Q_INIT` | 4000 | Starting value of Q |
| `AIMD_JAIN_THRESHOLD` | 0.75 | Jain Fairness Index below this → tighten Q |
| `AIMD_TTFT_SLO_MS` | 2000 | P99 time-to-first-token (ms) above this → tighten Q |
| `AIMD_ADDITIVE_STEP` | 500 | Tokens added to Q each healthy control step |
| `AIMD_MULT_FACTOR` | 0.5 | Q is multiplied by this when a violation is detected |
| `AIMD_CONTROL_INTERVAL` | 50 | Scheduling steps between controller updates |
| `MINISGL_TELEMETRY_WINDOW` | 200 | Number of recent requests used to compute metrics |

---

## How the Scheduler Works (Technical Detail)

### Where we hook in

mini-sglang's `PrefillManager.schedule_next_batch()` picks the next batch of requests to run. Normally it processes them in FIFO order. We inject our policy by **reordering the queue before the batch is built** — all GPU memory allocation logic is untouched.

```
Incoming request
    → PendingReq (with client_id, arrival_time)
    → reorder_pending_list()    ← our policy decision
      [LPM / DLPM / Adaptive]
    → PrefillAdder              ← unchanged mini-sglang logic
    → DeficitState.update()     ← track which clients were served
    → SlidingWindowTelemetry    ← record TTFT, Jain index, cache hit rate
    → AIMDController.step()     ← adjust Q for next round
```

### DLPM eligibility rule

```
eligible = { req : deficit[req.client_id] ≤ min_deficit_across_all_waiting + Q }
among eligible:  pick requests with longest cached prefix  (LPM)
ineligible:      stay in queue until their turn
after each round: served clients → deficit = 0
                  skipped clients → deficit += their prompt length
```

A large Q means almost everyone is always eligible → behaves like pure LPM (high cache hit rate, unfair).  
A small Q means only the most-starved clients are eligible → strictly fair, lower cache hit rate.

### Jain's Fairness Index

We use this to measure fairness across clients:

```
J = (sum of tokens served)² / (n × sum of squared tokens served)
```

J = 1.0 means all clients were served equally. J = 1/n means one client got everything. We target J ≥ 0.75 by default.

---

## Experiments

**Baselines:** LPM · Static DLPM (Q ∈ {500, 2000, 8000, 32000}) · Adaptive DLPM · FCFS  
**Metrics:** Throughput · Jain Fairness Index · P50/P99 TTFT · Cache Hit Rate · Max Wait Time

| Experiment | What it tests |
|---|---|
| `starvation` | One dominant client vs. one new client. LPM starves the new client; Adaptive DLPM shouldn't. |
| `workload_shift` | Traffic changes from uniform → diverse at t=60s. Adaptive DLPM should auto-adjust Q. |
| `pareto` | All policies plotted on Throughput vs. Fairness graph. Adaptive DLPM should sit on the Pareto frontier. |
| `ablation` | Sweep AIMD hyperparameters to understand sensitivity. |

---

## What's Still To Do

- [ ] **Dataset parsers** — download and parse Chatbot Arena / LooGLE traces
- [ ] **Workload client** — replay traces with Gamma-distributed arrival times (bursty traffic)
- [ ] **Run experiments** — starvation, workload shift, Pareto sweep
- [ ] **Figures** — plot results for the paper

---

## References

- DLPM paper: [Locality-aware Fair Scheduling in LLM Serving](https://arxiv.org/abs/2501.14312) (arXiv 2501.14312)
- mini-sglang: [github.com/sgl-project/mini-sglang](https://github.com/sgl-project/mini-sglang)
- k-LPM: arXiv 2502.04677
- AIMD: Clipper (Crankshaw et al., 2017)
