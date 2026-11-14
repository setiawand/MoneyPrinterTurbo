[Bahasa Indonesia](#id-v1.3.10)

<h2 id="id-v1.3.10">Sorotan</h2>

- Menambahkan **akses langganan OpenAI Codex** dengan login kode perangkat dan pemilihan model dinamis, serta penyedia **ChatGPT Native OAuth** yang terpisah. Ketersediaan Native OAuth bergantung pada kelayakan akun; login Codex yang ada tetap independen.
- Menambahkan **pembuatan gambar Codex** sebagai sumber materi. Pembuatan teks dan gambar dapat berbagi login Codex aplikasi, dan gambar yang dihasilkan mendukung efek statis dan slow zoom yang ada.
- Menambahkan **Infistar dan Jalapeno Cloud** untuk LLM dan pembuatan video, bersama penyedia LLM **Runcrate, CloudGPU, dan cheapaimodel**.
- Meningkatkan **umpan balik pembuatan video yang berjalan lama** dengan tahap pembuatan, waktu berlalu, dan status polling. Pelacakan tugas bertahan saat halaman di-refresh dan saat kueri gagal sementara, dengan perlindungan terhadap pengiriman ganda.
- Menyederhanakan **pengaturan dan pemilihan penyedia** di WebUI, sehingga layanan yang sudah dikonfigurasi lebih mudah ditemukan dan diganti.
- Menambahkan **pembentukan subtitle aksara Arab**, termasuk huruf bersambung, tata letak kanan-ke-kiri, fallback font aksara campuran, serta pemotongan baris dan latar yang sadar glyph.
- Membuat **slow zoom gambar lebih mulus** dengan rendering sub-piksel, menghilangkan efek bertingkat dan goyang yang terlihat.
- Menambahkan bahasa Indonesia ke pilihan bahasa naskah dan menyempurnakan terjemahan antarmuka bahasa Indonesia.

## Perbaikan dan Peningkatan

- Memperbaiki narasi Edge TTS yang panjang kehabisan waktu akibat jeda tidak perlu di antara potongan stream. Menambahkan dukungan suara Edge dengan subtag skrip dan diagnostik audio kosong Gemini yang lebih jelas.
- Menghapus emoji dari narasi dan subtitle yang dibakar, serta menjelaskan bahwa Gemini dan MiMo TTS tidak memakai pengaturan kecepatan suara.
- Meningkatkan pemisahan subtitle di sekitar jam, angka lebar penuh, tanggal, singkatan, nama, dan tanda baca Mandarin dan Jepang. Menambahkan pemisahan kalimat untuk aksara Thai dan Lao.
- Mempertahankan transkripsi bertimestamp asli ketika koreksi subtitle tidak dapat menyelaraskan seluruh naskah. Memperbaiki kasus string kosong dan pemuaian panjang Unicode pada penilaian kemiripan subtitle.
- Mempertahankan tanda gabung pada hashtag sosial multibahasa, mengecualikan tanda emoji, dan mengenali pemisah hashtag Mandarin dan Jepang.
- Mempertahankan naskah dan kata kunci yang ada saat pembuatan AI gagal, menampilkan error yang dapat ditindaklanjuti, dan tidak meminta kata kunci setelah pembuatan naskah sudah gagal.
- Mempertahankan posisi topik yang berulang saat pencocokan materi stok berdasarkan urutan naskah, memperbaiki cache video yang rusak, dan menambahkan log kegagalan pencarian Pexels dan Coverr yang lebih jelas.
- Menghentikan ketikan konsol yang mengakhiri atau menahan penggabungan klip FFmpeg sebelum waktunya. Memperbaiki sinkronisasi keluaran render di Windows dan kecerahan TIFF grayscale big-endian.
- Meningkatkan startup Windows dari path berkarakter khusus, dari direktori kerja lain, dan dengan LAN listening aktif. Memperbaiki log konsol yang dialihkan serta mempertahankan path Windows dan spasi tak terputus saat menyimpan konfigurasi.
- Membagi batas konkurensi tugas Redis antar worker, dengan reservasi slot atomik, perpanjangan lease, dan pemulihan tugas yang antre.
- Meningkatkan pesan error font subtitle, default enum API, dan diagnostik login ChatGPT/Codex. Memperjelas pengaturan konfigurasi Docker dan pemulihan dari direktori `config.toml` yang ter-mount tidak sengaja.
- Memperbarui dependensi container CPU untuk mengatasi temuan keamanan yang dapat diperbaiki dan menambahkan pemindaian kerentanan container. Memperluas cakupan regresi dan mengoreksi assertion path khusus Windows.

## Apa yang Berubah

- Penyedia langganan Codex — @Hackerprod di [#1715](https://github.com/harry0703/MoneyPrinterTurbo/pull/1715).
- Penyedia ChatGPT Native OAuth — @Quiyyy di [#1716](https://github.com/harry0703/MoneyPrinterTurbo/pull/1716).
- Sumber materi gambar Codex — @Hackerprod di [#1719](https://github.com/harry0703/MoneyPrinterTurbo/pull/1719).
- Penyedia LLM dan video Infistar — [ebb0e28](https://github.com/harry0703/MoneyPrinterTurbo/commit/ebb0e283) / [fddd3d6](https://github.com/harry0703/MoneyPrinterTurbo/commit/fddd3d6a).
- Dukungan LLM dan video Jalapeno Cloud — [66e41b0](https://github.com/harry0703/MoneyPrinterTurbo/commit/66e41b0f).
- Penyedia LLM Runcrate — @heydryft di [#1713](https://github.com/harry0703/MoneyPrinterTurbo/pull/1713).
- Penyedia LLM CloudGPU — @cursoragent di [#1730](https://github.com/harry0703/MoneyPrinterTurbo/pull/1730).
- Penyedia LLM cheapaimodel — @nicho810 di [#1757](https://github.com/harry0703/MoneyPrinterTurbo/pull/1757).
- Kemajuan pembuatan video dan pelacakan tugas — [950ba89](https://github.com/harry0703/MoneyPrinterTurbo/commit/950ba898).
- Pengaturan penyedia yang disederhanakan — @Hackerprod di [#1723](https://github.com/harry0703/MoneyPrinterTurbo/pull/1723).
- Pembentukan subtitle Arab — @DrEssam97 di [#1698](https://github.com/harry0703/MoneyPrinterTurbo/pull/1698).
- Zoom gambar yang mulus — @kindsr di [#1767](https://github.com/harry0703/MoneyPrinterTurbo/pull/1767).
- Peningkatan bahasa Indonesia — @mteguhfh di [5c1268b](https://github.com/harry0703/MoneyPrinterTurbo/commit/5c1268b5) / [89c7e41](https://github.com/harry0703/MoneyPrinterTurbo/commit/89c7e418).
- Sinkronisasi keluaran render Windows — @rodriguetg di [#1701](https://github.com/harry0703/MoneyPrinterTurbo/pull/1701).
- Perluasan path FFmpeg dan error path font yang lebih jelas — @RerankerGuo di [#1662](https://github.com/harry0703/MoneyPrinterTurbo/pull/1662) / [#1664](https://github.com/harry0703/MoneyPrinterTurbo/pull/1664).
- Diagnostik audio kosong Gemini dan timing transkripsi yang dipertahankan — @Shubham-Padkonde di [#1721](https://github.com/harry0703/MoneyPrinterTurbo/pull/1721) / [#1763](https://github.com/harry0703/MoneyPrinterTurbo/pull/1763).
- Konkurensi Redis, perbaikan cache, dan default enum — @guishiw di [#1742](https://github.com/harry0703/MoneyPrinterTurbo/pull/1742) / [#1744](https://github.com/harry0703/MoneyPrinterTurbo/pull/1744) / [bbb9c13](https://github.com/harry0703/MoneyPrinterTurbo/commit/bbb9c13c).
- Pembaruan keamanan container CPU — @TheInfamousToTo di [13fabd5](https://github.com/harry0703/MoneyPrinterTurbo/commit/13fabd52).
- Panduan konfigurasi Docker — @ketpatil77 di [#1653](https://github.com/harry0703/MoneyPrinterTurbo/pull/1653).
- Pemulihan konfigurasi Docker — @ChandraChaan di [#1753](https://github.com/harry0703/MoneyPrinterTurbo/pull/1753).
- Perbaikan subtitle, suara, startup Windows, dan error pembuatan — @tanishqbaweja di [#1728](https://github.com/harry0703/MoneyPrinterTurbo/pull/1728) / [#1755](https://github.com/harry0703/MoneyPrinterTurbo/pull/1755) / [#1756](https://github.com/harry0703/MoneyPrinterTurbo/pull/1756) / [#1760](https://github.com/harry0703/MoneyPrinterTurbo/pull/1760) / [#1766](https://github.com/harry0703/MoneyPrinterTurbo/pull/1766).
- Penanganan hashtag, tanda baca subtitle, topik materi berulang, dan kompatibilitas suara Edge — @L4XB di [#1772](https://github.com/harry0703/MoneyPrinterTurbo/pull/1772) / [#1773](https://github.com/harry0703/MoneyPrinterTurbo/pull/1773).
- Batas kemiripan subtitle — @liangliang205 di [#1776](https://github.com/harry0703/MoneyPrinterTurbo/pull/1776).
- Nama berkas unduhan yang lebih aman dan penanganan gambar TIFF — @rudycelekli di [33dde16](https://github.com/harry0703/MoneyPrinterTurbo/commit/33dde166) / [9c13dd6](https://github.com/harry0703/MoneyPrinterTurbo/commit/9c13dd6d).
- Pembersihan test layanan — @SammyFerreiraa dan @Natan-Lucena di [#1724](https://github.com/harry0703/MoneyPrinterTurbo/pull/1724).
- Perbaikan test path Windows — @kumain-in di [#1778](https://github.com/harry0703/MoneyPrinterTurbo/pull/1778).

**Changelog Lengkap**: [v1.3.9...v1.3.10](https://github.com/harry0703/MoneyPrinterTurbo/compare/v1.3.9...v1.3.10)
