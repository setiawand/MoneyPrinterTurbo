# OpenAI - Codex

Pilih **OpenAI - Codex** di pengaturan penyedia LLM dan pilih **Hubungkan ChatGPT
dengan kode**. Buka halaman otorisasi OpenAI, masukkan kode yang ditampilkan, lalu
setujui akses. Antarmuka memeriksa konfirmasi secara otomatis. Login kode perangkat
harus diaktifkan untuk akun tersebut. Gunakan **Uji Koneksi LLM** setelah terhubung dan
memilih model.

Penyedia ini memakai kuota Codex dari langganan ChatGPT yang terhubung untuk
pembuatan teks dan gambar (opsional). Tidak perlu kunci API, pemasangan Codex CLI, maupun
kredensial CLI bersama. Render suara dan video tetap memakai penyedia yang sudah ada.

## Sumber materi gambar

Pilih **OpenAI - Codex Images** di bawah **AI Image** pada Sumber Video. Di Pengaturan,
bagian AI Image Generation APIs memiliki pemilih model Responses dan batas waktu
permintaan yang terpisah (`codex_image_model_name`, `codex_image_timeout`). Tidak ada
model default. Katalog hanya mendaftar kandidat, bukan akses gambar khusus akun;
model Responses yang dipilih harus mendukung alat pembuatan gambar untuk akun tersebut.
Alat itu yang memilih mesin gambarnya; jangan mengganti ID model Responses dengan nama mesin GPT Image.

Teks dan gambar berbagi satu akun ChatGPT dan satu login kode perangkat. Menghubungkan
dari pengaturan gambar juga menghubungkan LLM, dan sesi LLM yang sudah ada dipakai
ulang secara otomatis. Memutuskan koneksi menghapus sesi bersama untuk keduanya. Penyedia
LLM dan modelnya tetap independen dari sumber gambar dan modelnya.

Codex menghasilkan materi PNG lewat jalur gambar-ke-video yang sudah ada, termasuk
efek statis/zoom dan penanganan durasi yang ada. Ini tidak mengubah pembuatan naskah,
kata kunci, atau narasi. Setiap gambar memakai kuota akun. Jika hasil sebuah
permintaan tidak pasti, tidak valid, atau tidak dapat disimpan/dirender, pekerjaan berhenti
tanpa otomatis membuat pengganti. Hanya HTTP 401 yang eksplisit yang mengizinkan
satu kali penyegaran token terkoordinasi dan percobaan ulang. Logout atau pergantian akun membatalkan
pekerjaan gambar yang antre dan sedang berjalan dari otorisasi sebelumnya.

## Model

Pemilih mengambil `https://models.dev/api.json` dan menerapkan aturan kompatibilitas
yang sama dengan [Jarvys](https://github.com/Hackerprod/Jarvys). Katalog publik ini bukan
pemeriksaan hak akses khusus akun. Tidak ada model default tetap: pilih ID
dari daftar. ID model dipertahankan persis saat mengirim permintaan.

Katalog di-cache secara lokal selama 24 jam. **Refresh models** melewati cache.
Jika penyegaran gagal, katalog valid terakhir tetap tersedia. Tanpa cache,
antarmuka mengizinkan memasukkan ID model secara manual. Model yang sebelumnya dipilih
tetapi tidak ada di katalog yang disegarkan akan dipertahankan, bukan diam-diam berganti model.
Permintaan katalog tidak membawa kredensial ChatGPT.

## Kredensial dan error

Kredensial disimpan di `storage/auth/openai_codex.bin`, di luar Git dan berkas
konfigurasi. Windows memakai enkripsi DPAPI per pengguna; sistem lain memakai
berkas privat. Token disegarkan dengan kunci agar token refresh yang berotasi
tidak dipakai bersamaan. Penyedia ini tidak pernah mengimpor atau mengubah kredensial
yang dipakai aplikasi desktop atau CLI Codex. **Putuskan ChatGPT** menghapus
kredensial lokal aplikasi ini; sesi lain tidak dicabut.

Pekerjaan gambar terikat pada akun pengirim dan revisi login yang persisten.
Proses yang berbagi direktori runtime mengoordinasikan perubahan dan penyegaran
kredensial dengan file lock. Memutuskan koneksi atau login ulang membatalkan pekerjaan gambar yang lebih lama,
termasuk login baru ke akun yang sama; penyegaran normal mempertahankan revisinya.
Kredensial yang ada dimigrasikan secara atomik tanpa perlu login lagi.

Permintaan dibatasi pada endpoint otorisasi OpenAI dan Codex Responses,
tanpa mengikuti redirect. Hanya keluaran Responses yang selesai yang diterima; stream
parsial dan isi error mentah dari penyedia tidak ditampilkan sebagai teks hasil. Respons 401
memicu paling banyak satu kali penyegaran token dan percobaan ulang. Kontrol dan pesan
autentikasi serta pemilih model memakai sistem lokalisasi aplikasi yang ada dalam
14 bahasa yang didukung. Tips pengaturan penyedia yang diperluas mengikuti konvensi proyek
berbahasa Mandarin dan Inggris.

Protokol kode perangkat dan Responses diperiksa di Jarvys dan diimplementasikan
secara independen di Python. Lihat juga [dokumentasi autentikasi OpenAI](https://learn.chatgpt.com/docs/auth).

## Validasi

Test mencakup login yang tertunda, dibatalkan, dan kedaluwarsa, penyimpanan Windows terenkripsi,
penyegaran token bersamaan, percobaan ulang setelah 401, respons SSE lengkap dan tidak lengkap,
penyaringan katalog, persistensi cache, pemulihan saat penyegaran dan gangguan, serta
kontrol Streamlit yang diterjemahkan. Login dengan akun asli juga dikonfirmasi oleh pengguna selama
pengujian lokal. Test otomatis memakai kredensial sintetis.

### Akseptansi gambar langsung yang dapat direproduksi

Akses gambar terpisah dari akses teks: model Responses yang dipilih dan
akun yang terhubung harus diizinkan memakai `image_generation` pada rute Codex.
Keberadaan model di katalog publik, permintaan teks yang berhasil, atau sekadar nama
paket tidak membuktikan akses tersebut. Penyedia terpisah **ChatGPT (Native OAuth)**
tidak menyediakan sesi Codex yang dipakai sumber gambar ini.

Login sekali lewat **OpenAI - Codex** di WebUI, lalu jalankan skrip akseptansi
dari instalasi dan direktori runtime yang sama. Jika memakai `MPT_HOME`,
gunakan nilai yang sama untuk WebUI dan skrip. Pasang dulu dependensi terkunci
dengan `uv sync --frozen`; FFmpeg harus tersedia lewat konfigurasi FFmpeg normal aplikasi.

```sh
uv run python scripts/accept_codex_image.py --model "<exact Responses model ID>" --output storage/acceptance/codex-image.json --plan pro --confirm-image-generation
```

`--model` wajib dan dikirim apa adanya. Misalnya, untuk mereproduksi
penolakan yang dilaporkan pada `gpt-5.6-luna`, berikan ID persis tersebut. Skrip tidak
mencoba model atau penyedia lain. `--plan` bersifat opsional dan merupakan konteks yang dilaporkan sendiri;
ini bukan hak akses yang terverifikasi dan tidak menjamin akses gambar.

`--confirm-image-generation` secara eksplisit meminta satu gambar nyata memakai kuota
akun bersama. Tidak ada pembuatan gambar tambahan untuk pemeriksaan statis/zoom:
keduanya merender PNG yang diterima. Transport normal dapat menyegarkan dan mencoba ulang
sekali setelah HTTP 401 yang eksplisit. Kegagalan lain menghentikan proses tanpa membuat ulang.
Batas waktu permintaan default 300 detik (`--timeout`), dan setiap render beserta
pemeriksaan dekodenya dibatasi 120 detik.

Skrip memakai `capture_context` → `generate_images_codex` → `request_image`.
Keberhasilan hanya dilaporkan setelah mengamati respons selesai dan hasil alat
gambar selesai, mendekode PNG yang dikembalikan, dan mendekode frame dari kedua klip
dua detik yang dirender. Aset yang dihasilkan ditulis di samping laporan JSON.

Laporan memuat model yang diminta secara persis, versi OS/Python/paket/FFmpeg,
revisi sumber, status HTTP dan ID permintaan bila tersedia, ID respons/alat
dan status selesai, ukuran/hash/dimensi gambar, serta bukti dekode dan
durasi statis/zoom. ID server yang tidak ada tetap tidak ada atau null. Permintaan yang gagal
menghasilkan status keluar bukan nol dan laporan yang disanitasi; penolakan HTTP 400 yang dikenal
terkait `tool_choice`/alat gambar tidak ada diidentifikasi tanpa menyalin isi
mentahnya. Laporan tidak pernah memuat token, ID akun, URL otorisasi, prompt
sembarang, base64 gambar, atau pesan pengecualian mentah dari penyedia/transport.

Bagikan laporan JSON setelah diperiksa; jaga kredensial dan media hasil agar tidak masuk
ke commit. Laporan yang berhasil hanya membuktikan kombinasi model/akun tersebut pada
saat itu, bukan ketersediaan untuk setiap akun atau model.

### Akseptansi gambar langsung yang tercatat

Jalur materi gambar normal diuji dengan sesi kode perangkat Codex yang sudah ada dan
paket Pro yang dilaporkan sendiri. Laporan ini mencatat pembuatan yang berhasil,
ID respons/alat, hash dan dimensi PNG yang didekode, serta render statis/zoom dua detik
yang didekode. Tidak ada kredensial atau pengenal akun di dalamnya:

- [akseptansi gpt-5.6-luna](validation/codex-image-gpt-5.6-luna-2026-10-28.json)
- [akseptansi gpt-6-luna](validation/codex-image-gpt-6-luna-2026-10-28.json)

Setiap laporan mengidentifikasi commit sumber yang bersih dan versi runtime terkait.
Tidak ada respons yang menyertakan header request-ID. Keberhasilan pada akun ini tidak
membuktikan akses untuk setiap akun atau menjelaskan HTTP 400 pada instalasi lain.
Skrip akseptansi mempertahankan klasifikasi kegagalan yang terbatas dan disanitasi
ketika sebuah endpoint menolak permintaan yang sama; skrip tidak pernah berganti model secara otomatis.
