# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Kolom beton: geometri, data, perintah, dan alat klik-lokasi.

Satu kolom = satu container group; parameternya di ``group.ext["kolom_beton"]``
(kunci yang sama dengan plugin Kolom beton lama, jadi kolom dari dokumen lama
tetap terbaca dan bisa diedit). Mesh dibangun dari parameter di koordinat
lokal (dasar di z = 0, naik ke +Z); posisi ada di matriks group, jadi
Move/Rotate tidak perlu membangun ulang apa pun.
"""
from __future__ import annotations

import copy
import math
import re

from PySide6.QtGui import QMatrix4x4, QVector3D

from tools.base import Tool

from .common import StructureCommand as ColumnCommand
from .common import at_top_level as _at_top_level
from .common import run_command as _run
from .common import warn as _warn

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
# Perintah (dipanggil dari tombol, klik, dan menu klik kanan)
# ---------------------------------------------------------------------------

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
