"""HTTP TTS adapter — posts report text to a user-hosted TTS server.

Expects a server that accepts POST /synthesize with JSON body
  {"text": "...", "voice": "..."}
and returns raw MP3 bytes (Content-Type: audio/mpeg).

This is the universal escape hatch for custom-trained voices: the user
wraps their model in a small FastAPI/Flask server and points srp at it
via --tts-endpoint or the SRP_TTS_ENDPOINT env var.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path


def synthesize(text: str, endpoint: str, voice: str = "default") -> bytes:
    """Call the HTTP TTS endpoint and return raw MP3 bytes.

    Args:
        text: The narration text to synthesize.
        endpoint: Full URL of the TTS server (e.g. http://localhost:8080/synthesize).
        voice: Voice identifier forwarded to the server.

    Returns:
        MP3 audio bytes.

    Raises:
        RuntimeError: If the server responds with a non-200 status.
    """
    import json

    payload = json.dumps({"text": text, "voice": voice}).encode()
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "audio/mpeg"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"TTS server returned {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"TTS server unreachable: {exc.reason}") from exc


def write_audio(text: str, out_path: Path, endpoint: str, voice: str = "default") -> Path:
    """Synthesize *text* and write the resulting MP3 to *out_path*.

    Args:
        text: The narration text to synthesize.
        out_path: Destination path for the MP3 file.
        endpoint: Full URL of the TTS server.
        voice: Voice identifier forwarded to the server.

    Returns:
        The written path (same as out_path).
    """
    audio = synthesize(text, endpoint, voice)
    out_path.write_bytes(audio)
    return out_path
