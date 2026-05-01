"""Enrichment technology adapters."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.technologies import BaseTechnology


def _coerce_word_limit(value: object, default: int = 100) -> int:
    """Return a positive integer word limit."""
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return default
    return limit if limit > 0 else default


def _limit_words(text: str, word_limit: int) -> str:
    """Cap text to at most word_limit whitespace-delimited words."""
    words = text.split()
    return " ".join(words[:word_limit])


class SummaryEnsembleTech(BaseTechnology[object, str]):
    """Technology using the LLM ensemble to generate summaries."""

    name: ClassVar[str] = "llm_ensemble"
    enabled_config_key: ClassVar[str] = "llm_ensemble"

    async def _execute(self, data: object) -> str | None:
        from social_research_probe.utils.llm.ensemble import multi_llm_prompt

        title = data.get("title", "") if isinstance(data, dict) else ""
        configured_limit = data.get("summary_word_limit") if isinstance(data, dict) else None
        word_limit = _coerce_word_limit(configured_limit)

        surrogate = data.get("text_surrogate") if isinstance(data, dict) else None
        if surrogate:
            content = surrogate.get("primary_text", "")
            label = "Content"
        else:
            content = data.get("transcript", "") if isinstance(data, dict) else ""
            label = "Transcript"

        prompt = (
            f"Summarise this YouTube video in at most {word_limit} words.\n"
            f"Title: {title}\n{label}: {content[:3000]}"
        )

        summary = await multi_llm_prompt(prompt) or ""
        summary = _limit_words(summary, word_limit)
        return summary if summary else None


class TranscriptWhisperTech(BaseTechnology[str, str]):
    """Fallback technology using yt-dlp to download audio and Whisper to transcribe."""

    name: ClassVar[str] = "whisper_fallback"
    enabled_config_key: ClassVar[str] = "whisper"

    async def _execute(self, input_data: str) -> str | None:
        import asyncio
        import tempfile

        from social_research_probe.technologies.media_fetch.yt_dlp import download_audio
        from social_research_probe.technologies.transcript_fetch.whisper import transcribe_audio

        with tempfile.TemporaryDirectory(prefix="srp-ytdlp-") as tmpdir:
            audio_path = await asyncio.to_thread(download_audio, input_data, tmpdir)
            if audio_path is not None:
                return await asyncio.to_thread(transcribe_audio, audio_path)
