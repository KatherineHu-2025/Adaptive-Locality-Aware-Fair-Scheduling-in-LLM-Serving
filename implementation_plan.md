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

### Step 1.1 — Clone and verify mini SGLang

```bash
git clone https://github.com/sgl-project/mini-sglang
cd mini-sglang
pip install -e .
# Smoke test: run existing LPM and FCFS policies with a toy workload
python test_basic.py --policy lpm
python test_basic.py --policy fcfs
```

**Verify:** Server starts, requests complete, radix tree is populated after first few requests. Confirm `prefix_match()` is callable from within the scheduler.

**Key files to locate:**
- `scheduler.py` (or equivalent): the main scheduling loop with `get_next_batch_to_run()`
- `radix_cache.py` (or equivalent): the radix tree with the prefix match API
- `server.py`: the HTTP server / continuous batching loop

---

### Step 1.2 — Scheduler hook point (already mapped)

The relevant files and exact hook points in mini-sglang:

| Concept | File | Class / Field |
|---|---|---|
| Waiting queue | `python/minisgl/scheduler/prefill.py` | `PrefillManager.pending_list: List[PendingReq]` |
| **Scheduling hook** | `python/minisgl/scheduler/prefill.py` | **`PrefillManager.schedule_next_batch(prefill_budget: int)`** |
| Prefix scoring (read-only) | `python/minisgl/scheduler/cache.py` | `CacheManager.match_req(pending_req) → MatchResult` |
| Cached length | `python/minisgl/kvcache/base.py` | `MatchResult.cuda_handle.cached_len: int` |
| Incoming requests | `python/minisgl/message/backend.py` | `UserMsg.uid / .input_ids / .sampling_params` |
| Pending request object | `python/minisgl/scheduler/utils.py` | `PendingReq.uid / .input_ids / .sampling_params / .chunked_req` |

**Key facts for our implementation:**
- `PrefillManager.schedule_next_batch()` iterates `pending_list` in FIFO order. We inject our policy by **reordering `pending_list` before the loop** — all downstream `PrefillAdder` logic stays intact.
- `cache_manager.match_req(pending_req)` is **read-only** (no locking). We can safely call it on every pending request to score them. The lock only happens inside `PrefillAdder._try_allocate_one()` after selection.
- `UserMsg` and `PendingReq` have no `client_id` or `arrival_time` fields — we add these ourselves.
- The scheduler runs in a single Python thread, so no additional locking is needed for our policy state.

**Files to create/modify:**

| Action | File |
|---|---|
| Modify | `python/minisgl/message/backend.py` — add `client_id: str` to `UserMsg` |
| Modify | `python/minisgl/scheduler/utils.py` — add `client_id: str`, `arrival_time: float` to `PendingReq` |
| Modify | `python/minisgl/scheduler/prefill.py` — inject policy reordering + deficit tracking |
| **Create** | `python/minisgl/scheduler/telemetry.py` — `SlidingWindowTelemetry` |
| **Create** | `python/minisgl/scheduler/policies.py` — DLPM logic + `AIMDController` |
| Modify | `python/minisgl/scheduler/scheduler.py` — record completed requests to telemetry |

---

### Step 1.3 — Implement a pluggable policy interface

Refactor `get_next_batch_to_run()` to accept a `--policy` flag that selects the scheduling policy. Keep the existing LPM logic intact as the `lpm` policy.

```python
# scheduler.py

POLICY = os.environ.get("SGLANG_POLICY", "lpm")  # or CLI arg

def get_next_batch_to_run(waiting_queue, radix_cache, budget):
    if POLICY == "lpm":
        return lpm_select(waiting_queue, radix_cache, budget)
    elif POLICY == "dlpm":
        return dlpm_select(waiting_queue, radix_cache, budget, Q=STATIC_Q)
    elif POLICY == "adaptive_dlpm":
        return dlpm_select(waiting_queue, radix_cache, budget, Q=controller.current_Q)
    elif POLICY == "fcfs":  # sanity check / related-work reference only
        return fcfs_select(waiting_queue, budget)
```

**Goal:** Be able to switch between policies with a single environment variable or CLI flag. The three primary policies are `lpm`, `dlpm`, and `adaptive_dlpm`; `fcfs` is a secondary sanity-check baseline matching the related work in the proposal.

---

### Step 1.4 — Implement Static DLPM

Implement the DLPM scheduling algorithm from the paper (arXiv 2501.14312).

**Algorithm:**

```python
# Per-client state (persisted across scheduling steps)
deficit: Dict[client_id, float] = defaultdict(float)   # tokens "owed" to this client
served:  Dict[client_id, float] = defaultdict(float)   # tokens actually served

def dlpm_select(waiting_queue, radix_cache, budget, Q):
    """
    DLPM scheduling: among requests whose client deficit is within Q of the
    minimum-deficit client, pick the one with the longest cached prefix.
    Falls back to min-deficit client if no eligible requests.
    """
    if not waiting_queue:
        return []

    # Step 1: compute each request's cache score
    for req in waiting_queue:
        req.cached_len = radix_cache.match_prefix(req.tokens)

    # Step 2: find min deficit across all waiting clients
    waiting_clients = {req.client_id for req in waiting_queue}
    min_deficit = min(deficit[c] for c in waiting_clients)

    # Step 3: eligible set — clients within Q tokens of min deficit
    eligible = [
        req for req in waiting_queue
        if deficit[req.client_id] <= min_deficit + Q
    ]

    # Step 4: among eligible, pick longest cached prefix (LPM)
    eligible.sort(key=lambda r: r.cached_len, reverse=True)

    # Step 5: fill batch up to budget
    batch = []
    tokens_used = 0
    for req in eligible:
        if tokens_used + len(req.tokens) > budget:
            break
        batch.append(req)
        tokens_used += len(req.tokens)

    # Step 6: update deficit for selected requests
    # deficit[c] increases by tokens_not_served (opportunity cost)
    # served[c] increases by tokens actually served
    selected_clients = {req.client_id for req in batch}
    for req in waiting_queue:
        if req.client_id not in selected_clients:
            # This client was skipped — their deficit grows
            deficit[req.client_id] += len(req.tokens)

    return batch
```

> **Note:** Consult the paper (Section 3-4) for the precise deficit update formula. The above is a working approximation — adjust once you've confirmed the exact formulation from the paper.

**Test:** Run a two-client workload where Client A sends prefix-heavy requests and Client B sends cold requests. Verify that under LPM, Client B starves; under Static DLPM with low Q, Client B gets scheduled periodically.

---

### Step 1.5 — Parse datasets

**Chatbot Arena:**
```python
# parse_chatbot_arena.py
# Input: raw Chatbot Arena JSONL or CSV
# Output: list of Request objects with (client_id, turns: List[str], timestamps)

# Multi-turn format: each turn appends to the previous context
# client_id can be the conversation_id field
```

**LooGLE:**
```python
# parse_loogle.py
# Input: LooGLE long-context QA dataset
# Output: list of Request objects with long prompts (thousands of tokens)
# Use these to trigger starvation: long prompts are expensive cold-start prefills
```

Both parsers should output a unified `RequestSpec` format:
```python
@dataclass
class RequestSpec:
    client_id: str
    prompt: str          # full prompt text (all turns concatenated for multi-turn)
    expected_output_len: int  # optional, for throughput estimation
    arrival_time: float  # seconds from start of trace, for replay
```

---

### Step 1.6 — Build the workload client

The proposal specifies a **Gamma process** for inter-arrival times. The Gamma distribution (shape k, rate λ) is a generalization of the Poisson process (k=1) and better models bursty real-world traffic (k<1 → over-dispersed / bursty; k>1 → more regular).

```python
# client.py

import asyncio, time, numpy as np

async def send_request(session, url, req: RequestSpec, results: list):
    t0 = time.perf_counter()
    async with session.post(url, json={"prompt": req.prompt, ...}) as resp:
        # Record TTFT on first token (use streaming API if available)
        ttft = time.perf_counter() - t0
        full_resp = await resp.json()
        tpot = (time.perf_counter() - t0 - ttft) / len(full_resp["tokens"])
        results.append({
            "client_id": req.client_id,
            "ttft": ttft,
            "tpot": tpot,
            "prompt_len": len(req.prompt),
            "arrival_time": req.arrival_time,
        })

async def run_workload(
    requests: List[RequestSpec],
    url: str,
    rate: float,        # mean requests/sec
    gamma_shape: float = 1.0,  # k=1 → Poisson; k<1 → bursty
):
    """
    Replay requests using a Gamma process at `rate` req/sec.
    Inter-arrival times ~ Gamma(shape=gamma_shape, scale=1/(rate*gamma_shape)).
    """
    results = []
    rng = np.random.default_rng(seed=42)
    async with aiohttp.ClientSession() as session:
        t_next = time.perf_counter()
        for req in sorted(requests, key=lambda r: r.arrival_time):
            # Draw Gamma inter-arrival time
            inter = rng.gamma(shape=gamma_shape, scale=1.0 / (rate * gamma_shape))
            t_next += inter
            await asyncio.sleep(max(0, t_next - time.perf_counter()))
            asyncio.create_task(send_request(session, url, req, results))
    await asyncio.gather(*asyncio.all_tasks() - {asyncio.current_task()})
    return results
```

**Also implement:** A synthetic starvation workload — one "dominant client" sending N requests/sec with a long shared system prompt, plus one "cold client" sending 1 request every few seconds with a fresh prompt. This is your controlled starvation test case.

---

### Step 1.7 — Multi-turn conversation simulation

For multi-turn, the client must concatenate all prior turns into the prompt to maximize prefix cache reuse:

```python
def build_multiturn_prompt(history: List[str], new_turn: str) -> str:
    # history = [turn1, turn2, ...], new_turn = current message
    # Concatenate in a consistent template so the prefix is stable
    return "\n".join([f"User: {t}" for t in history]) + f"\nUser: {new_turn}\nAssistant:"
```

The key property: each successive turn in a conversation shares a longer and longer prefix with the cached KV state → simulates the cache-hot dominant client scenario.

---

### Step 1.8 — Sliding window state

```python
# telemetry.py

from collections import deque
import threading, time

@dataclass
class CompletedRequest:
    client_id: str
    arrival_time: float
    ttft: float
    prompt_len: int
    cached_len: int

class SlidingWindowTelemetry:
    def __init__(self, window_size: int = 200):
        self.window: deque[CompletedRequest] = deque(maxlen=window_size)
        self.lock = threading.Lock()

    def record(self, req: CompletedRequest):
        with self.lock:
            self.window.append(req)

    def p99_ttft(self) -> float:
        with self.lock:
            if not self.window:
                return 0.0
            ttfts = sorted(r.ttft for r in self.window)
            return ttfts[int(0.99 * len(ttfts))]

    def jain_fairness_index(self) -> float:
        """
        Jain's Fairness Index over per-client token throughput in the window.
        J = (Σ x_i)^2 / (n * Σ x_i^2), range [1/n, 1], 1 = perfectly fair
        """
        with self.lock:
            if not self.window:
                return 1.0
            client_tokens: Dict[str, int] = defaultdict(int)
            for r in self.window:
                client_tokens[r.client_id] += r.prompt_len
            x = list(client_tokens.values())
            n = len(x)
            return (sum(x) ** 2) / (n * sum(xi ** 2 for xi in x))

    def cache_hit_rate(self) -> float:
        with self.lock:
            if not self.window:
                return 0.0
            return sum(r.cached_len for r in self.window) / max(
                1, sum(r.prompt_len for r in self.window)
            )
```

---

### Step 1.9 — Latency timestamps

Add timestamps to each request object at the scheduler level:

```python
@dataclass
class Request:
    ...
    arrival_time: float = field(default_factory=time.perf_counter)
    prefill_start_time: float = 0.0
    first_token_time: float = 0.0   # TTFT = first_token_time - arrival_time
    completion_time: float = 0.0

    @property
    def ttft(self):
        return self.first_token_time - self.arrival_time

    @property
    def tpot(self):
        n_output = len(self.output_tokens)
        if n_output <= 1:
            return 0.0
        return (self.completion_time - self.first_token_time) / (n_output - 1)
```

Hook `first_token_time` into the decode loop: set it on the first token decoded for each request.

---

### Step 1.10 — Per-client deficit tracking (for Jain Index)

The deficit state lives in the scheduler (Step 1.4). Expose it as a read-only snapshot for the telemetry engine:

```python
def get_deficit_snapshot(self) -> Dict[str, float]:
    return dict(self.deficit)

def deficit_disparity(self) -> float:
    """Max deficit minus min deficit across active clients."""
    vals = list(self.deficit.values())
    return max(vals) - min(vals) if len(vals) > 1 else 0.0
```

---

### Week 1 Integration Checkpoint

By end of Week 1:
- [ ] All three primary policy flags work (`lpm`, `dlpm`, `adaptive_dlpm`); `fcfs` works as secondary
- [ ] Static DLPM passes the two-client starvation test
- [ ] Client script fires Gamma-process traffic at the server
- [ ] Telemetry logs TTFT, TPOT, Jain Index, cache hit rate per request
- [ ] A single run produces a CSV/JSON log that can be analyzed offline

---

## 3. Week 2: Adaptive AIMD Controller

**Owner:** All three — this is the core novel contribution.

### Step 2.1 — Define the control loop parameters

```python
@dataclass
class AIMDConfig:
    # Q bounds
    Q_min: float = 500         # tokens — strictest fairness
    Q_max: float = 64_000      # tokens — near-pure LPM
    Q_init: float = 4_000      # starting point

    # Fairness trigger
    jain_threshold: float = 0.75   # below this → decrease Q
    ttft_slo_ms: float = 2000.0    # above this P99 TTFT → decrease Q

    # AIMD rates
    additive_step: float = 500     # tokens added per step when healthy
    multiplicative_factor: float = 0.5  # Q halved when fairness violated

    # Control loop frequency
    control_interval_steps: int = 50   # re-evaluate every N scheduling steps
```

These are initial guesses. The Week 3 ablation sweep will tune them.

---

### Step 2.2 — Implement the AIMD controller

```python
# aimd_controller.py

class AIMDController:
    def __init__(self, config: AIMDConfig, telemetry: SlidingWindowTelemetry):
        self.config = config
        self.telemetry = telemetry
        self.current_Q = config.Q_init
        self.step_count = 0
        self.Q_history: List[Tuple[float, float]] = []  # (timestamp, Q)

    def step(self):
        """Called once per scheduling step. Updates Q every control_interval_steps."""
        self.step_count += 1
        if self.step_count % self.config.control_interval_steps != 0:
            return

        jain = self.telemetry.jain_fairness_index()
        p99  = self.telemetry.p99_ttft() * 1000  # convert to ms

        fairness_violated = (
            jain < self.config.jain_threshold or
            p99 > self.config.ttft_slo_ms
        )

        if fairness_violated:
            # Multiplicative decrease — slash Q
            new_Q = max(self.config.Q_min, self.current_Q * self.config.multiplicative_factor)
        else:
            # Additive increase — gradually relax toward more locality
            new_Q = min(self.config.Q_max, self.current_Q + self.config.additive_step)

        self.current_Q = new_Q
        self.Q_history.append((time.perf_counter(), new_Q))

    def get_Q(self) -> float:
        return self.current_Q
```

Hook `controller.step()` into the scheduling loop — call it at the top of each `get_next_batch_to_run()` invocation. Pass `controller.get_Q()` as the Q argument to `dlpm_select`.

---

### Step 2.3 — Wire the controller into the scheduler

```python
# In the scheduler's main loop:

controller = AIMDController(AIMDConfig(), telemetry)

def get_next_batch_to_run(waiting_queue, radix_cache, budget):
    if POLICY == "adaptive_dlpm":
        controller.step()
        return dlpm_select(waiting_queue, radix_cache, budget, Q=controller.get_Q())
    ...
```

**Thread safety:** The controller reads from `telemetry` (which uses a lock). The `current_Q` float is written only by the controller thread and read only by the scheduler thread — if both run in the same Python thread (likely for mini SGLang), no additional locking needed.

---

### Step 2.4 — Log Q trajectory

Append to the telemetry log:
```json
{"timestamp": 1.23, "event": "q_update", "Q": 3500, "jain": 0.81, "p99_ttft_ms": 412}
```

This is the data for the "Q over time" figure in your paper.

---

### Step 2.5 — Validate AIMD behavior on synthetic workload

Run the synthetic starvation workload (dominant client + cold client):

**Expected behavior:**
1. At startup, Q is at `Q_init` — DLPM allows some starvation.
2. Dominant client floods the queue → cold client's TTFT spikes → Jain drops.
3. Controller detects violation → Q drops multiplicatively → cold client gets scheduled.
4. System stabilizes → Jain recovers → Q climbs back up additively.
5. Plot Q over time: should show AIMD saw-tooth pattern.

If the saw-tooth doesn't appear, debug the telemetry calculation or threshold values.

---

### Week 2 Checkpoint

- [ ] AIMD controller runs without blocking the scheduling hot path
- [ ] Q trajectory is logged with timestamps and triggering metrics
- [ ] Synthetic starvation test shows saw-tooth Q oscillation
- [ ] Adaptive DLPM outperforms static DLPM (any Q) on Jain Index without catastrophic throughput drop
- [ ] No regressions on existing LPM behavior

---

## 4. Week 3: Experiments and Ablations

### Step 3.1 — Baseline runs

The primary comparison (per the proposal) is **LPM vs. static DLPM vs. Adaptive DLPM**. Run the following configs:

| Policy | Q | Notes |
|---|---|---|
| `lpm` | — | Primary baseline |
| `dlpm` | 500 | Strict fairness end of Pareto frontier |
| `dlpm` | 2000 | — |
| `dlpm` | 8000 | — |
| `dlpm` | 32000 | High-locality end of Pareto frontier |
| `adaptive_dlpm` | dynamic | Our contribution |
| `fcfs` | — | Secondary / related-work reference only |

For each config, run:
- Chatbot Arena trace at 3 request/sec (Gamma process, moderate load)
- LooGLE trace at 3 request/sec (starvation-inducing long prompts)
- Synthetic starvation workload

Collect per-run CSV: `{request_id, client_id, arrival_time, ttft, tpot, prompt_len, cached_len}`.

---

### Step 3.2 — AIMD hyperparameter sweep

Sweep the following independently:

| Parameter | Values to test |
|---|---|
| `jain_threshold` | 0.6, 0.7, 0.75, 0.8, 0.85 |
| `ttft_slo_ms` | 1000, 2000, 4000 |
| `additive_step` | 100, 500, 1000 |
| `multiplicative_factor` | 0.25, 0.5, 0.75 |
| `control_interval_steps` | 10, 50, 100 |

Run the synthetic starvation workload for each. Optimize for Jain Index while keeping throughput within 10% of LPM.

---

### Step 3.3 — Varying traffic intensity

For the best AIMD config, sweep arrival rate: 1, 2, 3, 5, 8 req/sec.

Show that adaptive DLPM gracefully degrades (Jain stays high, throughput tracks LPM) while static DLPM at large Q starves under high load.

---

### Step 3.4 — Workload shift experiment

Design a workload that shifts mid-run:
- t=0–60s: homogeneous traffic (one dominant client, high prefix reuse) → static large Q is fine
- t=60–120s: diverse traffic (many new clients, cold starts) → small Q needed

Show that adaptive DLPM detects the shift and adjusts Q. Static DLPM cannot.

This is your headline experiment — it directly motivates why adaptive Q is necessary.

---

### Step 3.5 — Generate figures

**Figure 1 — Pareto Frontier**
- X-axis: Jain Fairness Index (higher = better)
- Y-axis: Throughput (tokens/sec, higher = better)
- Points: LPM, DLPM@Q=500, DLPM@Q=2000, DLPM@Q=8000, DLPM@Q=32000, Adaptive DLPM
- FCFS shown as a labeled reference point (far-left low-throughput anchor from related work)
- Adaptive DLPM should appear in the top-right corner (Pareto-dominant or near it)

**Figure 2 — Q Over Time (AIMD Saw-tooth)**
- X-axis: time (seconds)
- Y-axis: Q value
- Overlay: Jain Index on secondary Y-axis
- Show the workload shift at t=60s

**Figure 3 — CDF of TTFT by Policy**
- X-axis: TTFT (ms)
- Y-axis: CDF
- Lines: LPM, Static DLPM (best Q), Adaptive DLPM
- Key insight: Adaptive DLPM should match or beat static DLPM at the tail (P99)

**Figure 4 — Per-client Max Wait Time**
- Bar chart: for each policy, the max waiting time experienced by the "cold client"
- Shows starvation is eliminated by DLPM and further improved by Adaptive DLPM

---

### Week 3 Checkpoint

- [ ] All baseline runs complete and logged
- [ ] AIMD hyperparameters tuned
- [ ] All four figures drafted (can be rough plots)
- [ ] Result: Adaptive DLPM Pareto-dominates or matches static DLPM across at least 2 of 3 workload types

---

## 5. Week 4: Analysis and Writeup

### Step 4.1 — Polish figures

Use matplotlib or seaborn. Consistent color scheme, readable fonts (min 10pt), axis labels with units. Follow MLSys paper style.

### Step 4.2 — Write the paper (suggested structure)

The proposal is already formatted in MLSys 2025 style. Expand each section:

1. **Abstract** (~150 words): Problem → Gap (static Q) → Contribution (AIMD) → Key result (X% better Jain, Y% throughput retained)
2. **Introduction** (§1 from proposal): Multi-tenant LLM serving, starvation problem, why static Q fails, our approach. Cite \cite{locality_aware_fair_scheduling_llm}, \cite{sglang}, \cite{VTC}.
3. **Problem Statement** (§2 from proposal): RQ1 (which metrics signal misconfigured Q) and RQ2 (can AIMD track optimal Q). Formalize with notation.
4. **Related Work** (§3 from proposal): VTC, vLLM FCFS, SGLang LPM, DLPM — expand with k-LPM (arXiv 2502.04677) and PARS.
5. **Implementation** (§4 from proposal): Mini SGLang hook points, AIMD loop (cite Clipper \cite{crankshaw2017clipperlowlatencyonlineprediction}), sliding window, threading model, overhead analysis.
6. **Evaluation**: Experimental setup (Gamma process, two datasets), all four figures with discussion.
7. **Conclusion + Future Work**: D²LPM (distributed), eviction-aware scheduling.

### Step 4.3 — Presentation slides

- Slide 1: Title / motivation (1 sentence: "LPM starves cold clients")
- Slide 2: Background — LPM vs. DLPM, the static Q limitation
- Slide 3: Our design — AIMD controller diagram
- Slide 4: Figure 2 (Q over time) — the "aha" slide
- Slide 5: Figure 1 (Pareto frontier) — the payoff slide
- Slide 6: Conclusion + limitations

---

## 6. Key Data Structures and Interfaces

### Request object (additions to mini SGLang's existing Request)

```python
@dataclass
class Request:
    # -- existing fields --
    tokens: List[int]
    output_tokens: List[int]
    # -- new fields --
    client_id: str                  # for per-client deficit tracking
    arrival_time: float             # perf_counter at submission
    first_token_time: float = 0.0   # set on first decode step
    completion_time: float = 0.0
    cached_len: int = 0             # filled by scheduler before selection
```

### Scheduler state (additions)

```python
class Scheduler:
    deficit: Dict[str, float]             # per-client deficit (tokens)
    telemetry: SlidingWindowTelemetry
    controller: AIMDController            # only for adaptive_dlpm
    policy: str                           # "lpm" | "dlpm" | "adaptive_dlpm" | "fcfs"
    static_Q: float                       # only for dlpm
```

### Log format (one JSON line per completed request)

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
| mini SGLang's scheduler API differs from assumed structure | Medium | Read the code in Week 1 before writing any scheduler code (Step 1.2) |
| OOM errors with long LooGLE prompts | Medium | Cap prompt length at GPU's max unchunked prefill size |
| AIMD Q oscillates too fast / not at all | Medium | Tune `control_interval_steps` and `multiplicative_factor` in Week 3 sweep |
| Jain Index insensitive to starvation in our workload | Low | Also report max per-client wait time as a direct starvation metric |
| Chatbot Arena traces don't have consistent client IDs | Low | Assign synthetic client IDs by conversation_id field |
| Adaptive DLPM does not outperform best static Q | Low | Frame result as: adaptive Q finds the right Q automatically without human tuning — this is valuable even if peak performance is matched |
