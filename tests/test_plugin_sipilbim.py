# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""SipilBIM plugin: column (geometry, takeoff, IFC, undo), the left palette,
the «SipilBIM» sidebar tab with its generic Properties form, and the loader
in the main window."""
from __future__ import annotations

import importlib.util
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtGui import QVector3D as V  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu  # noqa: E402

import core.extensions as extensions  # noqa: E402
from core import bim  # noqa: E402
from core.history import History  # noqa: E402
from core.scene import Scene  # noqa: E402

_app = QApplication.instance() or QApplication([])

REPO = Path(__file__).resolve().parents[1]
# A copy of the package in a folder of its own: the loader then loads only
# «sipilbim», not every bundled plugin (AI, Blender…).
PKG_DIR = Path(tempfile.mkdtemp(prefix="ingetrazo-test-sipilbim-"))
shutil.copytree(REPO / "plugins" / "sipilbim", PKG_DIR / "sipilbim",
                ignore=shutil.ignore_patterns("__pycache__"))

# Dimuat lewat pemuat plugin SipilBIM yang sama dengan aplikasi (paket
# dengan __init__.py), supaya impor relatif dan nama modul sama persis.
_plugins, _errors = extensions.discover_plugins([PKG_DIR])
assert not _errors, _errors
kb = importlib.import_module("ingetrazo_plugin_sipilbim.column")


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
    {"width": "abc"}, {"height": float("nan")}, {"shape": "triangle"},
    {"rotation": float("inf")},
])
def test_invalid_parameters_are_refused_with_a_sentence(bad):
    with pytest.raises(kb.ColumnError):
        kb.normalize_params(bad)


def test_the_messages_for_the_user_are_in_english():
    with pytest.raises(kb.ColumnError, match=r"Width: must be between 10 and 5000 mm"):
        kb.normalize_params({"width": 0})
    with pytest.raises(kb.ColumnError, match="Cross-section"):
        kb.normalize_params({"shape": "triangle"})


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
    assert len(vp.scene.groups) == 1 and "Concrete" in vp.scene.materials
    vp.history.undo()
    assert vp.scene.groups == [] and "Concrete" not in vp.scene.materials
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
    assert info["type"] == "Column"
    assert ("Section", "250 × 400 mm") in info["props"]
    r, _ = _column(vp, (5, 0, 0), shape="round", diameter=0.5)
    assert ("Section", "Ø 500 mm") in kb.outliner_kind(r)["props"]


def test_placing_is_refused_while_a_group_is_open(vp, monkeypatch):
    vp.scene.edit_group = object()
    seen = []
    common = importlib.import_module("ingetrazo_plugin_sipilbim.common")
    monkeypatch.setattr(common, "warn", lambda _vp, text: seen.append(text))
    assert not kb.place_column(vp, V(0, 0, 0), {"params": dict(kb.DEFAULTS)})
    assert vp.scene.groups == []
    assert seen and "group" in seen[0]


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


# ---- main window: left palette, SipilBIM tab, generic Properties form --

@pytest.fixture
def win(monkeypatch):
    monkeypatch.setattr(extensions, "plugin_dirs", lambda: [PKG_DIR])
    from views.main_window import MainWindow
    w = MainWindow()
    yield w
    w._saved_version = w.viewport.scene.version     # no "save?" dialog
    w.close()


def _mods():
    return (importlib.import_module("ingetrazo_plugin_sipilbim.panel"),
            importlib.import_module("ingetrazo_plugin_sipilbim.widgets"),
            importlib.import_module("ingetrazo_plugin_sipilbim.elements"))


def _dock(win):
    return win.extension_panels()["extension_sipilbim"]


def _wb(win):
    panel_mod, _w, _e = _mods()
    return win.findChild(panel_mod.Workbench)


def _form(win):
    return _wb(win).panel.form


def _refresh(win):
    _wb(win).sync(force=True)


def _columns(vp):
    """A new window already holds a built-in figure: count only columns."""
    return [g for g in vp.scene.groups if kb.column_data(g) is not None]


def _select(vp, *groups):
    vp.scene.selection.clear()
    vp.scene.selection.update(groups)


def test_the_loader_finds_the_package_and_it_has_a_setup():
    plugins, errors = extensions.discover_plugins([PKG_DIR])
    assert not errors
    assert [p.stem for p in plugins] == ["sipilbim"]
    assert callable(plugins[0].setup)


def test_the_sidebar_tab_is_called_sipilbim(win):
    dock = _dock(win)
    assert dock.windowTitle() == "SipilBIM"
    assert dock.objectName() == "extension_sipilbim"
    assert "extension_structure" not in win.extension_panels()
    assert dock.widget().findChild(_mods()[0].SipilBimPanel) is not None


def test_the_sipilbim_tab_folds_and_unfolds_with_the_sidebar(win):
    dock = _dock(win)
    win.show()                                    # Qt reports a tray open once it is up
    for _ in range(5):
        _app.processEvents()
    win._act_sidebar.setChecked(False)                            # Ctrl+F5
    _app.processEvents()
    assert dock.isHidden()                                        # folded with the rest
    win._act_sidebar.setChecked(True)
    _app.processEvents()
    assert not dock.isHidden()                                    # the tab came back


def test_the_tab_has_a_collapsible_model_and_properties_section(win):
    _p, widgets, _e = _mods()
    panel = _wb(win).panel
    sections = panel.findChildren(widgets.CollapsibleSection)
    assert [s.toggle.text() for s in sections] == ["Model", "Properties"]
    model, props = sections
    assert model.is_expanded() and props.is_expanded()
    assert panel.model_note.text() == "No model data yet."   # empty for now
    model.toggle.click()
    assert not model.is_expanded() and not model.body.isVisibleTo(panel)
    assert props.body.isVisibleTo(panel)                      # independent
    model.toggle.click()
    assert model.body.isVisibleTo(panel)


def test_the_palette_is_a_left_toolbar_not_part_of_the_tab(win):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel, QToolBar
    wb = _wb(win)
    bar = win.findChild(QToolBar, "sipilbim_elements_bar")
    assert bar is wb.palette and win.toolBarArea(bar) == Qt.LeftToolBarArea
    assert bar.isMovable() and not wb.palette.is_horizontal       # a column
    titles = [lb.text() for lb in wb.palette.findChildren(QLabel, "sipilbim_title")]
    assert titles == ["Building Elements", "Connections"]
    assert not _dock(win).isAncestorOf(wb.palette)                # nothing left on the right
    assert wb.panel.findChildren(type(wb.buttons["column"])) == []


def test_the_palette_follows_the_toolbar_when_it_is_dragged_to_the_top(win):
    from PySide6.QtCore import Qt
    wb = _wb(win)
    bar = wb.palette
    assert wb.buttons["base_plate"].text() == "Base plate"        # a column: full text
    win.addToolBar(Qt.TopToolBarArea, bar)
    _app.processEvents()
    assert win.toolBarArea(bar) == Qt.TopToolBarArea and bar.is_horizontal
    assert wb.buttons["base_plate"].text() == ""                  # a row: icon only
    assert wb.buttons["column"].text() == "Column"                # the elements keep it
    win.addToolBar(Qt.LeftToolBarArea, bar)
    _app.processEvents()
    assert not bar.is_horizontal and wb.buttons["base_plate"].text() == "Base plate"


def test_the_palette_folds_behind_the_arrow_instead_of_forcing_the_window_size(win):
    """One tall widget in the toolbar could not fold: the window could not be
    shorter than the palette, and on a small screen the layout was squeezed
    (the sidebar lost 84 px of its width — tests/test_sidebar_trays.py). Each
    button is its own toolbar item, so the toolbar's minimum is a few buttons."""
    bar = _wb(win).palette
    assert bar.minimumSizeHint().height() < 300
    assert bar.minimumSizeHint().width() < 300
    assert len(bar.actions()) == 18               # 14 buttons, 2 titles, 2 separators
    assert bar.widgetForAction(bar.actions()[1]) is not None


def test_the_palette_has_the_elements_the_connections_and_help(win):
    from PySide6.QtCore import Qt
    wb = _wb(win)
    for key, text in (("column", "Column"), ("beam", "Beam"), ("slab", "Slab"),
                      ("wall", "Wall"), ("footing", "Footing")):
        assert wb.buttons[key].text() == text
    conns = importlib.import_module("ingetrazo_plugin_sipilbim.connections")
    assert len(conns.CONNECTIONS) >= 8
    for key, label, _kind in conns.CONNECTIONS:
        b = wb.buttons[key]
        assert b.text() == label                          # a column: every label
        assert b.accessibleName() == label and label in b.toolTip()
        assert not b.icon().isNull()
    from PySide6.QtWidgets import QPushButton
    help_btn = wb.palette.help_button
    assert help_btn in wb.palette.findChildren(QPushButton)
    assert help_btn.text() == "Help" and not help_btn.icon().isNull()
    assert help_btn.toolTip()
    wb.palette.set_orientation(Qt.Horizontal)             # in a row: icon only
    assert [wb.buttons[k].text() for k, *_ in conns.CONNECTIONS] == [""] * len(conns.CONNECTIONS)
    assert help_btn.text() == ""


def test_help_opens_a_message_box(win, monkeypatch):
    from PySide6.QtWidgets import QMessageBox, QPushButton
    shown = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: shown.append(self.text()) or 0)
    next(b for b in _wb(win).palette.findChildren(QPushButton)
         if b.accessibleName() == "Help").click()
    assert shown and "Building Elements" in shown[0]


def test_only_the_column_works_the_rest_are_greyed_out(win):
    wb = _wb(win)
    working = [e.key for e in wb.elements + wb.connections if e.implemented]
    assert working == ["column"]
    assert wb.buttons["column"].isCheckable()
    assert wb.buttons["column"].property("ready") == "true"
    others = [k for k in wb.buttons if k != "column"]
    assert not any(wb.buttons[k].isCheckable() for k in others)
    assert all(wb.buttons[k].property("ready") == "false" for k in others)


def test_an_empty_button_only_says_it_is_not_available(win, monkeypatch):
    vp = win.viewport
    wb = _wb(win)
    said = []
    monkeypatch.setattr(type(vp), "flash_status",
                        lambda self, text, ms=0: said.append(text))
    tool_before = vp.active_tool
    n_groups = len(vp.scene.groups)
    version = vp.scene.version
    for key in ("beam", "slab", "wall", "footing", "base_plate", "bolted",
                "welded", "bracing"):
        wb.buttons[key].click()
    assert len(said) == 8 and all("not available yet" in s for s in said)
    assert vp.active_tool is tool_before
    assert len(vp.scene.groups) == n_groups and vp.scene.version == version


def test_there_is_one_properties_form_for_new_and_existing_elements(win):
    from PySide6.QtWidgets import QLineEdit
    _p, widgets, _e = _mods()
    panel = _wb(win).panel
    assert len(panel.findChildren(widgets.PropertiesForm)) == 1
    # the Name field lives in that one form: a single QLineEdit in the tab
    assert len(panel.findChildren(QLineEdit)) == 1
    assert panel.form.isAncestorOf(panel.form.name_edit)


def test_with_nothing_selected_and_no_tool_only_the_hint_shows(win):
    vp = win.viewport
    panel = _wb(win).panel
    _select(vp)
    vp.set_active_tool(None)
    _refresh(win)
    assert panel.hint.isVisibleTo(panel)
    assert not panel.form.isVisibleTo(panel)


def test_the_column_button_arms_the_tool_and_shows_the_defaults(win):
    vp = win.viewport
    wb = _wb(win)
    form = wb.panel.form
    tool = wb.elements[0].tool()
    wb.buttons["column"].click()
    assert vp.active_tool is tool
    assert wb.buttons["column"].isChecked()
    assert form.isVisibleTo(wb.panel) and not wb.panel.hint.isVisibleTo(wb.panel)
    # the same fields as for an existing column — Element, Name, then the rest
    assert form.element_label.text() == "Column"
    assert form.name_edit.text() == "K1" and not form.name_edit.isEnabled()
    assert "next column" in form.status.text()
    wb.buttons["column"].click()
    assert vp.active_tool is not tool and not wb.buttons["column"].isChecked()


def test_selecting_a_column_shows_element_and_name_and_editing_is_one_undo_step(win):
    vp = win.viewport
    kb.place_column(vp, V(2, 3, 0), {"params": dict(kb.DEFAULTS)})
    g = _columns(vp)[0]
    wb = _wb(win)
    form = wb.panel.form
    _select(vp, g)
    _refresh(win)
    assert form.isVisibleTo(wb.panel) and not wb.panel.hint.isVisibleTo(wb.panel)
    assert form.element_label.text() == "Column"
    assert form.name_edit.isEnabled() and form.name_edit.text() == "K1"
    assert form.status.text() == ""
    assert (form.field("height").value(), form.field("width").value()) == (3000, 300)
    form.field("height").setValue(4500)
    assert kb.column_data(g)["params"]["height"] == pytest.approx(4.5)
    assert form.field("height").value() == 4500
    vp.history.undo()
    assert kb.column_data(g)["params"]["height"] == pytest.approx(3.0)


def test_the_property_rows_have_professional_english_labels(win):
    wb = _wb(win)
    wb.buttons["column"].click()
    form = wb.panel.form
    rows = form._form
    from PySide6.QtWidgets import QFormLayout
    labels = [rows.itemAt(i, QFormLayout.ItemRole.LabelRole).widget().text()
              for i in range(rows.rowCount())]
    assert labels == ["Element", "Name", "Cross-section", "Width (X)",
                      "Depth (Y)", "Diameter", "Height", "Rotation"]
    assert [form.field("shape").itemText(i) for i in range(2)] == [
        "Rectangular", "Circular"]


def test_changing_the_shape_rebuilds_and_swaps_the_rows(win):
    vp = win.viewport
    kb.place_column(vp, V(0, 0, 0), {"params": dict(kb.DEFAULTS)})
    g = _columns(vp)[0]
    wb = _wb(win)
    form = wb.panel.form
    _select(vp, g)
    _refresh(win)
    assert form.is_row_shown("width") and not form.is_row_shown("diameter")
    form.field("shape").setCurrentIndex(1)
    assert kb.column_data(g)["params"]["shape"] == "round"
    assert form.is_row_shown("diameter") and not form.is_row_shown("width")
    assert not form.is_row_shown("rotation")


def test_with_several_columns_only_the_edited_field_is_applied_to_all(win):
    vp = win.viewport
    kb.place_column(vp, V(0, 0, 0), {"params": dict(kb.DEFAULTS)})
    kb.place_column(vp, V(5, 0, 0), {"params": dict(
        kb.DEFAULTS, shape="round", diameter=0.5)})
    a, b = _columns(vp)
    wb = _wb(win)
    form = wb.panel.form
    _select(vp, a, b)
    _refresh(win)
    assert form.element_label.text() == "Column (2 selected)"
    assert not form.name_edit.isEnabled() and form.name_edit.text() == ""
    assert "all 2 selected columns" in form.status.text()
    form.field("height").setValue(5000)
    pa, pb = (kb.column_data(g)["params"] for g in (a, b))
    assert pa["height"] == pytest.approx(5.0) == pytest.approx(pb["height"])
    assert (pa["shape"], pb["shape"]) == ("rect", "round")
    assert pb["diameter"] == pytest.approx(0.5)


def test_with_the_tool_armed_and_nothing_selected_the_form_sets_the_next_column(win):
    vp = win.viewport
    wb = _wb(win)
    form = wb.panel.form
    _select(vp)
    wb.buttons["column"].click()
    form.field("shape").setCurrentIndex(1)
    form.field("diameter").setValue(500)
    form.field("height").setValue(4000)
    wb.elements[0].tool().on_click(
        SimpleNamespace(viewport=vp, world=V(1, 1, 0)))
    p = kb.column_data(_columns(vp)[-1])["params"]
    assert (p["shape"], p["diameter"], p["height"]) == ("round", 0.5, 4.0)


def test_renaming_from_the_panel_updates_the_column_and_its_ifc_name(win):
    vp = win.viewport
    kb.place_column(vp, V(0, 0, 0), {"params": dict(kb.DEFAULTS)})
    g = _columns(vp)[0]
    form = _form(win)
    _select(vp, g)
    _refresh(win)
    form.name_edit.setText("KB-9")
    form.name_edit.editingFinished.emit()
    assert g.name == "KB-9" and g.ifc["name"] == "KB-9"
    assert form.name_edit.text() == "KB-9"


def test_the_form_is_generic_a_new_element_needs_no_new_form(win):
    """An element that only declares a property schema gets a working form."""
    _p, _w, els = _mods()
    seen = {}

    class Beam(els.Element):
        key, label, plural, implemented = "beam2", "Beam", "Beams", True

        def __init__(self):
            super().__init__()
            self.state = {"params": {"span": 6.0, "kind": "i"}}

        def properties(self):
            return (els.choice("kind", "Profile", (("i", "I-section"),
                                                   ("box", "Box"))),
                    els.length("span", "Span", 0.5, 30.0, step=100.0),
                    els.length("flange", "Flange", 0.01, 1.0,
                               when=lambda v: v["kind"] == "i"))

        def default_params(self):
            return dict(self.state["params"], flange=0.2)

        def params_of(self, group):
            return dict(self.default_params())

        def next_name(self, scene):
            return "B1"

        def modify(self, viewport, groups, changes, name=None):
            seen.update(changes, name=name, n=len(groups))
            return True

    form = _form(win)
    form.load(Beam(), [])
    assert form.element_label.text() == "Beam" and form.name_edit.text() == "B1"
    assert form.field("span").value() == 6000 and form.field("span").suffix() == " mm"
    assert form.is_row_shown("flange")
    form.field("kind").setCurrentIndex(1)
    assert not form.is_row_shown("flange")
    g = SimpleNamespace(name="B7")
    form.load(form._element, [g])
    form.field("span").setValue(8000)
    assert seen == {"span": pytest.approx(8.0), "name": None, "n": 1}


def test_right_click_offers_properties_only_on_a_column(win):
    vp = win.viewport
    labels = lambda: [a.text() for m in [QMenu()] for fn in win._ext_context_menus  # noqa: E731
                      if not fn(m, list(vp.scene.selection))
                      for a in m.actions() if a.text()]
    _select(vp)
    assert labels() == []
    _select(vp, *vp.scene.groups)                    # built-in figure, not a column
    assert labels() == []
    kb.place_column(vp, V(0, 0, 0), {"params": dict(kb.DEFAULTS)})
    assert "Column properties…" in labels()
    kb.place_column(vp, V(5, 0, 0), {"params": dict(kb.DEFAULTS)})
    _select(vp, *_columns(vp))
    assert "Properties of 2 columns…" in labels()


def test_right_click_properties_brings_the_sipilbim_tab_to_the_front(win, monkeypatch):
    vp = win.viewport
    kb.place_column(vp, V(0, 0, 0), {"params": dict(kb.DEFAULTS)})
    dock = _dock(win)
    shown = []
    monkeypatch.setattr(win, "set_tray_shown",
                        lambda d, on=True: shown.append((d, on)))
    menu = QMenu()
    for fn in win._ext_context_menus:
        fn(menu, list(vp.scene.selection))
    next(a for a in menu.actions() if a.text() == "Column properties…").trigger()
    _app.processEvents()
    assert (dock, True) in shown


def test_right_click_properties_unfolds_the_sidebar_and_shows_the_tab(win):
    vp = win.viewport
    kb.place_column(vp, V(0, 0, 0), {"params": dict(kb.DEFAULTS)})
    dock = _dock(win)
    win._act_sidebar.setChecked(False)                            # folded (Ctrl+F5)
    _app.processEvents()
    assert dock.isHidden() and not win._act_sidebar.isChecked()
    menu = QMenu()
    for fn in win._ext_context_menus:
        fn(menu, list(vp.scene.selection))
    next(a for a in menu.actions() if a.text() == "Column properties…").trigger()
    _app.processEvents()
    assert win._act_sidebar.isChecked() and not dock.isHidden()


def test_the_extensions_menu_has_a_sipilbim_submenu(win):
    sub = next(a.menu() for a in win._ext_menu.actions()
               if a.menu() is not None and a.text() == "SipilBIM")
    texts = [a.text() for a in sub.actions()]
    assert "Place column" in texts and "Show SipilBIM panel" in texts
    assert "Building Elements" in texts              # show / hide the palette


def test_a_column_is_read_and_edited_from_its_group_data(win):
    """A column keeps its data in group.ext under its element key."""
    vp = win.viewport
    kb.place_column(vp, V(0, 0, 0), {"params": dict(kb.DEFAULTS)})
    g = _columns(vp)[0]
    assert list(g.ext) == ["column"] and kb.KEY == "column"
    assert kb.outliner_kind(g)["type"] == "Column"
    _select(vp, g)
    _refresh(win)
    wb = _wb(win)
    assert wb.panel.form.isVisibleTo(wb.panel)


def test_the_old_plugin_being_loaded_triggers_a_warning(monkeypatch):
    monkeypatch.setitem(sys.modules, "ingetrazo_plugin_kolom_beton", object())
    monkeypatch.setattr(extensions, "plugin_dirs", lambda: [PKG_DIR])
    import views.viewport as vpmod
    said = []
    monkeypatch.setattr(vpmod.Viewport, "flash_status",
                        lambda self, text, ms=0: said.append(text))
    from views.main_window import MainWindow
    w = MainWindow()
    try:
        assert any("kolom_beton.py" in s for s in said)
    finally:
        w._saved_version = w.viewport.scene.version
        w.close()


# ---- packaging ------------------------------------------------------------

def test_the_build_spec_ships_the_package_folder_and_scans_its_imports():
    spec = (REPO / "sipilbim.spec").read_text(encoding="utf-8")
    assert "('plugins/sipilbim'" in spec
    assert "('plugins/structure'" not in spec
    assert "Path('plugins').rglob('*.py')" in spec


def test_the_old_names_are_gone_so_there_is_one_column_tool():
    assert not (REPO / "plugins" / "kolom_beton.py").exists()
    assert not (REPO / "plugins" / "structure").exists()
    assert (REPO / "plugins" / "sipilbim" / "__init__.py").is_file()
    assert not (REPO / "plugins" / "sipilbim" / "column_form.py").exists()
