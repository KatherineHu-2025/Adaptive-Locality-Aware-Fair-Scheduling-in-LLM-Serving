# Codebase Guide

A walkthrough of every file we wrote or modified, explained from first principles.

---

## The Big Picture

When you type a message into an AI chat app, here's what happens on the server:

```
1. HTTP request arrives        "Hello, who are you?"  +  client_id: "alice"
        ↓
2. Tokenization                "Hello, who are you?"  →  [9906, 11, 889, 527, 499, 30]
        ↓
3. Scheduling                  Whose request gets processed next?
        ↓
4. GPU forward pass            Model generates tokens one by one
        ↓
5. Response streams back       "I am an AI assistant..."
```

**Our project only changes step 3.** But to make fairness work, we need to know *which user* each request belongs to (`client_id`). That information enters at step 1 and has to be carried through step 2 without being dropped. That's why we touched files in all three layers.

---

## Layer 1: The Front Door (HTTP)

### `src/minisgl/server/api_server.py`

**What it is:** A web server built with FastAPI. It's the first thing that receives a user's request over the internet.

**What it does:** Listens for HTTP POST requests, reads the JSON body, and packages everything up to pass deeper into the system.

**What we changed:** Added a `client_id` field to the request models.

Before our change, the server only read `prompt` and `max_tokens`. Even if a client sent `client_id`, the server ignored it silently:

```python
# Before
class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int
```

After:
```python
# After
class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int
    client_id: str = ""   # ← new; "" means "anonymous" if not provided
```

We also updated both HTTP endpoints (`/generate` and `/v1/chat/completions`) to pass `client_id` into the next stage.

**Example HTTP request that now works:**
```bash
curl -X POST http://localhost:19190/generate \
  -d '{"prompt": "Hello", "max_tokens": 50, "client_id": "alice"}'
```

---

## Layer 2: The Tokenizer (Text → Numbers)

LLMs don't understand words — they understand integers called **tokens**. "Hello" might become `[9906]`. The tokenizer does this conversion in a separate background process.

### `src/minisgl/message/tokenizer.py`

**What it is:** A data structure (called `TokenizeMsg`) that acts like an envelope passed from the API server to the tokenizer.

**What it does:** Carries the user's text and settings (max tokens, temperature, etc.) from the API server to the tokenizer worker.

**What we changed:** Added `client_id` to the envelope so it isn't lost in transit:

```python
# Before
@dataclass
class TokenizeMsg(BaseTokenizerMsg):
    uid: int
    text: str
    sampling_params: SamplingParams

# After
@dataclass
class TokenizeMsg(BaseTokenizerMsg):
    uid: int
    text: str
    sampling_params: SamplingParams
    client_id: str = ""   # ← new
```

Without this, `client_id` would have been dropped the moment the API server handed off to the tokenizer — like writing a name on a sticky note but handing it over in an envelope with no room for sticky notes.

### `src/minisgl/tokenizer/server.py`

**What it is:** The tokenizer worker process. It receives text, converts it to token IDs, and sends the result to the scheduler.

**What it does:** This is the handoff point between "understanding the request" and "deciding when to serve it."

**What we changed:** Added one line to pass `client_id` through when creating the outgoing message:

```python
# Before
UserMsg(
    uid=msg.uid,
    input_ids=t,
    sampling_params=msg.sampling_params,
)

# After
UserMsg(
    uid=msg.uid,
    input_ids=t,
    sampling_params=msg.sampling_params,
    client_id=msg.client_id,   # ← new; relay it forward
)
```

This is the critical relay. Without this line, `client_id` arrives in the tokenizer but never makes it out to the scheduler.

### `src/minisgl/message/backend.py`

**What it is:** Another envelope — this one (`UserMsg`) carries the tokenized request from the tokenizer to the scheduler.

**What we changed:** Added `client_id` here too, so the field exists for the tokenizer to fill in:

```python
@dataclass
class UserMsg(BaseBackendMsg):
    uid: int
    input_ids: torch.Tensor
    sampling_params: SamplingParams
    client_id: str = ""   # ← new
```

---

## Layer 3: The Scheduler (Our Main Contribution)

This is where all the interesting work happens. The scheduler maintains a **waiting queue** of requests and decides which ones to process in each batch.

### `src/minisgl/scheduler/utils.py`

**What it is:** Defines `PendingReq` — the internal object representing a request while it's sitting in the waiting queue.

**What we changed:** Added two fields:

```python
@dataclass
class PendingReq:
    uid: int
    input_ids: torch.Tensor
    sampling_params: SamplingParams
    client_id: str = ""                                    # ← which tenant owns this request
    arrival_time: float = field(default_factory=time.perf_counter)  # ← when it arrived
```

- `client_id` is used by the deficit tracker to group requests by tenant.
- `arrival_time` is used to measure how long each request waited before getting its first token (called **TTFT — Time To First Token**).

---

### `src/minisgl/scheduler/policies.py`

**What it is:** The actual scheduling algorithms.

**What it does:** Contains one main function, `reorder_pending_list()`, that takes the waiting queue and returns it in a new order based on the chosen policy.

#### The four policies

**FCFS (First-Come-First-Served)**
Return the queue unchanged. Simple, fair in arrival order, but completely ignores the cache.

**LPM (Longest Prefix Match)**
Sort by how many tokens are already in the KV cache. The request with the most cached tokens goes first, because serving it requires less computation.

```
Queue: [alice: 0 cached, bob: 500 cached, carol: 200 cached]
After LPM: [bob: 500, carol: 200, alice: 0]
```

Problem: alice never gets served if bob and carol keep arriving with good cache hits. This is called **starvation**.

**DLPM (Deficit Longest Prefix Match)**
Adds fairness on top of LPM. Maintains a "deficit" counter per client — how many tokens they've been denied. Only clients within `Q` tokens of the least-served client are *eligible* to be scheduled. Among eligible clients, pick by LPM.

```
deficit = {alice: 3000, bob: 0, carol: 500}
Q = 1000
min_deficit = 0  (bob)
eligible = clients where deficit ≤ 0 + 1000 → {bob: 0, carol: 500}
ineligible = {alice: 3000}   ← alice must wait until others accumulate deficit
```

After serving bob and carol, their deficits reset to 0 and alice's grows — eventually alice becomes eligible.

**Adaptive DLPM (our contribution)**
Same as DLPM, but Q is not fixed. The AIMD controller (see `telemetry.py`) adjusts Q automatically at runtime based on live metrics.

#### DeficitState

Also defined in this file. A dictionary that tracks, for each `client_id`, how many tokens of service they've been denied:

```python
# After a round where bob was served but alice was not (alice had 800 token prompt):
deficit = {alice: 800, bob: 0}
```

---

### `src/minisgl/scheduler/telemetry.py`

**What it is:** The measurement and control layer. Two classes: `SlidingWindowTelemetry` and `AIMDController`.

#### SlidingWindowTelemetry

Keeps a rolling record of the last 200 completed requests and computes live metrics:

| Metric | What it means |
|---|---|
| **P99 TTFT** | The wait time at the 99th percentile — catches the worst-case clients |
| **Jain Fairness Index** | A number from 0 to 1. 1 = all clients served equally. 1/n = one client got everything |
| **Cache hit rate** | What fraction of tokens were served from the KV cache |
| **Max wait time** | The single longest wait — a direct starvation signal |

The Jain Fairness Index formula:

```
J = (sum of tokens served to each client)²
    ─────────────────────────────────────────
    n  ×  sum of (tokens served to each client)²

Range: [1/n, 1]    where n = number of clients
```

#### AIMDController

Reads the telemetry metrics every 50 scheduling steps and adjusts Q. The rule is simple:

```
if Jain index < 0.75  OR  P99 TTFT > 2000ms:
    Q = Q × 0.5        ← cut in half (enforce stricter fairness)
else:
    Q = Q + 500        ← grow slowly (allow more cache-chasing)
```

This is the **Additive Increase / Multiplicative Decrease** pattern — the same idea behind TCP congestion control. Grow slowly when things are good; react sharply when something goes wrong. Over time, Q traces a sawtooth wave that tracks the workload.

---

### `src/minisgl/scheduler/prefill.py`

**What it is:** The heart of the scheduler — the component that builds each batch of requests to send to the GPU.

**What it does:** mini-sglang processes requests in batches. This file manages the waiting queue (`pending_list`) and each round picks the next batch. The GPU can only hold so many requests at once, so the `PrefillAdder` inside this file tries to fit as many as possible given memory constraints.

**What we changed:** Before each batch is built, we now run our policy:

```
Step 1: Ask the AIMD controller to update Q (if enough steps have passed)
Step 2: Reorder the waiting queue using our policy
Step 3: Run the original PrefillAdder on the reordered queue  ← unchanged
Step 4: Rebuild the queue with remaining requests
Step 5: Update deficit counters (who was served, who wasn't)
```

The key design decision: by reordering the queue *before* the batching logic runs, we inject our entire scheduling policy without touching any GPU memory or allocation code. mini-sglang's internals are completely unaware that we changed anything.

---

### `src/minisgl/scheduler/scheduler.py`

**What it is:** The top-level coordinator. It creates all the components and connects them together.

**What it does:** On startup, reads configuration from environment variables and instantiates:
- `SlidingWindowTelemetry` — the metrics tracker
- `AIMDController` — the Q tuner (only for `adaptive_dlpm`)
- `PrefillManager` — the batching engine (with our policy plugged in)

It also hooks into the request lifecycle to record timing:
- When a `UserMsg` arrives → record arrival time
- When the first output token is produced → record the time, compute TTFT, log to telemetry

---

## Supporting Infrastructure

### `apply_patches.sh`

Copies all 9 modified files from `src/` into a cloned mini-sglang repo. Run this before any GPU test.

```bash
bash apply_patches.sh ./mini-sglang
```

mini-sglang is a separate project; we don't fork it. Instead, we keep our changes in `src/` and overlay them on top. This script does the overlaying.

### `run_modal.py`

Runs everything on a cloud A100 GPU via [Modal](https://modal.com). The image build process is:

1. Start from an NVIDIA CUDA base image (Linux + GPU drivers)
2. Clone mini-sglang and install it
3. Copy our project files into `/workspace`
4. Run `apply_patches.sh` to overlay our changes onto mini-sglang

Key commands:
```bash
modal run run_modal.py                          # run unit tests on GPU
modal run run_modal.py --smoke-test             # start server, send one request
modal run run_modal.py --experiment starvation  # run a named experiment
```

### `tests/test_scheduler_logic.py`

25 unit tests that verify the scheduler logic without any GPU. They test:
- FCFS, LPM, DLPM ordering correctness
- Deficit accumulation and reset
- Starvation prevention
- Jain index calculation
- AIMD sawtooth behavior (increase when healthy, halve when violated)

Run with: `pytest tests/test_scheduler_logic.py -v`
