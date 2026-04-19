import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

from social_research_probe.llm.host import emit_packet


def test_emit_packet_writes_json_and_exits_zero(tmp_path):
    script = tmp_path / "emit.py"
    script.write_text(
        textwrap.dedent("""
        from social_research_probe.llm.host import emit_packet
        emit_packet({"topic":"ai"}, kind="synthesis")
    """)
    )
    repo_root = Path(__file__).resolve().parents[2]
    env = {**os.environ, "PYTHONPATH": str(repo_root)}
    p = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, env=env)
    assert p.returncode == 0
    out = json.loads(p.stdout)
    assert out == {"kind": "synthesis", "packet": {"topic": "ai"}}


def test_emit_packet_in_process(monkeypatch, capsys):
    """emit_packet writes the unified envelope to stdout without exiting."""
    emit_packet({"topic": "ai"}, kind="synthesis")
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out == {"kind": "synthesis", "packet": {"topic": "ai"}}
