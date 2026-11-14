# Direktori Test MoneyPrinterTurbo

Direktori ini berisi unit test untuk proyek **MoneyPrinterTurbo**.

## Struktur Direktori

- `services/`: Unit test dan test controller berfokus domain
  - `test_task.py`: Test pipeline tugas
  - `test_task_manager.py`: Test antrean in-memory dan Redis
  - `test_controller_*.py`: Test controller API yang dipisah per domain controller
  - `test_video.py`, `test_voice.py`: Test layanan media
- `test_main.py`: Test entry point aplikasi

## Menjalankan Test

Suite CI memakai pytest, yang juga menjalankan test `unittest.TestCase`
yang sudah ada:

```bash
# Jalankan semua test
uv run python -X utf8 -m pytest -q test

# Jalankan satu berkas test tertentu
uv run python -X utf8 -m pytest -q test/services/test_video.py

# Jalankan satu kelas test tertentu
uv run python -X utf8 -m pytest -q test/services/test_video.py::TestVideoService

# Jalankan satu metode test tertentu
uv run python -X utf8 -m pytest -q test/services/test_video.py::TestVideoService::test_preprocess_video
```

Untuk menjalankan pemeriksaan branch coverage yang sama dengan CI:

```bash
uv run python -X utf8 -m coverage run -m pytest -q test
uv run python -m coverage report
```

Test penyedia langsung dilewati secara default. Untuk menjalankan test yang dapat memanggil layanan
TTS atau LLM eksternal, atur `MPT_RUN_INTEGRATION_TESTS=1` dan berikan kredensial
penyedia yang diperlukan.

## Menambah Test Baru

Untuk menambah test bagi komponen lain, ikuti panduan berikut:

1. Beri nama berkas `test_<domain>.py` dan jaga setiap berkas tetap fokus pada satu domain.
2. Pecah suite controller yang luas menjadi berkas seperti `test_controller_video.py`.
3. Gunakan fungsi pytest atau `unittest.TestCase`; pytest mengumpulkan keduanya.
4. Beri nama fungsi dan metode test dengan awalan `test_`.

## Sumber Daya Test

Letakkan berkas sumber daya yang diperlukan untuk pengujian di direktori `test/resources`.
