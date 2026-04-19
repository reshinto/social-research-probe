from __future__ import annotations

import json
import sys
from typing import Literal, NoReturn

PacketKind = Literal["synthesis", "suggestions", "corroboration"]

def emit_packet(packet: dict, kind: PacketKind) -> NoReturn:
    json.dump({"skill_mode": True, "kind": kind, "packet": packet},
              sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()
    sys.exit(0)
