# Perubahan terhadap upstream

Dasar: [ingelibre/ingetrazo](https://github.com/ingelibre/ingetrazo), versi `0.5.8`,
commit `e5c016e5df74a18204b785edd0a8401300cb4353` (GPL-3.0-or-later). Build ini: **SipilBIM 0.5.8.1**.

Semua perubahan dibuat oleh satu skrip yang bisa diulang, `rebrand/ingetrazo/` di
[zlabx/Apps](https://github.com/zlabx/Apps/tree/main/rebrand/ingetrazo), dijalankan pada checkout upstream
yang bersih. Hasilnya di-commit apa adanya ke repo ini. Hak cipta dan pemberitahuan lisensi upstream
(`LICENSE`, `AUTHORS`, baris `Copyright` dan `SPDX` di setiap berkas) tidak diubah.

## Yang diganti

- **Nama produk**: "IngeTrazo" menjadi "SipilBIM" di teks antarmuka, terjemahan (`i18n/*.json`, kunci dan nilai
  bersama-sama), jendela, dialog, dan pesan.
- **Berkas dan identitas Windows**: `sipilbim.exe`, `sipilbim-mcp.exe`, `dist/sipilbim`, `sipilbim.spec`,
  `installer/sipilbim.iss`, `sipilbim-setup-v<versi>.exe`, `sipilbim-windows.zip`, nama log (`sipilbim-errors.log`,
  `sipilbim-gl.txt`), soket instance tunggal, nama server MCP (`sipilbim`), nama berkas ekspor pintasan.
  Folder data dan log mengikuti nama aplikasi (`%LOCALAPPDATA%\SipilBIM`, kunci pengaturan SipilBIM).
- **Installer**: `AppId` baru (SipilBIM terpasang sebagai produk sendiri dan tidak menimpa IngeTrazo),
  penerbit `SipilStock`, URL situs, dukungan, dan pembaruan mengarah ke repo ini. ProgID dokumen menjadi
  `SipilBIM.Document`.
- **Ikon**: set ikon SipilBIM (app, `.ico`, `.icns`, PNG) dan ikon dokumen `.igz/.dae/.skp` dengan logo SipilBIM
  di sudutnya.
- **User-Agent** permintaan jaringan (tile peta, geokode, pustaka): `SipilBIM/<versi> (...; based on IngeTrazo)`,
  supaya lalu lintas build ini tidak tercatat atas nama upstream.
- **Dialog About**: ditambah keterangan bahwa SipilBIM adalah build dari IngeTrazo, dengan tautan ke repo ini;
  kredit pembuat dan kontributor upstream dipertahankan.
- **Versi**: `0.5.8` menjadi `0.5.8.1` (revisi build SipilBIM di atas versi upstream).
- **Workflow**: hanya `build-windows.yml` yang dipertahankan; `ci.yml`, `release*.yml` dihapus (Linux/macOS tidak
  dibangun di sini). Langkah tanda tangan SignPath di dalamnya **nonaktif** (organisasi SignPath milik upstream).
- **Ditambahkan**: `README.md` (README upstream dipindah ke `README.upstream.md`), berkas ini, dan `site/`
  (halaman unduhan untuk https://sipilstock.com/sipilbim/).

## Yang sengaja tidak diubah

- Format berkas `.igz` dan tag `generator` pada GLB/glTF (supaya berkas upstream tetap terbaca dan sebaliknya).
- Variabel lingkungan `INGETRAZO_*`, nama logger `ingetrazo.plugins` dan `ingetrazo.extensions`, tipe MIME
  `application/x-ingetrazo-*`, dan folder plugin pengguna `%APPDATA%\ingetrazo\plugins` (plugin untuk IngeTrazo tetap
  berlaku; dokumentasi API plugin upstream tetap akurat).
- Layanan yang dijalankan upstream dan dipakai app apa adanya: katalog Ekstensi
  (`raw.githubusercontent.com/ingelibre/ingetrazo-extensions`) dan pustaka komponen daring (`ingetrazo.com/biblioteca`).
- `docs/`, `packaging/` (Flatpak, AppImage, macOS, snap), `resources/mime/`, dan semua berkas `*.md` upstream.
  Berkas Linux/macOS tersebut tidak dibangun di repo ini dan masih memakai nama IngeTrazo.
