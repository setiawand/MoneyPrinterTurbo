# Memeriksa metadata artefak

Endpoint artefak menerima `HEAD` selain `GET`:

```sh
curl --head http://localhost:8080/api/v1/stream/TASK_ID/final-1.mp4
curl --head http://localhost:8080/api/v1/download/TASK_ID/final-1.mp4
```

HEAD mengembalikan panjang konten dan tipe media artefak secara utuh tanpa mengirim
byte-nya. Unduhan juga mengembalikan nama berkas attachment yang sudah ada dan header
metadata berkas. Sertakan autentikasi yang sama seperti GET saat kunci API
dikonfigurasi. Berkas yang hilang dan path di luar penyimpanan tugas mempertahankan
status error yang sudah ada. Range dan If-Range tidak memilih representasi parsial untuk
HEAD; kirim GET dengan Range untuk mengambil sebagian stream. Artefak kosong memiliki
panjang nol. Permintaan metadata yang berhasil tidak memvalidasi dekode video atau
menjamin bahwa permintaan berikutnya akan melihat berkas yang sama.
