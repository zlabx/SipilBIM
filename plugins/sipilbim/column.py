# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Concrete column: geometry, data, commands and the click-to-place tool.

One column = one container group; its parameters live in
``group.ext["column"]`` (the key is the element's ``key``, so each new element
type keeps its data under its own name). The mesh is built from the parameters
in local coordinates (base at z = 0, rising along +Z); the position is the
group's matrix, so Move/Rotate never rebuild anything.
"""
from __future__ import annotations

import copy
import math
import re

from PySide6.QtGui import QMatrix4x4, QVector3D

from tools.base import Tool

from .common import ElementCommand as ColumnCommand
from .common import at_top_level as _at_top_level
from .common import run_command as _run
from .common import warn as _warn

KEY = "column"
IFC_CLASS = "IfcColumn"
MATERIAL = "Concrete"
CONCRETE_COLOR = (0.74, 0.74, 0.72)
ROUND_SEGMENTS = 32
MARK_PREFIX = "K"

#: Model units are metres; the panel shows millimetres (civil practice).
DEFAULTS = {
    "shape": "rect",        # "rect" | "round"
    "width": 0.30,          # side along the local X axis (rect)
    "depth": 0.30,          # side along the local Y axis (rect)
    "diameter": 0.40,       # (round)
    "height": 3.00,
    "rotation": 0.0,        # degrees, section turn about the Z axis
}

#: Allowed ranges in metres (the panel and the validation share them).
SIZE_RANGE = (0.01, 5.0)        # width, depth, diameter
HEIGHT_RANGE = (0.1, 100.0)


class ColumnError(Exception):
    """Invalid column parameter (the message is a sentence for the user)."""


# ---------------------------------------------------------------------------
# Parameter
# ---------------------------------------------------------------------------

def _num(p: dict, key: str, lo: float, hi: float, label: str) -> float:
    try:
        v = float(p[key])
    except (KeyError, TypeError, ValueError):
        raise ColumnError(f"{label}: invalid value.") from None
    if not math.isfinite(v) or v < lo or v > hi:
        raise ColumnError(
            f"{label}: must be between {lo * 1000:g} and {hi * 1000:g} mm.")
    return v


def normalize_params(params: dict | None) -> dict:
    """Complete, validated parameters (defaults fill the missing ones)."""
    p = dict(DEFAULTS)
    if params:
        p.update({k: params[k] for k in DEFAULTS if k in params})
    if p["shape"] not in ("rect", "round"):
        raise ColumnError("Cross-section must be rectangular or circular.")
    p["width"] = _num(p, "width", *SIZE_RANGE, "Width")
    p["depth"] = _num(p, "depth", *SIZE_RANGE, "Depth")
    p["diameter"] = _num(p, "diameter", *SIZE_RANGE, "Diameter")
    p["height"] = _num(p, "height", *HEIGHT_RANGE, "Height")
    try:
        rot = float(p["rotation"])
    except (TypeError, ValueError):
        raise ColumnError("Rotation: invalid value.") from None
    if not math.isfinite(rot):
        raise ColumnError("Rotation: invalid value.")
    p["rotation"] = rot % 360.0
    return p


def column_data(group):
    """Column data in ``group.ext``, or ``None`` if the group is not ours."""
    ext = getattr(group, "ext", None)
    if not ext:
        return None
    data = ext.get(KEY)
    return data if isinstance(data, dict) and "params" in data else None


def next_mark(scene) -> str:
    """Next column mark: K{max+1} over the existing columns."""
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
# Geometry (local coordinates: base at z = 0, rising along +Z)
# ---------------------------------------------------------------------------

def profile_points(p: dict) -> list:
    """The section as a counter-clockwise 2D polygon (metres), already
    turned by ``rotation``."""
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
    """Closed (watertight) mesh: the section extruded ``height`` high, all
    normals facing outward."""
    from core.mesh import Mesh
    pts = profile_points(p)
    if _newell_z(pts) < 0:          # keep CCW order
        pts = list(reversed(pts))
    n, h = len(pts), p["height"]
    mesh = Mesh()

    def add(loop3):
        face = mesh.add_face([QVector3D(*q) for q in loop3])
        if attrs:
            face.attrs.update(copy.deepcopy(attrs))
        return face

    add([(x, y, 0.0) for x, y in reversed(pts)])        # base, normal -Z
    add([(x, y, h) for x, y in pts])                    # top,  normal +Z
    for i in range(n):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
        add([(ax, ay, 0.0), (bx, by, 0.0), (bx, by, h), (ax, ay, h)])
    if p["shape"] == "round":
        # Vertical edges are softened so the cylinder looks smooth (like a
        # push/pull cylinder); the top and bottom rims stay visible.
        for x, y in pts:
            a = mesh.vertex_at(QVector3D(x, y, 0.0))
            b = mesh.vertex_at(QVector3D(x, y, h))
            edge = mesh.find_edge(a, b) if a is not None and b is not None \
                else None
            if edge is not None:
                edge.soft = True
    return mesh


def ensure_material(scene) -> dict:
    """The «Concrete» material in the document registry; returns the face
    attributes."""
    from core.materials import Material
    mat = scene.materials.get(MATERIAL)
    if mat is None:
        mat = Material(MATERIAL, color=CONCRETE_COLOR)
        scene.materials[MATERIAL] = mat
    return mat.face_attrs()


def _make_child(scene, p: dict, pose: QMatrix4x4):
    from core.group import Group
    child = Group(build_mesh(p, ensure_material(scene)), name="Concrete")
    child.xform = QMatrix4x4(pose)
    child.component = False
    return child


def _pose_of(group) -> QMatrix4x4:
    """Where the column mesh sits inside the container (the click point)."""
    for k in getattr(group, "children", None) or ():
        if k.xform is not None:
            return QMatrix4x4(k.xform)
    return QMatrix4x4()


def make_column(scene, point: QVector3D, params: dict, mark: str):
    """Create a column with its base at ``point``; returns its container."""
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
    """New parameters, same place: the mesh is rebuilt at the current
    position (a Move/Rotate on the column is kept)."""
    if column_data(group) is None:
        raise ColumnError(f"«{group.name}» is not a concrete column.")
    p = normalize_params(params)
    group.children = [_make_child(scene, p, _pose_of(group))]
    ext = dict(group.ext or {})
    ext[KEY] = dict(ext[KEY], params=p)
    group.ext = ext
    if mark:
        group.name = mark
    ifc = dict(group.ifc or {"class": IFC_CLASS})   # keep the BIM-panel tag
    ifc["name"] = group.name
    group.ifc = ifc


def column_volume(p: dict) -> float:
    """Theoretical concrete volume (m³) — a check for the takeoff."""
    if p["shape"] == "round":
        r = p["diameter"] / 2.0
        n = ROUND_SEGMENTS
        area = 0.5 * n * r * r * math.sin(2.0 * math.pi / n)
    else:
        area = p["width"] * p["depth"]
    return area * p["height"]


# ---------------------------------------------------------------------------
# Commands (called from the buttons, the click and the right-click menu)
# ---------------------------------------------------------------------------

def selected_columns(scene) -> list:
    out = []
    for e in scene.selection:
        g = getattr(e, "owner", None) or e
        if g in scene.groups and column_data(g) is not None and g not in out:
            out.append(g)
    return out


def place_column(viewport, point: QVector3D, state: dict) -> bool:
    """One click = one column with the last properties used."""
    if not _at_top_level(viewport):
        return False
    scene = viewport.scene
    params = dict(state["params"])
    mark = next_mark(scene)
    return _run(viewport, lambda sc: make_column(sc, point, params, mark),
                f"Column {mark} placed — click again for the next one.")


def modify_columns(viewport, cols: list, changes: dict,
                   mark: str | None = None) -> bool:
    """Apply ``changes`` (parameter name → value) to every column in
    ``cols`` as ONE undo step. No real change: no undo step."""
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
    return _run(viewport, mutate, f"Column updated: {names}.")



# ---------------------------------------------------------------------------
# Tool: click a location
# ---------------------------------------------------------------------------

class ColumnPlaceTool(Tool):
    """Click a location → the column is placed. Stays active until another
    tool is picked.

    It needs a constructor argument, so the plugin loader does not add a menu
    entry for it automatically; the entry is made in ``setup``."""

    name = "Column"
    description = "Place a concrete column with one click."
    uses_snap = True
    wireframe_color = (0.95, 0.45, 0.16, 1.0)

    def __init__(self, state: dict) -> None:
        self.state = state
        self._hover: QVector3D | None = None

    def on_activate(self, viewport) -> None:
        self._hover = None
        viewport.flash_status(
            "Column: click to place (right-click a column ▸ Column "
            "properties…). Pick another tool to finish.", 8000)

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
        """Ghost of the column (wireframe) under the cursor."""
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
    return {"type": "Column", "props": [("Section", section),
                                        ("Height", fmt_len(p["height"]))]}
