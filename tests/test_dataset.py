"""
Tests for workload/dataset.py

The synthetic loader runs without any download.
The Chatbot Arena loader is tested only when HuggingFace auth is available
(skipped otherwise via pytest.importorskip / a marker).

Run:
    pytest tests/test_dataset.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make sure workload/ is importable from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from workload.dataset import RequestSpec, load_synthetic, load_loogle, _word_count_estimator


# ---------------------------------------------------------------------------
# RequestSpec
# ---------------------------------------------------------------------------

class TestRequestSpec:
    def test_defaults(self):
        r = RequestSpec(client_id="c", prompt="hello", expected_output_len=10)
        assert r.arrival_time == 0.0

    def test_fields(self):
        r = RequestSpec(client_id="alice", prompt="hi", expected_output_len=5, arrival_time=1.5)
        assert r.client_id == "alice"
        assert r.prompt == "hi"
        assert r.expected_output_len == 5
        assert r.arrival_time == 1.5


# ---------------------------------------------------------------------------
# Token estimator
# ---------------------------------------------------------------------------

class TestWordCountEstimator:
    def test_nonempty(self):
        assert _word_count_estimator("hello world") == 2  # floor(2 * 1.3) = 2
        assert _word_count_estimator("one two three four") == 5  # floor(4*1.3)=5

    def test_empty_returns_one(self):
        assert _word_count_estimator("") == 1

    def test_single_word(self):
        assert _word_count_estimator("hello") >= 1


# ---------------------------------------------------------------------------
# Synthetic workload
# ---------------------------------------------------------------------------

class TestLoadSynthetic:
    def test_output_length(self):
        specs = load_synthetic(dominant_reqs=10, cold_reqs=5)
        # 10 dominant + 5 cold = 15 total, interleaved then remaining dominant
        assert len(specs) == 15

    def test_client_ids(self):
        specs = load_synthetic(dominant_reqs=4, cold_reqs=4)
        client_ids = {s.client_id for s in specs}
        assert "client_dominant" in client_ids
        assert "client_cold" in client_ids

    def test_interleaving(self):
        specs = load_synthetic(dominant_reqs=4, cold_reqs=4)
        # First 8 should alternate dominant/cold
        assert specs[0].client_id == "client_dominant"
        assert specs[1].client_id == "client_cold"
        assert specs[2].client_id == "client_dominant"
        assert specs[3].client_id == "client_cold"

    def test_dominant_has_shared_prefix(self):
        specs = load_synthetic(dominant_reqs=10, cold_reqs=0)
        dominant = [s for s in specs if s.client_id == "client_dominant"]
        # All dominant requests share the same system prompt prefix
        first_prefix = dominant[0].prompt.split("\n\nQuestion")[0]
        for s in dominant[1:]:
            assert s.prompt.startswith(first_prefix)

    def test_cold_prompts_are_unique(self):
        specs = load_synthetic(dominant_reqs=0, cold_reqs=10)
        prompts = [s.prompt for s in specs]
        assert len(set(prompts)) == 10  # all distinct

    def test_arrival_times_are_zero(self):
        specs = load_synthetic(dominant_reqs=5, cold_reqs=5)
        assert all(s.arrival_time == 0.0 for s in specs)

    def test_expected_output_len(self):
        specs = load_synthetic(dominant_reqs=2, cold_reqs=2,
                                dominant_output_len=32, cold_output_len=128)
        for s in specs:
            if s.client_id == "client_dominant":
                assert s.expected_output_len == 32
            else:
                assert s.expected_output_len == 128

    def test_more_dominant_than_cold(self):
        specs = load_synthetic(dominant_reqs=10, cold_reqs=3)
        dominant = [s for s in specs if s.client_id == "client_dominant"]
        cold = [s for s in specs if s.client_id == "client_cold"]
        assert len(dominant) == 10
        assert len(cold) == 3

    def test_empty(self):
        assert load_synthetic(dominant_reqs=0, cold_reqs=0) == []


# ---------------------------------------------------------------------------
# LooGLE (public dataset, no auth needed)
# ---------------------------------------------------------------------------

class TestLoadLooGLE:
    def test_returns_request_specs(self):
        specs = load_loogle(max_docs=5)
        assert len(specs) > 0
        assert all(isinstance(s, RequestSpec) for s in specs)

    def test_client_id_is_doc_id(self):
        specs = load_loogle(max_docs=3, one_per_doc=True)
        # With one_per_doc=True and max_docs=3, exactly 3 distinct client_ids
        client_ids = {s.client_id for s in specs}
        assert len(client_ids) == 3

    def test_one_per_doc_gives_unique_prompts(self):
        specs = load_loogle(max_docs=10, one_per_doc=True)
        prompts = [s.prompt for s in specs]
        assert len(set(prompts)) == len(prompts)  # all distinct

    def test_multi_qa_per_doc_shares_prefix(self):
        # Without one_per_doc, multiple QA pairs from the same doc
        # should share the context prefix.
        specs = load_loogle(max_docs=3, one_per_doc=False)
        from collections import defaultdict
        by_doc: dict = defaultdict(list)
        for s in specs:
            by_doc[s.client_id].append(s)
        # Find a doc with multiple QA pairs
        multi = [reqs for reqs in by_doc.values() if len(reqs) >= 2]
        if multi:
            reqs = multi[0]
            # Both prompts share the same context prefix (context is identical)
            assert reqs[1].prompt.startswith(reqs[0].prompt.split("\n\nQuestion:")[0])

    def test_prompt_contains_context_and_question(self):
        specs = load_loogle(max_docs=2, one_per_doc=True)
        for s in specs:
            assert "\n\nQuestion:" in s.prompt

    def test_context_is_long(self):
        specs = load_loogle(max_docs=5, one_per_doc=True)
        # longdep_qa contexts are very long — at least a few thousand chars
        assert all(len(s.prompt) > 1000 for s in specs)

    def test_output_len_positive_and_floored(self):
        specs = load_loogle(max_docs=5)
        assert all(s.expected_output_len >= 8 for s in specs)

    def test_arrival_times_are_zero(self):
        specs = load_loogle(max_docs=5)
        assert all(s.arrival_time == 0.0 for s in specs)

    def test_max_docs_respected(self):
        specs = load_loogle(max_docs=4, one_per_doc=True)
        assert len({s.client_id for s in specs}) == 4


# ---------------------------------------------------------------------------
# Chatbot Arena (skipped without HuggingFace auth)
# ---------------------------------------------------------------------------

def _hf_available() -> bool:
    try:
        from datasets import load_dataset
        load_dataset("lmsys/chatbot_arena_conversations", split="train",
                     streaming=True)
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _hf_available(), reason="HuggingFace auth not available")
class TestLoadChatbotArena:
    def test_returns_request_specs(self):
        from workload.dataset import load_chatbot_arena
        specs = load_chatbot_arena(max_conversations=5, language="English")
        assert len(specs) > 0
        assert all(isinstance(s, RequestSpec) for s in specs)

    def test_client_id_is_question_id(self):
        from workload.dataset import load_chatbot_arena
        specs = load_chatbot_arena(max_conversations=5, language="English")
        # All specs from same conversation share a client_id
        client_ids = {s.client_id for s in specs}
        assert len(client_ids) <= 5

    def test_multiturn_prompts_grow(self):
        from workload.dataset import load_chatbot_arena
        specs = load_chatbot_arena(max_conversations=10, min_turns=2,
                                    language="English")
        # Group by client_id and verify prompts grow (later turns include earlier ones)
        from collections import defaultdict
        by_client: dict = defaultdict(list)
        for s in specs:
            by_client[s.client_id].append(s)
        for client, reqs in by_client.items():
            if len(reqs) >= 2:
                assert len(reqs[1].prompt) > len(reqs[0].prompt), \
                    f"Turn 2 prompt should be longer than turn 1 for {client}"

    def test_later_turns_start_with_earlier_turns(self):
        from workload.dataset import load_chatbot_arena
        specs = load_chatbot_arena(max_conversations=10, min_turns=2,
                                    language="English")
        from collections import defaultdict
        by_client: dict = defaultdict(list)
        for s in specs:
            by_client[s.client_id].append(s)
        for client, reqs in by_client.items():
            if len(reqs) >= 2:
                assert reqs[1].prompt.startswith(reqs[0].prompt), \
                    f"Turn 2 should start with turn 1 prefix for {client}"

    def test_output_len_positive(self):
        from workload.dataset import load_chatbot_arena
        specs = load_chatbot_arena(max_conversations=5, language="English")
        assert all(s.expected_output_len > 0 for s in specs)

    def test_first_turn_has_nonzero_arrival_time(self):
        """First turns of later conversations should have arrival_time > 0
        (set from the tstamp field; the very first conversation is 0.0)."""
        from workload.dataset import load_chatbot_arena
        from collections import defaultdict
        specs = load_chatbot_arena(max_conversations=10, language="English")
        by_client: dict = defaultdict(list)
        for s in specs:
            by_client[s.client_id].append(s)
        first_turns = [reqs[0] for reqs in by_client.values()]
        # At least one conversation (not the first) must have a positive offset
        assert any(t.arrival_time > 0 for t in first_turns), (
            "Expected at least one conversation with arrival_time > 0 from tstamp"
        )

    def test_subsequent_turns_have_zero_arrival_time(self):
        """Only the first turn of each conversation carries the tstamp offset;
        subsequent turns must be 0.0 (sequential mode handles ordering)."""
        from workload.dataset import load_chatbot_arena
        from collections import defaultdict
        specs = load_chatbot_arena(max_conversations=10, min_turns=2, language="English")
        by_client: dict = defaultdict(list)
        for s in specs:
            by_client[s.client_id].append(s)
        for reqs in by_client.values():
            for turn in reqs[1:]:
                assert turn.arrival_time == 0.0, (
                    f"Turn 2+ should have arrival_time=0.0, got {turn.arrival_time}"
                )
