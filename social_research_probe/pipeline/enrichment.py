"""Transcript fetching and LLM-based enrichment for top-5 items."""

from __future__ import annotations

import asyncio

from social_research_probe.llm.ensemble import multi_llm_prompt
from social_research_probe.types import ScoredItem
from social_research_probe.utils.progress import log


def _build_summary_prompt(title: str, channel: str, transcript: str) -> str:
    """Build the prompt sent to the LLM ensemble for a 100-word video summary."""
    return (
        "Write a detailed summary of this YouTube video (minimum 100 words). Cover:\n"
        "- The main topic and what the video is about\n"
        "- The key arguments, findings, demonstrations, or announcements\n"
        "- Who the target audience is and what they should take away\n"
        "- Specific claims, tools, people, companies, or data points mentioned\n\n"
        "Be specific and factual. Do not start with 'This video' or 'In this video'.\n\n"
        f"Title: {title}\nChannel: {channel}\n\n"
        f"Transcript:\n{transcript}"
    )


def _fallback_transcript_summary(transcript: str, word_limit: int = 220) -> str:
    """Return a readable transcript-derived fallback when the LLM summary fails."""
    words = transcript.split()
    if not words:
        return transcript
    excerpt = " ".join(words[:word_limit]).strip()
    if len(words) > word_limit:
        excerpt += " ..."
    return excerpt


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


async def _enrich_one(
    item: ScoredItem,
    fetch_transcript,
    fetch_transcript_whisper,
    whisper_sem: asyncio.Semaphore,
) -> None:
    """Fetch transcript and LLM summary for a single video item.

    Runs transcript fetch and LLM summary concurrently across items via
    asyncio.gather. Whisper fallback acquires ``whisper_sem`` to cap
    concurrent audio-download + ML-transcription jobs. Modifies item in place.

    When no transcript is available, falls back to an LLM summary built
    from the video title and description, marked as description-based.
    """
    title = item.get("title", "untitled")[:80]
    log(f"[srp] transcript: fetching for {title!r}")

    # Caption fetch runs in a thread; whisper fallback acquires the semaphore
    # only if the caption fetch returns nothing.
    text = await asyncio.to_thread(fetch_transcript, item["url"])
    if not (text and text.strip()):
        async with whisper_sem:
            text = await asyncio.to_thread(fetch_transcript_whisper, item["url"])

    cleaned = " ".join(text.split())[:6000] if text else ""

    if cleaned:
        item["transcript"] = cleaned
        item["summary_source"] = "transcript"
        log(f"[srp] summary: transcript-based for {title[:60]!r}")
        prompt = _build_summary_prompt(
            title=item.get("title", ""),
            channel=item.get("channel", ""),
            transcript=cleaned,
        )
        task_label = f"summarising transcript for {title[:60]!r}"
    else:
        item["summary_source"] = "description"
        log(f"[srp] summary: description-based for {title[:60]!r} (transcript unavailable)")
        prompt = _build_description_summary_prompt(item)
        task_label = f"summarising description for {title[:60]!r}"

    summary = await multi_llm_prompt(prompt, task=task_label)
    if summary:
        item["one_line_takeaway"] = summary
    elif cleaned:
        item["one_line_takeaway"] = _fallback_transcript_summary(cleaned)


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

    async def _gather() -> None:
        # Limit concurrent whisper jobs to 2 to avoid memory exhaustion from
        # simultaneous audio-download + ML-transcription across all top-5 items.
        whisper_sem = asyncio.Semaphore(2)
        await asyncio.gather(
            *[
                _enrich_one(item, fetch_transcript, fetch_transcript_whisper, whisper_sem)
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
