---
name: moneyprinterturbo-video
description: Use this skill whenever the user wants to create a finished video from a topic, title, idea, prompt, or script with MoneyPrinterTurbo. This includes short-form, voice-over, educational, marketing, social-media, and stock-footage videos. Also use it when the user mentions MoneyPrinterTurbo, provides this Skill URL, asks an AI agent to install or configure MoneyPrinterTurbo, needs missing API keys identified, wants a failed generation repaired, or wants a generated MP4 located and delivered. Use this skill when the expected outcome is a final video file, not setup instructions.
compatibility: Requires an AI agent with terminal, network, filesystem, and long-running command support. Supports macOS and Windows and uses uv exclusively.
metadata:
  author: "harry0703@hotmail.com"
  version: "1.3.2"
  upstream: "https://github.com/harry0703/MoneyPrinterTurbo"
---

# Pembuatan Video MoneyPrinterTurbo

Pengguna hanya perlu memberikan topik atau naskah video. Selesaikan pemasangan, pemakaian ulang konfigurasi, pembuatan, penantian, dan pengiriman MP4 akhir secara otomatis. Jangan berhenti setelah hanya memberi petunjuk atau perintah.

## Perilaku Wajib

1. Tanyakan kepada pengguna hanya kredensial API yang wajib dan hilang, ditolak, atau tidak dapat dipakai. Gabungkan semua kredensial yang diperlukan dalam satu permintaan.
2. Jangan meminta konfirmasi sebelum memasang, membuat, menunggu, memakai default, atau mengembalikan hasil.
3. Jangan membuat atau berulang kali memperbarui rencana terperinci untuk permintaan pembuatan standar. Kirim satu pembaruan progres singkat lalu jalankan.
4. Jalankan helper sebagai satu perintah foreground dengan timeout minimal 20 menit.
5. Jangan melakukan polling dengan `sleep`, `echo`, `ps`, `ls` berulang, atau `tail` berulang. Jika terminal mengembalikan ID sesi yang dapat dilanjutkan, lanjutkan menunggu pada sesi yang sama.
6. Jangan membaca seluruh log setelah berhasil. Baca hanya error singkat yang dilaporkan atau bagian akhir log yang relevan setelah gagal.
7. Jangan pernah mencetak kunci API, token, `config.toml` lengkap, atau potongan konfigurasi yang memuat kredensial.

## Default

Kecuali pengguna meminta lain, buat satu video potret `9:16` berbahasa Mandarin dengan footage Pexels, suara Edge TTS Mandarin default, subtitle, dan musik latar. Pasang MoneyPrinterTurbo di bawah direktori home pengguna.

## Eksekusi

### 1. Temukan helper

Tentukan `SKILL_DIR` dari berkas `SKILL.md` ini. Helper-nya adalah `mpt_agent.py` di sebelahnya. Atur direktori kerja alat terminal ke `SKILL_DIR` dan panggil helper dengan nama berkas relatifnya. Jangan menaruh path absolut helper di perintah, dan jangan menjalankan pemeriksaan `ls` atau `dir` tambahan.

Ini wajib di Windows karena beberapa validator terminal agent menghapus backslash dari path absolut yang tertanam di perintah. Memakai `mpt_agent.py` dengan `workdir=SKILL_DIR` menghindari kegagalan itu dan berfungsi di macOS maupun Windows.

Jika klien hanya memuat `SKILL.md` jarak jauh, unduh helper dari repositori resmi ke direktori sementara, lalu pakai direktori sementara itu sebagai direktori kerja perintah:

```text
https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/docs/skill/mpt_agent.py
```

### 2. Jalankan helper

Jangan menjalankan pemeriksaan awal `uv --version` tersendiri. Jalankan helper secara langsung. Jika shell secara eksplisit melaporkan uv tidak ada, pasang uv lalu coba lagi perintah helper yang sama sekali saja.

Pemasangan uv di macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Pemasangan uv di Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Gunakan perintah foreground ini dengan `workdir=SKILL_DIR` dan timeout minimal 20 menit:

```bash
uv run --no-project --python 3.11 python mpt_agent.py --subject "<topik video>"
```

Di Windows, jangan mencoba path absolut dengan backslash, path absolut dengan forward slash, atau salinan di workspace sebelum perintah relatif ini. Jika alat terminal melaporkan `referenced_script_path_missing`, pastikan direktori kerjanya persis `SKILL_DIR` dan coba lagi perintah relatif sekali saja. Jangan berputar-putar mencoba varian path.

Jangan memakai Docker, Conda, pip sistem, atau virtual environment yang dikelola manual.

## Penanganan Kode Keluar

### Kode keluar 0: sampaikan hasilnya

Keluaran yang berhasil berbentuk:

```text
MPT_RESULT
VIDEO_FILE=<absolute path>/final-1.mp4
TASK_DIR=<absolute path>/storage/tasks/<task_id>
LOG_FILE=<absolute path>/run-<task_id>.log
RESULT_FILE=<absolute path>/latest-result.json
```

`mpt_agent.py` hanya mengeluarkan `VIDEO_FILE` setelah memastikan berkas ada dan tidak kosong. Jangan menjalankan `ls`, `stat`, atau perintah validasi berkas lain.

Jika terminal melaporkan `exitCode=0` tetapi keluarannya terpotong atau mengembalikan rujukan berkas riwayat tanpa `MPT_RESULT`, jangan menyimpulkan gagal dan jangan memeriksa log lama. Baca berkas ini sekali:

```text
~/MoneyPrinterTurbo/.agent-logs/moneyprinterturbo-video/latest-result.json
```

Anggap `status=completed` sebagai berhasil. Kembalikan hanya path absolut video dan deskripsi ringkas, misalnya:

```text
Video sudah siap.
Topik: ...
Berkas video: /absolute/path/to/final-1.mp4
Ringkasan: Video potret berbahasa Mandarin dengan narasi, subtitle, dan musik latar.
```

### Kode keluar 10: minta kredensial satu kali

`MPT_NEEDS_INPUT` hanya memuat field yang diperlukan, penyedia LLM yang direkomendasikan beserta tautan pendaftaran, persyaratan OpenAI-compatible kustom, dan tautan pendaftaran penyedia materi. Tanyakan hanya nilai yang tercantum dan jangan meminta kredensial yang sudah ada di `config.toml`.

Setelah pengguna menjawab, jalankan ulang perintah foreground yang sama hanya dengan variabel lingkungan yang diperlukan:

```text
MPT_LLM_PROVIDER
MPT_LLM_API_KEY
MPT_LLM_BASE_URL
MPT_LLM_MODEL_NAME
MPT_PEXELS_API_KEY
MPT_VOLCENGINE_ARK_API_KEY
MPT_OFOX_API_KEY
MPT_METASO_MINIMAX_API_KEY
MPT_MUAPI_API_KEY
MPT_INFISTAR_VIDEO_API_KEY
MPT_JALAPENO_VIDEO_API_KEY
```

Bila `SEEDANCE_CHARGE_CONFIRMATION_REQUIRED` muncul, jelaskan bahwa setiap
klip Seedance yang dihasilkan membuat tugas Ark berbayar. Hanya setelah pengguna secara eksplisit
mengonfirmasi, jalankan ulang dengan `--confirm-seedance-charge`; jangan pernah menambahkan flag ini secara diam-diam.

Bila `WAVESPEED_CHARGE_CONFIRMATION_REQUIRED` muncul, jelaskan bahwa setiap
klip WaveSpeed yang dihasilkan ditagih per permintaan oleh WaveSpeed. Hanya setelah pengguna
secara eksplisit mengonfirmasi, jalankan ulang dengan `--confirm-wavespeed-charge`; jangan pernah menambahkan
flag ini secara diam-diam.

Bila `OFOX_CHARGE_CONFIRMATION_REQUIRED` muncul, jelaskan bahwa setiap
klip OFox yang dihasilkan membuat tugas berbayar. Hanya setelah pengguna secara eksplisit
mengonfirmasi, jalankan ulang dengan `--confirm-ofox-charge`; jangan pernah menambahkan flag ini secara diam-diam.

Bila `METASO_MINIMAX_CHARGE_CONFIRMATION_REQUIRED` muncul, jelaskan bahwa
setiap klip MiniMax H3 yang dihasilkan membuat tugas Metaso berbayar. Hanya setelah pengguna
secara eksplisit mengonfirmasi, jalankan ulang dengan `--confirm-metaso-minimax-charge`; jangan pernah menambahkan
flag ini secara diam-diam.

Bila `MUAPI_CHARGE_CONFIRMATION_REQUIRED` muncul, jelaskan bahwa setiap
klip MuAPI yang dihasilkan membuat tugas berbayar. Hanya setelah pengguna secara eksplisit
mengonfirmasi, jalankan ulang dengan `--confirm-muapi-charge`; jangan pernah menambahkan flag ini secara diam-diam.

Bila `INFISTAR_CHARGE_CONFIRMATION_REQUIRED` muncul, jelaskan bahwa setiap
klip Infistar yang dihasilkan membuat tugas berbayar. Hanya setelah pengguna secara eksplisit
mengonfirmasi, jalankan ulang dengan `--confirm-infistar-charge`; jangan pernah menambahkan flag ini secara diam-diam.
Gunakan kunci video khusus, terpisah dari kunci LLM Infistar.

Bila `JALAPENO_CHARGE_CONFIRMATION_REQUIRED` muncul, jelaskan bahwa setiap
klip Jalapeno Cloud yang dihasilkan membuat tugas berbayar. Setelah pengguna mengonfirmasi,
jalankan ulang dengan `--confirm-jalapeno-charge`. Kunci video yang kosong memakai ulang
kunci LLM Jalapeno Cloud yang dikonfigurasi; kunci video khusus diprioritaskan.

### Kode keluar 1: perbaiki atau laporkan

Gunakan `MPT_ERROR` dan `LOG_FILE` untuk memperbaiki masalah yang dapat dipulihkan dan coba lagi sekali. Tanyakan kepada pengguna hanya jika perbaikan memerlukan kunci API baru. Jika percobaan ulang gagal, laporkan tahap yang gagal, error singkat, dan path log.

Error validasi path pada alat terminal bukan kegagalan pembuatan video karena helper belum dimulai. Perbaiki direktori kerja dan coba lagi perintah relatif sekali saja. Jangan pernah meminta pengguna menyalin `mpt_agent.py`, menjalankan perintah secara manual, atau mengonfirmasi apakah agent boleh melanjutkan.

## Konfigurasi dan Cadangan Latar Belakang

Helper boleh membaca `config.toml` lokal secara lengkap untuk memakai ulang pengaturan yang ada, tetapi tidak boleh mencetak isinya. Helper memakai ulang penyedia LLM yang berfungsi secara otomatis dan memvalidasi kunci Pexels yang dikonfigurasi lewat endpoint My Collections yang terautentikasi sebelum pembuatan.

Gunakan mode latar belakang hanya jika platform agent tidak dapat menunggu proses foreground. Tunggu notifikasi proses selesai dari platform tanpa polling, lalu baca `latest-result.json` sekali.

## Cakupan

- Hanya mendukung macOS dan Windows.
- Hanya gunakan uv dan CLI MoneyPrinterTurbo.
- Jangan memulai layanan Docker, WebUI, atau API.
- Jangan menjalankan beberapa job video secara bersamaan.
- Berikan kebutuhan video tambahan setelah `--`. Jalankan `cli.py --help` sekali saja hanya ketika opsi yang belum dikenal perlu diverifikasi.
