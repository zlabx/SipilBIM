# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 SipilStock.
"""SipilBIM — building elements (columns, beams, slabs, connections…).

The extension is a package: SipilBIM calls :func:`setup` when the main window
is built. The user interface (``panel.py``) is only imported then, so the
geometry modules (``column.py``) stay pure Python.

Layout of the interface:

* **Top** — the «Building Elements» and «Connections» palette
  (``palette.py``), one button per element, in a toolbar row of its own that
  can be dragged to any side.
* **Right** — the «SipilBIM» side-tray tab (closed until needed) with two
  collapsible sections,
  *Model* (empty for now) and *Properties* (``widgets.py``): a form built from
  the selected element's property schema (``elements.py``).

Today only the concrete column works. Beams, slabs, walls, footings and the
connections are greyed-out placeholders.
"""
__version__ = "0.2"


def setup(app) -> None:
    from .panel import setup as _setup
    _setup(app)
