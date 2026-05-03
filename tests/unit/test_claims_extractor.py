"""Unit tests for deterministic claim extraction engine."""

from __future__ import annotations

import re

from social_research_probe.utils.claims.extractor import (
    _classify_sentence,
    _derive_claim_id,
    _extract_context,
    _extract_entities,
    _split_sentences,
    extract_claims_deterministic,
)


class TestSplitSentences:
    def test_empty_string_returns_empty(self) -> None:
        assert _split_sentences("") == []

    def test_whitespace_only_returns_empty(self) -> None:
        assert _split_sentences("   ") == []

    def test_single_sentence(self) -> None:
        result = _split_sentences("Hello world.")
        assert len(result) == 1
        assert result[0][0] == "Hello world."
        assert result[0][1] == 0

    def test_multiple_sentences_returns_offsets(self) -> None:
        text = "First sentence. Second sentence. Third sentence."
        result = _split_sentences(text)
        assert len(result) == 3
        assert result[0][0] == "First sentence."
        assert result[1][0] == "Second sentence."
        assert result[2][0] == "Third sentence."

    def test_offsets_are_char_positions(self) -> None:
        text = "Hello. World."
        result = _split_sentences(text)
        for sentence, offset in result:
            assert text[offset : offset + len(sentence)] == sentence

    def test_trailing_whitespace_ignored(self) -> None:
        # Split produces an empty trailing part — must not appear in results
        result = _split_sentences("Hello world.   ")
        assert len(result) == 1
        assert result[0][0] == "Hello world."


class TestClassifySentence:
    def test_question_type(self) -> None:
        assert _classify_sentence("Is this a good idea?") == "question"

    def test_prediction_type_will(self) -> None:
        assert _classify_sentence("AI will replace many jobs.") == "prediction"

    def test_prediction_type_expect(self) -> None:
        assert _classify_sentence("We expect growth in Q3.") == "prediction"

    def test_recommendation_starts_with_should(self) -> None:
        assert _classify_sentence("Should consider refactoring now.") == "recommendation"

    def test_recommendation_starts_with_must(self) -> None:
        assert _classify_sentence("Must update the library.") == "recommendation"

    def test_objection_however(self) -> None:
        assert _classify_sentence("However, the results were mixed.") == "objection"

    def test_objection_despite(self) -> None:
        assert _classify_sentence("Despite the effort, it failed.") == "objection"

    def test_pain_point_difficult(self) -> None:
        assert _classify_sentence("It is difficult to scale this system.") == "pain_point"

    def test_pain_point_struggle(self) -> None:
        assert _classify_sentence("Teams struggle with onboarding.") == "pain_point"

    def test_experience_ive_been(self) -> None:
        assert _classify_sentence("I've been using this for years.") == "experience"

    def test_experience_in_my_experience(self) -> None:
        assert _classify_sentence("In my experience, this works well.") == "experience"

    def test_market_signal_growing(self) -> None:
        assert _classify_sentence("The market is growing rapidly.") == "market_signal"

    def test_market_signal_industry(self) -> None:
        assert _classify_sentence("Industry adoption is accelerating.") == "market_signal"

    def test_opinion_i_think(self) -> None:
        assert _classify_sentence("I think this is wrong.") == "opinion"

    def test_opinion_i_believe(self) -> None:
        assert _classify_sentence("I believe we can do better.") == "opinion"

    def test_fact_claim_number(self) -> None:
        assert _classify_sentence("Revenue grew by 42%.") == "fact_claim"

    def test_fact_claim_according_to(self) -> None:
        assert _classify_sentence("According to studies, results improved.") == "fact_claim"

    def test_no_match_returns_none(self) -> None:
        assert _classify_sentence("This is a plain unremarkable sentence.") is None

    def test_question_beats_prediction_priority(self) -> None:
        # Ends with ? → question wins over any other signal
        result = _classify_sentence("Will AI replace jobs?")
        assert result == "question"

    def test_prediction_beats_market_signal(self) -> None:
        # "will" + "market" — prediction wins (higher priority)
        result = _classify_sentence("The market will grow significantly.")
        assert result == "prediction"


class TestExtractEntities:
    def test_extracts_numbers(self) -> None:
        entities = _extract_entities("Revenue grew by 42%.")
        assert "42%" in entities

    def test_extracts_capitalized_phrases(self) -> None:
        entities = _extract_entities("Google acquired YouTube in 2006.")
        assert "Google" in entities
        assert "YouTube" in entities

    def test_empty_sentence_returns_empty(self) -> None:
        assert _extract_entities("plain words here") == []

    def test_no_duplicates(self) -> None:
        entities = _extract_entities("Apple Apple Apple sold 100 units.")
        assert entities.count("Apple") == 1


class TestDeriveClaimId:
    def test_returns_16_char_hex(self) -> None:
        claim_id = _derive_claim_id("vid123", "AI will take over.")
        assert len(claim_id) == 16
        assert re.match(r"^[0-9a-f]{16}$", claim_id)

    def test_deterministic(self) -> None:
        a = _derive_claim_id("vid123", "AI will take over.")
        b = _derive_claim_id("vid123", "AI will take over.")
        assert a == b

    def test_different_source_gives_different_id(self) -> None:
        a = _derive_claim_id("vid1", "Same text.")
        b = _derive_claim_id("vid2", "Same text.")
        assert a != b

    def test_different_text_gives_different_id(self) -> None:
        a = _derive_claim_id("vid1", "Text A.")
        b = _derive_claim_id("vid1", "Text B.")
        assert a != b


class TestExtractContext:
    def test_middle_position(self) -> None:
        text = "abcdefghij"
        before, after = _extract_context(text, 5, width=3)
        assert before == "cde"
        assert after == "fgh"

    def test_sentence_len_shifts_after(self) -> None:
        text = "Revenue grew. This is key."
        sentence = "Revenue grew."
        before, after = _extract_context(text, 0, sentence_len=len(sentence), width=10)
        assert before == ""
        assert after == " This is k"

    def test_start_position_clamps(self) -> None:
        text = "hello world"
        before, _after = _extract_context(text, 0, width=50)
        assert before == ""

    def test_end_position_clamps(self) -> None:
        text = "hello"
        _before, after = _extract_context(text, 4, width=50)
        assert after == "o"


class TestExtractClaimsDeterministic:
    def _base_kwargs(self) -> dict:
        return {
            "source_id": "vid001",
            "source_url": "https://youtube.com/watch?v=vid001",
            "source_title": "Test Video",
            "evidence_layer": "transcript",
            "evidence_tier": "metadata_comments_transcript",
        }

    def test_empty_text_returns_empty(self) -> None:
        result = extract_claims_deterministic("", **self._base_kwargs())
        assert result == []

    def test_whitespace_only_returns_empty(self) -> None:
        result = extract_claims_deterministic("   \n  ", **self._base_kwargs())
        assert result == []

    def test_extracts_single_claim(self) -> None:
        text = "AI will replace 50% of jobs by 2030."
        result = extract_claims_deterministic(text, **self._base_kwargs())
        assert len(result) == 1
        assert result[0]["claim_type"] == "prediction"

    def test_respects_max_claims_limit(self) -> None:
        sentences = " ".join([f"This will happen in scenario {i}." for i in range(20)])
        result = extract_claims_deterministic(sentences, **self._base_kwargs(), max_claims=3)
        assert len(result) <= 3

    def test_respects_max_chars_limit(self) -> None:
        long_sentence = "According to experts, " + "a" * 600 + "."
        text = long_sentence + " Revenue grew by 10%."
        result = extract_claims_deterministic(text, **self._base_kwargs(), max_chars=50)
        # Long sentence skipped; short one extracted
        assert all(len(c["claim_text"]) <= 50 for c in result)

    def test_claim_fields_populated(self) -> None:
        text = "I think this product is excellent."
        result = extract_claims_deterministic(text, **self._base_kwargs())
        assert len(result) == 1
        claim = result[0]
        assert claim["confidence"] == 0.7
        assert claim["extraction_method"] == "deterministic"
        assert claim["corroboration_status"] == "pending"
        assert claim["contradiction_status"] == "none"
        assert claim["needs_review"] is False
        assert claim["uncertainty"] == "low"

    def test_needs_corroboration_true_for_fact_claim(self) -> None:
        text = "Revenue grew by 42% last year."
        result = extract_claims_deterministic(text, **self._base_kwargs())
        assert len(result) >= 1
        assert result[0]["needs_corroboration"] is True

    def test_needs_corroboration_true_for_prediction(self) -> None:
        text = "AI will displace 50 million workers."
        result = extract_claims_deterministic(text, **self._base_kwargs())
        assert len(result) >= 1
        assert result[0]["needs_corroboration"] is True

    def test_needs_corroboration_true_for_market_signal(self) -> None:
        text = "The market for AI tools is growing fast."
        result = extract_claims_deterministic(text, **self._base_kwargs())
        assert len(result) >= 1
        assert result[0]["needs_corroboration"] is True

    def test_needs_corroboration_false_for_opinion(self) -> None:
        text = "I think this approach is wrong."
        result = extract_claims_deterministic(text, **self._base_kwargs())
        assert len(result) >= 1
        assert result[0]["needs_corroboration"] is False

    def test_claim_id_deterministic(self) -> None:
        text = "Revenue grew by 42% last year."
        r1 = extract_claims_deterministic(text, **self._base_kwargs())
        r2 = extract_claims_deterministic(text, **self._base_kwargs())
        assert r1[0]["claim_id"] == r2[0]["claim_id"]

    def test_position_in_text_is_offset(self) -> None:
        text = "Plain sentence. Revenue grew by 10%."
        result = extract_claims_deterministic(text, **self._base_kwargs())
        for claim in result:
            pos = claim["position_in_text"]
            sentence = claim["source_sentence"]
            assert text[pos : pos + len(sentence)] == sentence

    def test_no_match_returns_empty(self) -> None:
        text = "This is a plain sentence. Another plain sentence."
        result = extract_claims_deterministic(text, **self._base_kwargs())
        assert result == []

    def test_extracts_multiple_types(self) -> None:
        text = (
            "Is this a good idea? AI will replace jobs. I think we should act. Revenue grew by 20%."
        )
        result = extract_claims_deterministic(text, **self._base_kwargs())
        types = {c["claim_type"] for c in result}
        assert len(types) >= 3

    def test_does_not_call_llm(self) -> None:
        # extract_claims_deterministic must never invoke LLM even if use_llm=True in config
        # (Phase 5B concern — verify no subprocess or LLM call happens here)
        import subprocess

        original_run = subprocess.run
        called: list[object] = []

        def mock_run(*args: object, **kwargs: object) -> object:
            called.append(args)
            return original_run(*args, **kwargs)

        import unittest.mock as mock

        with mock.patch("subprocess.run", side_effect=mock_run):
            extract_claims_deterministic(
                "Revenue grew by 50%. AI will take over.",
                **self._base_kwargs(),
            )
        assert called == [], "subprocess.run must not be called by deterministic extractor"
