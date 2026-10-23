# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Tab «Structure» di sidebar kanan.

Atas: palet «Elemen» dan «Sambungan» (tombol berikon). Bawah: properti
elemen yang sedang dipilih, atau elemen yang alatnya sedang aktif."""
from __future__ import annotations

import sys

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (QGridLayout, QLabel, QToolButton, QVBoxLayout,
                               QWidget)

from . import connections as conns
from . import elements as els
from .common import selected_groups
from .icons import icon

COLUMNS = 4


def _heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("font-weight: bold;")
    return label


class StructurePanel(QWidget):
    POLL_MS = 250

    def __init__(self, app, elements=None, connections=None) -> None:
        super().__init__()
        self._app = app
        self.elements = elements if elements is not None else els.build_elements()
        self.connections = (connections if connections is not None
                            else conns.build_connections())
        self.buttons: dict = {}
        self.forms: dict = {}
        self._seen = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 8)
        lay.addWidget(_heading("Elemen"))
        lay.addLayout(self._grid(self.elements))
        lay.addWidget(_heading("Sambungan"))
        lay.addLayout(self._grid(self.connections))
        self.note = QLabel("Tombol abu-abu sudah ada tempatnya, fungsinya "
                           "menyusul.")
        self.note.setWordWrap(True)
        self.note.setStyleSheet("color: gray;")
        lay.addWidget(self.note)
        lay.addStretch(1)

        # ---- Properti di dasar tab -------------------------------------------
        self.hint = QLabel("Klik elemen di atas, atau pilih elemen di model, "
                           "untuk melihat propertinya.")
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: gray;")
        lay.addWidget(self.hint)
        for el in self.elements:
            form = el.make_form(app) if el.implemented else None
            if form is not None:
                form.setVisible(False)
                self.forms[el.key] = form
                lay.addWidget(form)

        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_MS)
        self._timer.timeout.connect(self.sync)
        self.sync(force=True)

    # ---- Palet -----------------------------------------------------------------
    def _grid(self, items) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(4)
        for i, el in enumerate(items):
            button = QToolButton()
            button.setText(el.label)
            button.setIcon(icon(el.icon_kind))
            button.setIconSize(QSize(32, 32))
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.setToolTip(el.tip)
            button.setMinimumWidth(66)
            button.setAutoRaise(True)
            if el.implemented:
                button.setCheckable(True)
                button.clicked.connect(
                    lambda checked, e=el: self._on_arm(e, checked))
            else:
                button.setStyleSheet("color: gray;")
                button.clicked.connect(
                    lambda _c=False, e=el: self._on_placeholder(e))
            self.buttons[el.key] = button
            grid.addWidget(button, i // COLUMNS, i % COLUMNS)
        return grid

    def _on_placeholder(self, el) -> None:
        self._app.viewport.flash_status(
            f"{el.label}: belum tersedia (tombol ini belum ada fungsinya).",
            4000)

    def _on_arm(self, el, checked: bool) -> None:
        vp = self._app.viewport
        if checked:
            vp.set_active_tool(el.tool())
            self.sync(force=True)
            return
        activate = getattr(vp.window(), "_activate_tool", None)
        if callable(activate):
            activate("select")
        else:
            vp.set_active_tool(None)
        self.sync(force=True)

    # ---- Mengikuti pilihan ----------------------------------------------------
    def showEvent(self, ev) -> None:            # noqa: N802 (Qt)
        super().showEvent(ev)
        self._timer.start()
        self.sync(force=True)

    def hideEvent(self, ev) -> None:            # noqa: N802 (Qt)
        self._timer.stop()
        super().hideEvent(ev)

    def sync(self, *_args, force: bool = False) -> None:
        """Perbarui tombol dan properti bila pilihan atau dokumen berubah."""
        vp = self._app.viewport
        active = vp.active_tool
        for el in self.elements:
            if el.implemented:
                self.buttons[el.key].setChecked(active is el.tool())
        chosen, owned = None, []
        selected = selected_groups(vp.scene)
        for el in self.elements:
            if el.implemented:
                owned = [g for g in selected if el.owns(g)]
                if owned:
                    chosen = el
                    break
        if chosen is None:
            owned = []
            for el in self.elements:
                if el.implemented and active is el.tool():
                    chosen = el
        key = (chosen.key if chosen else None,
               tuple(id(g) for g in owned), vp.scene.version)
        if not force and key == self._seen:
            return
        self._seen = key
        for k, form in self.forms.items():
            form.setVisible(chosen is not None and chosen.key == k)
        self.hint.setVisible(chosen is None or chosen.key not in self.forms)
        if chosen is not None and chosen.key in self.forms:
            self.forms[chosen.key].load(owned)


def setup(app) -> None:
    """Tab «Structure», menu Extensions ▸ Structure, entri klik kanan, dan
    keterangan di Browser."""
    panel = StructurePanel(app)
    # panel="structure": tab bersama, bila ekstensi lain ingin ikut di sini.
    dock = app.add_panel("Structure", panel, panel="structure")

    def show_panel() -> None:
        app.show_panel(dock)
        panel.sync(force=True)

    sub = app.add_menu("Structure")
    if sub is not None:
        for el in panel.elements:
            if el.implemented:
                sub.addAction(
                    f"Tempatkan {el.label.lower()}",
                    lambda e=el: app.viewport.set_active_tool(e.tool()))
        sub.addAction("Tampilkan panel Structure", show_panel)

    def context(menu, selection) -> None:
        selected = selected_groups(app.viewport.scene)
        for el in panel.elements:
            if not el.implemented:
                continue
            owned = [g for g in selected if el.owns(g)]
            label = el.context_label(len(owned)) if owned else None
            if label:
                menu.addSeparator()
                action = menu.addAction(label)
                action.triggered.connect(
                    lambda _c=False: QTimer.singleShot(0, show_panel))

    app.add_context_menu(context)
    app.on_document_changed(panel.sync)

    def outliner_kind(group):
        for el in panel.elements:
            if el.implemented:
                info = el.outliner_kind(group)
                if info is not None:
                    return info
        return None

    add_kind = getattr(app, "add_outliner_kind", None)
    if add_kind is not None:
        add_kind(outliner_kind)

    # Plugin Kolom beton lama (bawaan exe versi awal) bentrok: dua tab kolom.
    if "ingetrazo_plugin_kolom_beton" in sys.modules:
        app.viewport.flash_status(
            "Structure: plugin kolom_beton.py lama ikut dimuat — hapus atau "
            "ganti namanya (kolom_beton.py.off) agar tidak ada dua tab "
            "kolom.", 15000)
