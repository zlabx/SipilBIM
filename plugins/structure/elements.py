# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Daftar elemen dan sambungan pada palet tab Structure.

Elemen yang sudah berfungsi (``implemented = True``) punya alat klik-lokasi
dan form properti. Sisanya hanya tombol: mengkliknya menampilkan «belum
tersedia» di status bar. Menambah elemen baru = satu kelas ``Element`` di
sini dan satu entri di ``ELEMENT_CLASSES``; panel tidak perlu diubah.

Sambungan didaftar sebagai data di ``connections.py``.
"""
from __future__ import annotations

from . import column as col


class Element:
    """Satu jenis elemen struktur pada palet."""

    key = ""                    # pengenal stabil
    label = ""                  # teks tombol
    tip = ""                    # tooltip
    icon_kind = ""              # nama ikon (icons.py)
    implemented = False

    def owns(self, group) -> bool:
        """Apakah ``group`` elemen jenis ini (untuk menampilkan propertinya)."""
        return False

    def tool(self):
        """Alat klik-lokasi (satu objek, dipakai ulang) atau ``None``."""
        return None

    def make_form(self, app):
        """Widget properti untuk bagian bawah tab, atau ``None``."""
        return None

    def context_label(self, n: int) -> str | None:
        """Teks entri klik kanan untuk ``n`` elemen terpilih (``None`` = tidak
        ada entri)."""
        return None

    def outliner_kind(self, group):
        return None


class ColumnElement(Element):
    key = "column"
    label = "Kolom"
    tip = "Kolom beton — klik tombol ini, lalu klik lokasi di viewport"
    icon_kind = "column"
    implemented = True

    def __init__(self) -> None:
        self.state = {"params": dict(col.DEFAULTS)}
        self._tool = None

    def owns(self, group) -> bool:
        return col.column_data(group) is not None

    def tool(self):
        if self._tool is None:
            self._tool = col.ColumnPlaceTool(self.state)
        return self._tool

    def make_form(self, app):
        from .column_form import ColumnForm
        return ColumnForm(app, self.state)

    def context_label(self, n: int) -> str | None:
        return "Properti kolom…" if n == 1 else f"Properti {n} kolom…"

    def outliner_kind(self, group):
        return col.outliner_kind(group)


class PlaceholderElement(Element):
    """Tombol tanpa fungsi (belum dikerjakan)."""

    implemented = False

    def __init__(self, key: str, label: str, icon_kind: str, tip: str) -> None:
        self.key, self.label, self.icon_kind, self.tip = (
            key, label, icon_kind, tip)


def build_elements() -> list:
    """Elemen pada palet, berurutan. Tambah elemen baru di sini."""
    return [
        ColumnElement(),
        PlaceholderElement("beam", "Balok", "beam",
                           "Balok — belum ada fungsinya"),
        PlaceholderElement("slab", "Pelat", "slab",
                           "Pelat lantai — belum ada fungsinya"),
        PlaceholderElement("wall", "Dinding", "wall",
                           "Dinding — belum ada fungsinya"),
        PlaceholderElement("footing", "Pondasi", "footing",
                           "Pondasi — belum ada fungsinya"),
    ]
