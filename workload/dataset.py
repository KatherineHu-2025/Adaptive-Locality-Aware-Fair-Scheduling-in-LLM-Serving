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

    conversation_id — used by sequential replay mode to group turns into
    independent coroutines.  Defaults to client_id (backward-compatible).
    In misbehaving scenarios, multiple conversations share the same
    client_id (so the server tracks their combined fairness) but have
    distinct conversation_ids (so each gets its own sequential coroutine).
    """
    client_id: str
    prompt: str
    expected_output_len: int
    arrival_time: float = 0.0
    conversation_id: str = ""  # empty → falls back to client_id in replay


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
    max_turns: Optional[int] = None,
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
    max_turns           Skip conversations with more turns than this
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
        if max_turns is not None and len(pairs) > max_turns:
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
# Chatbot Arena misbehaving-client scenario
# ---------------------------------------------------------------------------

def load_chatbot_arena_misbehave(
    n_well_convos_per_group: int = 5,
    n_misbehave_convos_per_group: int = 15,
    n_well_groups: int = 2,
    n_misbehave_groups: int = 2,
    min_turns: int = 2,
    language: Optional[str] = "English",
    token_len_fn: Callable[[str], int] = _word_count_estimator,
) -> List[RequestSpec]:
    """
    Replicate the original DLPM paper's misbehaving-client scenario
    (Section 6.3, Figure 8) using Chatbot Arena data.

    Setup
    -----
    Four virtual client groups are created:
      - well_0, well_1        : n_well_convos_per_group conversations each
      - misbehave_0, misbehave_1 : n_misbehave_convos_per_group conversations each

    Each group is assigned a single client_id (e.g. "well_0") so the server
    tracks their combined token budget for fairness.  Each conversation within
    a group gets a unique conversation_id (e.g. "well_0_c3") so the sequential
    replay runner spawns one coroutine per conversation.

    Result: misbehaving groups run more parallel sequential threads → generate
    proportionally more tokens → Jain index drops → AIMD triggers correctly.

    All conversations start at t=0 (no stagger) so contention is immediate.

    Parameters
    ----------
    n_well_convos_per_group      conversations assigned to each well-behaved group
    n_misbehave_convos_per_group conversations assigned to each misbehaving group
    n_well_groups                number of well-behaved client groups (default 2)
    n_misbehave_groups           number of misbehaving client groups (default 2)
    min_turns                    minimum turns per conversation (default 2)
    """
    total_needed = (
        n_well_groups * n_well_convos_per_group
        + n_misbehave_groups * n_misbehave_convos_per_group
    )
    # Load a flat list then re-group by original client_id to get per-conversation lists.
    flat = load_chatbot_arena(
        max_conversations=total_needed,
        language=language,
        min_turns=min_turns,
        token_len_fn=token_len_fn,
    )

    # Collect per-conversation turn lists preserving order.
    conversations: List[List[RequestSpec]] = []
    current_conv: List[RequestSpec] = []
    current_cid: Optional[str] = None
    for spec in flat:
        if spec.client_id != current_cid:
            if current_conv:
                conversations.append(current_conv)
            current_conv = [spec]
            current_cid = spec.client_id
        else:
            current_conv.append(spec)
    if current_conv:
        conversations.append(current_conv)

    result: List[RequestSpec] = []
    conv_idx = 0

    def _assign(group_name: str, n_convos: int) -> None:
        nonlocal conv_idx
        for c in range(n_convos):
            if conv_idx >= len(conversations):
                break
            conv_id = f"{group_name}_c{c}"
            for spec in conversations[conv_idx]:
                result.append(RequestSpec(
                    client_id=group_name,
                    conversation_id=conv_id,
                    prompt=spec.prompt,
                    expected_output_len=spec.expected_output_len,
                    arrival_time=0.0,  # all start together
                ))
            conv_idx += 1

    for g in range(n_well_groups):
        _assign(f"well_{g}", n_well_convos_per_group)
    for g in range(n_misbehave_groups):
        _assign(f"misbehave_{g}", n_misbehave_convos_per_group)

    return result


def load_chatbot_arena_misbehave_rate(
    n_well_groups: int = 2,
    n_misbehave_groups: int = 2,
    n_convos_per_group: int = 100,
    rate_well: float = 0.5,
    rate_misbehave: float = 1.5,
    duration_sec: float = 30.0,
    phase_profile: str = "steady",
    num_phases: int = 1,
    phase_duration_sec: Optional[float] = None,
    rate_well_low: Optional[float] = None,
    rate_well_high: Optional[float] = None,
    rate_misbehave_low: Optional[float] = None,
    rate_misbehave_high: Optional[float] = None,
    min_turns: int = 2,
    well_min_turns: int = 1,
    well_max_turns: Optional[int] = None,
    misbehave_min_turns: Optional[int] = None,
    language: Optional[str] = "English",
    token_len_fn: Callable[[str], int] = _word_count_estimator,
    seed: int = 42,
) -> List[RequestSpec]:
    """
    Rate-based misbehaving-client scenario (faithful DLPM paper §6.3 replication).

    All groups run over the same measurement duration, but misbehaving groups
    start conversations at a higher Poisson rate.  Each conversation keeps its
    turns sequential, so turn N+1 is only sent after turn N completes and can
    reuse the prefix cache.  Use with arrival_mode="sequential".

    Parameters
    ----------
    n_well_groups       number of well-behaved client groups (default 2)
    n_misbehave_groups  number of misbehaving client groups (default 2)
    n_convos_per_group  max conversation starts per group (default 100)
    rate_well           Poisson conversation-start rate for well groups (req/s)
    rate_misbehave      Poisson conversation-start rate for misbehaving groups
    duration_sec        fixed measurement duration for generating starts
    phase_profile       "steady" for one fixed-rate interval; "alternating"
                        alternates well-heavy and misbehave-heavy phases
    num_phases          number of phases for alternating profile
    phase_duration_sec  duration of each phase; defaults to duration_sec
    rate_*_low/high     per-phase rates used by alternating profile
    well_min_turns      minimum turns for well-behaved conversations
    well_max_turns      maximum turns for well-behaved conversations
    misbehave_min_turns minimum turns for misbehaving conversations
    seed                RNG seed for reproducibility
    """
    import numpy as np

    if duration_sec <= 0:
        raise ValueError("duration_sec must be positive")
    if rate_well <= 0 or rate_misbehave <= 0:
        raise ValueError("rate_well and rate_misbehave must be positive")
    if n_convos_per_group <= 0:
        raise ValueError("n_convos_per_group must be positive")
    if phase_profile not in {"steady", "alternating"}:
        raise ValueError("phase_profile must be 'steady' or 'alternating'")
    if num_phases <= 0:
        raise ValueError("num_phases must be positive")
    if phase_duration_sec is not None and phase_duration_sec <= 0:
        raise ValueError("phase_duration_sec must be positive")

    rng = np.random.default_rng(seed)
    group_names = [f"well_{g}" for g in range(n_well_groups)] + [
        f"misbehave_{g}" for g in range(n_misbehave_groups)
    ]

    if phase_profile == "steady":
        phases = [(0.0, duration_sec)]
        effective_duration_sec = duration_sec
    else:
        per_phase = phase_duration_sec if phase_duration_sec is not None else duration_sec
        phases = [(i * per_phase, per_phase) for i in range(num_phases)]
        effective_duration_sec = num_phases * per_phase

    well_hi = rate_well_high if rate_well_high is not None else rate_well
    mis_hi = rate_misbehave_high if rate_misbehave_high is not None else rate_misbehave
    well_lo = rate_well_low if rate_well_low is not None else max(rate_well * 0.25, 0.05)
    mis_lo = rate_misbehave_low if rate_misbehave_low is not None else max(rate_misbehave * 0.25, 0.05)

    for name, value in {
        "rate_well_low": well_lo,
        "rate_well_high": well_hi,
        "rate_misbehave_low": mis_lo,
        "rate_misbehave_high": mis_hi,
    }.items():
        if value <= 0:
            raise ValueError(f"{name} must be positive")

    def _phase_rate(group_name: str, phase_idx: int) -> float:
        if phase_profile == "steady":
            return rate_well if group_name.startswith("well_") else rate_misbehave
        well_heavy_phase = phase_idx % 2 == 0
        if group_name.startswith("well_"):
            return well_hi if well_heavy_phase else well_lo
        return mis_lo if well_heavy_phase else mis_hi

    group_starts: List[tuple[str, List[float]]] = []
    total_needed = 0
    for group_name in group_names:
        starts: List[float] = []
        for phase_idx, (phase_start, phase_duration) in enumerate(phases):
            rate = _phase_rate(group_name, phase_idx)
            t = 0.0
            while len(starts) < n_convos_per_group:
                t += float(rng.exponential(scale=1.0 / rate))
                if t > phase_duration:
                    break
                starts.append(phase_start + t)
            if len(starts) >= n_convos_per_group:
                break
        if not starts:
            # Keep tiny test runs meaningful even when the sampled first arrival
            # lands just outside a short duration.
            fallback_rate = _phase_rate(group_name, 0)
            starts = [min(effective_duration_sec, 1.0 / fallback_rate)]
        group_starts.append((group_name, starts))
        total_needed += len(starts)

    effective_mis_min_turns = misbehave_min_turns if misbehave_min_turns is not None else min_turns

    well_needed = sum(len(starts) for group_name, starts in group_starts if group_name.startswith("well_"))
    mis_needed = total_needed - well_needed

    def _regroup(flat: List[RequestSpec]) -> List[List[RequestSpec]]:
        conversations: List[List[RequestSpec]] = []
        current_conv: List[RequestSpec] = []
        current_cid: Optional[str] = None
        for spec in flat:
            if spec.client_id != current_cid:
                if current_conv:
                    conversations.append(current_conv)
                current_conv = [spec]
                current_cid = spec.client_id
            else:
                current_conv.append(spec)
        if current_conv:
            conversations.append(current_conv)
        return conversations

    well_flat = load_chatbot_arena(
        max_conversations=well_needed,
        language=language,
        min_turns=well_min_turns,
        max_turns=well_max_turns,
        token_len_fn=token_len_fn,
    ) if well_needed > 0 else []
    mis_flat = load_chatbot_arena(
        max_conversations=mis_needed,
        language=language,
        min_turns=effective_mis_min_turns,
        max_turns=None,
        token_len_fn=token_len_fn,
    ) if mis_needed > 0 else []

    conversations_by_kind = {
        "well": _regroup(well_flat),
        "misbehave": _regroup(mis_flat),
    }
    conv_idx_by_kind = {"well": 0, "misbehave": 0}

    result: List[RequestSpec] = []

    for group_name, starts in group_starts:
        pool_name = "well" if group_name.startswith("well_") else "misbehave"
        conversations = conversations_by_kind[pool_name]
        for c, start_time in enumerate(starts):
            conv_idx = conv_idx_by_kind[pool_name]
            if conv_idx >= len(conversations):
                break
            conv_idx_by_kind[pool_name] += 1
            conv_id = f"{group_name}_c{c}"
            for spec in conversations[conv_idx]:
                result.append(RequestSpec(
                    client_id=group_name,
                    conversation_id=conv_id,
                    prompt=spec.prompt,
                    expected_output_len=spec.expected_output_len,
                    # Only the first turn's arrival_time is consulted by
                    # sequential replay. Leaving it on every turn is harmless
                    # and useful for debugging the generated trace.
                    arrival_time=start_time,
                ))

    # Sort conversation groups by start time for deterministic replay logs.
    result.sort(key=lambda s: s.arrival_time)
    return result

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
