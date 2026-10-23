# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Bagian umum paket Structure: satu langkah undo untuk mengubah elemen,
peringatan, dan pembantu pemilihan. Dipakai kolom sekarang, balok/pelat
dan lainnya nanti."""
from __future__ import annotations

import copy

from PySide6.QtGui import QMatrix4x4
from PySide6.QtWidgets import QMessageBox

from core.history import Command


class StructureCommand(Command):
    """Satu langkah undo: daftar group, isi/tag/parameter/nama/matriks tiap
    group, dan registri material."""

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
    """Pesan di status bar dan kotak peringatan."""
    try:
        viewport.flash_status("Structure: " + text.splitlines()[0], 6000)
    except Exception:  # noqa: BLE001
        pass
    QMessageBox.warning(viewport.window(), "Structure", text)


def run_command(viewport, mutate, ok_message: str) -> bool:
    """Jalankan ``mutate(scene)`` sebagai satu langkah undo."""
    hist = viewport.history
    hist.execute(StructureCommand(mutate))
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
    """Elemen hanya dibuat/diubah di tingkat atas, bukan di dalam group."""
    if getattr(viewport.scene, "edit_group", None) is not None:
        warn(viewport, "Tutup group yang sedang diedit, lalu ulangi.")
        return False
    return True


def selected_groups(scene) -> list:
    """Group tingkat atas yang terpilih (tanpa duplikat)."""
    out = []
    for e in scene.selection:
        g = getattr(e, "owner", None) or e
        if g in scene.groups and g not in out:
            out.append(g)
    return out
