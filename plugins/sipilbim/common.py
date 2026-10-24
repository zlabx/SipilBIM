# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Shared pieces of the SipilBIM plugin: one undo step for editing an element,
warnings, and selection helpers. Used by the column today and by beams, slabs
and the other elements later."""
from __future__ import annotations

import copy

from PySide6.QtGui import QMatrix4x4
from PySide6.QtWidgets import QMessageBox

from core.history import Command

TITLE = "SipilBIM"


class ElementCommand(Command):
    """One undo step: the list of groups, and the contents, tags, parameters,
    name and matrix of each group, plus the material registry."""

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


def warn(viewport, text: str) -> None:
    """Message in the status bar and a warning box."""
    try:
        viewport.flash_status(f"{TITLE}: " + text.splitlines()[0], 6000)
    except Exception:  # noqa: BLE001
        pass
    QMessageBox.warning(viewport.window(), TITLE, text)


def run_command(viewport, mutate, ok_message: str) -> bool:
    """Run ``mutate(scene)`` as a single undo step."""
    hist = viewport.history
    hist.execute(ElementCommand(mutate))
    if hist.last_error:
        warn(viewport, hist.last_error.split(": ", 1)[-1])
        return False
    notify = getattr(viewport, "notify_scene_changed", None)
    if callable(notify):
        notify()
    viewport.update()
    viewport.flash_status(ok_message, 4000)
    return True


def at_top_level(viewport) -> bool:
    """Elements are only created or edited at the top level, not inside a
    group that is open for editing."""
    if getattr(viewport.scene, "edit_group", None) is not None:
        warn(viewport, "Close the group being edited, then try again.")
        return False
    return True


def selected_groups(scene) -> list:
    """Selected top-level groups (no duplicates)."""
    out = []
    for e in scene.selection:
        g = getattr(e, "owner", None) or e
        if g in scene.groups and g not in out:
            out.append(g)
    return out
