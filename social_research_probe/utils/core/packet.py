"""Helpers for the canonical emitted packet envelope."""

from __future__ import annotations

from typing import Literal, TypedDict

from social_research_probe.utils.core.types import PacketPayload

PacketKind = Literal["synthesis", "suggestions", "corroboration"]


class PacketEnvelope(TypedDict):
    """Top-level envelope emitted by CLI commands that return a packet."""

    kind: PacketKind
    packet: PacketPayload


def wrap_packet(packet: PacketPayload, kind: PacketKind) -> PacketEnvelope:
    """Return the canonical emitted envelope for *packet*."""
    return {"kind": kind, "packet": packet}


def unwrap_packet(payload: object) -> object:
    """Return the inner packet when *payload* is an emitted envelope."""
    if (
        isinstance(payload, dict)
        and isinstance(payload.get("kind"), str)
        and isinstance(payload.get("packet"), dict)
    ):
        return payload["packet"]
    return payload
