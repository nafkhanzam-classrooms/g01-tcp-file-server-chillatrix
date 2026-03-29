import json
import os
import socket
from pathlib import Path

HOST = '127.0.0.1'
PORT = 5000
BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / 'storage'
DOWNLOAD_DIR = BASE_DIR / 'downloads'
STORAGE_DIR.mkdir(exist_ok=True)
DOWNLOAD_DIR.mkdir(exist_ok=True)


def sanitize_filename(filename: str) -> str:
    return os.path.basename(filename.strip())


def send_json(sock: socket.socket, obj: dict) -> None:
    data = (json.dumps(obj, ensure_ascii=False) + '\n').encode('utf-8')
    sock.sendall(data)


def recv_line(sock: socket.socket, buffer: bytearray):
    while b'\n' not in buffer:
        chunk = sock.recv(4096)
        if not chunk:
            return None
        buffer.extend(chunk)
    idx = buffer.index(b'\n')
    line = bytes(buffer[:idx])
    del buffer[: idx + 1]
    return line.decode('utf-8')


def recv_exact(sock: socket.socket, buffer: bytearray, size: int):
    out = bytearray()
    if buffer:
        take = min(len(buffer), size)
        out.extend(buffer[:take])
        del buffer[:take]
    while len(out) < size:
        chunk = sock.recv(min(4096, size - len(out)))
        if not chunk:
            return None
        out.extend(chunk)
    return bytes(out)


def list_server_files():
    return sorted([p.name for p in STORAGE_DIR.iterdir() if p.is_file()])


def queue_json_bytes(obj: dict) -> bytes:
    return (json.dumps(obj, ensure_ascii=False) + '\n').encode('utf-8')
