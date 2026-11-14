# Server gambar lokal untuk `openai_image`

Footage stok sering kurang berkaitan dengan naskah. Sumber `openai_image` mengatasinya dengan membuat satu gambar per segmen naskah. Folder ini berisi server kecil yang melakukannya di GPU Anda sendiri, sehingga tidak ada biaya per gambar.

Server ini menyediakan API OpenAI `/v1/images/generations` dan menjalankan [RealVisXL V5.0 Lightning](https://huggingface.co/SG161222/RealVisXL_V5.0_Lightning), model SDXL fotorealistis yang membutuhkan sekitar 6 langkah per gambar.

Diuji pada RTX 5070 Ti (16 GB):

- sekitar 3,9 dtk per gambar 832x1216 lewat HTTP setelah hangat (sekitar 2 dtk di antaranya untuk modelnya sendiri)
- 5 sampai 7 menit untuk video 50 dtk dengan 8 adegan, termasuk suara, subtitle Whisper, dan render; narasi online menyumbang sebagian besar variasinya

## Pengaturan

```bash
cd docs/local-image-server
python -m venv .venv
.venv/Scripts/pip install torch --index-url https://download.pytorch.org/whl/cu128
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python server.py
```

`uvicorn server:app --port 7861` bekerja dengan cara yang sama: worker idle dimulai bersama aplikasi pada kedua cara.

Permintaan pertama mengunduh bobot fp16, sekitar 6,6 GB. Server mendengarkan di `http://127.0.0.1:7861`. Nilai `size` yang bukan `LEBARxTINGGI` dengan angka positif mendapat respons 422.

Test, dari root repo, tanpa perlu GPU: `python -m pytest test/services/test_local_image_policy.py test/services/test_local_image_server.py`. Test server menjalankan aplikasi HTTP yang sebenarnya dengan pipeline pengganti dan Ollama palsu.

## config.toml

```toml
[app]
video_source = "openai_image"
openai_image_base_url = "http://127.0.0.1:7861/v1"
openai_image_model = "realvisxl-v5-lightning"
match_materials_to_script = true
video_clip_duration = 6
```

`match_materials_to_script` meminta LLM menghasilkan hingga 8 kata kunci sesuai urutan narasi, sehingga tiap bagian naskah mendapat satu adegan. Setiap gambar menjadi satu klip, jadi 8 kata kunci x 6 dtk mencakup sekitar 48 dtk narasi. Dengan klip yang lebih pendek, adegan diulang untuk mengisi kekurangannya.

## Berbagi GPU dengan Ollama

Diukur pada RTX 5070 Ti: bobot SDXL memakai 6,7 GB, dan melukis satu gambar 832x1216 mencapai puncak 10,6 GB teralokasi. qwen3:14b di Ollama memakai 9,0 GB. Keduanya tidak muat bersama di kartu 16 GB, sehingga server menjaga hanya salah satunya di GPU pada satu waktu:

- Sebelum setiap gambar, server menanyakan ke Ollama model mana yang sedang dimuat, membongkarnya, dan menunggu sampai Ollama melaporkan model itu hilang. Ini berjalan pada setiap permintaan, bukan hanya yang pertama, karena MPT mungkin memuat LLM lagi di antara gambar atau di antara video yang berurutan.
- Setelah setiap permintaan, server melepas buffer cache PyTorch. Tanpa itu, proses menahan sekitar 14 GB di antara gambar.
- Setelah `IMAGE_IDLE_SECONDS` (default 90) tanpa permintaan, worker latar memindahkan SDXL ke CPU, sehingga Ollama mendapat seluruh GPU untuk naskah berikutnya.

Server tidak dapat mencegah Ollama dimuat saat gambar sedang dilukis. Menjalankan pekerjaan LLM dan gambar pada saat yang sama tidak didukung: permintaan gambar berikutnya merebut kembali GPU, tetapi sementara itu kedua model berbagi GPU. Di Windows, driver menumpahkan kelebihannya ke memori sistem, yang lambat tetapi tidak crash saat pengujian. Kami belum menguji kasus ini di Linux.

## Opsi

| Variabel | Default | |
|---|---|---|
| `IMAGE_MODEL` | `SG161222/RealVisXL_V5.0_Lightning` | repo SDXL apa pun dengan bobot fp16 |
| `IMAGE_STEPS` | `6` | |
| `IMAGE_GUIDANCE` | `1.5` | |
| `IMAGE_IDLE_SECONDS` | `90` | waktu idle sebelum SDXL dipindahkan ke CPU |
| `IMAGE_IDLE_CHECK_SECONDS` | `10` | seberapa sering worker idle memeriksa |
| `IMAGE_PORT` | `7861` | dipakai oleh `python server.py` |
| `OLLAMA_URL` | `http://localhost:11434` | |
| `OLLAMA_UNLOAD_TIMEOUT` | `30` | berapa lama menunggu Ollama melepas GPU |
| `CONTENT_POLICY` | `policy.toml` | path ke berkas kebijakan, atau `off` |

## Kebijakan konten

Kata kunci adegan berasal dari LLM, sehingga video tentang agama atau sejarah dapat meminta model gambar membuat hal-hal yang tidak seharusnya dibuat. Sebelum setiap prompt sampai ke model, `policy.toml` memeriksanya. Kebijakan ini aktif secara default, dan sebuah aturan hanya bertindak bila kata kuncinya muncul.

| Aturan | Fungsinya |
|---|---|
| `god` | Tuhan tidak pernah ditampilkan sebagai sosok. Adegan menjadi cahaya yang menembus awan. |
| `prophet_muhammad`, `islamic_prophets`, `companions_and_family_of_the_prophet` | Tidak ada penggambaran, sesuai tradisi Islam. Adegan menjadi lanskap kosong dari tempat yang disebut (Mekah, Madinah, Hira, Sinai, Yerusalem), atau gurun saat matahari terbit jika tidak ada. |
| `bahai_central_figures`, `sikh_gurus` | Tidak ada penggambaran. Adegan menjadi tempat yang sesuai tanpa orang. |
| `atrocities` | Tidak ada "foto sejarah" rekaan dari kekejaman yang nyata. Adegan menjadi peringatan lilin. |
| `children_in_distress` | Adegan menjadi gambar simbolis tanpa orang. |
| `living_public_figures` | Tidak ada wajah fotorealistis pejabat yang disebut namanya. Adegan menjadi gedung pemerintahan. |
| `sacred_script` | Model gambar menulis aksara Arab, Ibrani, Sanskerta, atau Gurmukhi palsu, sehingga kaligrafi diganti pola geometris. |
| `holy_books` | Kitab suci ditampilkan tertutup, tanpa tulisan. |
| `revered_figures` | Yesus, Maria, Buddha, dewa-dewi Hindu, dan lainnya digambarkan dalam tradisi masing-masing, sehingga tetap dipertahankan dan dibingkai dengan hormat. |

`islamic_prophets_english_names` nonaktif secara default. Untuk konten Islam, aktifkan agar Yesus, Musa, Ibrahim, dan Nuh juga ditampilkan sebagai tempat, bukan sebagai orang.

Mengganti seluruh adegan memang disengaja. Negative prompt saja tidak andal menjaga orang tetap tidak muncul: dalam pengujian, ia tetap menghasilkan sosok pada 2 dari 6 adegan nabi. Menaikkan kekuatan guidance sebagai kompensasi justru merusak gambar model Lightning.

Keterbatasan yang diketahui: aturan kata kunci melewatkan frasa yang tidak didaftar dan dapat salah sasaran pada nama umum (Muhammad Ali, seseorang bernama Isa). `test/services/test_local_image_policy.py` mencakup kasus yang diharapkan. Edit `policy.toml` agar sesuai dengan audiens Anda.
