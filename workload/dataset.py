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

    specs: List[RequestSpec] = []
    n_conversations = 0

    for ex in ds:
        if max_conversations is not None and n_conversations >= max_conversations:
            break

        # Both conversation_a and conversation_b have the same user turns;
        # use conversation_a for the assistant responses (output length est.)
        turns = ex["conversation_a"]
        client_id: str = ex["question_id"]

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

        # Build prompts with growing context (prefix-cache friendly)
        context_parts: List[str] = []
        for user_msg, assistant_msg in pairs:
            context_parts.append(f"Human: {user_msg}")
            prompt = "\n".join(context_parts)
            output_len = token_len_fn(assistant_msg)
            specs.append(RequestSpec(
                client_id=client_id,
                prompt=prompt,
                expected_output_len=output_len,
                arrival_time=0.0,
            ))
            context_parts.append(f"Assistant: {assistant_msg}")

        n_conversations += 1

    return specs


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
) -> List[RequestSpec]:
    """
    Generate a two-client starvation workload (no download needed).

    dominant client ("client_dominant")
        Sends `dominant_reqs` requests, each starting with `system_prompt`
        followed by a short unique question. High prefix-cache hit rate —
        the system prompt is always cached after the first request.

    cold client ("client_cold")
        Sends `cold_reqs` requests with unique, unrelated prompts.
        No shared prefix → always triggers a cold-start prefill.
        Under LPM, this client is always deprioritized.

    Under DLPM / Adaptive DLPM, the cold client's growing deficit should
    eventually force the scheduler to serve it, preventing starvation.

    Returns
    -------
    List[RequestSpec] with dominant and cold requests interleaved 1:1
    (up to the shorter list, then the remainder of the longer list appended).
    Arrival times are all 0.0 — the workload client assigns real timing.
    """
    dominant: List[RequestSpec] = [
        RequestSpec(
            client_id="client_dominant",
            prompt=f"{system_prompt}\n\nQuestion {i}: What is {i} + {i}?",
            expected_output_len=dominant_output_len,
            arrival_time=0.0,
        )
        for i in range(dominant_reqs)
    ]

    cold: List[RequestSpec] = [
        RequestSpec(
            client_id="client_cold",
            prompt=(
                f"Explain the history and significance of the {_COLD_TOPICS[i % len(_COLD_TOPICS)]} "
                f"in detail. Request id: {i}."
            ),
            expected_output_len=cold_output_len,
            arrival_time=0.0,
        )
        for i in range(cold_reqs)
    ]

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

        prompt = f"{context}\n\nQuestion: {question}"
        output_len = max(token_len_fn(answer), 8)  # answers are short; floor at 8

        specs.append(RequestSpec(
            client_id=doc_id,
            prompt=prompt,
            expected_output_len=output_len,
            arrival_time=0.0,
        ))
        seen_docs[doc_id] += 1

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
