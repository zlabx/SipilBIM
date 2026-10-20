# Modifications

SipilBIM is a modified version of [IngeTrazo](https://github.com/ingelibre/ingetrazo) 0.5.8
(commit `e5c016e5df74a18204b785edd0a8401300cb4353`, GPL-3.0-or-later). This build is **SipilBIM 2027.3**.

All changes are produced by a single repeatable script, [`rebrand/ingetrazo`](https://github.com/zlabx/Apps/tree/main/rebrand/ingetrazo),
run against a clean upstream checkout. The output is committed here unchanged. Upstream copyright and license
notices (`LICENSE`, `AUTHORS`, and the `Copyright` and `SPDX` lines in every file) are preserved.

## Changed

- **Branding**: "IngeTrazo" is replaced with "SipilBIM" in the UI, dialogs, messages, and translations (`i18n/*.json`).
- **Windows identity**: `sipilbim.exe`, `sipilbim-mcp.exe`, `sipilbim.spec`, `installer/sipilbim.iss`,
  `sipilbim-setup-v<version>.exe`, log names, single-instance socket, MCP server name, and the data folder
  (`%LOCALAPPDATA%\SipilBIM`).
- **Installer**: new `AppId`, so SipilBIM installs alongside IngeTrazo rather than replacing it. Publisher is
  `SipilStock`; website, support, and update links point to this repository. Document ProgID is `SipilBIM.Document`.
- **Document format**: SipilBIM saves and opens `.sbim` (previously `.igz`). The contents are identical, so a
  renamed file opens in either app. The installer does not associate `.igz`, leaving it to IngeTrazo if installed.
- **User-Agent**: network requests (map tiles, geocoding, library) identify as `SipilBIM/<version> (based on IngeTrazo)`.
- **Default theme**: light. Dark and system themes remain available; saved preferences are unaffected.
- **About dialog**: shortened to icon, name, version, one-line description, and License and Source links.
  IngeTrazo credit is kept in `README.md`, this file, and source headers; contributors remain in `AUTHORS`.
- **Icons**: SipilBIM app and `.sbim`/`.dae`/`.skp` document icons.
- **Version**: `0.5.8` to `2027.3`.
- **CI**: only `build-windows.yml` is kept; it builds the installer and attaches it to the Release. SignPath
  signing is disabled (the SignPath organization belongs to upstream), and the portable ZIP step is removed.
  `actions/upload-artifact` is updated to v7 and `softprops/action-gh-release` to v3 (Node 24).
- **Added**: `README.md` (upstream README moved to `README.upstream.md`), this file, and `site/`
  (download page for <https://sipilstock.com/sipilbim/>, with an unmodified copy of `LICENSE`).

## Unchanged

- Internal format identifiers: the `igz_format` key, the `formats.igz` module, and the GLB/glTF `generator` tag.
- Plugin and environment compatibility: `INGETRAZO_*` variables, `ingetrazo.*` logger names,
  `application/x-ingetrazo-*` MIME types, and the `%APPDATA%\ingetrazo\plugins` folder, so IngeTrazo plugins keep working.
- Upstream-hosted services used as-is: the extensions catalog (`ingelibre/ingetrazo-extensions`) and the online
  component library (`ingetrazo.com/biblioteca`).
- `docs/`, `packaging/` (Flatpak, AppImage, macOS, snap), `resources/mime/`, and all upstream `*.md` files.
  The Linux and macOS packaging is not built in this repository and still uses the IngeTrazo name.
