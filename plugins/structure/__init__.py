# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Structure — elemen struktur (kolom, balok, pelat, sambungan…) untuk SipilBIM.

Ekstensi berbentuk paket: SipilBIM memanggil :func:`setup` saat jendela utama
dibuat. Antarmuka (``panel.py``) baru diimpor saat itu, sehingga modul
geometri (``column.py``) tetap murni Python.

Sekarang yang berfungsi: kolom beton. Balok, pelat, dinding, pondasi, dan
sambungan baru berupa tombol kosong.
"""
__version__ = "0.1"


def setup(app) -> None:
    from .panel import setup as _setup
    _setup(app)
