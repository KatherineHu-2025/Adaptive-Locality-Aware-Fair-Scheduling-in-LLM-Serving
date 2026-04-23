"""
workload/dataset.py — Dataset parsers for Adaptive DLPM experiments.

Parsers load raw datasets and produce lists of RequestSpec, a unified
format consumed by the workload client (client.py, Step 1.6).

Supported datasets
------------------
chatbot_arena   lmsys/chatbot_arena_conversations (HuggingFace, gated)
                Multi-turn human-vs-model conversations. Each conversation
                becomes a sequence of requests from the same client_id,
                with prior turns prepended to each prompt so the prefix
                cache is maximally reused (implements Step 1.7).

synthetic       No download needed. Generates a two-client starvation
                workload: one dominant client with a long shared system
                prompt (high cache hit rate) and one cold client (no
                prefix reuse). Used to validate the AIMD sawtooth and
                DLPM starvation prevention.

Usage
-----
    from workload.dataset import load_chatbot_arena, load_synthetic

    specs = load_chatbot_arena(max_conversations=500, language="English")
    specs = load_synthetic(dominant_reqs=200, cold_reqs=20, prompt_tokens=2000)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Callable, List, Optional


# ---------------------------------------------------------------------------
# Unified request spec
# ---------------------------------------------------------------------------

@dataclass
class RequestSpec:
    """
    One schedulable request, ready for replay by the workload client.

    arrival_time is seconds from the start of the trace (t=0). The
    workload client (Step 1.6) uses this as a relative offset when
    replaying with a Gamma process; it does NOT mean wall-clock time.
    Set to 0.0 for datasets that don't carry timing information.
    """
    client_id: str
    prompt: str
    expected_output_len: int
    arrival_time: float = 0.0


# ---------------------------------------------------------------------------
# Token-length estimator
# ---------------------------------------------------------------------------

def _word_count_estimator(text: str) -> int:
    """
    Rough token-count estimate without a tokenizer: ~1.3 tokens per word,
    minimum 1. Good enough for sizing expected_output_len from assistant
    responses in the trace.
    """
    return max(1, int(len(text.split()) * 1.3))


# ---------------------------------------------------------------------------
# Chatbot Arena parser
# ---------------------------------------------------------------------------

def load_chatbot_arena(
    split: str = "train",
    max_conversations: Optional[int] = None,
    language: Optional[str] = "English",
    min_turns: int = 1,
    token_len_fn: Callable[[str], int] = _word_count_estimator,
) -> List[RequestSpec]:
    """
    Load lmsys/chatbot_arena_conversations and return a flat list of
    RequestSpec objects, one per user turn across all conversations.

    Multi-turn handling (Step 1.7)
    --------------------------------
    For a conversation with T user turns, this produces T RequestSpecs
    from the same client_id. Each prompt is the full conversation history
    up to and including the current user message:

        Turn 1 prompt:  "Human: <u1>"
        Turn 2 prompt:  "Human: <u1>\nAssistant: <a1>\nHuman: <u2>"
        Turn 3 prompt:  "Human: <u1>\nAssistant: <a1>\nHuman: <u2>\n
                         Assistant: <a2>\nHuman: <u3>"

    This ensures every turn after the first reuses the prefix cached from
    the previous turn — which is exactly the cache-reuse pattern DLPM is
    designed to exploit.

    Parameters
    ----------
    split               HuggingFace split name (only "train" exists)
    max_conversations   Cap on number of conversations to load (None = all)
    language            Filter to this language only (None = all languages)
    min_turns           Skip conversations with fewer turns than this
    token_len_fn        Callable(text) -> int for estimating output length.
                        Defaults to a word-count heuristic. Pass a real
                        tokenizer's encode function for exact counts.

    Returns
    -------
    List[RequestSpec] ordered by (conversation, turn) — i.e. all turns
    from conversation 0 come before all turns from conversation 1.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        raise ImportError("pip install datasets")

    ds = load_dataset("lmsys/chatbot_arena_conversations", split=split)

    if language is not None:
        ds = ds.filter(lambda ex: ex["language"] == language)

    # First pass: collect (tstamp, [RequestSpec, ...]) per conversation.
    # tstamp is a Unix timestamp (float) recording when the conversation was
    # submitted to Chatbot Arena — one value per conversation, not per turn.
    # We use it to stagger when each client starts in sequential replay mode,
    # matching the paper's "re-scale the request timestamps" approach (§6.3).
    conv_data: List[tuple[float, List[RequestSpec]]] = []
    n_conversations = 0

    for ex in ds:
        if max_conversations is not None and n_conversations >= max_conversations:
            break

        # Both conversation_a and conversation_b have the same user turns;
        # use conversation_a for the assistant responses (output length est.)
        turns = ex["conversation_a"]
        client_id: str = ex["question_id"]
        tstamp: float = float(ex.get("tstamp", 0.0))

        # Separate into (user_msg, assistant_msg) pairs
        pairs: List[tuple[str, str]] = []
        i = 0
        while i + 1 < len(turns):
            u = turns[i]
            a = turns[i + 1]
            if u.get("role") == "user" and a.get("role") == "assistant":
                pairs.append((u["content"], a["content"]))
            i += 2

        if len(pairs) < min_turns:
            continue

        # Build prompts with growing context (prefix-cache friendly).
        # All turns in this conversation share the same tstamp; arrival_time
        # is set below after normalization (second pass).
        conv_specs: List[RequestSpec] = []
        context_parts: List[str] = []
        for user_msg, assistant_msg in pairs:
            context_parts.append(f"Human: {user_msg}")
            prompt = "\n".join(context_parts)
            output_len = token_len_fn(assistant_msg)
            conv_specs.append(RequestSpec(
                client_id=client_id,
                prompt=prompt,
                expected_output_len=output_len,
                arrival_time=0.0,
            ))
            context_parts.append(f"Assistant: {assistant_msg}")

        if conv_specs:
            conv_data.append((tstamp, conv_specs))
        n_conversations += 1

    # Second pass: normalize timestamps so the earliest conversation starts at
    # t=0. Store the relative offset (seconds) on the FIRST turn of each
    # conversation only — subsequent turns keep arrival_time=0.0 because
    # sequential replay mode (arrival_mode="sequential") sends them in order
    # after each response, and does not consult their arrival_time.
    if conv_data:
        min_tstamp = min(t for t, _ in conv_data)
        for tstamp, conv_specs in conv_data:
            conv_specs[0].arrival_time = tstamp - min_tstamp

    return [s for _, conv_specs in conv_data for s in conv_specs]


# ---------------------------------------------------------------------------
# Synthetic starvation workload generator
# ---------------------------------------------------------------------------

# Shared system prompt used by the dominant client — long enough that
# the radix cache covers most of each request's tokens.
_SYSTEM_PROMPT = (
    "You are a helpful, harmless, and honest AI assistant. "
    "Always respond clearly and concisely. "
    "You have deep expertise in computer science, mathematics, and natural language. "
) * 60  # ~750 words ≈ ~1000 tokens


def load_synthetic(
    dominant_reqs: int = 200,
    cold_reqs: int = 20,
    system_prompt: str = _SYSTEM_PROMPT,
    dominant_output_len: int = 64,
    cold_output_len: int = 128,
    num_dominant_clients: int = 1,
    num_cold_clients: int = 1,
) -> List[RequestSpec]:
    """
    Generate a multi-client starvation workload (no download needed).

    dominant clients ("client_dominant_0", "client_dominant_1", ...)
        Each sends dominant_reqs // num_dominant_clients requests, all
        starting with the same system_prompt. High prefix-cache hit rate —
        the system prompt is always cached after the first request from any
        dominant client.

    cold clients ("client_cold_0", "client_cold_1", ...)
        Each sends cold_reqs // num_cold_clients requests with unique,
        unrelated prompts. No shared prefix → always cold-start prefill.
        Under LPM, these clients are always deprioritized.

    More clients → more simultaneous contenders in the pending list →
    Q affects scheduling order more visibly → AIMD sawtooth is clearer.

    Returns
    -------
    List[RequestSpec] with dominant and cold requests interleaved 1:1
    (up to the shorter list, then the remainder of the longer list appended).
    Arrival times are all 0.0 — the workload client assigns real timing.
    """
    reqs_per_dominant = max(1, dominant_reqs // num_dominant_clients)
    reqs_per_cold = max(1, cold_reqs // num_cold_clients)

    dominant: List[RequestSpec] = []
    for ci in range(num_dominant_clients):
        client_id = f"client_dominant_{ci}" if num_dominant_clients > 1 else "client_dominant"
        for i in range(reqs_per_dominant):
            dominant.append(RequestSpec(
                client_id=client_id,
                prompt=f"{system_prompt}\n\nQuestion {i}: What is {i} + {i}?",
                expected_output_len=dominant_output_len,
                arrival_time=0.0,
            ))

    cold: List[RequestSpec] = []
    for ci in range(num_cold_clients):
        client_id = f"client_cold_{ci}" if num_cold_clients > 1 else "client_cold"
        for i in range(reqs_per_cold):
            cold.append(RequestSpec(
                client_id=client_id,
                prompt=(
                    f"Explain the history and significance of the "
                    f"{_COLD_TOPICS[(ci * reqs_per_cold + i) % len(_COLD_TOPICS)]} "
                    f"in detail. Request id: {i}."
                ),
                expected_output_len=cold_output_len,
                arrival_time=0.0,
            ))

    # Interleave: dominant, cold, dominant, cold, ...
    interleaved: List[RequestSpec] = []
    for d, c in zip(dominant, cold):
        interleaved.append(d)
        interleaved.append(c)
    # Append leftovers from whichever list is longer
    interleaved.extend(dominant[len(cold):])
    interleaved.extend(cold[len(dominant):])

    return interleaved


# ---------------------------------------------------------------------------
# LooGLE parser
# ---------------------------------------------------------------------------

def load_loogle(
    config: str = "longdep_qa",
    split: str = "test",
    max_docs: Optional[int] = None,
    one_per_doc: bool = False,
    max_input_tokens: Optional[int] = 26000,
    token_len_fn: Callable[[str], int] = _word_count_estimator,
) -> List[RequestSpec]:
    """
    Load bigai-nlco/LooGLE and return a list of RequestSpec objects.

    Why LooGLE?
    -----------
    Each example contains a very long `context` (tens of thousands of chars)
    plus a short question. The prompt = context + question, making each
    prefill extremely expensive. Since different documents share no prefix,
    LooGLE requests are ideal for simulating a cold client that can never
    benefit from the radix cache — the exact starvation scenario DLPM is
    designed to address.

    client_id = doc_id
    ------------------
    Multiple QA pairs from the same document (doc_id) share a prefix, so
    they are treated as one client. If one_per_doc=True, only the first QA
    pair per document is kept — every request is then a cold start with a
    unique context.

    Parameters
    ----------
    config          LooGLE sub-task: 'longdep_qa' (default), 'shortdep_qa',
                    or 'shortdep_cloze'. Use 'longdep_qa' for the starvation
                    experiment (longest contexts).
    split           Dataset split (only 'test' exists in LooGLE).
    max_docs        Cap on distinct documents to load (None = all).
    one_per_doc     If True, keep only the first QA pair per doc_id so every
                    request is a guaranteed cold start (no shared prefix).
    max_input_tokens
                    Conservative estimated-token budget for prompt input only
                    (context + question). If exceeded, the context is truncated
                    to fit this budget using token_len_fn. Set to None to
                    disable truncation.
    token_len_fn    Callable(text) -> int for estimating output length.

    Returns
    -------
    List[RequestSpec] ordered by (doc_id, QA index within doc).
    """
    try:
        from datasets import load_dataset
    except ImportError:
        raise ImportError("pip install datasets")

    ds = load_dataset("bigai-nlco/LooGLE", config, split=split)

    specs: List[RequestSpec] = []
    seen_docs: dict = {}   # doc_id → count of QA pairs already added
    n_docs = 0
    truncated_count = 0

    for ex in ds:
        doc_id: str = ex["doc_id"]

        if doc_id not in seen_docs:
            if max_docs is not None and n_docs >= max_docs:
                continue
            seen_docs[doc_id] = 0
            n_docs += 1

        if one_per_doc and seen_docs[doc_id] >= 1:
            continue

        context: str = ex["context"]
        question: str = ex["question"]
        answer: str = ex["answer"]

        question_suffix = f"\n\nQuestion: {question}"
        prompt = f"{context}{question_suffix}"

        if max_input_tokens is not None and token_len_fn(prompt) > max_input_tokens:
            # Keep the beginning of the document so requests from the same doc
            # still share a common prefix for cache-locality experiments.
            context_words = context.split()
            lo, hi = 0, len(context_words)
            best = 0
            while lo <= hi:
                mid = (lo + hi) // 2
                candidate_context = " ".join(context_words[:mid])
                candidate_prompt = f"{candidate_context}{question_suffix}"
                if token_len_fn(candidate_prompt) <= max_input_tokens:
                    best = mid
                    lo = mid + 1
                else:
                    hi = mid - 1

            context = " ".join(context_words[:best])
            prompt = f"{context}{question_suffix}"
            truncated_count += 1

        output_len = max(token_len_fn(answer), 8)  # answers are short; floor at 8

        specs.append(RequestSpec(
            client_id=doc_id,
            prompt=prompt,
            expected_output_len=output_len,
            arrival_time=0.0,
        ))
        seen_docs[doc_id] += 1

    if truncated_count > 0:
        print(
            f"[load_loogle] Truncated {truncated_count} prompts to max_input_tokens={max_input_tokens}"
        )

    return specs


def load_loogle_prefix_mix(
    config: str = "longdep_qa",
    split: str = "test",
    dominant_reqs: int = 80,
    cold_reqs: int = 20,
    dominant_client_id: str = "client_dominant",
    cold_client_prefix: str = "client_cold",
    max_docs: Optional[int] = 500,
    max_input_tokens: Optional[int] = 26000,
    mix_mode: str = "interleave",
    chunk_size: int = 20,
    seed: int = 42,
    token_len_fn: Callable[[str], int] = _word_count_estimator,
) -> List[RequestSpec]:
    """
    Build a prefix-heavy LooGLE workload with one dominant client and many
    cold/new-context clients.

    dominant client
        Sends `dominant_reqs` requests that all share the SAME long document
        context (maximizing prefix reuse). Questions are cycled over the QA
        pairs available for that document and repeated if needed.

    cold clients
        Send `cold_reqs` requests from DIFFERENT documents/contexts. Each cold
        request uses its own client_id so there is no cross-request reuse.

    This scenario is intentionally favorable to prefix matching and is useful
    as a counterpart to starvation-focused workloads.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        raise ImportError("pip install datasets")

    ds = load_dataset("bigai-nlco/LooGLE", config, split=split)

    by_doc: dict[str, list[dict]] = {}
    for ex in ds:
        doc_id: str = ex["doc_id"]
        if doc_id not in by_doc:
            if max_docs is not None and len(by_doc) >= max_docs:
                continue
            by_doc[doc_id] = []
        by_doc[doc_id].append(ex)

    if not by_doc:
        return []

    rng = random.Random(seed)

    # Pick the doc with most QA pairs so dominant requests can vary question text
    # while keeping the same long context prefix.
    dominant_doc_id, dominant_rows = max(by_doc.items(), key=lambda kv: len(kv[1]))
    dominant_context: str = str(dominant_rows[0]["context"])
    dominant_qas: list[tuple[str, str]] = [
        (str(r["question"]), str(r["answer"]))
        for r in dominant_rows
        if r.get("question") is not None and r.get("answer") is not None
    ]
    if not dominant_qas:
        return []
    rng.shuffle(dominant_qas)

    def _build_prompt(context: str, question: str) -> tuple[str, bool]:
        question_suffix = f"\n\nQuestion: {question}"
        prompt = f"{context}{question_suffix}"
        if max_input_tokens is None or token_len_fn(prompt) <= max_input_tokens:
            return prompt, False

        # Keep the front of the document so shared-prefix behavior is preserved.
        context_words = context.split()
        lo, hi = 0, len(context_words)
        best = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate_context = " ".join(context_words[:mid])
            candidate_prompt = f"{candidate_context}{question_suffix}"
            if token_len_fn(candidate_prompt) <= max_input_tokens:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        truncated_prompt = f"{' '.join(context_words[:best])}{question_suffix}"
        return truncated_prompt, True

    dominant_specs: list[RequestSpec] = []
    truncated_count = 0
    for i in range(max(0, dominant_reqs)):
        q, a = dominant_qas[i % len(dominant_qas)]
        prompt, truncated = _build_prompt(dominant_context, q)
        if truncated:
            truncated_count += 1
        dominant_specs.append(
            RequestSpec(
                client_id=dominant_client_id,
                prompt=prompt,
                expected_output_len=max(token_len_fn(a), 8),
                arrival_time=0.0,
            )
        )

    cold_pool: list[tuple[str, dict]] = []
    for doc_id, rows in by_doc.items():
        if doc_id == dominant_doc_id:
            continue
        if rows:
            # One QA per doc to keep cold requests on fresh contexts.
            cold_pool.append((doc_id, rows[0]))

    if not cold_pool and cold_reqs > 0:
        # Fallback: if only one doc was loaded, use the dominant doc but assign
        # unique cold client IDs so they still contend as separate clients.
        cold_pool = [(dominant_doc_id, r) for r in dominant_rows]

    rng.shuffle(cold_pool)
    cold_specs: list[RequestSpec] = []
    for i in range(max(0, cold_reqs)):
        _, ex = cold_pool[i % len(cold_pool)]
        context = str(ex["context"])
        question = str(ex["question"])
        answer = str(ex["answer"])
        prompt, truncated = _build_prompt(context, question)
        if truncated:
            truncated_count += 1
        cold_specs.append(
            RequestSpec(
                client_id=f"{cold_client_prefix}_{i:04d}",
                prompt=prompt,
                expected_output_len=max(token_len_fn(answer), 8),
                arrival_time=0.0,
            )
        )

    # Mix dominant/cold requests according to the requested strategy.
    # interleave: alternate while both lists have items, then append leftovers.
    # random: weighted random ordering while preserving exact counts.
    # chunked: preserve dominant/cold ratio per fixed-size window.
    mixed: list[RequestSpec] = []
    mode = (mix_mode or "interleave").strip().lower()
    if mode == "interleave":
        for d, c in zip(dominant_specs, cold_specs):
            mixed.append(d)
            mixed.append(c)
        mixed.extend(dominant_specs[len(cold_specs):])
        mixed.extend(cold_specs[len(dominant_specs):])
    elif mode == "random":
        dom_pool = list(dominant_specs)
        cold_pool = list(cold_specs)
        rng.shuffle(dom_pool)
        rng.shuffle(cold_pool)
        dom_idx = 0
        cold_idx = 0
        dom_left = len(dom_pool)
        cold_left = len(cold_pool)
        while dom_left + cold_left > 0:
            if dom_left == 0:
                mixed.append(cold_pool[cold_idx])
                cold_idx += 1
                cold_left -= 1
                continue
            if cold_left == 0:
                mixed.append(dom_pool[dom_idx])
                dom_idx += 1
                dom_left -= 1
                continue
            p_dom = dom_left / float(dom_left + cold_left)
            if rng.random() < p_dom:
                mixed.append(dom_pool[dom_idx])
                dom_idx += 1
                dom_left -= 1
            else:
                mixed.append(cold_pool[cold_idx])
                cold_idx += 1
                cold_left -= 1
    elif mode == "chunked":
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0 for loogle_prefix chunked mix mode")
        dom_pool = list(dominant_specs)
        cold_pool = list(cold_specs)
        rng.shuffle(dom_pool)
        rng.shuffle(cold_pool)
        dom_idx = 0
        cold_idx = 0
        total_reqs = len(dom_pool) + len(cold_pool)
        dom_ratio = len(dom_pool) / float(total_reqs) if total_reqs > 0 else 0.0
        while dom_idx < len(dom_pool) or cold_idx < len(cold_pool):
            dom_left = len(dom_pool) - dom_idx
            cold_left = len(cold_pool) - cold_idx
            this_chunk = min(chunk_size, dom_left + cold_left)
            if this_chunk <= 0:
                break
            dom_in_chunk = min(dom_left, int(round(this_chunk * dom_ratio)))
            cold_in_chunk = min(cold_left, this_chunk - dom_in_chunk)
            # Fill any shortfall due to rounding/clamping.
            missing = this_chunk - (dom_in_chunk + cold_in_chunk)
            if missing > 0 and dom_left - dom_in_chunk > 0:
                take = min(missing, dom_left - dom_in_chunk)
                dom_in_chunk += take
                missing -= take
            if missing > 0 and cold_left - cold_in_chunk > 0:
                take = min(missing, cold_left - cold_in_chunk)
                cold_in_chunk += take
            chunk: list[RequestSpec] = []
            chunk.extend(dom_pool[dom_idx: dom_idx + dom_in_chunk])
            chunk.extend(cold_pool[cold_idx: cold_idx + cold_in_chunk])
            rng.shuffle(chunk)
            mixed.extend(chunk)
            dom_idx += dom_in_chunk
            cold_idx += cold_in_chunk
    else:
        raise ValueError(f"Unknown loogle_prefix mix_mode: {mix_mode}")

    if truncated_count > 0:
        print(
            f"[load_loogle_prefix_mix] Truncated {truncated_count} prompts "
            f"to max_input_tokens={max_input_tokens}"
        )

    return mixed


_COLD_TOPICS = [
    "French Revolution",
    "theory of relativity",
    "Great Wall of China",
    "Byzantine Empire",
    "invention of the printing press",
    "Industrial Revolution",
    "human genome project",
    "Renaissance art movement",
    "origins of democracy in ancient Greece",
    "development of the internet",
    "quantum mechanics",
    "fall of the Roman Empire",
    "Silk Road trade routes",
    "Age of Exploration",
    "space race between the US and USSR",
    "Enlightenment philosophy",
    "abolition of slavery in the United States",
    "development of antibiotics",
    "construction of the pyramids",
    "Cold War",
]
