import json
import subprocess
import sys
import textwrap

import pytest

from social_research_probe.llm.host import emit_packet


def test_emit_packet_writes_json_and_exits_zero(tmp_path):
    script = tmp_path / "emit.py"
    script.write_text(textwrap.dedent("""
        from social_research_probe.llm.host import emit_packet
        emit_packet({"topic":"ai"}, kind="synthesis")
    """))
    p = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert p.returncode == 0
    out = json.loads(p.stdout)
    assert out == {"skill_mode": True, "kind": "synthesis", "packet": {"topic":"ai"}}


def test_emit_packet_in_process(monkeypatch, capsys):
    """Cover emit_packet lines directly by catching SystemExit."""
    with pytest.raises(SystemExit) as exc:
        emit_packet({"topic": "ai"}, kind="synthesis")
    assert exc.value.code == 0
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out == {"skill_mode": True, "kind": "synthesis", "packet": {"topic": "ai"}}
