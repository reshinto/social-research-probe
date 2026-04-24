"""Tests for the packet warning detector covering each branch."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from social_research_probe.synthesize.warnings import detect

from social_research_probe.platforms.base import RawItem, SignalSet


def _item(channel: str = "ch") -> RawItem:
    return RawItem(
        id="x",
        url="https://e",
        title="t",
        author_id="a",
        author_name=channel,
        published_at=datetime.now(UTC),
        metrics={"views": 100, "likes": 1, "comments": 1},
        text_excerpt="",
        thumbnail=None,
        extras={},
    )


def _signal(upload: datetime | None) -> SignalSet:
    return SignalSet(
        views=100,
        likes=1,
        comments=1,
        upload_date=upload,
        view_velocity=1.0,
        engagement_ratio=0.01,
        comment_velocity=0.0,
        cross_channel_repetition=0.0,
        raw={},
    )


def _scored(source_class: str = "secondary", overall: float = 0.7) -> dict:
    return {
        "source_class": source_class,
        "scores": {"trust": 0.6, "trend": 0.5, "opportunity": 0.7, "overall": overall},
    }


def test_no_items_returns_no_fetch_warning():
    notes = detect([], [], [])
    assert "no items fetched from platform" in notes
    assert "corroboration" in notes[-1]


def test_sparse_fetch_warning():
    notes = detect([_item("a")], [], [])
    assert any("sparse fetch" in n for n in notes)


def test_low_channel_diversity_warning():
    items = [_item("a"), _item("a"), _item("b")]
    notes = detect(items, [], [])
    assert any("low channel diversity" in n for n in notes)


def test_all_commentary_warning():
    items = [_item(f"ch{i}") for i in range(5)]
    top_n = [_scored("commentary") for _ in range(3)]
    notes = detect(items, [], top_n)
    assert any("commentary" in n for n in notes)


def test_all_unknown_class_warning():
    items = [_item(f"ch{i}") for i in range(5)]
    top_n = [_scored("unknown") for _ in range(3)]
    notes = detect(items, [], top_n)
    assert any("unknown source classification" in n for n in notes)


def test_low_score_warning():
    items = [_item(f"ch{i}") for i in range(5)]
    top_n = [_scored("secondary", overall=0.2) for _ in range(3)]
    notes = detect(items, [], top_n)
    assert any("scored below 0.5" in n for n in notes)


def test_stale_content_warning():
    now = datetime(2026, 4, 19, tzinfo=UTC)
    items = [_item(f"ch{i}") for i in range(5)]
    signals = [_signal(now - timedelta(days=60))]
    notes = detect(items, signals, [], now=now)
    assert any("stale content" in n for n in notes)


def test_clean_run_only_emits_corroboration_note():
    now = datetime(2026, 4, 19, tzinfo=UTC)
    items = [_item(f"ch{i}") for i in range(5)]
    signals = [_signal(now - timedelta(days=1))]
    top_n = [_scored("secondary", overall=0.7) for _ in range(5)]
    notes = detect(items, signals, top_n, now=now)
    assert notes == ["source corroboration was not run; trust scores are heuristic only"]


def test_corroboration_warning_omitted_when_corroboration_ran():
    now = datetime(2026, 4, 19, tzinfo=UTC)
    items = [_item(f"ch{i}") for i in range(5)]
    signals = [_signal(now - timedelta(days=1))]
    top_n = [_scored("secondary", overall=0.7) for _ in range(5)]
    notes = detect(items, signals, top_n, now=now, corroboration_ran=True)
    assert "source corroboration was not run; trust scores are heuristic only" not in notes
