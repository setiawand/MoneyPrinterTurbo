# MoneyPrinterTurbo — Paket Python Resmi

**mpt adalah distribusi Python resmi dari
[MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo), dikelola oleh
[harry0703](https://pypi.org/user/harry0703/).**

Pasang paket resmi dengan **`python -m pip install mpt`**.
Paket bernama `MoneyPrinterTurbo` yang terpisah di PyPI adalah distribusi
pihak ketiga dan tidak dikelola oleh proyek ini.

MoneyPrinterTurbo membuat video pendek dari sebuah topik atau naskah yang sudah disiapkan.
Ia menggabungkan materi lokal atau online, narasi suara, subtitle, dan musik latar.
Gunakan WebUI secara interaktif atau jalankan pipeline video yang sama dari CLI.

## Pemasangan

Memerlukan Python 3.11 atau lebih baru. Virtual environment disarankan:

```sh
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install mpt
```

## Menjalankan WebUI

```sh
mpt webui
```

WebUI mendengarkan di localhost dan terbuka di browser Anda. Untuk memilih port atau menjalankan
tanpa membuka browser:

```sh
mpt webui --port 8503 --headless
```

## Membuat video dari CLI

```sh
mpt cli --help
mpt cli --video-script "Your complete script." \
  --video-source local --video-materials /absolute/path/clip.mp4 \
  --custom-audio-file /absolute/path/narration.wav \
  --no-subtitle-enabled --bgm-type none
```

Gambar dan video lokal didukung. Model bahasa online, media stok,
dan penyedia suara memerlukan konfigurasi yang sesuai dan akses jaringan.
Pilih penyedia dan masukkan kredensial di pengaturan WebUI atau `config.toml`.

Paket ini menyertakan font default, musik latar, dan biner FFmpeg lewat
imageio-ffmpeg. FFmpeg sistem yang terpasang diprioritaskan. Model Whisper
dimuat sesuai kebutuhan.

## Konfigurasi dan berkas hasil

Aplikasi yang terpasang menyimpan konfigurasi, kredensial, unggahan, dan video
hasil di direktori pengguna Anda:

| Sistem | Direktori default |
| --- | --- |
| macOS | `~/Library/Application Support/MoneyPrinterTurbo` |
| Windows | `%LOCALAPPDATA%\MoneyPrinterTurbo` |
| Linux | `~/.local/share/MoneyPrinterTurbo` (atau `$XDG_DATA_HOME/MoneyPrinterTurbo`) |

Atur `MPT_HOME` sebelum memulai aplikasi untuk memilih direktori lain.
Konfigurasi disimpan di `config.toml`; video hasil berada di bawah
`storage/tasks/<task-id>/`. Konfigurasi dan sumber daya pengguna yang ada dipertahankan
saat aplikasi dimulai atau ditingkatkan.

Lihat [dokumentasi proyek](https://github.com/harry0703/MoneyPrinterTurbo)
untuk penyedia yang didukung dan opsi lanjutan. Laporkan masalah lewat
[GitHub Issues](https://github.com/harry0703/MoneyPrinterTurbo/issues).
