# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""The palette: «Building Elements» and «Connections».

A toolbar of its own whose items are flat, icon-and-text buttons. It lies in a
row under the host's toolbars by default (horizontal: the elements keep their
text, the connections and Help show only an icon with a tooltip) and becomes a
column if the user drags it to a side. Every button is a separate toolbar
item, so on a narrow window Qt folds the ones that do not fit behind the «»»
arrow, like the host's own toolbars; ONE wide widget could not fold and would
force the window wider. The toolbar only reports clicks (``on_arm``,
``on_placeholder``, ``on_help``); the logic is in ``panel.py``.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy, QToolBar

from .icons import icon

CSS = """
QLabel#sipilbim_title { font-weight: bold; padding: 2px 6px; }
QPushButton[sbim="item"] {
    text-align: left; padding: 3px 6px; border: none; border-radius: 4px;
}
QPushButton[sbim="item"]:hover { background: palette(midlight); }
QPushButton[sbim="item"]:checked {
    background: palette(highlight); color: palette(highlighted-text);
}
QPushButton[sbim="item"][ready="false"] { color: gray; }
"""

HELP_TEXT = (
    "<b>SipilBIM — Building Elements</b><br><br>"
    "• Click an element (for example <b>Column</b>), then click a location "
    "in the viewport to place it. Click the button again, or pick another "
    "tool, to finish.<br>"
    "• To read and edit an element's properties, select it and right-click "
    "▸ <b>Column properties…</b> (or use Extensions ▸ SipilBIM ▸ Show "
    "SipilBIM panel). That opens the <b>SipilBIM</b> tab of the right-hand "
    "sidebar, which is hidden until you need it.<br>"
    "• Greyed-out buttons are planned elements and connections that are not "
    "available yet.<br>"
    "• The palette can be dragged to any side of the window.")


class BuildingElementsBar(QToolBar):
    def __init__(self, window, elements, connections, on_arm, on_placeholder,
                 on_help) -> None:
        super().__init__("Building Elements", window)
        # A new name on purpose: a layout saved by an earlier build, with the
        # palette at the left, must not carry it away from the top.
        self.setObjectName("sipilbim_palette_bar")
        self.setMovable(True)
        self.setFloatable(False)
        self.setAllowedAreas(Qt.AllToolBarAreas)
        self.setIconSize(QSize(22, 22))
        self.setStyleSheet(CSS)
        self.buttons: dict = {}
        self._on_arm = on_arm
        self._on_placeholder = on_placeholder
        self._label_of: dict = {}         # button -> its text when shown
        self._compact: set = set()        # buttons that drop the text in a row

        self.addWidget(self._title("Building Elements"))
        for el in elements:
            self.addWidget(self._button(el))
        self.addSeparator()
        self.addWidget(self._title("Connections"))
        for el in connections:
            self.addWidget(self._button(el, compact=True))
        self.addSeparator()
        help_btn = self._item("Help", "help",
                              "How the SipilBIM palette works", compact=True)
        help_btn.clicked.connect(lambda _c=False: on_help())
        self.addWidget(help_btn)
        self.help_button = help_btn

        self.orientationChanged.connect(self.set_orientation)
        self.set_orientation(self.orientation())

    # ---- construction -------------------------------------------------------
    @staticmethod
    def _title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sipilbim_title")
        return label

    def _item(self, text: str, icon_kind: str, tip: str,
              compact: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setFlat(True)
        button.setProperty("sbim", "item")
        button.setIcon(icon(icon_kind))
        button.setIconSize(QSize(22, 22))
        button.setToolTip(tip)
        button.setAccessibleName(text)
        button.setFocusPolicy(Qt.NoFocus)       # keep keyboard focus in the view
        self._label_of[button] = text
        if compact:
            self._compact.add(button)
        return button

    def _button(self, el, compact: bool = False) -> QPushButton:
        button = self._item(el.label, el.icon_kind, el.tip, compact)
        button.setProperty("ready", "true" if el.implemented else "false")
        if el.implemented:
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked, e=el: self._on_arm(e, checked))
        else:
            button.clicked.connect(
                lambda _c=False, e=el: self._on_placeholder(e))
        self.buttons[el.key] = button
        return button

    # ---- orientation --------------------------------------------------------
    def set_orientation(self, orientation) -> None:
        """Row (``Qt.Horizontal``): the elements keep their text, the
        connections and Help show an icon only. Column: every button shows
        its text and the buttons share one width."""
        horizontal = orientation == Qt.Horizontal
        for button, label in self._label_of.items():
            show_text = not (horizontal and button in self._compact)
            button.setText(label if show_text else "")
            button.setMinimumWidth(0 if horizontal else 128)
            button.setSizePolicy(
                QSizePolicy.Fixed if horizontal else QSizePolicy.Expanding,
                QSizePolicy.Fixed)
        self._horizontal = horizontal

    @property
    def is_horizontal(self) -> bool:
        return self.orientation() == Qt.Horizontal

    def set_checked(self, key: str, on: bool) -> None:
        button = self.buttons.get(key)
        if button is not None and button.isChecked() != bool(on):
            button.setChecked(bool(on))
