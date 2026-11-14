# Catatan Konfigurasi Docker

Sebelum menjalankan layanan Docker Compose yang disediakan untuk pertama kali, salin `config.example.toml` menjadi `config.toml` di root repositori:

```bash
cp config.example.toml config.toml
docker compose -f docker-compose.release.yml up
```

Jika `config.toml` sudah ada sebagai berkas biasa, pertahankan dan jangan menimpa pengaturan Anda. File Compose yang disediakan me-mount berkas host ini ke dalam container. Jika berkas itu tidak ada, Compose dapat membuat direktori di path tersebut, sehingga aplikasi tidak dapat memuat atau menginisialisasi konfigurasinya.

Buat berkas ini sebelum memulai meskipun Anda berencana mengisi kunci API nanti lewat WebUI. Setelah WebUI berjalan, tambahkan kredensial LLM cloud, media, atau layanan video dari pengaturan dasarnya.

Pembuatan otomatis di tingkat aplikasi dari `config.example.toml` tersedia pada mode deployment tanpa bind mount berkas hilang yang menghalangi inisialisasi; ini tidak menggantikan prasyarat tersebut untuk deployment Compose yang disediakan.
