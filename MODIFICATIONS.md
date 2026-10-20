# Modifications

SipilBIM is derived from [IngeTrazo](https://github.com/ingelibre/ingetrazo) 0.5.8
(commit `e5c016e5df74a18204b785edd0a8401300cb4353`, GPL-3.0-or-later). This build is SipilBIM 2027.3.
All changes are made by the rebrand script [`rebrand/ingetrazo`](https://github.com/zlabx/Apps/tree/main/rebrand/ingetrazo)
run on a clean upstream checkout; upstream copyright and licence notices are kept.

- Product name replaced in 231 source, packaging, CI, test and translation files
  (`*.py`, `*.iss`, `*.spec`, `*.yml`, `*.qss`, `i18n/*.json`; not `docs/`, `packaging/`, `vendor/`):
  "IngeTrazo" to "SipilBIM", `.igz` to `.sbim`, and the executable, installer, icon, log, socket,
  MCP server and shortcut-export file names. Copyright and SPDX lines, the GLB/glTF `generator` tag
  and upstream contributor credits are left as written.
- Version `0.5.8` to `2027.3`. Network user agents (`core/version.py`, `georef/geocode.py`,
  `georef/tile_fetcher.py`) read `SipilBIM/<version> (+https://sipilstock.com/sipilbim/; based on IngeTrazo)`.
- About dialog (`views/about_dialog.py`) reduced to name, version, one line and License and Source links;
  the contributors list stays in the code, unused.
- Default theme is light (`views/theme.py`); dark and system stay selectable and saved choices are unchanged.
- Installer (`installer/sipilbim.iss`): new `AppId` (installs alongside IngeTrazo), publisher `SipilStock`,
  website, support and update URLs point to `zlabx/SipilBIM`.
- `.github/workflows/`: only `build-windows.yml` is kept; removed `ci.yml`, `release-flatpak.yml`, `release-macos.yml`, `release.yml`.
  It points to this repository, marks the SignPath signing steps as inactive, moves
  `actions/upload-artifact` v4 to v7 and `softprops/action-gh-release` v2 to v3 (Node 24),
  and drops the portable ZIP (installer only).
- Renamed: `ingetrazo.spec` and the installer script to `sipilbim.*`, and 12 bundled `.igz` documents
  (examples, library components) to `.sbim`. The `.sbim` format is the same JSON/ZIP as `.igz`.
- Icon set replaced (`resources/icons/`: app icon, `.dae`/`.skp`/document icons, `hicolor` PNGs); the
  `.sbim` document icon carries an "SBIM" title bar.
- `pytest.ini`: 7 tests deselected (they need files this repository does not carry, or assume
  upstream's dark theme, About credits or version).

Left as upstream: the `igz_format` key and `formats.igz` module (documents stay interchangeable by renaming),
`INGETRAZO_*` variables and `ingetrazo.*` logger names, the extensions catalogue and online component library
hosted by upstream, and everything under `docs/`, `packaging/` and `vendor/`.

Added: `MODIFICATIONS.md`, `README.md`, `site/LICENSE.txt`, `site/index.html`. The upstream `README.md` is moved to `README.upstream.md`.
