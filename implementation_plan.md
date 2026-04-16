# Implementation Plan: Adaptive DLPM Scheduler for LLM Serving

**Team:** Katherine Hu (yangh3), Emily Ho (emilyho), Quinn Zhu (annz)
**Course:** CMU 15-442/642
**Platform:** mini SGLang (with RadixAttention and chunked prefill)

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Week 1: Infrastructure, Baselines, and Telemetry](#2-week-1-infrastructure-baselines-and-telemetry)
3. [Week 2: Adaptive AIMD Controller](#3-week-2-adaptive-aimd-controller)
4. [Week 3: Experiments and Ablations](#4-week-3-experiments-and-ablations)
5. [Week 4: Analysis and Writeup](#5-week-4-analysis-and-writeup)
6. [Key Data Structures and Interfaces](#6-key-data-structures-and-interfaces)
7. [Evaluation Protocol](#7-evaluation-protocol)
8. [How to Run Tests](#8-how-to-run-tests)
9. [Risk Register](#9-risk-register)

---

## 1. System Architecture Overview

### Components Being Built

```
┌─────────────────────────────────────────────────────────┐
│                      mini SGLang                        │
│                                                         │
│  ┌──────────────┐    ┌──────────────────────────────┐   │
│  │  Radix Tree  │◄───│        Scheduler             │   │
│  │  (existing)  │    │  ┌──────────────────────┐    │   │
│  │              │    │  │  Policy (pluggable)  │    │   │
│  │ prefix_match │    │  │  - FCFS              │    │   │
│  │    (API)     │    │  │  - LPM               │    │   │
│  └──────────────┘    │  │  - Static DLPM  [NEW]│    │   │
│                      │  │  - Adaptive DLPM[NEW]│    │   │
│                      │  └──────────────────────┘    │   │
│                      │                              │   │
│                      │  ┌──────────────────────┐    │   │
│                      │  │  Telemetry Engine[NEW]│   │   │
│                      │  │  - Sliding window     │   │   │
│                      │  │  - Per-client deficit │   │   │
│                      │  │  - Jain Index calc    │   │   │
│                      │  └──────────────────────┘    │   │
│                      │                              │   │
│                      │  ┌──────────────────────┐    │   │
│                      │  │  AIMD Controller [NEW]│   │   │
│                      │  │  - Reads telemetry    │   │   │
│                      │  │  - Adjusts Q          │   │   │
│                      │  └──────────────────────┘    │   │
│                      └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
         ▲
         │ HTTP requests (Gamma process arrival)
         │
┌────────┴───────┐
│  Workload      │
│  Generator     │  ← Chatbot Arena traces + LooGLE
│  (client.py)   │
└────────────────┘
```

### Scheduling Policy Hierarchy

```
get_next_batch_to_run()
    │
    ├─── LPM (primary baseline):
    │        sort by prefix_match_length(r) DESC
    │
    ├─── Static DLPM (primary baseline):
    │        eligible = {r : deficit(client(r)) <= Q}
    │        if eligible non-empty: pick max prefix_match_length among eligible
    │        else: pick min-deficit client (fairness fallback)
    │
    ├─── Adaptive DLPM (our contribution):
    │        same as Static DLPM, but Q is updated each scheduling step
    │        by the AIMD controller based on live telemetry
    │
    └─── FCFS (sanity-check / related-work reference only):
             sort by arrival_time ASC
```

---

## 2. Week 1: Infrastructure, Baselines, and Telemetry

### Owner mapping
- **Person 1 (System):** Steps 1.1–1.4 — scheduler policies, benchmarking toggle
- **Person 2 (Workload):** Steps 1.5–1.7 — dataset parsing, client script, multi-turn logic
- **Person 3 (Telemetry):** Steps 1.8–1.10 — sliding window, timestamps, deficit tracking

---

### ✅ Step 1.1 — Clone and verify mini SGLang

mini-sglang is cloned at `./mini-sglang/`. Our changes live in `src/` and are applied via `apply_patches.sh`.

GPU smoke test is available via Modal:
```bash
modal run run_modal.py --smoke-test
```

**Relevant files:** [apply_patches.sh](apply_patches.sh) · [run_modal.py](run_modal.py)

---

### ✅ Step 1.2 — Scheduler hook point (already mapped)

The relevant files and exact hook points in mini-sglang:

| Concept | File | Class / Field |
|---|---|---|
| Waiting queue | `python/minisgl/scheduler/prefill.py` | `PrefillManager.pending_list: List[PendingReq]` |
| **Scheduling hook** | `python/minisgl/scheduler/prefill.py` | **`PrefillManager.schedule_next_batch(prefill_budget: int)`** |
| Prefix scoring (read-only) | `python/minisgl/scheduler/cache.py` | `CacheManager.match_req(pending_req) → MatchResult` |
| Cached length | `python/minisgl/kvcache/base.py` | `MatchResult.cuda_handle.cached_len: int` |
| Incoming requests | `python/minisgl/message/backend.py` | `UserMsg.uid / .input_ids / .sampling_params` |
| Pending request object | `python/minisgl/scheduler/utils.py` | `PendingReq.uid / .input_ids / .sampling_params / .chunked_req` |

**Key facts:**
- `PrefillManager.schedule_next_batch()` iterates `pending_list` in FIFO order. We inject our policy by **reordering `pending_list` before the loop** — all downstream `PrefillAdder` logic stays intact.
- `cache_manager.match_req(pending_req)` is **read-only** (no locking). We can safely call it on every pending request to score them. The lock only happens inside `PrefillAdder._try_allocate_one()` after selection.
- The scheduler runs in a single Python thread, so no additional locking is needed for our policy state.

---

### ✅ Step 1.3 — Implement a pluggable policy interface

Policy is selected via the `MINISGL_POLICY` environment variable. All four policies are implemented and dispatch through `reorder_pending_list()`.

```bash
MINISGL_POLICY=lpm python -m minisgl --model <model>
MINISGL_POLICY=dlpm MINISGL_STATIC_Q=8000 python -m minisgl --model <model>
MINISGL_POLICY=adaptive_dlpm python -m minisgl --model <model>
MINISGL_POLICY=fcfs python -m minisgl --model <model>
```

**Relevant files:** [src/minisgl/scheduler/policies.py](src/minisgl/scheduler/policies.py) · [src/minisgl/scheduler/prefill.py](src/minisgl/scheduler/prefill.py)

---

### ✅ Step 1.4 — Implement Static DLPM

DLPM is fully implemented. The eligibility rule:

```
eligible = { req : deficit[req.client_id] ≤ min_deficit_across_waiting + Q }
among eligible: sort by cached_len DESC (LPM)
ineligible: stay at back of queue in FIFO order
fallback: if eligible is empty, serve the most-starved client
```

Deficit is updated after every scheduling round: served clients reset to 0, skipped clients accumulate `prompt_len`.

The two-client starvation scenario (dominant vs. cold client) is verified by unit tests.

**Relevant files:** [src/minisgl/scheduler/policies.py](src/minisgl/scheduler/policies.py) (see `DeficitState`, `reorder_pending_list`) · [tests/test_scheduler_logic.py](tests/test_scheduler_logic.py)

---

### ✅ Step 1.5 — Parse datasets

Three loaders implemented in [workload/dataset.py](workload/dataset.py), all outputting a unified `RequestSpec`:

```python
@dataclass
class RequestSpec:
    client_id: str
    prompt: str
    expected_output_len: int
    arrival_time: float   # seconds from trace start, for replay (0.0 = unset)
```

| Loader | Dataset | `client_id` | Notes |
|---|---|---|---|
| `load_chatbot_arena()` | `lmsys/chatbot_arena_conversations` (gated) | `question_id` | Multi-turn: each turn's prompt prepends all prior turns (Step 1.7 folded in) |
| `load_loogle()` | `bigai-nlco/LooGLE longdep_qa` (public) | `doc_id` | Long contexts (60k+ chars); cold-start starvation trigger; `one_per_doc=True` for pure cold starts |
| `load_synthetic()` | Generated (no download) | `client_dominant` / `client_cold` | Controlled starvation experiment; dominant client has long shared system prompt |

**Relevant file:** [workload/dataset.py](workload/dataset.py) · [tests/test_dataset.py](tests/test_dataset.py)

---

### ✅ Step 1.6 — Build the workload client

Implemented in [workload/client.py](workload/client.py).

`gamma_interarrivals(n, rate, k, seed=42)` generates inter-arrival times from Gamma(shape=k, scale=1/(rate·k)). Mean is always 1/rate; k controls shape:

| k | Traffic pattern |
|---|---|
| < 1 | Bursty |
| = 1 | Poisson / memoryless |
| > 1 | Regular / smooth |

`replay(specs, server_url, rate, k, policy, output_path, ...)` fires requests at Gamma-timed intervals, parses the SSE stream, records TTFT and TPOT per request, and writes a JSONL log line per completed request. `print_summary()` prints throughput, P50/P99 TTFT, per-client breakdown, and Jain Index.

CLI usage (against a running server):
```bash
python -m workload.client --dataset synthetic --rate 3.0 --k 1.0 --policy adaptive_dlpm
python -m workload.client --dataset loogle    --rate 2.0 --k 0.5 --policy lpm
```

**Relevant file:** [workload/client.py](workload/client.py) · [tests/test_client.py](tests/test_client.py)

---

### ✅ Step 1.7 — Multi-turn conversation simulation

Implemented inside `load_chatbot_arena()` in [workload/dataset.py](workload/dataset.py). Each turn's prompt is the full conversation history up to that point:

```
Turn 1:  "Human: <u1>"
Turn 2:  "Human: <u1>\nAssistant: <a1>\nHuman: <u2>"
Turn 3:  "Human: <u1>\nAssistant: <a1>\nHuman: <u2>\nAssistant: <a2>\nHuman: <u3>"
```

This ensures every turn after the first reuses the prefix cached from the previous turn, maximizing cache hit rate for the dominant-client scenario.

---

### ✅ Step 1.8 — Sliding window state

`SlidingWindowTelemetry` keeps a rolling window of the last 200 completed requests and computes:
- P99 TTFT
- Jain Fairness Index
- Cache hit rate
- Max wait time

**Relevant file:** [src/minisgl/scheduler/telemetry.py](src/minisgl/scheduler/telemetry.py)

---

### ✅ Step 1.9 — Latency timestamps

`arrival_time` is recorded when `UserMsg` arrives at the scheduler. `first_token_time` is recorded when the first output token is produced. TTFT = `first_token_time − arrival_time`.

**Relevant files:** [src/minisgl/scheduler/utils.py](src/minisgl/scheduler/utils.py) (arrival_time on PendingReq) · [src/minisgl/scheduler/scheduler.py](src/minisgl/scheduler/scheduler.py) (`_first_token_time` dict, telemetry recording)

---

### ✅ Step 1.10 — Per-client deficit tracking

`DeficitState` in `policies.py` maintains a `dict[client_id → float]` deficit counter. Updated after every scheduling round inside `PrefillManager.schedule_next_batch()`.

**Relevant files:** [src/minisgl/scheduler/policies.py](src/minisgl/scheduler/policies.py) · [src/minisgl/scheduler/prefill.py](src/minisgl/scheduler/prefill.py)

---

### Week 1 Integration Checkpoint

- ✅ All three primary policy flags work (`lpm`, `dlpm`, `adaptive_dlpm`); `fcfs` works as secondary
- ✅ Static DLPM passes the two-client starvation test (unit tests)
- ✅ Client script fires Gamma-process traffic at the server (`workload/client.py`)
- ✅ Telemetry records TTFT, Jain Index, cache hit rate per request (in memory)
- ⚠️ Client writes per-request JSONL (client-side fields only); server-side fields (`cached_len`, `Q_at_scheduling`) require Step 2.4 file logging

---

## 3. Week 2: Adaptive AIMD Controller

**Owner:** All three — this is the core novel contribution.

### ✅ Step 2.1 — Define the control loop parameters

`AIMDConfig` dataclass with all hyperparameters, all overridable via environment variables.

| Env var | Default | Meaning |
|---|---|---|
| `AIMD_Q_MIN` | 500 | Minimum Q |
| `AIMD_Q_MAX` | 64000 | Maximum Q |
| `AIMD_Q_INIT` | 4000 | Starting Q |
| `AIMD_JAIN_THRESHOLD` | 0.75 | Jain below this → tighten |
| `AIMD_TTFT_SLO_MS` | 2000 | P99 TTFT above this → tighten |
| `AIMD_ADDITIVE_STEP` | 500 | Tokens added per healthy step |
| `AIMD_MULT_FACTOR` | 0.5 | Q multiplier on violation |
| `AIMD_CONTROL_INTERVAL` | 50 | Steps between controller updates |

**Relevant file:** [src/minisgl/scheduler/telemetry.py](src/minisgl/scheduler/telemetry.py) (see `AIMDConfig`)

---

### ✅ Step 2.2 — Implement the AIMD controller

`AIMDController` reads telemetry every `control_interval` steps and adjusts Q:
- **Violated** (Jain < threshold OR P99 > SLO): `Q = max(Q_min, Q × 0.5)`
- **Healthy**: `Q = min(Q_max, Q + 500)`

History of `(wall_time, Q, jain, p99_ms)` is stored in `controller.history` for plotting.

**Relevant file:** [src/minisgl/scheduler/telemetry.py](src/minisgl/scheduler/telemetry.py) (see `AIMDController`)

---

### ✅ Step 2.3 — Wire the controller into the scheduler

`Scheduler.__init__` reads all AIMD env vars, creates `SlidingWindowTelemetry` and `AIMDController`, and passes them into `PrefillManager`. `controller.step()` is called at the top of every `schedule_next_batch()`.

**Relevant files:** [src/minisgl/scheduler/scheduler.py](src/minisgl/scheduler/scheduler.py) · [src/minisgl/scheduler/prefill.py](src/minisgl/scheduler/prefill.py)

---

### ✅ Step 2.4 — Log Q trajectory

`RequestLogger` implemented in [src/minisgl/scheduler/telemetry.py](src/minisgl/scheduler/telemetry.py). Activated via `MINISGL_LOG_DIR` env var. Writes:
- `{log_dir}/requests_{policy}_{ts}.jsonl` — one line per completed request (TTFT, TPOT, cached_len, Q_at_scheduling)
- `{log_dir}/q_trajectory_{ts}.csv` — Q history (wall_time, Q, jain, p99_ttft_ms)

`AIMDController.step()` also writes live JSONL to `AIMD_DEBUG_LOG_PATH` for runtime monitoring.

---

### ⚠️ Step 2.5 — Validate AIMD behavior on synthetic workload

**Partially observed.** AIMD Q trajectory was observed in dummy-weight runs: Q dropped from 4000 → 2000 → 1000 → 500 (floor) in response to low Jain Index. However:
- Q never recovered (additive increase) — workload design issue: LooGLE `one_per_doc=True` assigns 1 req/client, so Jain stays at ~0.5 permanently
- In real-weight LooGLE runs, AIMD showed additive increase (Q: 4000 → 4500 → 5000, `violated=false`)
- Full sawtooth not yet demonstrated — requires high-load synthetic workload with dominant/cold client split

**Remaining:** Run synthetic dataset at rate ≥ 2.0 req/s with dominant/cold split to trigger sawtooth.

---

### Week 2 Checkpoint

- ✅ AIMD controller runs without blocking the scheduling hot path (lightweight, in-memory)
- ✅ Q trajectory file logging implemented (`RequestLogger`, `MINISGL_LOG_DIR`)
- ⚠️ AIMD Q changes observed but full sawtooth not demonstrated (needs high-load synthetic run)
- ⚠️ Adaptive DLPM vs static DLPM comparison done at low load — Adaptive DLPM not yet clearly winning
- ✅ No regressions on LPM behavior (confirmed via smoke tests and end-to-end runs)

---

## 4. Week 3: Experiments and Ablations

### ⚠️ Step 3.1 — Baseline runs

All 4 policies (fcfs, lpm, dlpm, adaptive_dlpm) run on Chatbot Arena and LooGLE at rate=1.0 req/s.
Static DLPM tested at Q=4000 only (paper sweeps Q=500, 2000, 8000, 32000 — not yet done).

**Completed runs:**

| Dataset | Policy | Rate | Result dir |
|---|---|---|---|
| Chatbot Arena (min_turns=2) | adaptive_dlpm, lpm, fcfs | 1.0 | `results/modal_grid_20260416_010102/` |
| Chatbot Arena (min_turns=2) | dlpm (Q=4000) | 1.0 | `results/modal_grid_20260416_133620/` |
| LooGLE (real weights) | adaptive_dlpm, lpm, fcfs | 1.0 | `results/loogle_real_weights_comparison/` |
| LooGLE (real weights) | dlpm (Q=4000) | 1.0 | `results/modal_grid_20260416_134623/` |

**Key findings so far:**
- LPM causes severe cold-start starvation in Chatbot Arena (Turn-1 P99 = 37,926ms)
- Adaptive DLPM halves LPM's starvation tail (P99 = 20,441ms, 46% reduction)
- Static DLPM Q=4000 has catastrophic tail on LooGLE (P99 = 148,603ms) — Q too small for long-context prompts
- FCFS competitive or wins at rate=1.0 req/s — DLPM advantage needs higher load
- AIMD never triggered (0 updates) — control interval requires deeper queue than current load produces

**Remaining:** Multi-Q sweep for static DLPM; synthetic workload; rate sweep ≥ 2.0 req/s.

---

### Step 3.2 — AIMD hyperparameter sweep ❌

Sweep `jain_threshold`, `ttft_slo_ms`, `additive_step`, `multiplicative_factor`, `control_interval` on synthetic workload. Optimize for Jain Index while keeping throughput within 10% of LPM.

---

### ⚠️ Step 3.3 — Varying traffic intensity

Only rate=1.0 req/s tested so far. At this rate, queues are shallow and FCFS is competitive.
**Remaining:** Sweep rates 2.0, 3.0 req/s on both datasets to stress the scheduler and trigger AIMD.

---

### Step 3.4 — Workload shift experiment ❌

- t=0–60s: homogeneous traffic (one dominant client, high prefix reuse)
- t=60–120s: diverse traffic (many new clients, cold starts)

Adaptive DLPM should auto-adjust Q at the shift point. This is the headline experiment.

---

### ⚠️ Step 3.5 — Generate figures

Figures generated for current results. Still missing sawtooth and pareto.

| Figure | Status | Location |
|---|---|---|
| TTFT CDF by policy (Chatbot Arena) | ✅ | `docs/plots/chatbot_arena_real_weights/` |
| TTFT by turn — starvation view (Chatbot Arena) | ✅ | `docs/plots/chatbot_arena_real_weights/chatbot_arena_starvation_turn1.png` |
| TTFT CDF + tail latency view (LooGLE) | ✅ | `docs/plots/loogle_real_weights/` |
| Pareto frontier (Throughput vs. Jain Index) | ❌ | Needs Jain metric fix + high-load runs |
| Q over time with Jain overlay (AIMD sawtooth) | ❌ | Needs high-load synthetic run to trigger AIMD |
| Per-client max wait time (starvation bar chart) | ❌ | Needs synthetic dominant/cold workload |

---

### Week 3 Checkpoint

- ⚠️ Baseline runs done for Chatbot Arena + LooGLE at rate=1.0, all 4 policies
- ❌ Multi-Q sweep for static DLPM not done
- ❌ AIMD hyperparameters not swept
- ⚠️ Figures partially complete — TTFT/starvation plots done; sawtooth + pareto pending
- ❌ Adaptive DLPM Pareto-dominance not yet demonstrated (needs higher load + Jain metric fix)

---

## 5. Week 4: Analysis and Writeup

### Step 4.1 — Polish figures ❌

Use matplotlib or seaborn. Consistent colors, readable fonts (min 10pt), axis labels with units.

### Step 4.2 — Write the paper ❌

Structure (MLSys 2025 format):
1. Abstract
2. Introduction
3. Problem Statement
4. Related Work
5. Implementation
6. Evaluation
7. Conclusion + Future Work

### Step 4.3 — Presentation slides ❌

6 slides: title/motivation → background → design → Q-over-time figure → Pareto figure → conclusion.

---

## 6. Key Data Structures and Interfaces

### Files modified and their roles

| File | Status | What it does |
|---|---|---|
| [src/minisgl/server/api_server.py](src/minisgl/server/api_server.py) | ✅ | Reads `client_id` from HTTP body |
| [src/minisgl/message/tokenizer.py](src/minisgl/message/tokenizer.py) | ✅ | Carries `client_id` from API server to tokenizer |
| [src/minisgl/tokenizer/server.py](src/minisgl/tokenizer/server.py) | ✅ | Passes `client_id` through to `UserMsg` |
| [src/minisgl/message/backend.py](src/minisgl/message/backend.py) | ✅ | Adds `client_id` to `UserMsg` |
| [src/minisgl/scheduler/utils.py](src/minisgl/scheduler/utils.py) | ✅ | Adds `client_id`, `arrival_time` to `PendingReq` |
| [src/minisgl/scheduler/policies.py](src/minisgl/scheduler/policies.py) | ✅ | FCFS / LPM / DLPM / Adaptive DLPM + `DeficitState` |
| [src/minisgl/scheduler/telemetry.py](src/minisgl/scheduler/telemetry.py) | ✅ | `SlidingWindowTelemetry` + `AIMDConfig` + `AIMDController` |
| [src/minisgl/scheduler/prefill.py](src/minisgl/scheduler/prefill.py) | ✅ | Injects policy reordering + deficit updates into batching loop |
| [src/minisgl/scheduler/scheduler.py](src/minisgl/scheduler/scheduler.py) | ✅ | Wires telemetry + AIMD + records TTFT per request |

### Additional infrastructure (added during implementation)

| File | Status | What it does |
|---|---|---|
| [run_modal_service.py](run_modal_service.py) | ✅ | Persistent Modal ASGI endpoint; proxies `/generate`, `/healthz`, `/aimd` |
| [benchmark_modal_service_grid.py](benchmark_modal_service_grid.py) | ✅ | Grid benchmark driver: deploys per policy, sweeps rate/k/count, writes CSV+JSON summary |
| [workload/client.py](workload/client.py) | ✅ | Added `--min-turns` flag for Chatbot Arena multi-turn filtering |
| [benchmark_modal_service_grid.py](benchmark_modal_service_grid.py) | ✅ | Jain metric fixed to use paper's service-rate formula (extend×1 + output×2) |

### Log format (one JSON line per completed request — Step 2.4 ✅)

```json
{
  "req_id": "abc123",
  "client_id": "client_0",
  "arrival_time": 0.123,
  "ttft_ms": 412.3,
  "tpot_ms": 28.1,
  "prompt_len": 1024,
  "cached_len": 900,
  "cache_hit_rate": 0.879,
  "policy": "adaptive_dlpm",
  "Q_at_scheduling": 3500
}
```

---

## 7. Evaluation Protocol

### Hardware
- Document GPU model, VRAM, and the maximum unchunked prompt length that fits without OOM
- All experiments on the same hardware — no mixing

### Reproducibility
- Fix random seeds for Gamma arrival process (seed=42 in client.py)
- Log server config (batch size cap, KV cache size) in every run output
- Each experiment run = 3 repetitions; report mean ± std

### Metrics definitions

| Metric | Formula | Unit |
|---|---|---|
| Throughput | total output tokens / total wall time | tokens/sec |
| Jain Fairness Index | (Σ x_i)² / (n · Σ x_i²) where x_i = tokens served to client i | [0, 1] |
| P50/P99 TTFT | 50th/99th percentile of (first_token_time − arrival_time) | ms |
| TPOT | (completion_time − first_token_time) / (output_tokens − 1) | ms/token |
| Cache Hit Rate | Σ cached_len / Σ prompt_len | [0, 1] |
| Max Wait Time | max(first_token_time − arrival_time) per client | ms |

---

## 8. How to Run Tests

> **Platform note:** `sgl_kernel` is CUDA-only and has no macOS build. Unit tests run locally on any machine; everything else requires a GPU and must be run via Modal.

---

### Unit Tests (local, no GPU)

All scheduling policy logic, AIMD controller, and telemetry math are covered by unit tests that need no GPU or mini-sglang install.

```bash
# From the project root
pip install pytest
pytest tests/test_scheduler_logic.py -v
```

Expected: **25 passed** in < 1 second.

---

### End-to-End Smoke Test (Modal — GPU required)

`run_modal.py` handles patching, installing, and starting the server on an A100 in the cloud.

**One-time setup:**

```bash
pip install modal
modal setup    # opens browser for auth
```

**Run the smoke test** (starts server with dummy weights, sends one request, prints result):

```bash
# From the project root
modal run run_modal.py --smoke-test
```

Expected output (dummy weights produce garbage tokens — that's normal):
```
Smoke test result: OK (policy=adaptive_dlpm): 200 — data: ...
```

Key log lines to verify our code is active:
```
Adaptive DLPM: AIMD controller initialized (Q_init=4000)
Scheduler policy: adaptive_dlpm (static_Q=4000)
POST /generate HTTP/1.1" 200 OK
```

**Test a specific policy:**

```bash
modal run run_modal.py --smoke-test --policy lpm
modal run run_modal.py --smoke-test --policy dlpm
```

**What the smoke test verifies:**
- HTTP server accepts `POST /generate` with a `client_id` field
- `client_id` flows through the full pipeline: `TokenizeMsg` → `UserMsg` → `PendingReq`
- Scheduler initializes with the correct policy and AIMD controller
- Prefill runs on the GPU, produces tokens, and the response streams back as HTTP 200

This is a **plumbing test only** — it confirms nothing crashes and all modified files integrate correctly. It does NOT verify scheduling correctness, AIMD Q adjustment, or starvation reduction; those require the workload client (Steps 1.5–1.6) sending sustained multi-client traffic.

**Why the output tokens are garbage:** `--dummy-weight` initializes model weights to random values instead of loading the real checkpoint. The GPU computation is real, but the outputs are statistically meaningless. This is expected and intentional.

**Note:** A `RuntimeError: CacheManager integrity check failed` traceback appears on shutdown — this is a pre-existing mini-sglang bug triggered during process termination and does not affect request correctness.

---

### AIMD Environment Variable Reference

Policy and AIMD knobs are set via environment variables in `run_modal.py` (or passed directly when running on a GPU machine):

| Env var | Default | Meaning |
|---|---|---|
| `MINISGL_POLICY` | `lpm` | Scheduling policy: `fcfs`, `lpm`, `dlpm`, `adaptive_dlpm` |
| `MINISGL_STATIC_Q` | `4000` | Token quota Q for static DLPM |
| `AIMD_Q_INIT` | `4000` | Starting Q for adaptive DLPM |
| `AIMD_Q_MIN` | `500` | Q lower bound |
| `AIMD_Q_MAX` | `64000` | Q upper bound |
| `AIMD_JAIN_THRESHOLD` | `0.75` | Jain index below this → tighten Q |
| `AIMD_TTFT_SLO_MS` | `2000` | P99 TTFT (ms) above this → tighten Q |
| `AIMD_ADDITIVE_STEP` | `500` | Tokens added to Q per healthy step |
| `AIMD_MULT_FACTOR` | `0.5` | Q multiplier on violation |
| `AIMD_CONTROL_INTERVAL` | `50` | Scheduling steps between controller updates |

---

## 9. Risk Register

| Risk | Likelihood | Status | Mitigation / Outcome |
|---|---|---|---|
| mini SGLang's scheduler API differs from assumed structure | Medium | ✅ Resolved | Hook points verified; `reorder_pending_list` approach works cleanly |
| OOM errors with long LooGLE prompts | Medium | ⚠️ Partial | 4 extreme-length docs (>15K words) timeout at 600s; add `max_prompt_words` filter |
| AIMD Q oscillates too fast / not at all | Medium | ⚠️ Active | AIMD never triggered at rate=1.0 req/s; needs higher load (≥2.0 req/s) to fire control interval |
| Jain Index insensitive to starvation in our workload | Medium | ⚠️ Active | Client-side `cached_len` not returned by server; Jain identical across policies in current runs; need synthetic workload with repeated dominant/cold requests |
| Chatbot Arena traces don't have consistent client IDs | Low | ✅ Resolved | `question_id` used as `client_id`; `--min-turns` filter added to get multi-turn conversations |
| Adaptive DLPM does not outperform best static Q | Low | ⚠️ Unresolved | At rate=1.0 FCFS wins; at high load DLPM advantage expected — experiments pending |
| Static DLPM Q=4000 too small for LooGLE long-context prompts | — | 🆕 Discovered | P99=148s on LooGLE; need to either sweep Q values or use per-workload tuning as motivation for adaptive approach |
