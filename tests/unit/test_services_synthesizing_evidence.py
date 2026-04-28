"""Tests for synthesizing.evidence + warnings."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from social_research_probe.platforms import EngagementMetrics, RawItem
from social_research_probe.services.synthesizing.synthesis.helpers import evidence, warnings


def _raw(idx, channel="A", title="t"):
    return RawItem(
        id=str(idx),
        url=f"https://x/{idx}",
        title=title,
        author_id=f"a{idx}",
        author_name=channel,
        published_at=datetime.now(UTC),
        metrics={},
        text_excerpt="",
        thumbnail="",
        extras={},
    )


def _em(velocity=1.0, engagement=0.05, age_days=5, views=100):
    return EngagementMetrics(
        views=views,
        likes=None,
        comments=None,
        upload_date=datetime.now(UTC) - timedelta(days=age_days),
        view_velocity=velocity,
        engagement_ratio=engagement,
        comment_velocity=None,
        cross_channel_repetition=None,
    )


class TestEvidenceSummarize:
    def test_empty_items(self):
        assert evidence.summarize([], [], []) == "no items fetched"

    def test_basic(self):
        items = [_raw(1, "A"), _raw(2, "B")]
        em = [_em(), _em()]
        out = evidence.summarize(items, em, [{"source_class": "primary"}])
        assert "2 items" in out
        assert "median upload age" in out
        assert "avg view velocity" in out
        assert "top-N source mix" in out


class TestAuthorNameOf:
    def test_dict_author_name(self):
        assert evidence._author_name_of({"author_name": "X"}) == "X"

    def test_dict_falls_back_to_channel(self):
        assert evidence._author_name_of({"channel": "Y"}) == "Y"

    def test_dict_empty(self):
        assert evidence._author_name_of({}) == ""

    def test_object_author_name(self):
        assert evidence._author_name_of(_raw(1, "Z")) == "Z"

    def test_object_missing_attr(self):
        class Bare:
            pass

        assert evidence._author_name_of(Bare()) == ""


class TestEvidenceEngagementSummary:
    def test_no_data(self):
        assert evidence.summarize_engagement_metrics([]) == "no data"

    def test_basic(self):
        out = evidence.summarize_engagement_metrics([_em(), _em(velocity=2.0)])
        assert "total views" in out
        assert "view velocity" in out


class TestWarningsDetect:
    def test_no_items(self):
        out = warnings.detect([], [], [])
        assert any("no items fetched" in w for w in out)

    def test_sparse_fetch(self):
        out = warnings.detect([_raw(1)], [], [])
        assert any("sparse fetch" in w for w in out)

    def test_low_diversity(self):
        items = [_raw(1, "A"), _raw(2, "A"), _raw(3, "A"), _raw(4, "A")]
        out = warnings.detect(items, [], [])
        assert any("low channel diversity" in w for w in out)

    def test_corroboration_skip_reason(self):
        out = warnings.detect(
            [], [], [], corroboration_ran=False, corroboration_skip_reason="no key"
        )
        assert any("no key" in w for w in out)

    def test_corroboration_ran(self):
        out = warnings.detect([], [], [], corroboration_ran=True)
        assert not any("source corroboration" in w for w in out)

    def test_top_n_all_commentary(self):
        items = [_raw(i, f"C{i}") for i in range(5)]
        top = [{"source_class": "commentary", "scores": {"overall": 0.6}} for _ in range(2)]
        out = warnings.detect(items, [], top, corroboration_ran=True)
        assert any("commentary" in w for w in out)

    def test_top_n_low_score(self):
        items = [_raw(i, f"C{i}") for i in range(5)]
        top = [{"source_class": "primary", "scores": {"overall": 0.1}}]
        out = warnings.detect(items, [], top, corroboration_ran=True)
        assert any("scored below" in w for w in out)

    def test_freshness_stale(self):
        items = [_raw(i, f"C{i}") for i in range(5)]
        em = [_em(age_days=120) for _ in range(5)]
        out = warnings.detect(items, em, [], corroboration_ran=True)
        assert any("stale content" in w for w in out)
