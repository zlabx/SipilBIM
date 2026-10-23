# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Daftar sambungan pada tab Structure.

Semuanya masih tombol kosong (belum ada fungsinya). Menambah sambungan baru
= satu baris di ``CONNECTIONS``: (kunci, teks tombol, ikon). Ikon yang tersedia
ada di ``icons._PAINTERS``; ikon yang tidak dikenal memakai ``plate``.
"""
from __future__ import annotations

from .elements import PlaceholderElement

CONNECTIONS = [
    ("base_plate", "Pelat dasar", "plate"),
    ("beam_column", "Balok–kolom", "plate"),
    ("beam_beam", "Balok–balok", "splice"),
    ("splice", "Splice", "splice"),
    ("bolted", "Baut", "bolt"),
    ("welded", "Las", "weld"),
    ("moment", "Momen", "moment"),
    ("bracing", "Bresing", "brace"),
]


def build_connections() -> list:
    return [PlaceholderElement(key, label, kind,
                               f"Sambungan {label.lower()} — belum ada "
                               "fungsinya")
            for key, label, kind in CONNECTIONS]
