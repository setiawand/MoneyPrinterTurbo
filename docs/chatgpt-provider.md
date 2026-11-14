# OpenAI - ChatGPT (Native OAuth)

Penyedia opsional ini mendaftarkan MoneyPrinterTurbo memakai
[alur Sign in with ChatGPT](https://developers.openai.com/siwc/token-sharing-open-source/sign-in) resmi OpenAI.
Pilih **OpenAI - ChatGPT (Native OAuth)** secara eksplisit di pengaturan LLM. ID
konfigurasinya `openai_chatgpt`; ia memakai paket ChatGPT yang diotorisasi lewat
endpoint publik `/v1/models` dan `/v1/responses` tanpa kunci API atau Codex CLI.

## Kompatibilitas dan kelayakan

Penyedia **OpenAI - Codex** (`openai_codex`) yang sudah ada mempertahankan login
kode perangkat, katalog model, kunci konfigurasi, dan kredensialnya. Peningkatan versi tidak
memilih native OAuth, menafsirkan ulang kredensial perangkat, atau mewajibkan pengguna Codex
yang ada untuk login lagi. Kedua penyedia memiliki pengaturan model yang independen.

Native OAuth memerlukan akun/workspace yang memenuhi syarat dan izin untuk memakai
paket ChatGPT-nya. Akun yang berfungsi dengan penyedia kode perangkat mungkin tidak dapat
mengotorisasi alur terpisah ini. Halaman persetujuan dengan tombol Continue nonaktif tidak
selalu dapat diperbaiki dengan login ulang. Jangan menyimpulkan kelayakan dari nama paket
saja atau menganggap hasil satu akun berlaku untuk semua akun Free.
Lihat [panduan kelayakan dan pemulihan](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery) OpenAI.

Jika otorisasi native tidak tersedia, pilih penyedia lain secara eksplisit.
Kegagalan otorisasi maupun inferensi tidak beralih ke Codex atau penagihan kunci API.
Login native, pembatalan, dan pemutusan koneksi tidak pernah mengubah kredensial alur perangkat.

## Login lokal

1. Jalankan MoneyPrinterTurbo dan pilih **OpenAI - ChatGPT (Native OAuth)**.
2. Pilih **Continue with ChatGPT**, lalu buka halaman otorisasi OpenAI.
3. Login dan otorisasi aplikasi ini. Browser kembali ke listener sementara
   `http://127.0.0.1:<port>/auth/callback` milik proses Python.
4. Kembali ke pengaturan, pilih model yang terdaftar di akun, lalu uji koneksi
   atau buat naskah dan kata kunci pencarian.

Browser dan runtime Python harus berjalan di komputer yang sama. Implementasi ini
tidak memiliki penerusan callback jarak jauh atau transfer kredensial untuk Docker/VM jarak jauh.
Memilih native OAuth di WebUI yang diakses dari jauh tidak membuat callback
dapat dijangkau. Gunakan penyedia Codex yang tersedia terpisah di tempat alur itu berfungsi,
atau konfigurasikan penyedia lain secara eksplisit. Layanan suara dan video tetap
dikonfigurasi terpisah.

## Registrasi dan penyimpanan

Registrasi awal memakai `dynamic_agent_client`, nama aplikasi, dan ID host instalasi
yang stabil. Login berikutnya memakai ulang ID klien yang diterbitkan. Setiap
percobaan memakai state, nonce, dan PKCE yang baru. Tanda tangan ID-token, issuer, audience,
kedaluwarsa, nonce, dan identitas yang kembali diverifikasi. Inferensi memerlukan scope
`chatgpt.tokens.use.direct` yang diberikan.

Penyimpanan di bawah root runtime (`MPT_HOME` bila diatur) terpisah:

| Penyedia | Berkas kredensial | Konfigurasi model |
| --- | --- | --- |
| Codex kode perangkat | `storage/auth/openai_codex.bin` | `openai_codex_model_name` |
| ChatGPT native OAuth | `storage/auth/openai_chatgpt.bin` | `openai_chatgpt_model_name` |

Windows memakai DPAPI per pengguna; penulisan di Unix memakai izin privat. Penulisan
native bersifat atomik. Discovery/JWKS berjalan sebelum masuk ke bagian kritis penyegaran;
pertukaran token berotasi dan persistensinya tetap diserialkan antar proses.
Setelah mendapat kunci, proses yang menunggu memuat ulang kredensial terbaru alih-alih
menyegarkan token lama lagi. Perebutan kunci dapat dipulihkan dan tidak menghapus
kredensial. Kontrol akun memiliki waktu tunggu kunci yang singkat dan terbatas serta aksi coba ulang;
jalur permintaan berbagi sisa anggaran waktunya dengan penyegaran dan penantian kunci.

**Putuskan ChatGPT** mencoba mencabut dan menghapus token akun native yang dipilih
sambil mempertahankan identitas registrasi/host-nya. Jika pencabutan
tidak dapat dikonfirmasi, periksa aplikasi yang terhubung di pengaturan ChatGPT.

### Pengguna pratinjau PR sebelumnya

Commit `8bab424` menyimpan kredensial native v2 di path Codex yang lama. Pengguna yang
benar-benar mencoba pratinjau itu dapat menyalin catatan tersebut secara eksplisit dengan:

```shell
uv run python scripts/accept_chatgpt_oauth.py --import-preview
```

Impor memerlukan catatan native v2 yang valid dan tujuan native yang belum ada. Impor
mempertahankan registrasi dan ID host, tidak pernah mengonversi kredensial perangkat, tidak pernah
menimpa penyimpanan native yang ada, dan mempertahankan berkas sumber. Perintah ini
kemudian menjalankan pemeriksaan model dan pembuatan pada akun yang diimpor; peningkatan
versi normal tidak memerlukannya. Untuk impor tanpa inferensi, panggil
`chatgpt_auth.import_preview_credentials()` dari sesi Python lokal.

Setelah impor berhasil, berkas pratinjau sebelumnya masih menempati path Codex.
Jika memakai penyedia Codex asli lagi, gunakan kontrol putuskan koneksinya untuk
menghapus catatan pratinjau itu lalu selesaikan login kode perangkat. Token perangkat
yang sudah tertimpa oleh pratinjau sebelumnya tidak dapat direkonstruksi. Tidak ada
konfigurasi penyedia yang beralih secara otomatis.

## Akseptansi akun asli yang dapat direproduksi

Skrip manual menjalankan entrypoint proyek yang sebenarnya dengan topik video
jalan kaki yang tetap dan tidak sensitif. Ini bukan bagian dari CI tanpa pengawasan dan
memakai kuota paket ChatGPT akun yang dipilih. Di mesin lokal dengan akun yang memenuhi syarat:

```shell
uv run python scripts/accept_chatgpt_oauth.py --login --disconnect
```

Secara opsional berikan `--model <account-listed-slug>` dan `--output <report.json>`.
Tanpa `--model`, model pertama yang dikembalikan dipakai. Path laporan default adalah
`storage/acceptance/chatgpt-native-<UTC timestamp>.json`. Skrip tidak mengubah
`config.toml` atau beralih ke penyedia lain. `--disconnect` mencabut dan
menghapus sesi native aktif setelah pemeriksaan inferensi berhasil.

Laporan memuat:

- timestamp UTC, OS/Python, commit, dan apakah checkout memiliki perubahan lokal;
- apakah otorisasi browser berjalan dan izin paket diberikan;
- ID model yang terdaftar di akun dan model yang dipilih;
- keluaran `llm.generate_script` dan `llm.generate_terms` yang nyata, status HTTP,
  ID permintaan bila ada, dan metadata `response.completed`;
- penyegaran paksa, kontinuitas registrasi, dan permintaan lanjutan yang selesai setelah penyegaran;
- konfirmasi pencabutan, penghapusan token lokal, dan penolakan inferensi saat
  logout tanpa mengirim permintaan API.

ID permintaan/respons yang tidak ada dicatat sebagai `null`, tidak pernah dikarang. Respons
token, klaim identitas, URL/kode otorisasi, nilai PKCE, cookie, dan header
sembarang tidak diekspor. Diagnostik permintaan dinonaktifkan untuk skrip ini;
trace opsionalnya memakai daftar izin metadata API. Proses tanpa login browser
baru atau tanpa pemutusan koneksi diberi label `partial`, bukan lulus penuh.
Jika akun tidak dapat mengotorisasi, laporan mencatat kegagalan tanpa mengubah
penyedia lain. Lakukan proses baru setelah perubahan implementasi; akseptansi pratinjau
sebelumnya bukan bukti perilaku langsung penyedia yang telah direvisi.

## Regresi otomatis

Jalankan test Codex yang asli dan test native yang baru bersama-sama. Test native memakai
kredensial dan identitas bertanda tangan sintetis. Rangkaian konkurensi memulai
interpreter Python independen dan server HTTP lokal yang lambat untuk memeriksa bahwa
antarmuka pulih, penantian yang gagal mempertahankan kredensial, tenggat terbatas, dan
token berotasi yang diperebutkan hanya ditukar sekali. Test skrip akseptansi menjalankan
entrypoint LLM yang sebenarnya lewat respons HTTP sintetis dan memeriksa penyamaran laporan;
test ini tidak membuktikan kelayakan atau akses API langsung.

## Akseptansi lokal yang tercatat

[Windows / Python 3.11.15, 2026-10-27](validation/chatgpt-native-oauth-windows-2026-10-27.json)
mencatat otorisasi browser baru, delapan model yang terdaftar di akun, pembuatan
naskah/kata kunci yang selesai memakai `gpt-6.1-sol`, penyegaran dan permintaan
lanjutan yang selesai, pencabutan yang terkonfirmasi, dan permintaan saat logout yang diblokir. ID respons
disertakan; header `x-request-id` tidak ada dan dicatat sebagai `null`.

Naskah yang dihasilkan juga dirender menjadi video 1080p berdurasi 18,47 detik memakai footage
uji lokal, mode senyap, dan subtitle, dengan pemeriksaan dekode penuh yang berhasil.
Layanan TTS eksternal dan media stok tidak diuji. Pemeriksaan browser mencakup
pemisahan penyedia dan pengaturan saat logout, sedangkan pemeriksaan model/inferensi langsung
dijalankan lewat skrip akseptansi dan entrypoint LLM proyek yang sebenarnya.
Ini adalah working tree yang belum di-commit berbasis `8bab424`; laporan menyertakan
hash berkas sumber untuk mengidentifikasi implementasi yang diuji.
