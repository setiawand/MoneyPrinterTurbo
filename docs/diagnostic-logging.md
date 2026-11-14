# Log Diagnostik

Di WebUI, buka **Pengaturan → Pengaturan Antarmuka → Log Diagnostik**, pilih level log, lalu
aktifkan **Catat parameter permintaan API** bila perlu, dan klik **Terapkan pengaturan log**.
Pengaturan berlaku segera pada layanan saat ini, termasuk log berikutnya dari tugas yang sedang
berjalan; semua sesi browser pada layanan yang sama memakai pengaturan ini.
Mengaktifkan "Sembunyikan log" hanya menyembunyikan log di antarmuka, tidak mematikan keluaran terminal.

API, CLI, dan WebUI memakai konfigurasi yang sama:

```toml
[diagnostics]
log_level = "INFO"
log_requests = false
```

`log_level` dapat berupa TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL.
Jika dihilangkan, nilai `log_level` tingkat atas yang lama dipakai, dengan default DEBUG. Setelah mengubah file secara manual,
layanan perlu dimulai ulang; tombol "Terapkan" di WebUI hanya memperbarui proses saat ini secara instan dan tidak mengubah
proses API atau CLI lain dari jarak jauh.

Pelacakan permintaan adalah sakelar terpisah dan dapat diaktifkan bahkan pada level ERROR. Defaultnya nonaktif, dan yang dicatat adalah:

- ID permintaan, metode HTTP, alamat yang disamarkan, dan parameter permintaan yang dibatasi panjangnya.
- Status respons (bila tersedia), durasi, atau jenis pengecualian saat gagal.
- Parameter pemanggilan SDK LLM. Ini adalah masukan ke SDK, bukan JSON mentah yang akhirnya dikirim SDK;
  percobaan ulang otomatis di dalam SDK tidak ditampilkan satu per satu. Durasi permintaan streaming hanya dihitung sampai
  respons atau objek stream diperoleh, tidak termasuk waktu pengunduhan berikutnya.

Cakupannya meliputi permintaan `requests` yang dipakai proyek secara eksplisit untuk materi, video, suara, publikasi, dan login, serta
pemanggilan naskah OpenAI-compatible, Azure OpenAI, Qwen, Gemini, dan LiteLLM.
Tidak mencakup lalu lintas jaringan browser itu sendiri, isi API masuk, subproses CLI, WebSocket Edge TTS,
atau transportasi internal SDK lainnya. Log aplikasi biasa dan level log SDK pihak ketiga juga bukan sakelar yang sama.

Header permintaan, isi respons, dan isi file yang diunggah tidak dicatat. Kunci, token, cookie, kata sandi, dan field tanda tangan
disamarkan, semua nilai parameter query URL disembunyikan, dan konten audio/video/base64 dihilangkan. Isi permintaan mentah
yang tidak terstruktur tidak dicatat. **Prompt dan parameter bisnis lain dapat muncul di log**, jadi matikan pelacakan
setelah pemecahan masalah selesai, dan periksa dulu apakah ada konten pribadi sebelum membagikan log. Diagnostik tidak mengirim log ke pihak luar,
dan tidak membuat, mencoba ulang, atau memutar ulang permintaan tambahan.

Log CLI tetap keluar ke stderr, sedangkan stdout tetap berupa JSON yang dapat dibaca mesin. Log tugas WebUI memakai
filter kepemilikan thread dan batas jumlah baris yang ada, dan tidak melepas handler log tugas yang sedang berjalan saat level diganti.
