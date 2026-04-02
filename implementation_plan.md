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
8. [Risk Register](#8-risk-register)

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

### ❌ Step 1.5 — Parse datasets

Not yet implemented. Need parsers for:
- **Chatbot Arena** — multi-turn conversations; use `conversation_id` as `client_id`
- **LooGLE** — long-context QA; useful for triggering starvation (expensive cold-start prefills)

Both should output a unified `RequestSpec`:
```python
@dataclass
class RequestSpec:
    client_id: str
    prompt: str
    expected_output_len: int
    arrival_time: float   # seconds from trace start, for replay
```

---

### ❌ Step 1.6 — Build the workload client

Not yet implemented. Needs to replay traces using a **Gamma process** for inter-arrival times (k<1 = bursty, k=1 = Poisson/random, k>1 = regular).

Also needs a synthetic starvation workload: one dominant client sending N req/sec with a long shared system prompt, plus one cold client sending 1 req every few seconds.

---

### ❌ Step 1.7 — Multi-turn conversation simulation

Not yet implemented. For multi-turn, each new turn must concatenate all prior turns into the prompt so the prefix cache is maximally reused.

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
- ❌ Client script fires Gamma-process traffic at the server
- ✅ Telemetry records TTFT, Jain Index, cache hit rate per request (in memory)
- ❌ A single run produces a CSV/JSON log that can be analyzed offline

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

### ⚠️ Step 2.4 — Log Q trajectory

Q history is stored in memory (`controller.history`). File-based logging (CSV/JSON per run) is not yet implemented — needed for generating the "Q over time" figure.

---

### ❌ Step 2.5 — Validate AIMD behavior on synthetic workload

Requires a GPU run with the starvation workload (Step 1.6). Expected: Q should show a sawtooth pattern — climbing slowly when Jain is healthy, dropping sharply when the cold client is starved.

---

### Week 2 Checkpoint

- ✅ AIMD controller runs without blocking the scheduling hot path (lightweight, in-memory)
- ⚠️ Q trajectory stored in memory — file logging not yet done
- ❌ Synthetic starvation test shows sawtooth Q oscillation (requires GPU + workload client)
- ❌ Adaptive DLPM outperforms static DLPM on Jain Index (requires experiments)
- ❌ No regressions on LPM behavior (requires GPU smoke test confirmation)

---

## 4. Week 3: Experiments and Ablations

### Step 3.1 — Baseline runs ❌

Run all policy/Q combinations on Chatbot Arena + LooGLE + synthetic workload. Collect per-request CSV logs.

| Policy | Q |
|---|---|
| `lpm` | — |
| `dlpm` | 500, 2000, 8000, 32000 |
| `adaptive_dlpm` | dynamic |
| `fcfs` | — |

---

### Step 3.2 — AIMD hyperparameter sweep ❌

Sweep `jain_threshold`, `ttft_slo_ms`, `additive_step`, `multiplicative_factor`, `control_interval` on synthetic workload. Optimize for Jain Index while keeping throughput within 10% of LPM.

---

### Step 3.3 — Varying traffic intensity ❌

Sweep arrival rate (1, 2, 3, 5, 8 req/sec) for best AIMD config. Show graceful degradation.

---

### Step 3.4 — Workload shift experiment ❌

- t=0–60s: homogeneous traffic (one dominant client, high prefix reuse)
- t=60–120s: diverse traffic (many new clients, cold starts)

Adaptive DLPM should auto-adjust Q at the shift point. This is the headline experiment.

---

### Step 3.5 — Generate figures ❌

- **Figure 1:** Pareto frontier (Throughput vs. Jain Index)
- **Figure 2:** Q over time with Jain overlay (AIMD sawtooth)
- **Figure 3:** CDF of TTFT by policy
- **Figure 4:** Per-client max wait time (starvation bar chart)

---

### Week 3 Checkpoint

- ❌ All baseline runs complete and logged
- ❌ AIMD hyperparameters tuned
- ❌ All four figures drafted
- ❌ Adaptive DLPM Pareto-dominates or matches static DLPM across ≥2 workload types

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

### Log format (one JSON line per completed request) — target for Step 2.4

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

## 8. Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| mini SGLang's scheduler API differs from assumed structure | Medium | Hook points were verified by reading the source (Step 1.2) |
| OOM errors with long LooGLE prompts | Medium | Cap prompt length at GPU's max unchunked prefill size |
| AIMD Q oscillates too fast / not at all | Medium | Tune `control_interval` and `multiplicative_factor` in Week 3 sweep |
| Jain Index insensitive to starvation in our workload | Low | Also report max per-client wait time as a direct starvation metric |
| Chatbot Arena traces don't have consistent client IDs | Low | Assign synthetic client IDs by conversation_id field |
| Adaptive DLPM does not outperform best static Q | Low | Frame result as: adaptive Q finds the right Q automatically without human tuning — this is valuable even if peak performance is matched |
