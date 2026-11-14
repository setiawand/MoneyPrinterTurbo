# Paket Pemasangan pip dan Rilis PyPI

Nama paket rilis adalah `mpt`, sedangkan nama proyek tetap MoneyPrinterTurbo. Versi kode sumber saat ini `1.3.10`,
sudah dirilis di [PyPI](https://pypi.org/project/mpt/1.3.10/), dengan wheel dan sdist.
File yang sudah dirilis tidak dapat ditimpa; perubahan kode berikutnya harus menaikkan versi lalu dibangun dan diverifikasi ulang.

## Build dan Pemasangan

Memerlukan Python 3.11 atau lebih baru. Dependensi di-resolve dan dipasang bersama wheel; FFmpeg memprioritaskan versi
sistem, atau dapat memakai biner dari imageio-ffmpeg.

Pengguna memasang dari PyPI dan menjalankan:

```sh
python -m pip install mpt
mpt webui
mpt cli --help
```

Build dan verifikasi lokal:

```sh
uv build --out-dir storage/package/mpt-dist
python -m pip install ./storage/package/mpt-dist/mpt-1.3.10-py3-none-any.whl
mpt --help
mpt webui
mpt cli --help
```

Sebelum unggah resmi, pastikan akun PyPI, versi target, dan hash paket rilis, agar tidak memakai direktori
yang tercampur paket lama untuk unggah massal. Setiap rilis memerlukan otorisasi eksplisit dari pengguna, dan tidak
dirilis otomatis saat kode di-commit atau di-push.

## Pemeriksaan Sebelum Rilis

```sh
uvx twine check --strict \
  storage/package/mpt-dist/mpt-1.3.10-py3-none-any.whl \
  storage/package/mpt-dist/mpt-1.3.10.tar.gz
```

Periksa halaman deskripsi PyPI, metadata paket rilis, dan keterpasangan dependensi, lalu selesaikan pembuatan video di virtual environment baru.
Rilis resmi hanya dijalankan setelah unggahan diizinkan secara eksplisit; kata sandi akun, kode verifikasi, dan token API tidak ditulis ke repositori,
contoh perintah, atau log. README tiap bahasa menyediakan pintu masuk pemasangan bagi pengguna, sedangkan deskripsi PyPI dikelola terpisah di
`docs/pypi-description.md`; memperbarui dokumen repositori tidak otomatis mengubah halaman pengantar PyPI yang sudah dirilis.

`mpt webui` secara default hanya mendengarkan di `127.0.0.1`, memilih port kosong mulai dari 8501, dan membuka browser otomatis.
Gunakan `--host` dan `--port` untuk menentukan alamat, dan `--headless` agar browser tidak dibuka otomatis:

```sh
mpt webui --port 8503 --headless
```

CLI memakai ulang parameter `python cli.py`, pipeline tugas, kode keluar, dan keluaran JSON. Contoh offline lengkap:

```sh
mpt cli --video-script "A short video from local materials." \
  --video-source local --video-materials /absolute/path/clip.mp4 \
  --custom-audio-file /absolute/path/narration.wav \
  --no-subtitle-enabled --bgm-type none
```

Fitur online seperti naskah, materi, dan TTS tetap memerlukan konfigurasi, kunci, dan koneksi jaringan layanan terkait. Model Whisper
dimuat sesuai kebutuhan dan tidak dimasukkan ke wheel. Log CLI ditulis ke stderr, dan saat sukses stdout mengeluarkan JSON berisi path video.

## Konfigurasi dan Data

Menjalankan dari kode sumber tetap memakai direktori root proyek. Versi terpasang tidak bergantung pada direktori kerja saat ini, dan direktori runtime default-nya:

| Platform | Direktori runtime |
| --- | --- |
| macOS | `~/Library/Application Support/MoneyPrinterTurbo` |
| Windows | `%LOCALAPPDATA%\MoneyPrinterTurbo` |
| Linux | `$XDG_DATA_HOME/MoneyPrinterTurbo`, default `~/.local/share/MoneyPrinterTurbo` |

Direktori runtime dapat ditentukan secara eksplisit lewat `MPT_HOME` (versi kode sumber juga mendukungnya). Di dalamnya:

- `config.toml`: diinisialisasi pada peluncuran pertama dari templat tanpa kunci, dan peluncuran berikutnya tidak menimpa konfigurasi yang ada.
- `storage/tasks`: tugas dan video hasil; cache dan file unggahan lain ada di bawah `storage`.
- `resource/fonts`, `resource/songs`: sumber daya bawaan disalin pada pemakaian pertama, dan Anda dapat menambahkan file sendiri.
- `models`: tempat meletakkan model Whisper yang diunduh manual.

Sumber daya pengguna hanya melengkapi file yang hilang, dan peningkatan versi tidak menimpa file yang sudah ada. Paket pemasangan menyertakan dua font Mandarin default,
font Vietnam, dan musik latar bawaan; font cadangan `STHeitiLight.ttc` dan `MicrosoftYaHeiNormal.ttc`
tidak masuk ke paket rilis untuk menekan ukuran file. Jika memerlukan ketebalan font tersebut, letakkan di `resource/fonts` pada direktori runtime.
Sumber daya dan tampilan asli versi kode sumber tidak berubah.

## Persyaratan Verifikasi Lokal

Bangun ulang wheel dari sdist, pasang ke virtual environment baru yang tidak mewarisi paket sistem, keluar dari direktori kode sumber, dan hapus
`PYTHONPATH`, lalu verifikasi `mpt cli --help`, halaman WebUI yang sebenarnya, dan pembuatan video. Video keluaran harus dapat didekode penuh oleh
FFmpeg, dan pastikan konfigurasi serta hasil tidak ditulis ke site-packages. Paket rilis tidak boleh memuat
`config.toml` lokal, kunci, cache, hasil tugas, atau instruksi kolaborasi lokal.
