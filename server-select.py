import json
import select
import socket

from common import HOST, PORT, STORAGE_DIR, list_server_files, queue_json_bytes, sanitize_filename


def make_client_state(sock, addr):
    return {
        "sock": sock,
        "addr": addr,
        "name": f"{addr[0]}:{addr[1]}",
        "inb": bytearray(),
        "outb": bytearray(),
        "upload": None,
    }


def queue_json(state, obj):
    state["outb"].extend(queue_json_bytes(obj))


def broadcast(clients, obj):
    payload = queue_json_bytes(obj)
    for state in clients.values():
        state["outb"].extend(payload)


def start_upload(state, filename, size):
    path = STORAGE_DIR / filename
    f = path.open('wb')
    state["upload"] = {"file": f, "remaining": size, "filename": filename}
    if size == 0:
        f.close()
        state["upload"] = None
        queue_json(state, {"type": "info", "message": f"Upload berhasil: {filename} (0 bytes)"})


def finish_upload(clients, state):
    upload = state["upload"]
    upload["file"].close()
    filename = upload["filename"]
    queue_json(state, {"type": "info", "message": f"Upload berhasil: {filename}"})
    broadcast(clients, {"type": "info", "message": f"{state['name']} mengunggah file {filename}"})
    state["upload"] = None


def queue_file(state, filename):
    path = STORAGE_DIR / sanitize_filename(filename)
    if not path.exists() or not path.is_file():
        queue_json(state, {"type": "error", "message": f"File '{filename}' tidak ditemukan"})
        return
    header = {"type": "file", "filename": path.name, "size": path.stat().st_size}
    state["outb"].extend(queue_json_bytes(header))
    state["outb"].extend(path.read_bytes())


def process_incoming(clients, state):
    while True:
        upload = state["upload"]
        if upload is not None:
            remaining = upload["remaining"]
            if remaining == 0:
                finish_upload(clients, state)
                continue
            if not state["inb"]:
                break
            take = min(len(state["inb"]), remaining)
            chunk = bytes(state["inb"][:take])
            del state["inb"][:take]
            upload["file"].write(chunk)
            upload["remaining"] -= take
            if upload["remaining"] == 0:
                finish_upload(clients, state)
                continue
            break

        if b'\n' not in state["inb"]:
            break

        idx = state["inb"].index(b'\n')
        line = bytes(state["inb"][:idx])
        del state["inb"][: idx + 1]
        if not line:
            continue

        try:
            msg = json.loads(line.decode('utf-8'))
        except json.JSONDecodeError:
            queue_json(state, {"type": "error", "message": "Header JSON tidak valid"})
            continue

        mtype = msg.get("type")
        if mtype == "chat":
            text = str(msg.get("text", "")).strip()
            if text:
                broadcast(clients, {"type": "chat", "from": state["name"], "text": text})

        elif mtype == "list_request":
            queue_json(state, {"type": "list_response", "files": list_server_files()})

        elif mtype == "upload":
            filename = sanitize_filename(msg.get("filename", ""))
            size = int(msg.get("size", 0))
            if not filename or size < 0:
                queue_json(state, {"type": "error", "message": "Metadata upload tidak valid"})
                continue
            start_upload(state, filename, size)

        elif mtype == "download":
            filename = sanitize_filename(msg.get("filename", ""))
            queue_file(state, filename)

        else:
            queue_json(state, {"type": "error", "message": f"Tipe pesan tidak dikenal: {mtype}"})


def close_client(clients, sock):
    state = clients.pop(sock, None)
    if state is None:
        return
    upload = state.get("upload")
    if upload is not None:
        try:
            upload["file"].close()
        except OSError:
            pass
    try:
        sock.close()
    except OSError:
        pass
    print(f"[DISCONNECTED] {state['name']}")
    if clients:
        broadcast(clients, {"type": "info", "message": f"{state['name']} terputus"})


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    server.setblocking(False)

    clients = {}
    print(f"Select server berjalan di {HOST}:{PORT}")

    try:
        while True:
            read_list = [server] + list(clients.keys())
            write_list = [sock for sock, state in clients.items() if state["outb"]]
            except_list = [server] + list(clients.keys())

            readable, writable, exceptional = select.select(read_list, write_list, except_list)

            for sock in readable:
                if sock is server:
                    while True:
                        try:
                            client_sock, client_addr = server.accept()
                        except BlockingIOError:
                            break
                        client_sock.setblocking(False)
                        state = make_client_state(client_sock, client_addr)
                        clients[client_sock] = state
                        print(f"[CONNECTED] {state['name']}")
                        broadcast(clients, {"type": "info", "message": f"{state['name']} terhubung"})
                else:
                    try:
                        chunk = sock.recv(4096)
                    except (ConnectionResetError, OSError):
                        close_client(clients, sock)
                        continue
                    if not chunk:
                        close_client(clients, sock)
                        continue
                    state = clients.get(sock)
                    if state is None:
                        continue
                    state["inb"].extend(chunk)
                    process_incoming(clients, state)

            for sock in writable:
                state = clients.get(sock)
                if state is None or not state["outb"]:
                    continue
                try:
                    sent = sock.send(state["outb"])
                    del state["outb"][:sent]
                except (BrokenPipeError, ConnectionResetError, OSError):
                    close_client(clients, sock)

            for sock in exceptional:
                if sock is not server:
                    close_client(clients, sock)

    except KeyboardInterrupt:
        print("\nServer dihentikan")
    finally:
        for sock in list(clients.keys()):
            close_client(clients, sock)
        server.close()


if __name__ == "__main__":
    main()
