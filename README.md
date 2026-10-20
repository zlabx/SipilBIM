# SipilBIM

Pemodel 3D bebas untuk arsitektur dan teknik sipil, disajikan SipilStock di <https://sipilstock.com/sipilbim/>.
Ini build Windows dari **IngeTrazo** dengan nama dan ikon SipilStock; kode aplikasinya tetap karya
Marco Sumari Tellez dan kontributor IngeTrazo.

| | |
|---|---|
| Versi | `2027.3` |
| Upstream | [ingelibre/ingetrazo](https://github.com/ingelibre/ingetrazo), versi `0.5.8` (commit `e5c016e`) |
| Lisensi | GPL-3.0-or-later (lihat `LICENSE`) |
| Perubahan | [`MODIFICATIONS.md`](MODIFICATIONS.md) |

## Unduh

Installer ada di halaman [Releases](https://github.com/zlabx/SipilBIM/releases/latest):

- `sipilbim-setup-v<versi>.exe`: installer Windows

Build ini **belum ditandatangani**, jadi Windows SmartScreen bisa menampilkan peringatan
(More info, lalu Run anyway).

## Penandatanganan (rencana sebelum rilis publik)

1. **Setelah ada perubahan dan pemeliharaan sendiri**, ajukan [SignPath Foundation](https://signpath.org/)
   (penandatanganan gratis untuk proyek open source). Syaratnya menekankan bahwa tim penanda tangan harus
   mengembangkan dan memelihara proyeknya sendiri, jadi build yang hanya ganti nama bisa ditolak. Bila diterima,
   repo ini wajib memuat bagian *Code signing policy*, daftar peran tim, dan pernyataan privasi.
2. **Cadangan:** sertifikat OV dari CA yang menyediakan penandatanganan cloud/HSM (sejak Juni 2023 kuncinya wajib
   di HSM atau token, jadi token USB tidak cocok untuk CI), atau paket MSIX lewat Microsoft Store.
3. Apa pun jalurnya, pakai **identitas penandatangan yang sama** di semua rilis agar reputasi SmartScreen
   menumpuk. Sertifikat EV tidak lagi memberi kelonggaran khusus.

Langkah SignPath di `.github/workflows/build-windows.yml` nonaktif: organisasi dan proyek yang tertulis di sana
milik upstream.

## Cara build

Mendorong tag `v<versi>` (sama dengan `core/version.py`, mis. `v2027.3`) menjalankan
`.github/workflows/build-windows.yml`: PyInstaller, lalu Inno Setup, lalu lampiran ke Release. Build manual:
Actions, lalu *Build Windows*, lalu *Run workflow*.

## Memperbarui dari upstream

Pohon ini dihasilkan, bukan diedit tangan. Untuk versi upstream baru: checkout tag upstream yang bersih, jalankan
`rebrand/ingetrazo/apply.sh <checkout> <sha upstream>` dari [zlabx/Apps](https://github.com/zlabx/Apps/tree/main/rebrand/ingetrazo),
salin hasilnya ke repo ini, commit, dan beri tag. Skrip berhenti dengan pesan jelas bila teks upstream yang
diandalkannya sudah berubah.

## Berkas

- `README.upstream.md`: README asli IngeTrazo
- `MODIFICATIONS.md`: daftar perbedaan dengan upstream
- `site/`: halaman unduhan yang disajikan di https://sipilstock.com/sipilbim/
