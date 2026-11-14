[Bahasa Indonesia](#id-v1.3.9)

<h2 id="id-v1.3.9">Sorotan</h2>

- Menambahkan paket pip resmi **`mpt`**. Jalankan WebUI dengan `mpt webui` atau buat video dengan `mpt cli`.
- Menambahkan **efek gambar statis dan slow zoom** untuk gambar lokal dan gambar buatan AI. Slow zoom tetap menjadi default.
- Menambahkan akses langganan Kimi Code dengan otorisasi browser, beserta perbaikan pada dialog login, pembaruan status, dan pembatalan.
- Menambahkan **server gambar SDXL lokal** opsional untuk alur materi gambar kompatibel OpenAI, dengan pelepasan GPU saat idle.
- Menambahkan penyedia LLM Opper, onomeo, Muse Spark, dan EmpirioLabs AI, serta melengkapi terjemahan WebUI Portugis Brasil.
- Menambahkan **kontrol log diagnostik** di WebUI, termasuk perubahan level log saat runtime dan pelacakan permintaan API opt-in dengan penyamaran dan batas ukuran.

## Perbaikan dan Peningkatan

- Memperbaiki kecerahan gambar grayscale, latar gambar transparan, penyelarasan mask zoom, dan warna latar subtitle. Meningkatkan transisi pada klip pendek, fade-out musik latar, dan penanganan karakter khusus pada path penggabungan.
- Mengisolasi berkas gambar perantara antar job bersamaan, meningkatkan identitas cache gambar, dan memvalidasi unduhan yang di-cache. Video yang sudah selesai dipertahankan saat video lain dalam batch yang sama gagal.
- Memperbaiki penanganan kecepatan bicara, volume, dan kontainer audio pada beberapa penyedia. Meningkatkan validasi audio jarak jauh dan mempertahankan audio yang ada sampai keluaran penggantinya siap.
- Meningkatkan pembulatan timestamp subtitle, pemotongan kata panjang, penanganan Unicode, dan pengenalan tag jeda. Baris hanya-simbol dan pemisah tidak lagi mengacaukan estimasi penyelarasan subtitle.
- Memperbaiki judul sosial cadangan bahasa Mandarin dan Jepang yang memakai seluruh naskah. Meningkatkan ekstraksi JSON, penghapusan penalaran, pembersihan Markdown, dan validasi kata kunci pencarian yang dihasilkan.
- Memperluas format unggahan lokal yang didukung, termasuk JPEG kamera multi-gambar. Meningkatkan pemeriksaan riwayat tugas, status penghapusan, pratinjau subtitle, dan pesan error koneksi model di WebUI.
- Menambahkan dukungan HEAD untuk artefak yang dihasilkan dan meningkatkan unduhan byte-range, error validasi, serta pembaruan tugas Redis dan perlindungan penghapusan.
- Mengurangi pengiriman ulang suara yang tidak aman setelah respons hilang atau redirect, mempertahankan handle pelacakan Upload-Post, dan meningkatkan deteksi error pengiriman WaveSpeed.
- Memperbarui Edge TTS untuk mengatasi kegagalan 403, membatasi PyAV demi kompatibilitas Whisper, dan memperbaiki pembersihan cache Windows serta penanganan UTF-8 BOM pada berkas locale.
- Meningkatkan penanganan konfigurasi dan pemeriksaan awal pada helper agent, termasuk alur kerja dengan narasi dan visual yang sudah disiapkan yang tidak memerlukan LLM.

## Catatan Penggunaan dan Peningkatan

- Paket PyPI resmi adalah **`mpt`**, dikelola oleh proyek ini, dan memerlukan **Python 3.11 atau lebih baru**. Pasang atau tingkatkan dengan `python -m pip install --upgrade mpt`; virtual environment disarankan. Paket bernama `MoneyPrinterTurbo` yang terpisah adalah distribusi pihak ketiga.
- Pemasangan pip menyimpan konfigurasi dan berkas hasil di direktori pengguna secara default; atur `MPT_HOME` untuk memilih lokasi lain. Pemasangan dari sumber tetap memakai direktori proyek. Saat berpindah metode pemasangan, pindahkan konfigurasi dan sumber daya yang diperlukan ke direktori runtime yang dipilih.
- Gerak gambar default-nya **slow zoom** untuk pengguna yang ada. Untuk gambar diam tanpa efek transisi, pilih **Statis** untuk gerak gambar dan **Tidak ada** untuk transisi. Pengaturan tersedia di WebUI, CLI, dan API.
- Kimi Code memerlukan login browser dan memakai batas penggunaan paket Anda. Penyedia LLM baru lainnya memerlukan kredensial dan konfigurasi API masing-masing.
- Server SDXL lokal memerlukan dependensi terpisah, unduhan model, dan layanan GPU yang berjalan; server tidak dimulai otomatis bersama MPT. Pengaturan defaultnya membongkar model Ollama sebelum pembuatan gambar, jadi hindari pekerjaan LLM dan gambar bersamaan di GPU yang sama. Lihat [petunjuk pengaturan](https://github.com/harry0703/MoneyPrinterTurbo/blob/v1.3.9/docs/local-image-server/README.md).
- Pelacakan permintaan API **nonaktif secara default**. Prompt dan parameter bisnis dapat muncul di log saat diaktifkan; matikan pelacakan setelah pemecahan masalah dan periksa konten pribadi sebelum membagikan log. Lihat [panduan log diagnostik](https://github.com/harry0703/MoneyPrinterTurbo/blob/v1.3.9/docs/diagnostic-logging.md).

## Apa yang Berubah

- Paket pip resmi dengan peluncur WebUI dan CLI — [c3634de](https://github.com/harry0703/MoneyPrinterTurbo/commit/c3634de097ea4951935d22e94580ff0ad2665503).
- Opsi gambar statis dan slow zoom — [90f7701](https://github.com/harry0703/MoneyPrinterTurbo/commit/90f77011d7e3b46d382e6d0180dabfb6725ffee4).
- Penyedia langganan Kimi Code — @ysntony di [#1599](https://github.com/harry0703/MoneyPrinterTurbo/pull/1599), dilanjutkan dengan [perbaikan alur login](https://github.com/harry0703/MoneyPrinterTurbo/commit/4204d0f).
- Server gambar SDXL lokal — @imkashif di [#1668](https://github.com/harry0703/MoneyPrinterTurbo/pull/1668).
- Penyedia LLM Opper — @Felixkw12 di [#1589](https://github.com/harry0703/MoneyPrinterTurbo/pull/1589).
- Penyedia LLM onomeo — @Owaid0723666 di [#1600](https://github.com/harry0703/MoneyPrinterTurbo/pull/1600).
- Penyedia Muse Spark dan terjemahan Portugis Brasil — @humbertocortezia di [#1657](https://github.com/harry0703/MoneyPrinterTurbo/pull/1657).
- Penyedia EmpirioLabs AI — @Adam-Dalloul di [#1694](https://github.com/harry0703/MoneyPrinterTurbo/pull/1694).
- Log diagnostik runtime dan pelacakan permintaan — [6940611](https://github.com/harry0703/MoneyPrinterTurbo/commit/6940611cc2791d1ca13b3af7ee893ccd9544b874).
- Judul sosial cadangan bahasa Mandarin dan Jepang — [e25326e](https://github.com/harry0703/MoneyPrinterTurbo/commit/e25326e).
- Video yang sudah selesai dipertahankan setelah kegagalan batch — @hdu-r3drum di [#1597](https://github.com/harry0703/MoneyPrinterTurbo/pull/1597).
- Perbaikan Edge TTS 403 — @HEOJUNFO di [#1652](https://github.com/harry0703/MoneyPrinterTurbo/pull/1652).
- Kompatibilitas Whisper/PyAV — @cristianchiriac di [#1582](https://github.com/harry0703/MoneyPrinterTurbo/pull/1582).
- Pembersihan cache Windows — @shan3520 di [#1654](https://github.com/harry0703/MoneyPrinterTurbo/pull/1654).
- Dukungan locale dengan UTF-8 BOM — @ketpatil77 di [#1658](https://github.com/harry0703/MoneyPrinterTurbo/pull/1658).
- Perlindungan tugas untuk status yang tidak dapat diurai — @RerankerGuo di [#1663](https://github.com/harry0703/MoneyPrinterTurbo/pull/1663).
- Error koneksi model yang lebih jelas — @fengqiaoqu di [#1645](https://github.com/harry0703/MoneyPrinterTurbo/pull/1645).
- Pemeriksaan awal materi lokal — @drakeo338 di [#1585](https://github.com/harry0703/MoneyPrinterTurbo/pull/1585); ID tugas Redis dipertahankan — @ac1982 di [#1588](https://github.com/harry0703/MoneyPrinterTurbo/pull/1588).
- Render grayscale, permintaan HEAD artefak, dan alur kerja agent dengan media yang sudah disiapkan — @rudycelekli di [#1620](https://github.com/harry0703/MoneyPrinterTurbo/pull/1620), [#1636](https://github.com/harry0703/MoneyPrinterTurbo/pull/1636), dan [#1608](https://github.com/harry0703/MoneyPrinterTurbo/pull/1608), beserta banyak perbaikan keandalan subtitle, suara, materi, API, dan tugas.

Terima kasih kepada semua kontributor dan semua yang melaporkan masalah serta membantu menguji perubahan ini!

**Changelog Lengkap**: [v1.3.8...v1.3.9](https://github.com/harry0703/MoneyPrinterTurbo/compare/v1.3.8...v1.3.9)
