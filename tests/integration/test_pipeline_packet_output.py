import os
import subprocess
import sys

from social_research_probe.cli.parsers import Arg
from social_research_probe.commands import Command


def test_run_pipeline_emits_packet_envelope(tmp_path):
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
            Command.UPDATE_PURPOSES,
            Arg.ADD,
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
            "youtube",
            "ai agents",
            "trends",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    assert out.startswith("srp serve-report --report ") or out.endswith(".md")
