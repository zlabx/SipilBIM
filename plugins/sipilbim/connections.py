# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Connections listed in the «Connections» group of the palette.

All of them are still placeholders (no function yet). Adding a connection =
one row in ``CONNECTIONS``: (key, button text, icon). The available icons are
in ``icons._PAINTERS``; an unknown icon falls back to ``plate``.
"""
from __future__ import annotations

from .elements import PlaceholderElement

CONNECTIONS = [
    ("base_plate", "Base plate", "plate"),
    ("beam_column", "Beam–column", "plate"),
    ("beam_beam", "Beam–beam", "splice"),
    ("splice", "Splice", "splice"),
    ("bolted", "Bolted", "bolt"),
    ("welded", "Welded", "weld"),
    ("moment", "Moment", "moment"),
    ("bracing", "Bracing", "brace"),
]


def build_connections() -> list:
    return [PlaceholderElement(key, label, kind,
                               f"{label} connection — not available yet")
            for key, label, kind in CONNECTIONS]
