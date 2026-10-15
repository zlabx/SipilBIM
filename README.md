# SipilBIM

Build Windows dari **IngeTrazo**, pemodel 3D bebas untuk arsitektur dan teknik sipil,
yang disajikan SipilStock di <https://sipilstock.com/sipilbim/>.

Repo ini adalah salinan source upstream tanpa perubahan kode aplikasi. Nama yang tampil
di dalam aplikasi masih **IngeTrazo**; rebrand belum dikerjakan.

| | |
|---|---|
| Upstream | [ingelibre/ingetrazo](https://github.com/ingelibre/ingetrazo) |
| Versi | `v0.5.8` |
| Commit upstream | `e5c016e5df74a18204b785edd0a8401300cb4353` |
| Lisensi | GPL-3.0-or-later (lihat `LICENSE`) |

## Unduh

Installer dan ZIP portabel ada di halaman
[Releases](https://github.com/zlabx/SipilBIM/releases/latest):

- `ingetrazo-setup-vX.Y.Z.exe`: installer Windows
- `ingetrazo-windows.zip`: versi portabel

Build ini **belum ditandatangani**, jadi Windows SmartScreen bisa menampilkan peringatan
(More info, lalu Run anyway).

## Penandatanganan (rencana sebelum rilis publik)

Build saat ini belum ditandatangani (lihat peringatan SmartScreen di atas). Sebelum dipromosikan ke publik luas:

1. **Setelah rebrand dan ada pemeliharaan sendiri**, ajukan [SignPath Foundation](https://signpath.org/)
   (penandatanganan gratis untuk proyek open source). Syaratnya menekankan bahwa tim penanda tangan harus
   mengembangkan dan memelihara proyeknya sendiri; salinan tanpa perubahan dari upstream kemungkinan tidak
   memenuhi syarat. Bila diterima, repo ini wajib memuat bagian *Code signing policy*, daftar peran tim, dan
   pernyataan privasi.
2. **Cadangan:** sertifikat OV dari CA yang menyediakan penandatanganan cloud/HSM (sejak Juni 2023 kuncinya wajib
   di HSM atau token, jadi token USB tidak cocok untuk CI), atau paket MSIX lewat Microsoft Store.
3. Apa pun jalurnya, pakai **identitas penandatangan yang sama** di semua rilis agar reputasi SmartScreen
   menumpuk. Sertifikat EV tidak lagi memberi kelonggaran khusus.

Tanda tangan upstream (akun SignPath milik proyek IngeTrazo) tidak dapat dipakai untuk build ini.

## Cara build

Mendorong tag `v*` menjalankan `.github/workflows/build-windows.yml` (workflow upstream,
tidak diubah): PyInstaller, lalu Inno Setup, lalu lampiran ke Release. Langkah penandatanganan
SignPath di workflow itu dilewati otomatis karena repo ini tidak punya `SIGNPATH_API_TOKEN`.
Build manual: Actions, lalu *Build Windows*, lalu *Run workflow*.

## Berkas

- `README.upstream.md`: README asli IngeTrazo
- `MODIFICATIONS.md`: daftar perbedaan dengan upstream
- `site/`: halaman unduhan yang disajikan di `sipilstock.com/sipilbim/`
