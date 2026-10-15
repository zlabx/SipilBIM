# Perubahan terhadap upstream

Dasar: [ingelibre/ingetrazo](https://github.com/ingelibre/ingetrazo), tag `v0.5.8`,
commit `e5c016e5df74a18204b785edd0a8401300cb4353` (GPL-3.0-or-later).

Per 15 Oktober 2026, satu-satunya perbedaan dengan tag itu:

1. `README.md` diganti; README asli dipindahkan ke `README.upstream.md`.
2. Folder `.github/` hanya menyisakan `workflows/build-windows.yml` (tidak diubah).
   `ci.yml`, `release.yml`, `release-flatpak.yml`, `release-macos.yml`, dan `.gitkeep`
   dihapus karena repo ini hanya membangun installer Windows.
3. Ditambahkan `MODIFICATIONS.md` (berkas ini) dan folder `site/` (halaman unduhan
   untuk `sipilstock.com/sipilbim/`).

Kode aplikasi, sumber daya, dan tes tidak diubah. Hak cipta dan pemberitahuan lisensi
upstream dipertahankan (`LICENSE`, `AUTHORS`, header berkas).
