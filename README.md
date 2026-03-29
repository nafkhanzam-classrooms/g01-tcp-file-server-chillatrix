[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/mRmkZGKe)
# Network Programming - Assignment G01

## Anggota Kelompok

| Nama               | NRP        | Kelas                  |
|--------------------|------------|------------------------|
| Izzudin Ali Akbari | 5025231313 | Pemrograman Jaringan C |

## Link Youtube (Unlisted)

Tautan video demo (unlisted) diletakkan pada bagian ini:

```
https://youtube.com/...
```

## Penjelasan Program

Program ini merupakan aplikasi terminal berbasis **TCP** yang mendukung koneksi multi-klien, pengiriman pesan (chat) secara broadcast, serta transfer file (unggah dan unduh). Implementasi server disediakan dalam empat variasi untuk memenuhi kebutuhan tugas, yaitu synchronous, berbasis `select`, berbasis `poll`, dan berbasis `thread`.

### File yang dikerjakan

- `server-sync.py` — server synchronous (melayani satu klien pada satu waktu)
- `server-select.py` — server asynchronous menggunakan modul `select`
- `server-poll.py` — server asynchronous menggunakan mekanisme `poll` (direkomendasikan untuk Linux)
- `server-thread.py` — server multi-klien menggunakan `threading`
- `client.py` — aplikasi klien terminal untuk seluruh variasi server
- `common.py` — modul bantu bersama (konfigurasi host/port, utilitas kirim/terima, serta definisi direktori)

### Fungsionalitas dan Perintah Klien

- Broadcast chat ke seluruh klien yang terhubung.
- Perintah yang tersedia pada klien:
  - `/list` — menampilkan daftar file pada server
  - `/upload <path_file>` — mengunggah file dari sisi klien ke server
  - `/download <filename>` — mengunduh file dari server ke sisi klien
  - `/quit` — mengakhiri sesi klien

### Struktur Direktori

- Berkas yang tersimpan pada server berada pada direktori `storage/`.
- Berkas hasil unduhan klien berada pada direktori `downloads/`.

### Spesifikasi Protokol (Ringkas)

- Seluruh pesan kontrol dikirim sebagai **header JSON** yang diakhiri newline (`\n`).
- Untuk unggah/unduh, setelah header dikirim, data file dikirim sebagai **raw bytes** dengan panjang sesuai nilai `size`.

Jenis pesan yang digunakan meliputi:
- `chat`, `info`, `error`
- `list_request` → `list_response`
- `upload` (memiliki `filename`, `size`) → server menerima bytes sesuai `size`
- `download` (memiliki `filename`) → server mengirim header `file` (memiliki `filename`, `size`) diikuti bytes

## Cara Menjalankan

1) Jalankan server (pilih salah satu variasi):

```bash
python3 server-thread.py
# atau:
# python3 server-select.py
# python3 server-poll.py
# python3 server-sync.py
```

2) Jalankan klien:

```bash
python3 client.py
```

Konfigurasi default host/port adalah `127.0.0.1:5000`.

Catatan: `server-sync.py` bersifat synchronous dan hanya melayani satu klien pada satu waktu, sesuai dengan spesifikasi tugas.

## Screenshot Hasil

Berikut adalah dokumentasi hasil pengujian program sesuai fungsionalitas yang diminta.

1. **Server Thread Berjalan**  
  Menunjukkan `server-thread.py` berhasil dijalankan dan melakukan bind pada `127.0.0.1:5000`.

  ![Server thread berjalan](ss/Screenshot%20from%202026-03-29%2014-47-01.png)

2. **Koneksi Multi-Klien (Thread Server)**  
  Menunjukkan server menerima lebih dari satu koneksi klien (ditandai dengan beberapa log `[CONNECTED]`).

  ![Multi-klien terhubung ke thread server](ss/Screenshot%20from%202026-03-29%2014-47-58.png)

3. **Broadcast Chat antar Klien**  
  Menunjukkan pesan chat dari satu klien diterima oleh klien lain (broadcast) melalui server.

  ![Broadcast chat](ss/Screenshot%20from%202026-03-29%2014-49-16.png)

4. **Unggah Berkas dan Daftar Berkas (`/upload` dan `/list`)**  
  Menunjukkan proses unggah berkas dari klien ke server berhasil, serta berkas yang diunggah muncul pada hasil `/list`.

  ![Upload dan list file](ss/Screenshot%20from%202026-03-29%2014-51-21.png)

5. **Unduh Berkas (`/download`)**  
  Menunjukkan proses unduh berkas dari server berhasil dan berkas tersimpan pada direktori `downloads/` di sisi klien.

  ![Download file](ss/Screenshot%20from%202026-03-29%2014-51-35.png)

6. **Server Select Berjalan**  
  Menunjukkan variasi server berbasis `select` (`server-select.py`) dapat dijalankan.

  ![Select server berjalan](ss/Screenshot%20from%202026-03-29%2014-52-10.png)

7. **Server Poll Berjalan**  
  Menunjukkan variasi server berbasis `poll` (`server-poll.py`) dapat dijalankan.

  ![Poll server berjalan](ss/Screenshot%20from%202026-03-29%2014-52-28.png)

8. **Server Sync Berjalan**  
  Menunjukkan variasi server synchronous (`server-sync.py`) dapat dijalankan dan melayani satu klien pada satu waktu.

  ![Sync server berjalan](ss/Screenshot%20from%202026-03-29%2014-52-50.png)
