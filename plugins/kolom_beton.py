# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Kolom beton — kolom parametrik sederhana sebagai ekstensi SipilBIM.

Alur kerja (gaya Tekla, versi paling sederhana):

1. Buka tab **Steel** di sidebar kanan dan klik **Kolom** (atau tombol «Kolom»
   di toolbar «Struktur», atau menu Extensions ▸ Kolom beton).
2. Klik lokasi kolom di viewport (snap ke titik/garis bantu seperti biasa).
   Alat tetap aktif, jadi bisa menempatkan banyak kolom berturut-turut.
3. Properti ada di bagian paling bawah tab Steel: kolom yang dipilih diubah
   langsung (penampang persegi/bulat, dimensi, tinggi, rotasi, tanda K1, K2…);
   tanpa kolom terpilih, isiannya dipakai untuk kolom berikutnya. Klik kanan
   sebuah kolom ▸ **Properti kolom…** membuka tab Steel.

Desain data — sama dengan pola Windowizer (examples/extensions/windowizer.py):

* Satu kolom = satu container group. Parameternya tersimpan di
  ``group.ext["kolom_beton"]`` (ikut tersimpan di .sbim dan ikut tersalin).
* Mesh-nya dibangun dari parameter di koordinat lokal (dasar kolom di z = 0,
  naik ke +Z). Posisi ada di matriks group, jadi Move/Rotate tidak perlu
  membangun ulang apa pun, dan mengubah properti tidak menggeser kolom.
* ``group.ifc = {"class": "IfcColumn", ...}`` — kolom otomatis ikut ekspor IFC
  dan takeoff (volume beton dari mesh yang tertutup rapat).

Catatan: mengubah properti membangun ulang mesh kolom. Hasil edit manual di
dalam group kolom (push/pull dsb.) akan tertimpa.

Belum ada: tulangan, balok, profil baja — lihat ROADMAP.
"""
from __future__ import annotations

import copy
import math
import re

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (QColor, QIcon, QMatrix4x4, QPainter, QPen, QPixmap,
                           QVector3D)
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from core.history import Command
from tools.base import Tool

KEY = "kolom_beton"
IFC_CLASS = "IfcColumn"
MATERIAL = "Beton"
CONCRETE_COLOR = (0.74, 0.74, 0.72)
ROUND_SEGMENTS = 32
MARK_PREFIX = "K"

#: Satuan di dalam model = meter. Dialog memakai milimeter (kebiasaan sipil).
DEFAULTS = {
    "shape": "rect",        # "rect" | "round"
    "width": 0.30,          # sisi sepanjang sumbu X lokal (rect)
    "depth": 0.30,          # sisi sepanjang sumbu Y lokal (rect)
    "diameter": 0.40,       # (round)
    "height": 3.00,
    "rotation": 0.0,        # derajat, putaran penampang terhadap sumbu Z
}


class ColumnError(Exception):
    """Parameter kolom tidak valid (pesan sudah berupa kalimat untuk pengguna)."""


# ---------------------------------------------------------------------------
# Parameter
# ---------------------------------------------------------------------------

def _num(p: dict, key: str, lo: float, hi: float, label: str) -> float:
    try:
        v = float(p[key])
    except (KeyError, TypeError, ValueError):
        raise ColumnError(f"{label}: nilai tidak valid.") from None
    if not math.isfinite(v) or v < lo or v > hi:
        raise ColumnError(
            f"{label}: harus antara {lo * 1000:g} dan {hi * 1000:g} mm.")
    return v


def normalize_params(params: dict | None) -> dict:
    """Parameter lengkap dan tervalidasi (default untuk yang kosong)."""
    p = dict(DEFAULTS)
    if params:
        p.update({k: params[k] for k in DEFAULTS if k in params})
    if p["shape"] not in ("rect", "round"):
        raise ColumnError("Bentuk penampang harus persegi atau bulat.")
    p["width"] = _num(p, "width", 0.01, 5.0, "Lebar")
    p["depth"] = _num(p, "depth", 0.01, 5.0, "Dalam")
    p["diameter"] = _num(p, "diameter", 0.01, 5.0, "Diameter")
    p["height"] = _num(p, "height", 0.1, 100.0, "Tinggi kolom")
    try:
        rot = float(p["rotation"])
    except (TypeError, ValueError):
        raise ColumnError("Rotasi: nilai tidak valid.") from None
    if not math.isfinite(rot):
        raise ColumnError("Rotasi: nilai tidak valid.")
    p["rotation"] = rot % 360.0
    return p


def column_data(group):
    """Data kolom pada ``group.ext`` atau ``None`` bila bukan kolom kita."""
    ext = getattr(group, "ext", None)
    if not ext:
        return None
    data = ext.get(KEY)
    return data if isinstance(data, dict) and "params" in data else None


def next_mark(scene) -> str:
    """Tanda kolom berikutnya: K{maks+1} dari kolom yang sudah ada."""
    pat = re.compile(rf"^{MARK_PREFIX}(\d+)$")
    top = 0
    for g in scene.groups:
        if column_data(g) is None:
            continue
        m = pat.match(g.name or "")
        if m:
            top = max(top, int(m.group(1)))
    return f"{MARK_PREFIX}{top + 1}"


# ---------------------------------------------------------------------------
# Geometri (koordinat lokal: dasar di z = 0, naik ke +Z)
# ---------------------------------------------------------------------------

def profile_points(p: dict) -> list:
    """Penampang sebagai poligon 2D berlawanan jarum jam (meter), sudah
    diputar sebesar ``rotation``."""
    if p["shape"] == "round":
        r = p["diameter"] / 2.0
        pts = [(r * math.cos(2.0 * math.pi * i / ROUND_SEGMENTS),
                r * math.sin(2.0 * math.pi * i / ROUND_SEGMENTS))
               for i in range(ROUND_SEGMENTS)]
    else:
        w, d = p["width"] / 2.0, p["depth"] / 2.0
        pts = [(-w, -d), (w, -d), (w, d), (-w, d)]
    rot = math.radians(p["rotation"])
    c, s = math.cos(rot), math.sin(rot)
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def _newell_z(loop) -> float:
    return sum((loop[i][0] * loop[(i + 1) % len(loop)][1]
                - loop[(i + 1) % len(loop)][0] * loop[i][1])
               for i in range(len(loop)))


def build_mesh(p: dict, attrs: dict | None = None):
    """Mesh tertutup (watertight) hasil ekstrusi penampang setinggi
    ``height``; semua normal menghadap keluar."""
    from core.mesh import Mesh
    pts = profile_points(p)
    if _newell_z(pts) < 0:          # jaga urutan CCW
        pts = list(reversed(pts))
    n, h = len(pts), p["height"]
    mesh = Mesh()

    def add(loop3):
        face = mesh.add_face([QVector3D(*q) for q in loop3])
        if attrs:
            face.attrs.update(copy.deepcopy(attrs))
        return face

    add([(x, y, 0.0) for x, y in reversed(pts)])        # dasar, normal -Z
    add([(x, y, h) for x, y in pts])                    # atas,  normal +Z
    for i in range(n):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
        add([(ax, ay, 0.0), (bx, by, 0.0), (bx, by, h), (ax, ay, h)])
    if p["shape"] == "round":
        # Rusuk tegak dilembutkan agar silinder tampak mulus (seperti
        # silinder hasil push/pull); lingkar atas/bawah tetap terlihat.
        for x, y in pts:
            a = mesh.vertex_at(QVector3D(x, y, 0.0))
            b = mesh.vertex_at(QVector3D(x, y, h))
            edge = mesh.find_edge(a, b) if a is not None and b is not None \
                else None
            if edge is not None:
                edge.soft = True
    return mesh


def ensure_material(scene) -> dict:
    """Material «Beton» di registri dokumen; mengembalikan atribut face."""
    from core.materials import Material
    mat = scene.materials.get(MATERIAL)
    if mat is None:
        mat = Material(MATERIAL, color=CONCRETE_COLOR)
        scene.materials[MATERIAL] = mat
    return mat.face_attrs()


def _make_child(scene, p: dict, pose: QMatrix4x4):
    from core.group import Group
    child = Group(build_mesh(p, ensure_material(scene)), name="Beton")
    child.xform = QMatrix4x4(pose)
    child.component = False
    return child


def _pose_of(group) -> QMatrix4x4:
    """Letak mesh kolom di dalam container (translasi titik klik)."""
    for k in getattr(group, "children", None) or ():
        if k.xform is not None:
            return QMatrix4x4(k.xform)
    return QMatrix4x4()


def make_column(scene, point: QVector3D, params: dict, mark: str):
    """Buat kolom dengan dasar di ``point``. Mengembalikan container-nya."""
    from core.group import Group
    p = normalize_params(params)
    pose = QMatrix4x4()
    pose.translate(QVector3D(point))
    g = Group(name=mark)
    g.adopt([_make_child(scene, p, pose)])
    g.component = False
    g.ifc = {"class": IFC_CLASS, "name": mark}
    g.ext = {KEY: {"params": p}}
    scene.groups.append(g)
    scene.selection.clear()
    scene.selection.add(g)
    return g


def rebuild_column(scene, group, params: dict, mark: str | None = None) -> None:
    """Parameter baru, tempat sama: mesh dibangun ulang di posisi sekarang
    (Move/Rotate pada kolom tetap dipertahankan)."""
    if column_data(group) is None:
        raise ColumnError(f"«{group.name}» bukan kolom beton.")
    p = normalize_params(params)
    group.children = [_make_child(scene, p, _pose_of(group))]
    ext = dict(group.ext or {})
    ext[KEY] = dict(ext[KEY], params=p)
    group.ext = ext
    if mark:
        group.name = mark
    ifc = dict(group.ifc or {"class": IFC_CLASS})   # tag dari panel BIM dijaga
    ifc["name"] = group.name
    group.ifc = ifc


def column_volume(p: dict) -> float:
    """Volume beton teoretis (m³) — pembanding untuk takeoff."""
    if p["shape"] == "round":
        r = p["diameter"] / 2.0
        n = ROUND_SEGMENTS
        area = 0.5 * n * r * r * math.sin(2.0 * math.pi / n)
    else:
        area = p["width"] * p["depth"]
    return area * p["height"]


# ---------------------------------------------------------------------------
# Undo
# ---------------------------------------------------------------------------

class ColumnCommand(Command):
    """Satu langkah undo: daftar group, isi/tag/parameter tiap group, dan
    registri material."""

    def __init__(self, mutate) -> None:
        self.mutate = mutate
        self.before = self.after = None

    @staticmethod
    def _capture(scene) -> dict:
        return {
            "groups": list(scene.groups),
            "state": [(g, list(g.children or ()), g.ifc and dict(g.ifc),
                       copy.deepcopy(getattr(g, "ext", None)), g.name,
                       g.xform and QMatrix4x4(g.xform))
                      for g in scene.groups],
            "mats": dict(scene.materials),
        }

    @staticmethod
    def _restore(scene, s) -> None:
        scene.groups[:] = s["groups"]
        for g, kids, ifc, ext, name, xform in s["state"]:
            g.children, g.ifc, g.name = list(kids), ifc and dict(ifc), name
            g.ext = copy.deepcopy(ext)
            g.xform = xform and QMatrix4x4(xform)
        scene.materials.clear()
        scene.materials.update(s["mats"])
        scene.selection.intersection_update(
            set(scene.mesh.faces) | set(scene.mesh.edges) | set(scene.groups))

    def do(self, scene) -> None:
        if self.after is None:
            self.before = self._capture(scene)
            try:
                self.mutate(scene)
            except BaseException:
                self._restore(scene, self.before)
                raise
            self.after = self._capture(scene)
        else:
            self._restore(scene, self.after)
        scene.version += 1

    def undo(self, scene) -> None:
        self._restore(scene, self.before)
        scene.version += 1


# ---------------------------------------------------------------------------
# Perintah (dipanggil dari tombol, klik, dan menu klik kanan)
# ---------------------------------------------------------------------------

def _warn(viewport, text: str) -> None:
    try:
        viewport.flash_status("Kolom beton: " + text.splitlines()[0], 6000)
    except Exception:  # noqa: BLE001
        pass
    QMessageBox.warning(viewport.window(), "Kolom beton", text)


def _run(viewport, mutate, ok_message: str) -> bool:
    hist = viewport.history
    hist.execute(ColumnCommand(mutate))
    if hist.last_error:
        _warn(viewport, hist.last_error.split(": ", 1)[-1])
        return False
    notify = getattr(viewport, "notify_scene_changed", None)
    if callable(notify):
        notify()
    viewport.update()
    viewport.flash_status(ok_message, 4000)
    return True


def _at_top_level(viewport) -> bool:
    if getattr(viewport.scene, "edit_group", None) is not None:
        _warn(viewport, "Tutup group yang sedang diedit, lalu ulangi.")
        return False
    return True


def selected_columns(scene) -> list:
    out = []
    for e in scene.selection:
        g = getattr(e, "owner", None) or e
        if g in scene.groups and column_data(g) is not None and g not in out:
            out.append(g)
    return out


def place_column(viewport, point: QVector3D, state: dict) -> bool:
    """Satu klik = satu kolom dengan properti terakhir yang dipakai."""
    if not _at_top_level(viewport):
        return False
    scene = viewport.scene
    params = dict(state["params"])
    mark = next_mark(scene)
    return _run(viewport, lambda sc: make_column(sc, point, params, mark),
                f"Kolom {mark} ditempatkan — klik lagi untuk kolom berikutnya.")


def modify_columns(viewport, cols: list, changes: dict,
                   mark: str | None = None) -> bool:
    """Ubah ``changes`` (nama parameter → nilai) pada semua ``cols`` dalam
    SATU langkah undo. Tanpa perubahan nyata: tidak ada langkah undo."""
    if not cols:
        return False
    if not _at_top_level(viewport):
        return False
    try:
        plan = []
        for g in cols:
            now = normalize_params(column_data(g)["params"])
            new = normalize_params(dict(now, **changes))
            renamed = mark is not None and mark != g.name
            if new != now or renamed:
                plan.append((g, new))
    except ColumnError as exc:
        _warn(viewport, str(exc))
        return False
    if not plan:
        return False

    def mutate(sc):
        for g, new in plan:
            rebuild_column(sc, g, new, mark)
    names = ", ".join(g.name for g, _ in plan[:4]) + (
        "…" if len(plan) > 4 else "")
    return _run(viewport, mutate, f"Kolom diperbarui: {names}.")



# ---------------------------------------------------------------------------
# Alat: klik lokasi
# ---------------------------------------------------------------------------

class ColumnPlaceTool(Tool):
    """Klik lokasi → kolom jadi. Tetap aktif sampai alat lain dipilih.

    Butuh argumen konstruktor, sehingga pemuat plugin tidak membuat entri
    menu otomatis untuknya; entrinya dibuat di ``setup``."""

    name = "Kolom beton"
    description = "Tempatkan kolom beton dengan satu klik."
    uses_snap = True
    wireframe_color = (0.95, 0.45, 0.16, 1.0)

    def __init__(self, state: dict) -> None:
        self.state = state
        self._hover: QVector3D | None = None

    def on_activate(self, viewport) -> None:
        self._hover = None
        viewport.flash_status(
            "Kolom: klik lokasi kolom (klik kanan kolom ▸ Properti kolom…). "
            "Pilih alat lain untuk selesai.", 8000)

    def on_deactivate(self, viewport) -> None:
        self._hover = None

    def on_hover(self, ctx) -> None:
        self._hover = QVector3D(ctx.world)
        ctx.viewport.update()

    def on_click(self, ctx) -> None:
        place_column(ctx.viewport, QVector3D(ctx.world), self.state)

    def on_cancel(self, viewport) -> None:
        self._hover = None
        viewport.update()

    def rubber_band_lines(self):
        """Bayangan kolom (rangka kawat) di bawah kursor."""
        if self._hover is None:
            return []
        try:
            p = normalize_params(self.state["params"])
        except ColumnError:
            return []
        pts = profile_points(p)
        o, h = self._hover, p["height"]
        base = [QVector3D(o.x() + x, o.y() + y, o.z()) for x, y in pts]
        top = [QVector3D(q.x(), q.y(), q.z() + h) for q in base]
        n = len(pts)
        lines = []
        for i in range(n):
            lines.append((base[i], base[(i + 1) % n]))
            lines.append((top[i], top[(i + 1) % n]))
        step = max(1, n // 8)
        lines += [(base[i], top[i]) for i in range(0, n, step)]
        return lines


# ---------------------------------------------------------------------------
# Panel «Steel» (tab di sidebar kanan)
# ---------------------------------------------------------------------------

class ColumnPanel(QWidget):
    """Isi tab «Steel».

    Atas: palet elemen (sekarang tombol «Kolom»; balok dan sambungan menyusul).
    Bawah: properti elemen yang sedang dipilih — kolom terpilih diubah
    langsung (satu langkah undo per perubahan); bila tidak ada kolom yang
    dipilih, isiannya menjadi properti untuk kolom BERIKUTNYA yang ditempatkan.
    Dimensi dalam milimeter."""

    POLL_MS = 250

    def __init__(self, app, state: dict, tool) -> None:
        super().__init__()
        self._app = app
        self._state = state
        self._tool = tool
        self._cols: list = []
        self._seen = None
        self._loading = False

        # ---- Palet ---------------------------------------------------------
        self.btn_column = QPushButton("  Kolom")
        self.btn_column.setCheckable(True)
        self.btn_column.setIcon(_toolbar_icon())
        self.btn_column.setToolTip(
            "Kolom beton — klik tombol ini, lalu klik lokasi di viewport")
        self.btn_column.clicked.connect(self._on_arm)

        # ---- Properti ------------------------------------------------------
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

        # ---- Tata letak: palet di atas, properti di dasar tab ---------------
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 8)
        head = QLabel("Elemen")
        head.setStyleSheet("font-weight: bold;")
        lay.addWidget(head)
        lay.addWidget(self.btn_column)
        lay.addStretch(1)
        lay.addWidget(self.title)
        lay.addWidget(self.note)
        lay.addLayout(self._form)

        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_MS)
        self._timer.timeout.connect(self.sync)
        self.sync(force=True)

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

    # ---- Mengikuti pilihan di viewport -------------------------------------
    def showEvent(self, ev) -> None:            # noqa: N802 (Qt)
        super().showEvent(ev)
        self._timer.start()
        self.sync(force=True)

    def hideEvent(self, ev) -> None:            # noqa: N802 (Qt)
        self._timer.stop()
        super().hideEvent(ev)

    def sync(self, *_args, force: bool = False) -> None:
        """Muat ulang form bila pilihan atau dokumen berubah (murah)."""
        vp = self._app.viewport
        self.btn_column.setChecked(vp.active_tool is self._tool)
        cols = selected_columns(vp.scene)
        key = (tuple(id(g) for g in cols), vp.scene.version)
        if not force and key == self._seen:
            return
        self._seen = key
        self._cols = cols
        self._load()

    def _load(self) -> None:
        self._loading = True
        try:
            try:
                if self._cols:
                    p = normalize_params(column_data(self._cols[0])["params"])
                else:
                    p = normalize_params(self._state["params"])
            except ColumnError:
                p = normalize_params(None)
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
            self.mark.setPlaceholderText("" if single else "(otomatis K1, K2, …)")
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

    # ---- Perubahan dari pengguna --------------------------------------------
    def _value(self, key: str):
        if key == "shape":
            return self.shape.currentData()
        if key == "rotation":
            return self.rotation.value()
        return getattr(self, key).value() / 1000.0

    def _changed(self, key: str) -> None:
        if self._loading:
            return
        if key == "shape":
            self._sync_rows()
        value = self._value(key)
        if self._cols:
            modify_columns(self._app.viewport, self._cols, {key: value})
            self.sync(force=True)       # tampilkan yang sebenarnya berlaku
        else:
            self._state["params"] = dict(self._state["params"], **{key: value})

    def _renamed(self) -> None:
        if self._loading or len(self._cols) != 1:
            return
        name = self.mark.text().strip()
        if name:
            modify_columns(self._app.viewport, self._cols, {}, mark=name)
        self.sync(force=True)

    def _on_arm(self, checked: bool) -> None:
        vp = self._app.viewport
        if checked:
            vp.set_active_tool(self._tool)
            return
        activate = getattr(vp.window(), "_activate_tool", None)
        if callable(activate):
            activate("select")
        else:
            vp.set_active_tool(None)


# ---------------------------------------------------------------------------
# Browser (Outliner) dan pemasangan
# ---------------------------------------------------------------------------

def outliner_kind(group):
    data = column_data(group)
    if data is None:
        return None
    try:
        p = normalize_params(data["params"])
    except ColumnError:
        return None
    from core.units import fmt_len
    if p["shape"] == "round":
        section = f"Ø {p['diameter'] * 1000:g} mm"
    else:
        section = f"{p['width'] * 1000:g} × {p['depth'] * 1000:g} mm"
    return {"type": "Kolom", "props": [("Penampang", section),
                                       ("Tinggi", fmt_len(p["height"]))]}


def _toolbar_icon() -> QIcon:
    """Elevasi kolom sederhana: kepala, batang, dan dasar."""
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    pen = QPainter(pm)
    pen.setRenderHint(QPainter.Antialiasing)
    pen.setPen(QPen(QColor(70, 70, 70), 2.5))
    pen.setBrush(QColor(176, 176, 170))
    pen.drawRect(14, 8, 20, 32)
    pen.setBrush(QColor(128, 128, 122))
    pen.drawRect(8, 3, 32, 6)
    pen.drawRect(8, 39, 32, 6)
    pen.end()
    return QIcon(pm)


def setup(app) -> None:
    """Tab «Steel» di sidebar kanan, menu Extensions ▸ Kolom beton, tombol
    «Kolom» di toolbar «Struktur», dan «Properti kolom…» di menu klik kanan
    (membuka tab Steel dengan kolom itu sudah terpilih)."""
    state = {"params": dict(DEFAULTS)}
    tool = ColumnPlaceTool(state)
    panel = ColumnPanel(app, state, tool)
    # panel="steel": tab bersama — balok dan sambungan nanti ikut di sini.
    dock = app.add_panel("Steel", panel, panel="steel")

    def start_tool() -> None:
        app.viewport.set_active_tool(tool)

    def show_panel() -> None:
        app.show_panel(dock)
        panel.sync(force=True)

    start = None
    sub = app.add_menu("Kolom beton")
    if sub is not None:
        start = sub.addAction("Tempatkan kolom", start_tool)
        start.setStatusTip("Klik lokasi di viewport untuk membuat kolom beton.")
        sub.addAction("Tampilkan panel Steel", show_panel)

    # Tombol di toolbar sendiri; gagal membuatnya tidak boleh merusak setup.
    try:
        from PySide6.QtGui import QAction
        win = app.window
        action = start or QAction("Tempatkan kolom", win)
        action.setText("Kolom")
        action.setIcon(_toolbar_icon())
        action.setToolTip("Kolom beton — klik lokasi untuk menempatkan kolom")
        if start is None:
            action.triggered.connect(lambda _c=False: start_tool())
        bar = win.addToolBar("Struktur")
        bar.setObjectName("extension_kolom_beton_toolbar")
        bar.addAction(action)
    except Exception:  # noqa: BLE001
        pass

    def context(menu, selection) -> None:
        cols = selected_columns(app.viewport.scene)
        if not cols:
            return
        menu.addSeparator()
        label = ("Properti kolom…" if len(cols) == 1
                 else f"Properti {len(cols)} kolom…")
        action = menu.addAction(label)
        action.triggered.connect(
            lambda _c=False: QTimer.singleShot(0, show_panel))

    app.add_context_menu(context)
    app.on_document_changed(panel.sync)

    add_kind = getattr(app, "add_outliner_kind", None)
    if add_kind is not None:
        add_kind(outliner_kind)
