import json
import select
import socket

from common import HOST, PORT, STORAGE_DIR, list_server_files, queue_json_bytes, sanitize_filename


def make_client_state(sock, addr):
    return {
        "sock": sock,
        "fd": sock.fileno(),
        "addr": addr,
        "name": f"{addr[0]}:{addr[1]}",
        "inb": bytearray(),
        "outb": bytearray(),
        "upload": None,
    }


def queue_json(state, obj):
    state["outb"].extend(queue_json_bytes(obj))


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


def broadcast(clients, obj):
    payload = queue_json_bytes(obj)
    for state in clients.values():
        state["outb"].extend(payload)


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
                broadcast(clients, {"type": "chat", "from": state['name'], "text": text})

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


def update_interest(poller, state):
    mask = select.POLLIN
    if state["outb"]:
        mask |= select.POLLOUT
    poller.modify(state["fd"], mask)


def close_client(clients, fd_map, poller, fd):
    state = fd_map.pop(fd, None)
    if state is None:
        return
    clients.pop(state["sock"], None)
    try:
        poller.unregister(fd)
    except OSError:
        pass
    upload = state.get("upload")
    if upload is not None:
        try:
            upload["file"].close()
        except OSError:
            pass
    try:
        state["sock"].close()
    except OSError:
        pass
    print(f"[DISCONNECTED] {state['name']}")
    if clients:
        broadcast(clients, {"type": "info", "message": f"{state['name']} terputus"})
        for st in clients.values():
            update_interest(poller, st)


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    server.setblocking(False)

    poller = select.poll()
    poller.register(server.fileno(), select.POLLIN)

    clients = {}
    fd_map = {server.fileno(): server}

    print(f"Poll server berjalan di {HOST}:{PORT}")

    try:
        while True:
            events = poller.poll()
            for fd, event in events:
                if fd == server.fileno():
                    while True:
                        try:
                            client_sock, client_addr = server.accept()
                        except BlockingIOError:
                            break
                        client_sock.setblocking(False)
                        state = make_client_state(client_sock, client_addr)
                        clients[client_sock] = state
                        fd_map[state["fd"]] = state
                        poller.register(state["fd"], select.POLLIN)
                        print(f"[CONNECTED] {state['name']}")
                        broadcast(clients, {"type": "info", "message": f"{state['name']} terhubung"})
                        for st in clients.values():
                            update_interest(poller, st)
                    continue

                state = fd_map.get(fd)
                if state is None or isinstance(state, socket.socket):
                    continue

                if event & (select.POLLHUP | select.POLLERR | getattr(select, 'POLLNVAL', 0)):
                    close_client(clients, fd_map, poller, fd)
                    continue

                if event & select.POLLIN:
                    try:
                        chunk = state["sock"].recv(4096)
                    except (ConnectionResetError, OSError):
                        close_client(clients, fd_map, poller, fd)
                        continue
                    if not chunk:
                        close_client(clients, fd_map, poller, fd)
                        continue
                    state["inb"].extend(chunk)
                    process_incoming(clients, state)
                    if fd in fd_map:
                        update_interest(poller, state)

                if fd in fd_map and event & select.POLLOUT:
                    try:
                        sent = state["sock"].send(state["outb"])
                        del state["outb"][:sent]
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        close_client(clients, fd_map, poller, fd)
                        continue
                    if fd in fd_map:
                        update_interest(poller, state)

    except KeyboardInterrupt:
        print("\nServer dihentikan")
    finally:
        for fd in list(fd_map.keys()):
            if fd != server.fileno():
                close_client(clients, fd_map, poller, fd)
        try:
            poller.unregister(server.fileno())
        except OSError:
            pass
        server.close()


if __name__ == "__main__":
    main()
