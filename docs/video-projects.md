# Proyek video lokal yang dapat disunting

Ubah satu adegan tanpa merender ulang seluruh episode. CLI opt-in ini
membuat snapshot footage dan narasi lokal yang sudah disiapkan, mencatat revisi yang tidak dapat diubah, dan
memakai ulang artefak hanya jika dependensi dan integritas SHA-256-nya sama-sama cocok.
CLI ini tidak memanggil API dan tidak memublikasikan video. Job pembuatan yang ada dan
perilaku WebUI tidak berubah.

Ini adalah fondasi revisi/artefak untuk usulan scene/director yang sudah ada,
bukan alur director atau penyedia berbayar yang baru. Buat/unduh dulu
footage dan narasi memakai pipeline tugas yang ada atau alat pilihan Anda.
Gunakan path keluaran lokalnya di bawah. Pertahankan ID adegan saat mengganti medianya;
ubah urutan di manifes untuk mengatur ulang urutan video.

## Persyaratan

Python 3.11 atau lebih baru serta FFmpeg/FFprobe di PATH, termasuk encoder `libx264`.
Masukan yang disiapkan harus berupa media ter-encode mandiri: MOV/MP4, Matroska/WebM, AVI,
MPEG-TS/video, Ogg, FLV, WAV, MP3, FLAC, atau AAC. Playlist HLS/DASH/concat dan
media dengan referensi eksternal ditolak; menyalin playlist saja tidak akan membuat snapshot
segmen yang dirujuknya. Concat hanya diizinkan untuk daftar perakitan yang dibuat secara internal.
Protokol jaringan dinonaktifkan untuk semua masukan render.
Tidak ada dependensi Python baru. Proyek adalah penyimpanan lokal satu host;
filesystem jaringan dengan penguncian yang tidak andal tidak didukung. Sediakan disk yang cukup
untuk snapshot sumber, revisi yang dipertahankan, dan ekspor. Tidak ada pemangkasan
artefak otomatis atau penghapusan ekspor sukses yang lebih lama.

## Membuat, memeriksa, dan merender

Simpan `episode.json` di samping aset yang sudah disiapkan:

```json
{
  "project_id": "product-episode",
  "settings": {
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "narration_volume": 1.0,
    "bgm_volume": 0.15
  },
  "scenes": [
    {
      "id": "opening",
      "footage": "opening.mp4",
      "audio": "opening.wav",
      "narration": "Introduce the product."
    },
    {
      "id": "product-detail",
      "footage": "detail.mp4",
      "duration": 5
    }
  ],
  "bgm": "music.mp3"
}
```

```sh
python -m app.services.video_project --project storage/projects/product-episode revise episode.json
python -m app.services.video_project --project storage/projects/product-episode plan
python -m app.services.video_project --project storage/projects/product-episode render
python -m app.services.video_project --project storage/projects/product-episode status
```

Path aset relatif di-resolve terhadap direktori manifes. Sumber disalin
ke dalam proyek; mengedit file asli di kemudian hari tidak diam-diam mengubah
revisi. ID revisi yang dicetak oleh `revise` mengidentifikasi snapshot masukan yang tidak
dapat diubah. `status` melaporkan tahap yang selesai, artefak yang dipakai ulang, kegagalan, dan
path ekspor. `project.json` menunjuk ke revisi saat ini dan ekspor sukses terakhir,
yang dipertahankan sampai revisi saat ini yang lebih baru berhasil.

Audio menentukan durasi adegan yang bernarasi. Adegan senyap memakai `duration`
(default lima detik). Footage pendek diulang; footage panjang dipotong. Audio video
sumber sengaja diganti dengan narasi yang disiapkan atau keheningan.
Semua keluaran adegan memakai dimensi, frame rate, dan audio stereo 48kHz yang sama.
Mix BGM akhir mengulang musik sampai durasi timeline dan tidak menormalisasi
narasi hingga hilang. Volume BGM nol menghasilkan ekspor tanpa mix.

`narration` adalah teks asal-usul, bukan permintaan TTS. Saat mengubah narasi, sediakan juga
audio yang baru disiapkan; CLI tidak dapat memverifikasi bahwa rekaman itu mengucapkan
teksnya. Subtitle yang selaras kata, transisi, overlay, dan pembuatan oleh penyedia
tidak diimplementasikan oleh renderer lokal pertama ini. Tahap timing mencatat durasi,
bukan keselarasan kata yang dihasilkan.

## Mengganti, membandingkan, dan memakai ulang

Edit hanya field adegan/BGM yang terdampak, lalu jalankan `revise` lagi dengan
`project_id` dan ID adegan yang sama. Gunakan ID lama dan baru yang dicetak untuk membandingkan:

```sh
python -m app.services.video_project --project storage/projects/product-episode compare OLD_REVISION NEW_REVISION
python -m app.services.video_project --project storage/projects/product-episode plan
python -m app.services.video_project --project storage/projects/product-episode render
```

| Perubahan | Tahap yang dibangun ulang |
|---|---|
| Footage satu adegan | Render adegan itu, perakitan, dan ekspor akhir |
| Narasi/audio satu adegan | Normalisasi audio, timing, dan render adegan itu; perakitan dan ekspor |
| File atau volume BGM | Hanya mix/ekspor akhir |
| Urutan adegan | Hanya perakitan dan ekspor |
| Dimensi/frame rate | Render adegan, perakitan, dan ekspor |
| Volume narasi | Audio, timing, adegan, perakitan, dan ekspor |
| Versi alat FFmpeg/kontrak renderer | Revisi baru dibangun ulang di bawah sidik jari transformasi yang berubah |

Rencana menjelaskan dependensi yang berubah, artefak selesai yang hilang, dan kegagalan
integritas. Artefak yang rusak dibangun ulang dari snapshot yang terverifikasi. Snapshot
sumber yang rusak gagal secara tertutup: buat revisi baru dari media asli yang sudah disiapkan.
Cache tetap berada di dalam satu proyek; proyek lain tidak dapat memakainya secara implisit.
Tidak ada persentase penghematan atau jaminan idempotensi pembuatan berbayar.

## Pembatalan, kegagalan, dan revisi bersamaan

```sh
python -m app.services.video_project --project storage/projects/product-episode cancel
python -m app.services.video_project --project storage/projects/product-episode render --retry
```

Permintaan pembatalan menghentikan subproses media yang aktif dan mencegah promosi.
`--retry` yang eksplisit diperlukan setelah render yang gagal, dibatalkan, atau terputus.
Tahap terverifikasi yang sudah selesai tetap dapat dipakai ulang. Crash proses dapat meninggalkan status
`running`; retry memeriksa ulang artefak alih-alih menganggapnya selesai. Direktori `.work`
sementara yang belum di-commit akibat proses mati mendadak boleh dihapus saat
tidak ada render yang aktif. Direktori itu tidak pernah menjadi sumber artefak yang dapat dipercaya untuk dipakai ulang.

Hanya satu renderer yang menulis sebuah revisi pada satu waktu. Revisi yang berbeda dapat dirender
bersamaan dan berbagi artefak selesai yang tidak dapat diubah. Jika revisi yang lebih baru
dibuat saat yang lebih lama dirender, revisi lama boleh selesai untuk perbandingan,
tetapi tidak dapat menggantikan ekspor sukses terakhir proyek saat ini. Kunci OS dilepas
setelah proses mati. Setiap perintah media eksternal memiliki tenggat terbatas (600
detik secara default, dapat diatur dengan `render --stage-timeout`).

Manifes dan catatan artefak memakai penggantian berkas atomik. Byte artefak
dipublikasikan sebelum catatan commit; penulisan yang tidak lengkap tidak pernah dipercaya. Sidik
jari mencakup kontrak renderer, versi FFmpeg/FFprobe, pengaturan terkait, dan hash
konten. Field manifes/pengaturan yang tidak dikenal ditolak, termasuk
kredensial penyedia. Simpan hanya konten narasi publik di sini; tidak ada
perangkat lunak yang dapat menyimpulkan apakah teks tulisan pengguna berisi rahasia.

## Pengaturan render episode/merek yang dapat dipakai ulang

```sh
python -m app.services.video_project --project storage/projects/product-episode save-preset brand-render.json
python -m app.services.video_project --project storage/projects/next-episode revise next-episode.json --preset brand-render.json
```

Preset memakai ulang dimensi, frame rate, dan volume narasi/BGM. Preset tidak berisi
aset, ID proyek, kredensial, pilihan penyedia, atau klaim karakter buatan AI yang konsisten.
Preset yang diberikan menggantikan pengaturan manifes.
Aset adegan dan narasi tetap eksplisit untuk setiap episode.

## Batas integrasi

`VideoProject.create_revision`, `plan`, `render`, `status`, dan `compare` menyediakan
kontrak media-yang-disiapkan yang sama dengan CLI. Director yang nanti diterima dapat meneruskan
path narasi/footage yang sudah selesai, mempertahankan ID adegan, dan memakai
tanda terima ekspor/revisi tanpa mengubah kepemilikan penyedia. Catatan
creative-outcome yang ada dapat merujuk ID revisi yang selesai tanpa memperkenalkan publikasi
otomatis atau memperlakukan performa observasional sebagai bukti kausal.
