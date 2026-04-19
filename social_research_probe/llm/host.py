from __future__ import annotations

import json
import sys
from typing import Literal

from social_research_probe.packet import wrap_packet

PacketKind = Literal["synthesis", "suggestions", "corroboration"]


def emit_packet(packet: dict, kind: PacketKind) -> None:
    json.dump(wrap_packet(packet, kind), sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()
