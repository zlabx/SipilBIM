# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Form properti kolom (bagian bawah tab Structure).

Kolom terpilih diubah langsung (satu langkah undo per perubahan). Tanpa
kolom terpilih, isiannya menjadi properti untuk kolom BERIKUTNYA yang
ditempatkan. Dimensi dalam milimeter."""
from __future__ import annotations

from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QLabel,
                               QLineEdit, QVBoxLayout, QWidget)

from . import column as col


class ColumnForm(QWidget):
    def __init__(self, app, state: dict) -> None:
        super().__init__()
        self._app = app
        self._state = state
        self._cols: list = []
        self._loading = False

        self.title = QLabel()
        self.title.setStyleSheet("font-weight: bold;")
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setStyleSheet("color: gray;")

        self.shape = QComboBox()
        self.shape.addItem("Persegi / persegi panjang", "rect")
        self.shape.addItem("Bulat", "round")
        self.width = self._mm(10, 5000)
        self.depth = self._mm(10, 5000)
        self.diameter = self._mm(10, 5000)
        self.height = self._mm(100, 100000)
        self.rotation = QDoubleSpinBox()
        self.rotation.setRange(0.0, 359.9)
        self.rotation.setDecimals(1)
        self.rotation.setSuffix(" °")
        self.rotation.setKeyboardTracking(False)
        self.mark = QLineEdit()

        self._form = QFormLayout()
        self._form.addRow("Penampang:", self.shape)
        self._form.addRow("Lebar (arah X):", self.width)
        self._form.addRow("Dalam (arah Y):", self.depth)
        self._form.addRow("Diameter:", self.diameter)
        self._form.addRow("Tinggi kolom:", self.height)
        self._form.addRow("Rotasi penampang:", self.rotation)
        self._form.addRow("Tanda / nama:", self.mark)

        self.shape.currentIndexChanged.connect(
            lambda _i: self._changed("shape"))
        for key in ("width", "depth", "diameter", "height", "rotation"):
            getattr(self, key).valueChanged.connect(
                lambda _v, k=key: self._changed(k))
        self.mark.editingFinished.connect(self._renamed)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.title)
        lay.addWidget(self.note)
        lay.addLayout(self._form)
        self.load([])

    @staticmethod
    def _mm(lo: float, hi: float) -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setRange(lo, hi)
        box.setDecimals(0)
        box.setSingleStep(50)
        box.setSuffix(" mm")
        # Ketikan baru berlaku saat Enter/pindah kolom; panah langsung.
        box.setKeyboardTracking(False)
        return box

    def load(self, cols) -> None:
        """Tampilkan ``cols`` (kolom terpilih); kosong = properti kolom baru."""
        self._cols = list(cols)
        self._loading = True
        try:
            try:
                if self._cols:
                    p = col.normalize_params(
                        col.column_data(self._cols[0])["params"])
                else:
                    p = col.normalize_params(self._state["params"])
            except col.ColumnError:
                p = col.normalize_params(None)
            if len(self._cols) == 1:
                self.title.setText(f"Properti — {self._cols[0].name}")
                self.note.setText("")
            elif self._cols:
                self.title.setText(f"Properti — {len(self._cols)} kolom")
                self.note.setText("Isian yang Anda ubah diterapkan ke semua "
                                  "kolom terpilih (nilai tampil dari kolom "
                                  "pertama).")
            else:
                self.title.setText("Properti kolom baru")
                self.note.setText("Tidak ada kolom dipilih: isian ini dipakai "
                                  "untuk kolom yang ditempatkan berikutnya.")
            self.shape.setCurrentIndex(0 if p["shape"] == "rect" else 1)
            self.width.setValue(round(p["width"] * 1000.0))
            self.depth.setValue(round(p["depth"] * 1000.0))
            self.diameter.setValue(round(p["diameter"] * 1000.0))
            self.height.setValue(round(p["height"] * 1000.0))
            self.rotation.setValue(p["rotation"])
            single = len(self._cols) == 1
            self.mark.setEnabled(single)
            self.mark.setText(self._cols[0].name if single else "")
            self.mark.setPlaceholderText(
                "" if single else "(otomatis K1, K2, …)")
        finally:
            self._loading = False
        self._sync_rows()

    def _sync_rows(self) -> None:
        rect = self.shape.currentData() == "rect"
        for widget, show in ((self.width, rect), (self.depth, rect),
                             (self.rotation, rect), (self.diameter, not rect)):
            widget.setVisible(show)
            label = self._form.labelForField(widget)
            if label is not None:
                label.setVisible(show)

    def _value(self, key: str):
        if key == "shape":
            return self.shape.currentData()
        if key == "rotation":
            return self.rotation.value()
        return getattr(self, key).value() / 1000.0

    def _reload(self) -> None:
        self.load(col.selected_columns(self._app.viewport.scene)
                  if self._cols else [])

    def _changed(self, key: str) -> None:
        if self._loading:
            return
        if key == "shape":
            self._sync_rows()
        value = self._value(key)
        if self._cols:
            col.modify_columns(self._app.viewport, self._cols, {key: value})
            self._reload()              # tampilkan yang sebenarnya berlaku
        else:
            self._state["params"] = dict(self._state["params"], **{key: value})

    def _renamed(self) -> None:
        if self._loading or len(self._cols) != 1:
            return
        name = self.mark.text().strip()
        if name:
            col.modify_columns(self._app.viewport, self._cols, {}, mark=name)
        self._reload()
