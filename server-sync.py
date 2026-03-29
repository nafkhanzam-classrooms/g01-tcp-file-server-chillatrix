import json
import socket

from common import (
    HOST,
    PORT,
    STORAGE_DIR,
    list_server_files,
    recv_exact,
    recv_line,
    sanitize_filename,
    send_json,
)


def send_file(sock, filename: str):
    path = STORAGE_DIR / sanitize_filename(filename)
    if not path.exists() or not path.is_file():
        send_json(sock, {"type": "error", "message": f"File '{filename}' tidak ditemukan"})
        return

    send_json(sock, {"type": "file", "filename": path.name, "size": path.stat().st_size})
    with path.open('rb') as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            sock.sendall(chunk)


def handle_client(client_sock, client_addr):
    client_name = f"{client_addr[0]}:{client_addr[1]}"
    buffer = bytearray()
    print(f"[CONNECTED] {client_name}")
    send_json(client_sock, {"type": "info", "message": f"Anda terhubung ke server-sync sebagai {client_name}"})
    send_json(client_sock, {"type": "info", "message": "Catatan: server-sync melayani satu klien pada satu waktu"})

    try:
        while True:
            line = recv_line(client_sock, buffer)
            if line is None:
                break

            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                send_json(client_sock, {"type": "error", "message": "Header JSON tidak valid"})
                continue

            mtype = msg.get("type")

            if mtype == "chat":
                text = str(msg.get("text", "")).strip()
                if text:
                    # Pada server sync, broadcast efektif hanya kembali ke klien aktif.
                    send_json(client_sock, {"type": "chat", "from": client_name, "text": text})

            elif mtype == "list_request":
                send_json(client_sock, {"type": "list_response", "files": list_server_files()})

            elif mtype == "upload":
                filename = sanitize_filename(msg.get("filename", ""))
                size = int(msg.get("size", 0))
                if not filename or size < 0:
                    send_json(client_sock, {"type": "error", "message": "Metadata upload tidak valid"})
                    continue

                data = recv_exact(client_sock, buffer, size)
                if data is None:
                    break

                path = STORAGE_DIR / filename
                path.write_bytes(data)
                send_json(client_sock, {"type": "info", "message": f"Upload berhasil: {filename} ({size} bytes)"})

            elif mtype == "download":
                filename = sanitize_filename(msg.get("filename", ""))
                send_file(client_sock, filename)

            else:
                send_json(client_sock, {"type": "error", "message": f"Tipe pesan tidak dikenal: {mtype}"})
    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        print(f"[DISCONNECTED] {client_name}")
        try:
            client_sock.close()
        except OSError:
            pass


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Sync server berjalan di {HOST}:{PORT}")
    print("Server ini akan melayani satu klien sampai klien tersebut disconnect.")

    try:
        while True:
            client_sock, client_addr = server.accept()
            handle_client(client_sock, client_addr)
    except KeyboardInterrupt:
        print("\nServer dihentikan")
    finally:
        server.close()


if __name__ == "__main__":
    main()
