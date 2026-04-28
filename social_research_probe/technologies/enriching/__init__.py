"""Enrichment technology adapters."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.technologies import BaseTechnology


class SummaryEnsembleTech(BaseTechnology[object, str]):
    """Technology using the LLM ensemble to generate summaries."""

    name: ClassVar[str] = "llm_ensemble"

    async def _execute(self, data: object) -> str | None:
        from social_research_probe.technologies.llms.ensemble import multi_llm_prompt
        from social_research_probe.utils.caching.pipeline_cache import (
            get_str,
            hash_key,
            set_str,
            summary_cache,
        )

        title = data.get("title", "") if isinstance(data, dict) else ""
        url = data.get("url", "") if isinstance(data, dict) else ""
        transcript = data.get("transcript", "") if isinstance(data, dict) else ""
        word_limit = 200
        prompt = (
            f"Summarise this YouTube video in at most {word_limit} words.\n"
            f"Title: {title}\nTranscript: {transcript[:3000]}"
        )
        cache_key = hash_key(str(url or title), prompt)

        summary = get_str(summary_cache(), cache_key)
        if summary is None:
            summary = await multi_llm_prompt(prompt) or ""
            set_str(summary_cache(), cache_key, summary, input_key=prompt)

        return summary if summary else None


class TranscriptWhisperTech(BaseTechnology[str, str]):
    """Fallback technology using yt-dlp to download audio and Whisper to transcribe."""

    name: ClassVar[str] = "whisper_fallback"

    async def _execute(self, input_data: str) -> str | None:
        import asyncio
        import tempfile

        from social_research_probe.technologies.media_fetch.yt_dlp import download_audio
        from social_research_probe.technologies.transcript_fetch.whisper import transcribe_audio

        with tempfile.TemporaryDirectory(prefix="srp-ytdlp-") as tmpdir:
            audio_path = await asyncio.to_thread(download_audio, input_data, tmpdir)
            if audio_path is not None:
                return await asyncio.to_thread(transcribe_audio, audio_path)
