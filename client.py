import os
import socket
import threading

from common import DOWNLOAD_DIR, HOST, PORT, recv_exact, recv_line, sanitize_filename, send_json


def receiver(sock):
    buffer = bytearray()
    import json
    try:
        while True:
            line = recv_line(sock, buffer)
            if line is None:
                print("\n[INFO] Koneksi ke server ditutup.")
                break
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                print("\n[ERROR] Menerima header JSON yang tidak valid.")
                continue

            mtype = msg.get("type")
            if mtype == "chat":
                print(f"\n[CHAT] {msg.get('from')}: {msg.get('text')}")

            elif mtype == "info":
                print(f"\n[INFO] {msg.get('message')}")

            elif mtype == "error":
                print(f"\n[ERROR] {msg.get('message')}")

            elif mtype == "list_response":
                files = msg.get("files", [])
                if files:
                    print("\n[FILES DI SERVER]")
                    for i, name in enumerate(files, start=1):
                        print(f"  {i}. {name}")
                else:
                    print("\n[FILES DI SERVER] Tidak ada file.")

            elif mtype == "file":
                filename = sanitize_filename(msg.get("filename", "download.bin"))
                size = int(msg.get("size", 0))
                data = recv_exact(sock, buffer, size)
                if data is None:
                    print("\n[ERROR] Koneksi putus saat menerima file.")
                    break
                path = DOWNLOAD_DIR / filename
                path.write_bytes(data)
                print(f"\n[DOWNLOAD] File tersimpan di: {path}")

            else:
                print(f"\n[UNKNOWN] {msg}")
    except (ConnectionResetError, OSError):
        print("\n[INFO] Koneksi terputus.")


def main():
    try:
        host = input(f"Host [{HOST}]: ").strip() or HOST
        port_text = input(f"Port [{PORT}]: ").strip()
    except EOFError:
        print("\n[INFO] Input ditutup (EOF). Keluar.")
        return

    try:
        port = int(port_text) if port_text else PORT
    except ValueError:
        print("[ERROR] Port harus berupa angka.")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
    except (ConnectionRefusedError, OSError) as e:
        print(f"[ERROR] Gagal terhubung ke {host}:{port} ({e})")
        try:
            sock.close()
        except OSError:
            pass
        return
    print(f"Terhubung ke {host}:{port}")
    print("Perintah:")
    print("  /list")
    print("  /upload <path_file>")
    print("  /download <filename_di_server>")
    print("  /quit")
    print("Selain itu dianggap sebagai chat message.")

    t = threading.Thread(target=receiver, args=(sock,), daemon=True)
    t.start()

    try:
        while True:
            text = input("> ").strip()
            if not text:
                continue

            if text == "/quit":
                break

            if text == "/list":
                send_json(sock, {"type": "list_request"})
                continue

            if text.startswith("/upload "):
                local_path = text[len("/upload "):].strip()
                if not os.path.isfile(local_path):
                    print("File lokal tidak ditemukan.")
                    continue
                filename = sanitize_filename(os.path.basename(local_path))
                size = os.path.getsize(local_path)
                send_json(sock, {"type": "upload", "filename": filename, "size": size})
                with open(local_path, 'rb') as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        sock.sendall(chunk)
                print(f"Mengirim file {filename} ({size} bytes)...")
                continue

            if text.startswith("/download "):
                filename = sanitize_filename(text[len("/download "):].strip())
                if not filename:
                    print("Nama file tidak boleh kosong.")
                    continue
                send_json(sock, {"type": "download", "filename": filename})
                continue

            send_json(sock, {"type": "chat", "text": text})

    except KeyboardInterrupt:
        print("\nClient dihentikan")
    finally:
        try:
            sock.close()
        except OSError:
            pass


if __name__ == "__main__":
    main()
