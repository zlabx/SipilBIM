# Modifications

SipilBIM is derived from IngeTrazo (https://github.com/ingelibre/ingetrazo),
GPL-3.0-or-later. Changes made by the rebrand overlay (GPL-3.0 section 5(a)):

- Product name, file extension and file names replaced in 250 source, packaging, CI, test and
  translation files; 14 files renamed (`ingetrazo.spec`, the installer script, 12 bundled
  documents to `.sbim`).
- App icon set replaced; the `.sbim` document icon carries an "SBIM" title bar.
- Upstream copyright, SPDX and licence notices (`LICENSE`, `AUTHORS`, header lines) are kept; the GLB/glTF
  `generator` tag and the credits for upstream contributors are left as written.
- Version set to 2027.5 (this build is based on IngeTrazo 0.5.9, commit `24e7ada6df9f0b4f5f761f287aaade9e40e6728c`).
  Network user agents read `SipilBIM/<version> (+https://sipilstock.com/sipilbim/; based on IngeTrazo)`.
- About dialog reduced to one page: name, version, a one-line description and the links to the licence
  and this repository; the contributors list stays in the code, unused.
- Default theme is light; dark and system stay selectable and saved choices are unchanged.
- Installer: new `AppId` (installs alongside IngeTrazo), publisher `SipilStock`, website, support and
  update URLs point to this repository.
- Workflows: only `build-windows.yml` is kept (removed `ci.yml`, `release-flatpak.yml`, `release-macos.yml`, `release.yml`). It marks the SignPath
  signing steps as inactive, moves `actions/upload-artifact` v4 to v7 and `softprops/action-gh-release`
  v2 to v3 (Node 24), and drops the portable ZIP (installer only).
- Tests: 7 deselected in `pytest.ini` (they need files this repository does not carry, or
  assume upstream's dark theme, About credits or version).
- Unchanged: the `igz_format` key and `formats.igz` module (`.sbim` is the same JSON/ZIP as `.igz`, so
  documents open in either app by renaming), `INGETRAZO_*` variables and `ingetrazo.*` logger names, the
  extensions catalogue and online component library hosted by upstream, and `docs/`, `packaging/`, `vendor/`.

Additional changes applied by the build after those substitutions:

- modified: `.github/workflows/build-windows.yml`
- modified: `core/version.py`
- modified: `georef/geocode.py`
- modified: `georef/tile_fetcher.py`
- modified: `installer/sipilbim.iss`
- modified: `pytest.ini`
- modified: `views/about_dialog.py`
- modified: `views/theme.py`
- added or replaced: `README.md`
- added or replaced: `site/favicon.svg`
- added or replaced: `site/icon.svg`
- added or replaced: `site/index.html`
- added or replaced: `site/screenshot.webp`
- added: `site/LICENSE.txt` (LICENSE, text unchanged)
- added: `README.upstream.md` (the upstream README, moved)

Changes made in this repository after the rebrand:

- added: `plugins/sipilbim/` (package extension: a «Building Elements» / «Connections» palette in a left toolbar and a
  «SipilBIM» side-tray tab with collapsible Model and Properties sections; Properties is one schema-driven form with the
  General properties Element and Name; the concrete column works — click-to-place, `IfcColumn` — and beams, slabs,
  walls, footings and connections are greyed-out buttons) and `tests/test_plugin_sipilbim.py`; `docs/plugins.md`
  lists it.
- modified: `sipilbim.spec` — the `plugins/sipilbim` folder is bundled as data and `plugins/` is scanned recursively
  for imports (the build only knew loose `plugins/*.py`).
- modified: `core/bim.py` — `collect_objects` now also returns `"faces"` (world space) for tagged groups, so the
  IFC export, the takeoff CSV and the BIM tray measure containers and component instances (their own `group.mesh`
  is empty) instead of skipping them.
