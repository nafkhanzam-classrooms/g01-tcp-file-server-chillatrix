import socket
import threading
from pathlib import Path

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

clients = {}
clients_lock = threading.Lock()
send_lock = threading.Lock()


def safe_send_json(sock, obj):
    with send_lock:
        send_json(sock, obj)


def safe_send_file(sock, filename: str):
    path = STORAGE_DIR / sanitize_filename(filename)
    if not path.exists() or not path.is_file():
        safe_send_json(sock, {"type": "error", "message": f"File '{filename}' tidak ditemukan"})
        return

    size = path.stat().st_size
    header = {"type": "file", "filename": path.name, "size": size}
    with send_lock:
        send_json(sock, header)
        with path.open('rb') as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                sock.sendall(chunk)


def broadcast(obj):
    with clients_lock:
        targets = list(clients.keys())
    dead = []
    for sock in targets:
        try:
            safe_send_json(sock, obj)
        except OSError:
            dead.append(sock)
    if dead:
        with clients_lock:
            for sock in dead:
                clients.pop(sock, None)
                try:
                    sock.close()
                except OSError:
                    pass


def handle_client(client_sock, client_addr):
    client_name = f"{client_addr[0]}:{client_addr[1]}"
    buffer = bytearray()

    with clients_lock:
        clients[client_sock] = client_name

    broadcast({"type": "info", "message": f"{client_name} terhubung"})
    print(f"[CONNECTED] {client_name}")

    try:
        while True:
            line = recv_line(client_sock, buffer)
            if line is None:
                break

            import json
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                safe_send_json(client_sock, {"type": "error", "message": "Header JSON tidak valid"})
                continue

            mtype = msg.get("type")

            if mtype == "chat":
                text = str(msg.get("text", "")).strip()
                if text:
                    broadcast({"type": "chat", "from": client_name, "text": text})

            elif mtype == "list_request":
                safe_send_json(client_sock, {"type": "list_response", "files": list_server_files()})

            elif mtype == "upload":
                filename = sanitize_filename(msg.get("filename", ""))
                size = int(msg.get("size", 0))
                if not filename or size < 0:
                    safe_send_json(client_sock, {"type": "error", "message": "Metadata upload tidak valid"})
                    continue

                data = recv_exact(client_sock, buffer, size)
                if data is None:
                    break

                path = STORAGE_DIR / filename
                path.write_bytes(data)
                safe_send_json(client_sock, {"type": "info", "message": f"Upload berhasil: {filename} ({size} bytes)"})
                broadcast({"type": "info", "message": f"{client_name} mengunggah file {filename}"})

            elif mtype == "download":
                filename = sanitize_filename(msg.get("filename", ""))
                safe_send_file(client_sock, filename)

            else:
                safe_send_json(client_sock, {"type": "error", "message": f"Tipe pesan tidak dikenal: {mtype}"})

    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        print(f"[DISCONNECTED] {client_name}")
        with clients_lock:
            clients.pop(client_sock, None)
        try:
            client_sock.close()
        except OSError:
            pass
        broadcast({"type": "info", "message": f"{client_name} terputus"})


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Thread server berjalan di {HOST}:{PORT}")

    try:
        while True:
            client_sock, client_addr = server.accept()
            t = threading.Thread(target=handle_client, args=(client_sock, client_addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\nServer dihentikan")
    finally:
        server.close()


if __name__ == "__main__":
    main()
