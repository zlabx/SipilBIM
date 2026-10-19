# Perubahan terhadap upstream

Dasar: [ingelibre/ingetrazo](https://github.com/ingelibre/ingetrazo), versi `0.5.8`,
commit `e5c016e5df74a18204b785edd0a8401300cb4353` (GPL-3.0-or-later). Build ini: **SipilBIM 2027.2**.

Semua perubahan dibuat oleh satu skrip yang bisa diulang, `rebrand/ingetrazo/` di
[zlabx/Apps](https://github.com/zlabx/Apps/tree/main/rebrand/ingetrazo), dijalankan pada checkout upstream
yang bersih. Hasilnya di-commit apa adanya ke repo ini. Hak cipta dan pemberitahuan lisensi upstream
(`LICENSE`, `AUTHORS`, baris `Copyright` dan `SPDX` di setiap berkas) tidak diubah.

## Yang diganti

- **Nama produk**: "IngeTrazo" menjadi "SipilBIM" di teks antarmuka, terjemahan (`i18n/*.json`, kunci dan nilai
  bersama-sama), jendela, dialog, dan pesan.
- **Berkas dan identitas Windows**: `sipilbim.exe`, `sipilbim-mcp.exe`, `dist/sipilbim`, `sipilbim.spec`,
  `installer/sipilbim.iss`, `sipilbim-setup-v<versi>.exe`, nama log (`sipilbim-errors.log`,
  `sipilbim-gl.txt`), soket instance tunggal, nama server MCP (`sipilbim`), nama berkas ekspor pintasan.
  Folder data dan log mengikuti nama aplikasi (`%LOCALAPPDATA%\SipilBIM`, kunci pengaturan SipilBIM).
- **Installer**: `AppId` baru (SipilBIM terpasang sebagai produk sendiri dan tidak menimpa IngeTrazo),
  penerbit `SipilStock`, URL situs, dukungan, dan pembaruan mengarah ke repo ini. ProgID dokumen menjadi
  `SipilBIM.Document`.
- **Format dokumen**: SipilBIM menyimpan dan membuka `.sbim` (sebelumnya `.igz`). Isinya sama dengan `.igz`
  (JSON, atau ZIP bila ada tekstur): berkas `.sbim` yang diganti nama menjadi `.igz` terbuka di IngeTrazo, dan
  sebaliknya. `.igz` tidak ada di dialog Buka/Simpan dan tidak lagi diasosiasikan oleh installer; Windows tidak lagi
  mengaitkannya dengan SipilBIM, sehingga IngeTrazo yang terpasang berdampingan tetap memegang `.igz`. Berkas contoh
  dan komponen pustaka bawaan diganti namanya ke `.sbim`.
- **User-Agent** permintaan jaringan (tile peta, geokode, pustaka): `SipilBIM/<versi> (...; based on IngeTrazo)`,
  supaya lalu lintas build ini tidak tercatat atas nama upstream.
- **Tema default**: terang (upstream membuka gelap). Tema gelap dan "Same as the system" tetap bisa dipilih di Window ▸ Preferences ▸ Theme;
  pilihan yang sudah tersimpan tidak berubah.
- **Dialog About**: dibuat singkat seperti app SipilStock lain: ikon, nama dan versi, satu kalimat tentang app, dan tautan
  Upstream (IngeTrazo), License, dan Source (repo ini). Daftar kontributor yang bergulir dan baris OpenGL dihapus dari dialog
  (daftarnya tetap ada di kode dan di `AUTHORS`; hak cipta dan lisensi tidak berubah).
- **Ikon**: set ikon SipilBIM (app, `.ico`, `.icns`, PNG) dan ikon dokumen `.sbim/.dae/.skp` dengan logo SipilBIM
  di sudutnya; batang judul ikon dokumen `.sbim` bertuliskan "SBIM".
- **Versi**: `0.5.8` menjadi `2027.2` (SipilBIM memakai skema versinya sendiri).
- **Workflow**: hanya `build-windows.yml` yang dipertahankan; `ci.yml`, `release*.yml` dihapus (Linux/macOS tidak
  dibangun di sini). Langkah tanda tangan SignPath di dalamnya **nonaktif** (organisasi SignPath milik upstream).
  Hanya installer yang dibangun dan dilampirkan ke Release: langkah `Incluir LEEME en el bundle` dan `Crear ZIP portable` dibuang
  (tidak ada ZIP portabel; `LEEME.txt` upstream berisi petunjuk mode portable).
  `actions/upload-artifact` dinaikkan dari v4 ke v7 dan `softprops/action-gh-release` dari v2 ke v3 (keduanya berpindah dari Node 20 ke
  Node 24; GitHub memaksa Node 24 dan menampilkan peringatan deprecation untuk versi lama).
- **Ditambahkan**: `README.md` (README upstream dipindah ke `README.upstream.md`), berkas ini, dan `site/`
  (halaman unduhan untuk https://sipilstock.com/sipilbim/).

## Yang sengaja tidak diubah

- Isi format dokumen: kunci `igz_format` di dalam berkas dan nama modul `formats.igz` tetap (hanya ekstensinya yang
  berubah). Tag `generator` pada GLB/glTF juga tetap, supaya pembaca mengenalinya.
- Variabel lingkungan `INGETRAZO_*`, nama logger `ingetrazo.plugins` dan `ingetrazo.extensions`, tipe MIME
  `application/x-ingetrazo-*`, dan folder plugin pengguna `%APPDATA%\ingetrazo\plugins` (plugin untuk IngeTrazo tetap
  berlaku; dokumentasi API plugin upstream tetap akurat).
- Layanan yang dijalankan upstream dan dipakai app apa adanya: katalog Ekstensi
  (`raw.githubusercontent.com/ingelibre/ingetrazo-extensions`) dan pustaka komponen daring (`ingetrazo.com/biblioteca`).
- `docs/`, `packaging/` (Flatpak, AppImage, macOS, snap), `resources/mime/`, dan semua berkas `*.md` upstream.
  Berkas Linux/macOS tersebut tidak dibangun di repo ini dan masih memakai nama IngeTrazo.
