# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""The left-hand palette: «Building Elements» and «Connections».

A narrow vertical card of flat, icon-and-text buttons, docked in a left
toolbar of its own beside the host's drawing tools. It only reports clicks
(``on_arm``, ``on_placeholder``, ``on_help``); the logic is in ``panel.py``.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QFrame, QLabel, QPushButton, QSizePolicy,
                               QVBoxLayout)

from .icons import icon

CSS = """
QFrame#sipilbim_palette {
    border: 1px solid palette(mid); border-radius: 6px;
    background: palette(window);
}
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
    "• Select an element in the model to read and edit its properties in the "
    "<b>SipilBIM</b> tab of the right-hand sidebar.<br>"
    "• Greyed-out buttons are planned elements and connections that are not "
    "available yet.")


class BuildingElementsBar(QFrame):
    def __init__(self, elements, connections, on_arm, on_placeholder,
                 on_help) -> None:
        super().__init__()
        self.setObjectName("sipilbim_palette")
        self.setStyleSheet(CSS)
        self.buttons: dict = {}
        self._on_arm = on_arm
        self._on_placeholder = on_placeholder

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 6)
        lay.setSpacing(1)
        self._title(lay, "Building Elements")
        for el in elements:
            lay.addWidget(self._button(el))
        self._title(lay, "Connections")
        for el in connections:
            lay.addWidget(self._button(el))
        help_btn = self._item("Help", "help",
                              "How the SipilBIM palette works")
        help_btn.clicked.connect(lambda _c=False: on_help())
        lay.addSpacing(4)
        lay.addWidget(help_btn)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    @staticmethod
    def _title(lay, text: str) -> None:
        label = QLabel(text)
        label.setObjectName("sipilbim_title")
        lay.addWidget(label)

    @staticmethod
    def _item(text: str, icon_kind: str, tip: str) -> QPushButton:
        button = QPushButton(text)
        button.setFlat(True)
        button.setProperty("sbim", "item")
        button.setIcon(icon(icon_kind))
        button.setIconSize(QSize(22, 22))
        button.setToolTip(tip)
        button.setFocusPolicy(Qt.NoFocus)       # keep keyboard focus in the view
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button.setMinimumWidth(128)
        return button

    def _button(self, el) -> QPushButton:
        button = self._item(el.label, el.icon_kind, el.tip)
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

    def set_checked(self, key: str, on: bool) -> None:
        button = self.buttons.get(key)
        if button is not None and button.isChecked() != bool(on):
            button.setChecked(bool(on))
