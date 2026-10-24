# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Widgets of the «SipilBIM» side-tray tab: a collapsible section and the
generic Properties form.

``PropertiesForm`` knows nothing about columns. It shows the two General
properties every element has — **Element** and **Name** — and then builds one
row per ``Prop`` the element declares (``elements.py``). One form serves both
a selected element and the defaults of the next one placed, so there is no
separate «new» and «existing» form.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QFrame,
                               QLabel, QLineEdit, QSizePolicy, QToolButton,
                               QVBoxLayout, QWidget)

MUTED = "color: gray;"


class CollapsibleSection(QWidget):
    """A titled section that folds away, like the Image / Ambience sections
    of the render panel. Put content in ``body_layout``."""

    def __init__(self, title: str, expanded: bool = True) -> None:
        super().__init__()
        self.toggle = QToolButton()
        self.toggle.setText(title)
        self.toggle.setCheckable(True)
        self.toggle.setChecked(expanded)
        self.toggle.setAutoRaise(True)
        self.toggle.setFocusPolicy(Qt.NoFocus)
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toggle.setStyleSheet(
            "QToolButton { border: none; font-weight: bold; "
            "text-align: left; padding: 3px 2px; }")
        self.body = QFrame()
        self.body.setObjectName("sipilbim_section_body")
        self.body.setStyleSheet(
            "QFrame#sipilbim_section_body { border: 1px solid palette(mid); "
            "border-radius: 4px; }")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(8, 8, 8, 8)
        self.body_layout.setSpacing(6)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(self.toggle)
        lay.addWidget(self.body)
        self.toggle.toggled.connect(self.set_expanded)
        self.set_expanded(expanded)

    def set_expanded(self, on: bool) -> None:
        self.toggle.setArrowType(Qt.DownArrow if on else Qt.RightArrow)
        self.body.setVisible(bool(on))
        if self.toggle.isChecked() != bool(on):
            self.toggle.setChecked(bool(on))

    def is_expanded(self) -> bool:
        return self.toggle.isChecked()


class PropertiesForm(QWidget):
    """Element, Name, then the rows of the element's property schema."""

    def __init__(self, app) -> None:
        super().__init__()
        self._app = app
        self._element = None
        self._groups: list = []
        self._loading = False
        self._props: dict = {}          # key -> Prop
        self._fields: dict = {}         # key -> editing widget
        self._labels: dict = {}         # key -> row label
        #: Called after an edit has been applied, so the panel can show what
        #: really took effect (set by the panel).
        self.on_edited = None

        self.element_label = QLabel()
        self.name_edit = QLineEdit()
        self.name_edit.editingFinished.connect(self._renamed)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setStyleSheet(MUTED)

        self._form = QFormLayout()
        self._form.setContentsMargins(0, 0, 0, 0)
        self._form.addRow("Element", self.element_label)
        self._form.addRow("Name", self.name_edit)
        self._fixed_rows = self._form.rowCount()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(self._form)
        lay.addWidget(self.status)

    # ---- access for tests and the panel -------------------------------------
    def field(self, key: str):
        """The editing widget of property ``key``."""
        return self._fields[key]

    def is_row_shown(self, key: str) -> bool:
        return self._fields[key].isVisibleTo(self)

    # ---- building -----------------------------------------------------------
    def _build(self, element) -> None:
        while self._form.rowCount() > self._fixed_rows:
            self._form.removeRow(self._form.rowCount() - 1)
        self._props, self._fields, self._labels = {}, {}, {}
        for prop in element.properties():
            widget = self._make_field(prop)
            self._form.addRow(prop.label, widget)
            self._props[prop.key] = prop
            self._fields[prop.key] = widget
            self._labels[prop.key] = self._form.labelForField(widget)
        self._element = element

    def _make_field(self, prop):
        if prop.kind == "choice":
            box = QComboBox()
            for value, text in prop.choices:
                box.addItem(text, value)
            box.currentIndexChanged.connect(
                lambda _i, p=prop: self._changed(p))
            widget = box
        else:
            spin = QDoubleSpinBox()
            spin.setRange(prop.lo * prop.scale, prop.hi * prop.scale)
            spin.setDecimals(prop.decimals)
            spin.setSingleStep(prop.step)
            spin.setSuffix(prop.suffix)
            # A typed value applies on Enter / leaving the field; arrows at once.
            spin.setKeyboardTracking(False)
            spin.valueChanged.connect(lambda _v, p=prop: self._changed(p))
            widget = spin
        if prop.tip:
            widget.setToolTip(prop.tip)
        return widget

    # ---- values -------------------------------------------------------------
    def _read(self, prop):
        widget = self._fields[prop.key]
        if prop.kind == "choice":
            return widget.currentData()
        return widget.value() / prop.scale

    def _write(self, prop, value) -> None:
        widget = self._fields[prop.key]
        if prop.kind == "choice":
            index = widget.findData(value)
            widget.setCurrentIndex(max(index, 0))
        else:
            widget.setValue(float(value) * prop.scale)

    def _values(self) -> dict:
        return {k: self._read(p) for k, p in self._props.items()}

    def _sync_rows(self) -> None:
        values = self._values()
        for key, prop in self._props.items():
            show = prop.when is None or bool(prop.when(values))
            self._fields[key].setVisible(show)
            if self._labels[key] is not None:
                self._labels[key].setVisible(show)

    # ---- showing an element -------------------------------------------------
    def load(self, element, groups) -> None:
        """Show ``groups`` (the selected elements of this kind). With none, the
        same fields show the values the next element will be placed with."""
        self._loading = True
        try:
            if element is not self._element:
                self._build(element)
            self._groups = list(groups)
            n = len(self._groups)
            params = (element.params_of(self._groups[0]) if n
                      else element.default_params())
            for key, prop in self._props.items():
                self._write(prop, params[key])
            if n == 0:
                self.element_label.setText(element.label)
                self.name_edit.setEnabled(False)
                self.name_edit.setPlaceholderText("")
                self.name_edit.setText(element.next_name(self._app.scene))
                self.status.setText(
                    f"Nothing selected — these values apply to the next "
                    f"{element.label.lower()} you place.")
            elif n == 1:
                self.element_label.setText(element.label)
                self.name_edit.setEnabled(True)
                self.name_edit.setPlaceholderText("")
                self.name_edit.setText(element.name_of(self._groups[0]))
                self.status.setText("")
            else:
                self.element_label.setText(f"{element.label} ({n} selected)")
                self.name_edit.setEnabled(False)
                self.name_edit.setText("")
                self.name_edit.setPlaceholderText("Multiple")
                self.status.setText(
                    f"Changes apply to all {n} selected "
                    f"{element.plural.lower()}. Values shown are from the "
                    f"first one.")
        finally:
            self._loading = False
        self._sync_rows()

    # ---- editing ------------------------------------------------------------
    def _edited(self) -> None:
        if callable(self.on_edited):
            self.on_edited()

    def _changed(self, prop) -> None:
        if self._loading or self._element is None:
            return
        value = self._read(prop)
        self._sync_rows()
        if self._groups:
            self._element.modify(self._app.viewport, self._groups,
                                 {prop.key: value})
            self._edited()              # show what really took effect
        else:
            self._element.set_default(prop.key, value)

    def _renamed(self) -> None:
        if self._loading or self._element is None or len(self._groups) != 1:
            return
        name = self.name_edit.text().strip()
        if name:
            self._element.modify(self._app.viewport, self._groups, {},
                                 name=name)
        self._edited()
