[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/mRmkZGKe)
# Network Programming - Assignment G01

## Anggota Kelompok

| Nama               | NRP        | Kelas                  |
|--------------------|------------|------------------------|
| Izzudin Ali Akbari | 5025231313 | Pemrograman Jaringan C |

## Link Youtube (Unlisted)

Tempel link video demo di sini:

```
https://youtube.com/...
```

## Penjelasan Program

Project ini adalah **TCP multi-client terminal app** dengan fitur chat broadcast dan transfer file.

### File yang dikerjakan

- `server-sync.py` — synchronous (melayani **1 client** pada satu waktu)
- `server-select.py` — asynchronous memakai modul `select`
- `server-poll.py` — asynchronous memakai syscall `poll` (paling cocok Linux)
- `server-thread.py` — multi-client memakai `threading`
- `client.py` — client terminal untuk semua server
- `common.py` — helper bersama (HOST/PORT, util kirim/terima, direktori)

### Fitur & Command Client

- Broadcast chat ke semua client yang terhubung
- Command:
	- `/list` — list file yang ada di server
	- `/upload <path_file>` — upload file ke server
	- `/download <filename>` — download file dari server
	- `/quit` — keluar dari client

### Lokasi file

- File server tersimpan di folder `storage/`
- File hasil download client tersimpan di folder `downloads/`

### Protokol (ringkas)

- Semua kontrol memakai **header JSON** yang diakhiri newline (`\n`).
- Untuk upload/download, setelah header dikirim, data file dikirim sebagai **raw bytes** sepanjang `size`.

Contoh tipe pesan:
- `chat`, `info`, `error`
- `list_request` → `list_response`
- `upload` (punya `filename`, `size`) → server menerima bytes
- `download` (punya `filename`) → server balas `file` (punya `filename`, `size`) lalu bytes

## Cara Menjalankan

Jalankan server (pilih salah satu):

```bash
python3 server-thread.py
# atau:
# python3 server-select.py
# python3 server-poll.py
# python3 server-sync.py
```

Lalu jalankan client:

```bash
python3 client.py
```

Default host/port: `127.0.0.1:5000`.

## Cara Demo (untuk video)

Rekomendasi demo utama: `server-thread.py` (multi-client jelas).

1. Jalankan `server-thread.py`
2. Buka 2 terminal, jalankan `client.py` di masing-masing terminal (Client A dan Client B)
3. **Broadcast**: kirim chat dari Client A, pastikan muncul di Client B
4. **/list**: ketik `/list` dan tampilkan daftar file server (lihat folder `storage/`)
5. **/upload**: buat file lalu upload
	 - `echo "ini file demo" > demo.txt`
	 - `/upload demo.txt`
6. **/download**: dari client lain ketik `/download demo.txt` lalu cek file masuk `downloads/`

Catatan untuk `server-sync.py`: server ini hanya melayani 1 client dalam satu waktu (sesuai requirement “sync”).

## Screenshot Hasil

Tambahkan screenshot hasil demo (client & server output) di sini.
