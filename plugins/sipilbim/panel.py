# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""The SipilBIM user interface.

* **Top** — the «Building Elements» / «Connections» palette in a toolbar of
  its own, in a row under the host's toolbars (``palette.py``). It can be
  dragged to any side; at a side it becomes a vertical card.
* **Right** — the «SipilBIM» tab of the side tray, closed until it is needed
  (right-click an element ▸ properties, or Window ▸ Panels): collapsible
  *Model* (empty for now) and *Properties* sections. Properties shows the selected element,
  or — with nothing selected and an element tool armed — the values the next
  element will be placed with, in the same form.

``Workbench`` ties the two together: it owns the elements, arms their tools
and keeps palette and form in step with the selection.
"""
from __future__ import annotations

import sys

from PySide6.QtCore import QObject, QSettings, Qt, QTimer
from PySide6.QtWidgets import (QLabel, QMessageBox, QToolBar, QVBoxLayout,
                               QWidget)

from . import connections as conns
from . import elements as els
from .common import TITLE, selected_groups
from .palette import HELP_TEXT, BuildingElementsBar
from .widgets import MUTED, CollapsibleSection, PropertiesForm


class SipilBimPanel(QWidget):
    """The right-hand tab: Model and Properties sections."""

    def __init__(self, app) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 8)
        lay.setSpacing(8)

        # Model — empty for now; the model tree will live here.
        self.model_section = CollapsibleSection("Model")
        self.model_note = QLabel("No model data yet.")
        self.model_note.setStyleSheet(MUTED)
        self.model_section.body_layout.addWidget(self.model_note)
        lay.addWidget(self.model_section)

        # Properties — one form for every element, new or existing.
        self.props_section = CollapsibleSection("Properties")
        self.hint = QLabel(
            "Select an element in the model, or choose one under Building "
            "Elements, to see its properties.")
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet(MUTED)
        self.form = PropertiesForm(app)
        self.props_section.body_layout.addWidget(self.hint)
        self.props_section.body_layout.addWidget(self.form)
        lay.addWidget(self.props_section)
        lay.addStretch(1)
        self.show_selection(None, [])

    def show_selection(self, element, groups) -> None:
        shown = element is not None
        self.hint.setVisible(not shown)
        self.form.setVisible(shown)
        if shown:
            self.form.load(element, groups)


class Workbench(QObject):
    """Owns the elements; keeps the palette and the Properties form in step
    with the active tool and the selection."""

    POLL_MS = 250

    def __init__(self, app) -> None:
        super().__init__(app.window)
        self._app = app
        self.elements = els.build_elements()
        self.connections = conns.build_connections()
        self._seen = None

        self.panel = SipilBimPanel(app)
        self.panel.form.on_edited = lambda: self.sync(force=True)
        self.palette = BuildingElementsBar(
            app.window, self.elements, self.connections, self._on_arm,
            self._on_placeholder, self._on_help)

        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_MS)
        self._timer.timeout.connect(self.sync)
        self._timer.start()
        self.sync(force=True)

    @property
    def buttons(self) -> dict:
        return self.palette.buttons

    # ---- palette clicks -------------------------------------------------------
    def _on_placeholder(self, el) -> None:
        self._app.viewport.flash_status(f"{el.label}: not available yet.", 4000)

    def _on_help(self) -> None:
        box = QMessageBox(self._app.window)
        box.setWindowTitle(f"{TITLE} — Help")
        box.setTextFormat(Qt.RichText)
        box.setText(HELP_TEXT)
        box.exec()

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

    # ---- following the selection ----------------------------------------------
    def sync(self, *_args, force: bool = False) -> None:
        """Update the buttons and the form when the selection, the active tool
        or the document changed."""
        if (not force and not self.palette.isVisible()
                and not self.panel.isVisible()):
            return
        vp = self._app.viewport
        active = vp.active_tool
        for el in self.elements:
            if el.implemented:
                self.palette.set_checked(el.key, active is el.tool())
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
        self.panel.show_selection(chosen, owned)


def _dock_palette(window, palette) -> QToolBar:
    """Put the palette toolbar in a new row at the top, under the host's
    toolbars. The user may drag it elsewhere; the buttons follow its
    orientation (``BuildingElementsBar.set_orientation``)."""
    window.addToolBarBreak(Qt.TopToolBarArea)
    window.addToolBar(Qt.TopToolBarArea, palette)
    try:                                    # the host's look for the «»» arrow
        from views.icons import style_overflow_button
        style_overflow_button(palette)
    except Exception:  # noqa: BLE001 — cosmetic only
        pass
    return palette


#: Remembers that the palette got its row once (the host does the same for
#: its Walkthrough toolbar: ``ui/placed/walkthrough``).
PLACED_KEY = "sipilbim/placed/palette_row"


def _own_row_once(window, bar) -> None:
    """First run only: give the palette a row of its own under the host's
    toolbars. ``restoreState`` lays out the saved window and puts a toolbar it
    does not know at the end of the last row, where the palette would be
    squeezed behind the «»» arrow. After this the user's arrangement is
    kept."""
    st = QSettings()
    if st.value(PLACED_KEY) is not None:
        return
    st.setValue(PLACED_KEY, 1)
    if window.toolBarArea(bar) != Qt.TopToolBarArea or window.toolBarBreak(bar):
        return
    window.removeToolBar(bar)
    window.addToolBarBreak(Qt.TopToolBarArea)
    window.addToolBar(Qt.TopToolBarArea, bar)
    bar.show()


def setup(app) -> None:
    """Palette in a toolbar at the top, «SipilBIM» tab on the right (closed
    at first), Extensions ▸ SipilBIM menu, right-click entries and the
    Browser's element descriptions."""
    wb = Workbench(app)
    # panel="sipilbim": a shared tab, should another extension join it.
    # start_hidden: the tab is closed the first time; right-click an element ▸
    # properties, Extensions ▸ SipilBIM or Window ▸ Panels opens it, and the
    # user's choice is kept from then on.
    dock = app.add_panel(TITLE, wb.panel, panel="sipilbim", start_hidden=True)
    wb.bar = _dock_palette(app.window, wb.palette)
    # After the host has restored the saved layout (it does that right after
    # the extensions' setup), not before.
    QTimer.singleShot(0, lambda: _own_row_once(app.window, wb.palette))

    def show_panel() -> None:
        app.show_panel(dock)
        wb.sync(force=True)

    sub = app.add_menu(TITLE)
    if sub is not None:
        for el in wb.elements:
            if el.implemented:
                sub.addAction(
                    f"Place {el.label.lower()}",
                    lambda e=el: app.viewport.set_active_tool(e.tool()))
        sub.addSeparator()
        sub.addAction(wb.bar.toggleViewAction())     # Building Elements
        sub.addAction(f"Show {TITLE} panel", show_panel)

    def context(menu, selection) -> None:
        selected = selected_groups(app.viewport.scene)
        for el in wb.elements:
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
    app.on_document_changed(wb.sync)

    def outliner_kind(group):
        for el in wb.elements:
            if el.implemented:
                info = el.outliner_kind(group)
                if info is not None:
                    return info
        return None

    add_kind = getattr(app, "add_outliner_kind", None)
    if add_kind is not None:
        add_kind(outliner_kind)

    # The original «concrete column» plugin (shipped with early builds)
    # clashes: two column tabs.
    if "ingetrazo_plugin_kolom_beton" in sys.modules:
        app.viewport.flash_status(
            f"{TITLE}: the old kolom_beton.py plugin was also loaded — "
            "remove it or rename it to kolom_beton.py.off so there is only "
            "one column tab.", 15000)
