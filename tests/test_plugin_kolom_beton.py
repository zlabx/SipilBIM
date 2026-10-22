# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""Plugin Kolom beton (plugins/kolom_beton.py): geometri, takeoff, IFC, undo,
dan pemasangannya di jendela utama (alat klik, menu klik kanan, dialog)."""
from __future__ import annotations

import importlib.util
import math
import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtGui import QVector3D as V  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QMenu  # noqa: E402

import core.extensions as extensions  # noqa: E402
from core import bim  # noqa: E402
from core.history import History  # noqa: E402
from core.scene import Scene  # noqa: E402

_app = QApplication.instance() or QApplication([])

PLUGIN = Path(__file__).resolve().parents[1] / "plugins" / "kolom_beton.py"
_spec = importlib.util.spec_from_file_location("kolom_beton_under_test", PLUGIN)
kb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kb)


@pytest.fixture(autouse=True)
def _no_modal_warnings(monkeypatch):
    """Peringatan modal menunggu klik selamanya di tes: jadikan kegagalan."""
    from PySide6.QtWidgets import QMessageBox

    def boom(_parent, title, text, *a, **k):
        raise AssertionError(f"peringatan modal tak terduga: {text}")
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(boom))


class _Vp:
    """Viewport tiruan secukupnya untuk perintah plugin."""

    def __init__(self, scene):
        self.scene = scene
        self.history = History(scene)
        self.status = []

    def update(self):
        pass

    def window(self):
        return None

    def flash_status(self, text, ms=0):
        self.status.append(text)


@pytest.fixture
def vp():
    return _Vp(Scene())


def _column(vp, point=(0.0, 0.0, 0.0), **params):
    state = {"params": dict(kb.DEFAULTS, **params)}
    assert kb.place_column(vp, V(*point), state)
    return vp.scene.groups[-1], state


def _volume(scene, group):
    obj = next(o for o in bim.collect_objects(scene) if o.get("group") is group)
    return obj


# ---- parameter ----------------------------------------------------------

def test_defaults_are_a_30x30_cm_column_three_metres_high():
    p = kb.normalize_params(None)
    assert (p["shape"], p["width"], p["depth"], p["height"]) == \
        ("rect", 0.30, 0.30, 3.0)


@pytest.mark.parametrize("bad", [
    {"width": 0}, {"width": -1}, {"height": 0.0}, {"diameter": 99},
    {"width": "abc"}, {"height": float("nan")}, {"shape": "segitiga"},
    {"rotation": float("inf")},
])
def test_invalid_parameters_are_refused_with_a_sentence(bad):
    with pytest.raises(kb.ColumnError):
        kb.normalize_params(bad)


def test_rotation_wraps_to_a_single_turn():
    assert kb.normalize_params({"rotation": -90})["rotation"] == pytest.approx(270.0)
    assert kb.normalize_params({"rotation": 450})["rotation"] == pytest.approx(90.0)


# ---- geometri -----------------------------------------------------------

def test_a_rectangular_column_is_a_closed_box_of_the_right_volume():
    p = kb.normalize_params({"width": 0.25, "depth": 0.40, "height": 3.5})
    mesh = kb.build_mesh(p)
    assert len(mesh.faces) == 6
    assert bim.face_set_volume(mesh.faces) == pytest.approx(0.25 * 0.40 * 3.5)
    zs = [v.position.z() for v in mesh.vertices]
    assert min(zs) == pytest.approx(0.0) and max(zs) == pytest.approx(3.5)


def test_every_normal_points_outward():
    mesh = kb.build_mesh(kb.normalize_params({"width": 0.3, "depth": 0.5,
                                              "height": 2.0}))
    centre = V(0.0, 0.0, 1.0)
    for f in mesh.faces:
        c = sum((v.position for v in f.loop), V(0, 0, 0)) / len(f.loop)
        assert V.dotProduct(f.normal(), c - centre) > 0


def test_a_round_column_matches_the_inscribed_polygon_volume():
    p = kb.normalize_params({"shape": "round", "diameter": 0.5, "height": 3.0})
    mesh = kb.build_mesh(p)
    assert len(mesh.faces) == kb.ROUND_SEGMENTS + 2
    vol = bim.face_set_volume(mesh.faces)
    assert vol == pytest.approx(kb.column_volume(p))
    # dekat silinder sejati (poligon 32 sisi: selisih < 0,7 %)
    assert vol == pytest.approx(math.pi * 0.25 ** 2 * 3.0, rel=0.007)


def test_the_vertical_seams_of_a_round_column_are_soft_but_the_rims_are_not():
    mesh = kb.build_mesh(kb.normalize_params({"shape": "round"}))
    soft = [e for e in mesh.edges if e.soft]
    assert len(soft) == kb.ROUND_SEGMENTS
    assert all(abs(e.a.x() - e.b.x()) < 1e-9 and abs(e.a.y() - e.b.y()) < 1e-9
               for e in soft)                       # semuanya tegak


def test_rotation_turns_the_section_without_changing_the_volume():
    flat = kb.build_mesh(kb.normalize_params({"width": 0.2, "depth": 0.6}))
    turned = kb.build_mesh(kb.normalize_params({"width": 0.2, "depth": 0.6,
                                                "rotation": 90}))
    assert bim.face_set_volume(turned.faces) == pytest.approx(
        bim.face_set_volume(flat.faces))
    xs = [v.position.x() for v in turned.vertices]
    assert max(xs) - min(xs) == pytest.approx(0.6)  # 0,6 m kini sepanjang X


# ---- menempatkan, takeoff, IFC -----------------------------------------

def test_a_click_makes_a_tagged_column_with_a_concrete_takeoff(vp):
    g, _ = _column(vp, (2.0, 3.0, 0.0), width=0.30, depth=0.30, height=3.0)
    assert g.name == "K1"
    assert g.ifc == {"class": "IfcColumn", "name": "K1"}
    assert kb.column_data(g)["params"]["height"] == 3.0
    obj = _volume(vp.scene, g)
    assert obj["class"] == "IfcColumn"
    assert obj["volume"] == pytest.approx(0.30 * 0.30 * 3.0)
    # kolom berdiri di titik klik: dasar di z=0, pusat penampang di (2, 3)
    from core.group import world_mesh
    pts = [v.position for v in world_mesh(g).vertices]
    assert min(q.z() for q in pts) == pytest.approx(0.0)
    assert (min(q.x() for q in pts) + max(q.x() for q in pts)) / 2 == pytest.approx(2.0)
    assert (min(q.y() for q in pts) + max(q.y() for q in pts)) / 2 == pytest.approx(3.0)


def test_the_base_sits_at_the_clicked_elevation(vp):
    g, _ = _column(vp, (0.0, 0.0, 4.2), height=3.0)
    from core.group import world_mesh
    zs = [v.position.z() for v in world_mesh(g).vertices]
    assert min(zs) == pytest.approx(4.2) and max(zs) == pytest.approx(7.2)


def test_marks_count_up_and_the_new_column_is_selected(vp):
    _column(vp, (0, 0, 0))
    state = {"params": dict(kb.DEFAULTS)}
    kb.place_column(vp, V(5, 0, 0), state)
    kb.place_column(vp, V(10, 0, 0), state)
    assert [g.name for g in vp.scene.groups] == ["K1", "K2", "K3"]
    assert vp.scene.selection == {vp.scene.groups[-1]}


def test_placing_and_undoing_is_one_step_and_redo_brings_it_back(vp):
    _column(vp)
    assert len(vp.scene.groups) == 1 and "Beton" in vp.scene.materials
    vp.history.undo()
    assert vp.scene.groups == [] and "Beton" not in vp.scene.materials
    vp.history.redo()
    assert [g.name for g in vp.scene.groups] == ["K1"]
    assert kb.column_data(vp.scene.groups[0]) is not None


def test_the_ifc_export_writes_an_ifccolumn_with_its_volume(vp, tmp_path):
    from formats import ifc
    _column(vp, height=3.0, width=0.3, depth=0.3)
    path = tmp_path / "k.ifc"
    assert ifc.save_ifc(vp.scene, path) == 1
    text = path.read_text()
    assert "IFCCOLUMN" in text and "Qto_ColumnBaseQuantities" in text
    assert "0.27" in text                           # 0,3 × 0,3 × 3 m³


def test_the_column_survives_save_and_open(vp, tmp_path):
    from formats import igz
    _column(vp, (1, 1, 0), shape="round", diameter=0.45, height=2.8)
    path = tmp_path / "m.sbim"
    igz.save_scene(vp.scene, path)
    other = Scene()
    igz.load_into(other, path)
    g = other.groups[0]
    data = kb.column_data(g)
    assert data["params"]["shape"] == "round"
    assert data["params"]["diameter"] == pytest.approx(0.45)
    assert g.ifc["class"] == "IfcColumn"


# ---- propriedades: reconstruir -----------------------------------------

def test_changing_the_profile_keeps_the_place_and_undo_restores_it(vp):
    g, _ = _column(vp, (2.0, 3.0, 0.0), width=0.30, depth=0.30, height=3.0)
    before = bim.face_set_volume(
        __import__("core.group", fromlist=["x"]).world_mesh(g).faces)
    vp.history.execute(kb.ColumnCommand(lambda sc: kb.rebuild_column(
        sc, g, {"shape": "round", "diameter": 0.5, "height": 4.0})))
    obj = _volume(vp.scene, g)
    assert obj["volume"] == pytest.approx(kb.column_volume(
        kb.normalize_params({"shape": "round", "diameter": 0.5, "height": 4.0})),
        rel=1e-4)                                   # koordinat dunia float32
    from core.group import world_mesh
    pts = [v.position for v in world_mesh(g).vertices]
    assert (min(q.x() for q in pts) + max(q.x() for q in pts)) / 2 == pytest.approx(2.0)
    assert max(q.z() for q in pts) == pytest.approx(4.0)
    vp.history.undo()
    assert kb.column_data(g)["params"]["shape"] == "rect"
    assert _volume(vp.scene, g)["volume"] == pytest.approx(before)


def test_a_moved_column_stays_where_it_was_moved_after_a_rebuild(vp):
    """Move/Rotate compõem na matriz do container: reconstruir não o devolve."""
    from PySide6.QtGui import QMatrix4x4
    from core.group import world_mesh
    g, _ = _column(vp, (0.0, 0.0, 0.0))
    m = QMatrix4x4(g.xform)
    m.translate(V(7.0, 0.0, 0.0))
    g.xform = m                                     # o que a ferramenta Move faz
    vp.history.execute(kb.ColumnCommand(
        lambda sc: kb.rebuild_column(sc, g, {"height": 5.0})))
    xs = [v.position.x() for v in world_mesh(g).vertices]
    assert (min(xs) + max(xs)) / 2 == pytest.approx(7.0)


def test_renaming_updates_the_ifc_name_and_keeps_a_retagged_class(vp):
    g, _ = _column(vp)
    g.ifc = {"class": "IfcMember", "name": "K1"}    # o painel BIM re-etiquetou
    vp.history.execute(kb.ColumnCommand(
        lambda sc: kb.rebuild_column(sc, g, {}, mark="KB-A")))
    assert g.name == "KB-A"
    assert g.ifc == {"class": "IfcMember", "name": "KB-A"}


def test_an_invalid_rebuild_changes_nothing(vp):
    g, _ = _column(vp)
    vp.history.execute(kb.ColumnCommand(
        lambda sc: kb.rebuild_column(sc, g, {"width": -1})))
    assert vp.history.last_error
    assert kb.column_data(g)["params"]["width"] == 0.30


def test_only_columns_are_found_in_the_selection(vp):
    g, _ = _column(vp)
    from core.group import Group
    other = Group(name="Grupo")
    vp.scene.groups.append(other)
    vp.scene.selection.update({g, other})
    assert kb.selected_columns(vp.scene) == [g]


def test_the_browser_describes_the_section(vp):
    g, _ = _column(vp, width=0.25, depth=0.40, height=3.0)
    info = kb.outliner_kind(g)
    assert info["type"] == "Kolom"
    assert ("Penampang", "250 × 400 mm") in info["props"]
    r, _ = _column(vp, (5, 0, 0), shape="round", diameter=0.5)
    assert ("Penampang", "Ø 500 mm") in kb.outliner_kind(r)["props"]


def test_placing_is_refused_while_a_group_is_open(vp, monkeypatch):
    vp.scene.edit_group = object()
    monkeypatch.setattr(kb, "_warn", lambda *_a, **_k: None)
    assert not kb.place_column(vp, V(0, 0, 0), {"params": dict(kb.DEFAULTS)})
    assert vp.scene.groups == []


# ---- alat ---------------------------------------------------------------

def test_the_tool_previews_a_wireframe_and_places_on_click(vp):
    state = {"params": dict(kb.DEFAULTS)}
    tool = kb.ColumnPlaceTool(state)
    assert tool.rubber_band_lines() == []            # belum ada kursor
    ctx = SimpleNamespace(viewport=vp, world=V(1.0, 2.0, 0.0))
    tool.on_hover(ctx)
    lines = tool.rubber_band_lines()
    assert len(lines) == 4 + 4 + 4                   # alas, atas, 4 rusuk tegak
    assert max(q.z() for ln in lines for q in ln) == pytest.approx(3.0)
    tool.on_click(ctx)
    assert [g.name for g in vp.scene.groups] == ["K1"]
    tool.on_click(SimpleNamespace(viewport=vp, world=V(4.0, 2.0, 0.0)))
    assert [g.name for g in vp.scene.groups] == ["K1", "K2"]   # alat tetap aktif


def test_the_tool_is_not_listed_by_the_loader():
    """Butuh argumen: pemuat tidak membuat entri menu ganda untuknya."""
    assert not extensions._builds_bare(kb.ColumnPlaceTool)


# ---- jendela utama: menu, klik kanan, dialog ---------------------------

@pytest.fixture
def win(tmp_path, monkeypatch):
    shutil.copy(PLUGIN, tmp_path / "kolom_beton.py")
    monkeypatch.setattr(extensions, "plugin_dirs", lambda: [tmp_path])
    from views.main_window import MainWindow
    w = MainWindow()
    yield w
    w._saved_version = w.viewport.scene.version     # tanpa dialog "simpan?"
    w.close()


def _mod():
    return next(m for n, m in sys.modules.items()
                if n.endswith("kolom_beton") and hasattr(m, "ColumnDialog")
                and m is not kb)


def _bar(win):
    from PySide6.QtWidgets import QToolBar
    return win.findChild(QToolBar, "extension_kolom_beton_toolbar")


def _columns(mod, vp):
    """Jendela baru sudah berisi figur bawaan: hanya hitung kolom."""
    return [g for g in vp.scene.groups if mod.column_data(g) is not None]


def test_setup_adds_the_menu_the_toolbar_button_and_the_context_hook(win):
    titles = [a.text() for a in win._ext_menu.actions()]
    assert any("Kolom beton" in t for t in titles)
    bar = _bar(win)
    assert bar is not None
    assert [a.text() for a in bar.actions()] == ["Kolom"]


def test_the_toolbar_button_arms_the_tool_and_clicks_make_columns(win):
    mod, vp = _mod(), win.viewport
    _bar(win).actions()[0].trigger()
    assert isinstance(vp.active_tool, mod.ColumnPlaceTool)
    vp.active_tool.on_click(SimpleNamespace(viewport=vp, world=V(3, 3, 0)))
    vp.active_tool.on_click(SimpleNamespace(viewport=vp, world=V(6, 3, 0)))
    assert [g.name for g in _columns(mod, vp)] == ["K1", "K2"]


def test_right_click_offers_properties_only_on_a_column(win, monkeypatch):
    mod, vp = _mod(), win.viewport
    labels = lambda: [a.text() for m in [QMenu()] for fn in win._ext_context_menus
                      if not fn(m, list(vp.scene.selection))
                      for a in m.actions() if a.text()]  # noqa: E731
    vp.scene.selection.clear()
    assert labels() == []                            # nada selecionado
    vp.scene.selection.update(vp.scene.groups)       # figur bawaan, bukan kolom
    assert labels() == []
    mod.place_column(vp, V(0, 0, 0), {"params": dict(mod.DEFAULTS)})
    assert "Properti kolom…" in labels()
    mod.place_column(vp, V(5, 0, 0), {"params": dict(mod.DEFAULTS)})
    vp.scene.selection.update(vp.scene.groups)
    assert "Properti 2 kolom…" in labels()


def test_the_properties_dialog_rebuilds_the_selected_column(win, monkeypatch):
    mod, vp = _mod(), win.viewport
    mod.place_column(vp, V(0, 0, 0), {"params": dict(mod.DEFAULTS)})
    g = _columns(mod, vp)[0]
    vp.scene.selection.clear()
    vp.scene.selection.add(g)

    def fake_exec(self):                              # pengguna mengisi form
        self.shape.setCurrentIndex(1)
        self.diameter.setValue(600)
        self.height.setValue(4500)
        self.mark.setText("KB-1")
        return QDialog.Accepted
    monkeypatch.setattr(mod.ColumnDialog, "exec", fake_exec)
    state = {"params": dict(mod.DEFAULTS)}
    mod.edit_columns(vp, state)
    data = mod.column_data(g)["params"]
    assert (data["shape"], data["diameter"], data["height"]) == ("round", 0.6, 4.5)
    assert g.name == "KB-1" and g.ifc["name"] == "KB-1"
    assert state["params"]["shape"] == "round"      # kolom berikutnya mengikuti


def test_the_dialog_shows_only_the_rows_that_matter_for_the_shape(win):
    mod = _mod()
    dlg = mod.ColumnDialog(win, mod.normalize_params(None), "t", mark="K1")
    dlg.show()
    assert dlg.width.isVisible() and not dlg.diameter.isVisible()
    dlg.shape.setCurrentIndex(1)
    assert dlg.diameter.isVisible() and not dlg.width.isVisible()
    assert not dlg.rotation.isVisible()
    dlg.close()
