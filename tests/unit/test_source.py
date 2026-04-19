from datetime import datetime, timezone
from social_research_probe.platforms.base import RawItem, TrustHints
from social_research_probe.validation.source import SourceClass, classify

def _item(url="https://youtube.com/watch?v=x", extras=None):
    return RawItem(
        id="x", url=url, title="t",
        author_id="c1", author_name="c1",
        published_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        metrics={}, text_excerpt=None, thumbnail=None,
        extras=extras or {},
    )

def test_primary_when_verified_and_old_channel():
    hints = TrustHints(account_age_days=3000, verified=True,
                       subscriber_count=500_000, upload_cadence_days=3.0,
                       citation_markers=["https://arxiv.org/abs/2401.0001"])
    assert classify(_item(), hints) is SourceClass.PRIMARY

def test_commentary_when_no_citations_and_young():
    hints = TrustHints(account_age_days=30, verified=False,
                       subscriber_count=50, upload_cadence_days=0.5,
                       citation_markers=[])
    assert classify(_item(), hints) is SourceClass.COMMENTARY

def test_secondary_default():
    hints = TrustHints(account_age_days=800, verified=False,
                       subscriber_count=20_000, upload_cadence_days=7.0,
                       citation_markers=["https://example.com/post"])
    assert classify(_item(), hints) is SourceClass.SECONDARY


def test_unknown_when_old_no_markers_low_subs():
    # No markers, subs < 1000, age >= 180 → UNKNOWN (covers line 29 of source.py)
    hints = TrustHints(account_age_days=365, verified=False,
                       subscriber_count=100, upload_cadence_days=30.0,
                       citation_markers=[])
    assert classify(_item(), hints) is SourceClass.UNKNOWN
