"""Transcript fetching and LLM-based enrichment for top-5 items."""

from __future__ import annotations

import asyncio

from social_research_probe.config import load_active_config
from social_research_probe.llm.base import LLMRunner
from social_research_probe.llm.ensemble import multi_llm_prompt
from social_research_probe.llm.prompts import RECONCILE_SUMMARY_PROMPT
from social_research_probe.platforms.youtube.extract import _extract_video_id
from social_research_probe.synthesize.divergence import jaccard_divergence
from social_research_probe.types import ScoredItem
from social_research_probe.utils.fast_mode import fast_mode_enabled
from social_research_probe.utils.pipeline_cache import (
    get_str,
    hash_key,
    set_str,
    summary_cache,
)
from social_research_probe.utils.progress import log

_FILLER_BLOCKLIST = (
    "this video",
    "in this video",
    "the speaker discusses",
    "the video discusses",
    "overall,",
    "in conclusion,",
    "stay tuned",
    "don't forget to like",
)


def _build_summary_prompt(title: str, channel: str, transcript: str, word_limit: int) -> str:
    """Build the prompt sent to the LLM ensemble for a ``word_limit``-word summary.

    Redesigned in Phase 9 of the evidence-suite plan to address observed
    failure modes in cached summaries (generic filler, missing numbers,
    hallucinated proper nouns, mid-sentence truncation). The prompt is now
    structured as:

    1. Explicit word budget (``≤ word_limit``, not "approximately").
    2. Required content list (numbers, organizations, factual claims).
    3. Anti-hallucination rule (never introduce info not in the transcript).
    4. Filler blocklist with concrete forbidden phrases.
    5. One-shot exemplar showing the desired style.
    6. Title / Channel / Transcript block the model rewrites.
    """
    exemplar = (
        "EXAMPLE INPUT: Transcript of a 15-minute talk by Prof. Jane Liu at"
        " Stanford explaining how transformer attention scales to 1M tokens"
        " via sliding windows.\n"
        "EXAMPLE OUTPUT: Stanford's Prof. Jane Liu explains how sliding-window"
        " attention lets transformer models scale to 1,000,000-token contexts"
        " without quadratic memory cost. She contrasts dense attention (O(n²))"
        " with windowed variants (O(n·w)), citing specific benchmarks where"
        " the windowed approach matches or beats the dense baseline on long-"
        "context retrieval tasks. Target audience: ML practitioners evaluating"
        " long-context architectures."
    )
    return (
        f"Summarise the YouTube video below in at most {word_limit} words.\n\n"
        "Required content:\n"
        "- Main topic and what the video argues, demonstrates, or announces.\n"
        "- Every specific number (counts, percentages, dates, durations) from"
        " the transcript.\n"
        "- Every named organization, person, product, or paper mentioned.\n"
        "- Target audience and the concrete takeaway for them.\n\n"
        "Hard rules:\n"
        "- Never introduce information that isn't in the transcript. If a"
        " fact isn't there, leave it out.\n"
        "- Never start with 'This video', 'In this video', or 'The speaker"
        " discusses'.\n"
        "- Never end with 'Overall,', 'In conclusion,', or 'Stay tuned'.\n"
        "- End on a complete sentence within the word limit. Prefer being"
        " one sentence short over being cut mid-sentence.\n\n"
        f"{exemplar}\n\n"
        f"Title: {title}\nChannel: {channel}\n\n"
        f"Transcript:\n{transcript}"
    )


def _first_media_url_runner() -> LLMRunner | None:
    """Return the first registered runner with ``supports_media_url=True`` that is healthy."""
    from social_research_probe.llm.registry import get_runner, list_runners

    for name in list_runners():
        try:
            runner = get_runner(name)
        except Exception:
            continue
        if getattr(runner, "supports_media_url", False) and runner.health_check():
            return runner
    return None


async def _url_based_summary(url: str, word_limit: int, cfg=None) -> str | None:
    """Return a runner-direct URL summary, or None when unavailable or disabled."""
    if fast_mode_enabled():
        return None
    if cfg is None:
        cfg = load_active_config()
    if not cfg.feature_enabled("media_url_summary_enabled"):
        return None
    video_id = _extract_video_id(url)
    cache = summary_cache() if video_id else None
    cache_key = f"url:{video_id}:{word_limit}" if video_id else None
    if cache is not None and cache_key is not None:
        cached = get_str(cache, cache_key)
        if cached is not None:
            return cached
    runner = _first_media_url_runner()
    if runner is None:
        return None
    try:
        summary = await runner.summarize_media(url, word_limit=word_limit)
    except Exception:
        return None
    if summary and cache is not None and cache_key is not None:
        set_str(cache, cache_key, summary)
    return summary


async def _reconcile_summaries(
    title: str, channel: str, transcript_summary: str, url_summary: str, word_limit: int
) -> str | None:
    """Merge two summaries into one via the multi-LLM ensemble."""
    prompt = RECONCILE_SUMMARY_PROMPT.format(
        word_limit=word_limit,
        title=title,
        channel=channel,
        transcript_summary=transcript_summary,
        url_summary=url_summary,
    )
    cache = summary_cache()
    key = hash_key("merged", title, str(word_limit), transcript_summary, url_summary)
    cached = get_str(cache, key)
    if cached is not None:
        return cached
    merged = await multi_llm_prompt(prompt, task=f"reconciling summaries for {title[:60]!r}")
    if merged:
        set_str(cache, key, merged)
    return merged


async def _cached_text_summary(item: ScoredItem, prompt: str, task_label: str) -> str | None:
    """Wrap the text-summary LLM call with on-disk memoisation.

    Key includes the full prompt hash so any change to transcript, title, or
    word limit invalidates naturally. Falls back to a direct LLM call when the
    item has no parseable video_id (non-YouTube or malformed URL).
    """
    video_id = _extract_video_id(item.get("url", "")) or ""
    if not video_id:
        return await multi_llm_prompt(prompt, task=task_label)
    cache = summary_cache()
    key = hash_key("text", video_id, prompt)
    cached = get_str(cache, key)
    if cached is not None:
        return cached
    summary = await multi_llm_prompt(prompt, task=task_label)
    if summary:
        set_str(cache, key, summary)
    return summary


def _fallback_transcript_summary(transcript: str, word_limit: int = 100) -> str:
    """Return a readable transcript-derived fallback when the LLM summary fails.

    Truncates at the last complete sentence that fits within ``word_limit``
    words, rather than cutting mid-sentence. When no sentence boundary fits,
    falls back to word-boundary truncation with an ellipsis marker.
    """
    words = transcript.split()
    if not words:
        return transcript
    if len(words) <= word_limit:
        return transcript.strip()
    # Try sentence-boundary truncation: take the longest prefix that ends in
    # . ! ? and still fits within word_limit.
    truncated = " ".join(words[:word_limit]).strip()
    last_stop = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
    if last_stop >= 0 and last_stop >= len(truncated) // 2:
        # Keep the terminator.
        return truncated[: last_stop + 1].strip()
    # No sentence boundary in the upper half — fall back to word cut + ellipsis.
    return truncated + " ..."


def _build_description_summary_prompt(item: ScoredItem) -> str:
    """Build the prompt for a 100-word summary based on video description only."""
    title = item.get("title", "")
    channel = item.get("channel", "")
    published = item.get("published_at", "")
    description = item.get("text_excerpt", "")
    return (
        "Write a summary of this YouTube video (minimum 100 words) using only the"
        " information provided below — no transcript is available.\n"
        "Cover: the main topic, likely key arguments or demonstrations, who the target"
        " audience is, and any specific people, tools, or events referenced.\n"
        "Do not invent content not present below."
        " Do not start with 'This video' or 'In this video'.\n\n"
        f"Title: {title}\nChannel: {channel}\nPublished: {published}\n\n"
        f"Description:\n{description}"
    )


async def _fetch_transcript_with_fallback(
    item: ScoredItem,
    fetch_transcript,
    fetch_transcript_whisper,
    whisper_sem: asyncio.Semaphore,
    cfg=None,
) -> str:
    """Fetch transcript with whisper fallback; return cleaned text or empty string."""
    if cfg is None:
        cfg = load_active_config()
    if not cfg.feature_enabled("transcript_fetch_enabled"):
        return ""
    text = await asyncio.to_thread(fetch_transcript, item["url"])
    if not (text and text.strip()):
        async with whisper_sem:
            text = await asyncio.to_thread(fetch_transcript_whisper, item["url"])
    return " ".join(text.split())[:6000] if text else ""


def _text_summary_prompt(item: ScoredItem, cleaned: str, word_limit: int) -> tuple[str, str]:
    """Build the text-based summary prompt and log label; picks transcript or description."""
    title = item.get("title", "untitled")[:80]
    if cleaned:
        item["transcript"] = cleaned
        item["summary_source"] = "transcript"
        log(f"[srp] summary: transcript-based for {title[:60]!r}")
        prompt = _build_summary_prompt(
            title=item.get("title", ""),
            channel=item.get("channel", ""),
            transcript=cleaned,
            word_limit=word_limit,
        )
        return prompt, f"summarising transcript for {title[:60]!r}"
    item["summary_source"] = "description"
    log(f"[srp] summary: description-based for {title[:60]!r} (transcript unavailable)")
    return _build_description_summary_prompt(item), f"summarising description for {title[:60]!r}"


async def _merge_or_pick(
    item: ScoredItem,
    text_summary: str | None,
    url_summary: str | None,
    cleaned: str,
    word_limit: int,
    divergence_threshold: float,
    cfg=None,
) -> str | None:
    """Reconcile text+url summaries, or return whichever single one exists."""
    if cfg is None:
        cfg = load_active_config()
    merge_on = cfg.feature_enabled("merged_summary_enabled") and not fast_mode_enabled()
    if text_summary and url_summary:
        divergence = jaccard_divergence(text_summary, url_summary)
        item["summary_divergence"] = divergence
        item["url_summary"] = url_summary
        if merge_on and divergence >= divergence_threshold:
            merged = await _reconcile_summaries(
                title=item.get("title", "")[:80],
                channel=item.get("channel", ""),
                transcript_summary=text_summary,
                url_summary=url_summary,
                word_limit=word_limit,
            )
            if merged:
                return merged
        return text_summary
    if text_summary:
        return text_summary
    if url_summary:
        item["url_summary"] = url_summary
        return url_summary
    if cleaned:
        return _fallback_transcript_summary(cleaned, word_limit=word_limit)
    return None


async def _enrich_one(
    item: ScoredItem,
    fetch_transcript,
    fetch_transcript_whisper,
    whisper_sem: asyncio.Semaphore,
    cfg=None,
) -> None:
    """Fetch transcript + LLM summaries concurrently, then merge into one summary.

    Fan-out in parallel: (a) transcript fetch → text-based summary, (b) runner
    direct URL summary when any runner supports it. Results reconciled into a
    single ``item["summary"]`` of ``per_item_summary_words``. Divergence between
    the two is recorded on the item so warnings can surface mismatches.
    """
    if cfg is None:
        cfg = load_active_config()
    if not cfg.feature_enabled("enrichment_enabled"):
        return
    word_limit = int(cfg.tunables.get("per_item_summary_words", 100))
    threshold = float(cfg.tunables.get("summary_divergence_threshold", 0.4))
    title = item.get("title", "untitled")[:80]
    log(f"[srp] transcript: fetching for {title!r}")

    cleaned_task = _fetch_transcript_with_fallback(
        item, fetch_transcript, fetch_transcript_whisper, whisper_sem, cfg=cfg
    )
    url_task = _url_based_summary(item["url"], word_limit, cfg=cfg)
    cleaned, url_summary = await asyncio.gather(cleaned_task, url_task)

    prompt, task_label = _text_summary_prompt(item, cleaned, word_limit)
    text_summary = await _cached_text_summary(item, prompt, task_label)

    merged = await _merge_or_pick(
        item, text_summary, url_summary, cleaned, word_limit, threshold, cfg=cfg
    )
    if merged:
        item["one_line_takeaway"] = merged
        item["summary"] = merged


async def _enrich_top5_with_transcripts(top5: list[ScoredItem]) -> None:
    """Fetch transcripts and AI summaries for top-5 items concurrently.

    Transcript sources tried in order per item:
    1. YouTube captions via yt-dlp (``fetch_transcript``).
    2. Whisper transcription of the downloaded audio (``fetch_transcript_whisper``).

    All 5 items are processed in parallel via asyncio.gather so transcript
    downloads and LLM calls overlap. Whisper is capped at 2 concurrent jobs
    to prevent memory exhaustion. Item failures do not abort the batch.

    The full transcript (up to 6000 chars) is stored as item["transcript"].
    A 100-word+ summary from the multi-LLM ensemble is stored as
    item["one_line_takeaway"]. Falls back silently on any error.
    Modifies the dicts in place.
    """
    from social_research_probe.platforms.youtube.extract import fetch_transcript
    from social_research_probe.platforms.youtube.whisper_transcript import (
        fetch_transcript_whisper,
    )

    # Load config once per batch instead of per-item-per-helper (was ~4 reads
    # per item = 20 disk reads for a top-5 run). Pass down via cfg= kwarg.
    cfg = load_active_config()

    async def _gather() -> None:
        # Limit concurrent whisper jobs to 2 to avoid memory exhaustion from
        # simultaneous audio-download + ML-transcription across all top-5 items.
        whisper_sem = asyncio.Semaphore(2)
        await asyncio.gather(
            *[
                _enrich_one(item, fetch_transcript, fetch_transcript_whisper, whisper_sem, cfg=cfg)
                for item in top5
            ],
            return_exceptions=True,
        )

    await _gather()


def _fetch_best_transcript(url: str, primary_fn, fallback_fn) -> str | None:
    """Try primary transcript fetch; fall back to whisper if it returns nothing.

    Both callables accept a URL and return ``str | None``.
    All exceptions are swallowed so failures never crash the pipeline.
    """
    try:
        text = primary_fn(url)
    except Exception:
        text = None
    if text and text.strip():
        return text
    try:
        return fallback_fn(url)
    except Exception:
        return None
