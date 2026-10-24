# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Element definitions for the SipilBIM palette and the Properties form.

An element that works (``implemented = True``) has a click-to-place tool and
describes its editable properties as DATA (``properties()``); the Properties
form in the side tray is generic and builds itself from that description, so a
new element never needs a new form. To add one:

1. write its geometry/commands module (like ``column.py``);
2. add an ``Element`` subclass here: ``key``, ``label``, ``properties()``,
   ``owns()``, ``tool()``, ``params_of()``, ``modify()``, ``next_name()``;
3. add it to ``build_elements()``.

Every element shares the same two General properties — **Element** (its type,
e.g. «Column») and **Name** (its mark, e.g. «K1») — followed by the properties
it declares. Connections are listed as data in ``connections.py``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import column as col


# ---------------------------------------------------------------------------
# Property schema
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Prop:
    """One editable property of an element.

    ``lo``/``hi`` are in STORED units (metres for lengths); ``scale`` converts
    a stored value to the displayed one (1000 = metres → millimetres).
    ``when`` receives the current values of all properties (``{key: value}``)
    and says whether this row is shown (e.g. diameter only for a circular
    section)."""

    key: str
    label: str
    kind: str                       # "length" | "angle" | "choice"
    lo: float = 0.0
    hi: float = 0.0
    step: float = 1.0               # in displayed units
    decimals: int = 0
    suffix: str = ""
    scale: float = 1.0
    choices: tuple = ()             # kind "choice": ((value, text), …)
    tip: str = ""
    when: Callable[[dict], bool] | None = None


def length(key: str, label: str, lo: float, hi: float, *, tip: str = "",
           when=None, step: float = 50.0) -> Prop:
    """A length stored in metres and shown in millimetres."""
    return Prop(key, label, "length", lo, hi, step, 0, " mm", 1000.0,
                tip=tip, when=when)


def angle(key: str, label: str, *, tip: str = "", when=None) -> Prop:
    """An angle in degrees, 0 – 360."""
    return Prop(key, label, "angle", 0.0, 359.9, 5.0, 1, " °", 1.0,
                tip=tip, when=when)


def choice(key: str, label: str, choices, *, tip: str = "",
           when=None) -> Prop:
    return Prop(key, label, "choice", choices=tuple(choices), tip=tip,
                when=when)


# ---------------------------------------------------------------------------
# Elements
# ---------------------------------------------------------------------------

class Element:
    """One kind of building element on the palette."""

    key = ""                    # stable identifier
    label = ""                  # singular name, shown as «Element» in Properties
    plural = ""                 # plural name
    tip = ""                    # tooltip
    icon_kind = ""              # icon name (icons.py)
    implemented = False

    def __init__(self) -> None:
        #: Properties of the NEXT element placed (used with nothing selected).
        self.state: dict = {"params": {}}

    # ---- identity -----------------------------------------------------------
    def owns(self, group) -> bool:
        """Is ``group`` an element of this kind?"""
        return False

    def tool(self):
        """The click-to-place tool (one reusable object), or ``None``."""
        return None

    def name_of(self, group) -> str:
        return group.name or ""

    def next_name(self, scene) -> str:
        """The automatic name the next element will get (e.g. «K3»)."""
        return ""

    # ---- properties ---------------------------------------------------------
    def properties(self) -> tuple:
        """The element's own editable properties (a tuple of ``Prop``)."""
        return ()

    def params_of(self, group) -> dict:
        """Current, validated values of ``group`` (``{prop key: value}``)."""
        return dict(self.state["params"])

    def default_params(self) -> dict:
        """Values for the next element placed."""
        return dict(self.state["params"])

    def set_default(self, key: str, value) -> None:
        self.state["params"] = dict(self.state["params"], **{key: value})

    def modify(self, viewport, groups: list, changes: dict,
               name: str | None = None) -> bool:
        """Apply ``changes`` (and a new ``name``) to ``groups`` as one undo
        step. Returns whether anything changed."""
        return False

    # ---- menus --------------------------------------------------------------
    def context_label(self, n: int) -> str | None:
        """Right-click entry for ``n`` selected elements (``None`` = none)."""
        if not self.implemented or n < 1:
            return None
        if n == 1:
            return f"{self.label} properties…"
        return f"Properties of {n} {self.plural.lower()}…"

    def outliner_kind(self, group):
        return None


class ColumnElement(Element):
    key = "column"
    label = "Column"
    plural = "Columns"
    tip = "Concrete column — click here, then click a location in the viewport"
    icon_kind = "column"
    implemented = True

    def __init__(self) -> None:
        super().__init__()
        self.state = {"params": dict(col.DEFAULTS)}
        self._tool = None

    def owns(self, group) -> bool:
        return col.column_data(group) is not None

    def tool(self):
        if self._tool is None:
            self._tool = col.ColumnPlaceTool(self.state)
        return self._tool

    def next_name(self, scene) -> str:
        return col.next_mark(scene)

    def properties(self) -> tuple:
        rect = lambda v: v.get("shape") == "rect"        # noqa: E731
        round_ = lambda v: v.get("shape") == "round"     # noqa: E731
        return (
            choice("shape", "Cross-section",
                   (("rect", "Rectangular"), ("round", "Circular"))),
            length("width", "Width (X)", *col.SIZE_RANGE, when=rect,
                   tip="Section size along the local X axis"),
            length("depth", "Depth (Y)", *col.SIZE_RANGE, when=rect,
                   tip="Section size along the local Y axis"),
            length("diameter", "Diameter", *col.SIZE_RANGE, when=round_),
            length("height", "Height", *col.HEIGHT_RANGE,
                   tip="Column height, from its base"),
            angle("rotation", "Rotation", when=rect,
                  tip="Turn of the section about the vertical axis"),
        )

    def params_of(self, group) -> dict:
        try:
            return col.normalize_params(col.column_data(group)["params"])
        except (col.ColumnError, TypeError, KeyError):
            return col.normalize_params(None)

    def default_params(self) -> dict:
        try:
            return col.normalize_params(self.state["params"])
        except col.ColumnError:
            return col.normalize_params(None)

    def modify(self, viewport, groups, changes, name=None) -> bool:
        return col.modify_columns(viewport, groups, changes, mark=name)

    def outliner_kind(self, group):
        return col.outliner_kind(group)


class PlaceholderElement(Element):
    """A button with no function yet."""

    implemented = False

    def __init__(self, key: str, label: str, icon_kind: str, tip: str) -> None:
        super().__init__()
        self.key, self.label, self.icon_kind, self.tip = (
            key, label, icon_kind, tip)
        self.plural = label


def build_elements() -> list:
    """The elements on the palette, in order. Add new elements here."""
    return [
        ColumnElement(),
        PlaceholderElement("beam", "Beam", "beam",
                           "Beam — not available yet"),
        PlaceholderElement("slab", "Slab", "slab",
                           "Slab — not available yet"),
        PlaceholderElement("wall", "Wall", "wall",
                           "Wall — not available yet"),
        PlaceholderElement("footing", "Footing", "footing",
                           "Footing — not available yet"),
    ]
