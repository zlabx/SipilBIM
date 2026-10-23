# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Ikon tombol palet, digambar dengan QPainter (tanpa berkas gambar)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF

INK = QColor(70, 70, 70)
LIGHT = QColor(176, 176, 170)
DARK = QColor(128, 128, 122)
ACCENT = QColor(242, 115, 41)


def _poly(*pts) -> QPolygonF:
    return QPolygonF([QPointF(x, y) for x, y in pts])


def _column(p) -> None:
    p.setBrush(LIGHT)
    p.drawRect(14, 8, 20, 32)
    p.setBrush(DARK)
    p.drawRect(8, 3, 32, 6)
    p.drawRect(8, 39, 32, 6)


def _beam(p) -> None:                       # penampang I
    p.setBrush(LIGHT)
    p.drawRect(21, 14, 6, 20)
    p.setBrush(DARK)
    p.drawRect(8, 8, 32, 7)
    p.drawRect(8, 33, 32, 7)


def _slab(p) -> None:
    p.setBrush(LIGHT)
    p.drawPolygon(_poly((4, 24), (26, 12), (44, 20), (22, 32)))
    p.setBrush(DARK)
    p.drawPolygon(_poly((4, 24), (22, 32), (22, 38), (4, 30)))
    p.drawPolygon(_poly((22, 32), (44, 20), (44, 26), (22, 38)))


def _wall(p) -> None:
    p.setBrush(LIGHT)
    p.drawRect(6, 8, 36, 32)
    for y in (18, 29):
        p.drawLine(6, y, 42, y)
    p.drawLine(20, 8, 20, 18)
    p.drawLine(32, 18, 32, 29)
    p.drawLine(16, 29, 16, 40)


def _footing(p) -> None:
    p.setBrush(LIGHT)
    p.drawRect(18, 6, 12, 20)
    p.setBrush(DARK)
    p.drawRect(5, 26, 38, 12)


def _plate(p) -> None:
    p.setBrush(LIGHT)
    p.drawRect(8, 10, 32, 28)
    p.setBrush(ACCENT)
    for x, y in ((14, 16), (34, 16), (14, 32), (34, 32)):
        p.drawEllipse(QPointF(x, y), 3, 3)


def _bolt(p) -> None:
    p.setBrush(LIGHT)
    p.drawPolygon(_poly((24, 6), (38, 14), (38, 32), (24, 40), (10, 32),
                        (10, 14)))
    p.setBrush(ACCENT)
    p.drawEllipse(QPointF(24, 23), 5, 5)


def _weld(p) -> None:
    p.setBrush(LIGHT)
    p.drawRect(6, 8, 15, 32)
    p.drawRect(27, 8, 15, 32)
    p.setPen(QPen(ACCENT, 3))
    p.drawPolyline(_poly((24, 10), (28, 16), (22, 22), (28, 28), (22, 34),
                         (26, 40)))


def _splice(p) -> None:
    p.setBrush(DARK)
    p.drawRect(3, 18, 18, 12)
    p.drawRect(27, 18, 18, 12)
    p.setBrush(LIGHT)
    p.drawRect(15, 12, 18, 24)
    p.setBrush(ACCENT)
    for x, y in ((19, 17), (29, 17), (19, 31), (29, 31)):
        p.drawEllipse(QPointF(x, y), 2, 2)


def _moment(p) -> None:
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(ACCENT, 4))
    p.drawArc(10, 10, 28, 28, 40 * 16, 270 * 16)
    p.setPen(QPen(INK, 2))
    p.setBrush(INK)
    p.drawPolygon(_poly((36, 8), (40, 20), (28, 16)))


def _brace(p) -> None:
    p.setBrush(Qt.NoBrush)
    p.drawRect(8, 8, 32, 32)
    p.setPen(QPen(ACCENT, 3))
    p.drawLine(8, 40, 40, 8)


_PAINTERS = {
    "column": _column, "beam": _beam, "slab": _slab, "wall": _wall,
    "footing": _footing, "plate": _plate, "bolt": _bolt, "weld": _weld,
    "splice": _splice, "moment": _moment, "brace": _brace,
}


def icon(kind: str) -> QIcon:
    """Ikon 48×48 untuk ``kind`` (``plate`` bila tidak dikenal)."""
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(INK, 2.2))
    _PAINTERS.get(kind, _plate)(p)
    p.end()
    return QIcon(pm)
