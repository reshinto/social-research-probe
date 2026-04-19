import json
import os
import subprocess
import sys


def test_run_research_skill_mode_emits_packet(tmp_path):
    env = {
        **os.environ,
        "SRP_DATA_DIR": str(tmp_path),
        "PYTHONPATH": "src",
        "SRP_TEST_USE_FAKE_YOUTUBE": "1",
    }
    subprocess.run(
        [
            sys.executable,
            "-m",
            "social_research_probe.cli",
            "update-purposes",
            "--add",
            '"trends"="Track emergence"',
        ],
        check=True,
        env=env,
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "social_research_probe.cli",
            "research",
            "--mode",
            "skill",
            "youtube",
            "ai agents",
            "trends",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["skill_mode"] is True
    assert payload["kind"] == "synthesis"
    pkt = payload["packet"]
    assert pkt["topic"] == "ai agents"
    assert pkt["platform"] == "youtube"
    assert pkt["purpose_set"] == ["trends"]
    assert "response_schema" in pkt
    assert pkt["html_report_path"].startswith("file://")
