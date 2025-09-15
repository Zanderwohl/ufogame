
import time
import logging
import socket
import json
from typing import Dict
from common.runner import run
from common.panel import Panel


class Client:
    def __init__(self, panel: Panel, sock: socket.socket):
        self.panel = panel
        self.sock = sock

PORT = 8200
_server_sock: socket.socket | None = None
_clients: Dict[int, Client] = {}
_last_sent: float = 0.0

def main():
    return run(
        logger_name="server",
        advertise_instance="ufogame-0",
        advertise_port=PORT,
        advertise_properties=None,
        run_frame=run_frame,
    )

def run_frame(logger: logging.Logger) -> bool:
    global _server_sock, _clients, _last_sent
    try:
        if _server_sock is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", PORT))
            s.listen(16)
            s.setblocking(False)
            _server_sock = s
            logger.info(f"Server listening on 0.0.0.0:{PORT}")

        # Accept any pending connections
        while True:
            try:
                c, addr = _server_sock.accept()
            except BlockingIOError:
                break
            # Read one JSON line handshake with blocking timeout
            c.settimeout(1.0)
            data = b""
            try:
                while not data.endswith(b"\n") and len(data) < 65536:
                    chunk = c.recv(4096)
                    if not chunk:
                        break
                    data += chunk
            finally:
                c.settimeout(0.0)
            panel_obj: Panel | None = None
            player_id: int | None = None
            try:
                obj = json.loads(data.decode("utf-8")) if data else {}
                player_id = int(obj.get("player")) if obj.get("player") is not None else None
                caps = obj.get("capabilities") if isinstance(obj, dict) else None
                if player_id is not None:
                    panel_obj = Panel(player_id)
                    if isinstance(caps, list):
                        panel_obj.capabilities = caps
            except Exception:
                panel_obj = None
                player_id = None
            if not player_id or not (1 <= player_id <= 9) or panel_obj is None:
                try:
                    c.close()
                except Exception:
                    pass
                logger.debug(f"Rejected connection {addr}: missing/invalid player id")
            else:
                # Replace any existing client for this player
                old = _clients.pop(player_id, None)
                if old is not None:
                    try:
                        old.sock.close()
                    except Exception:
                        pass
                    logger.info(f"Player {player_id} replaced existing connection")
                c.setblocking(False)
                _clients[player_id] = Client(panel=panel_obj, sock=c)
                logger.info(f"Player {player_id} connected from {addr}")
                logger.info(f"Player {player_id} capabilities: {panel_obj.capabilities}")

        # Read from clients and remove disconnected
        gone: list[int] = []
        for pid, client in _clients.items():
            c = client.sock
            try:
                data = c.recv(1)
                if data == b"":
                    try:
                        c.close()
                    except Exception:
                        pass
                    logger.info(f"Player {pid} disconnected")
                    gone.append(pid)
                elif data:
                    # Drain rest quickly
                    try:
                        rest = c.recv(4096)
                        data += rest
                    except BlockingIOError:
                        pass
                    logger.info(f"from player {pid}: {data!r}")
            except BlockingIOError:
                pass
            except Exception as e:
                try:
                    c.close()
                except Exception:
                    pass
                logger.debug(f"Player {pid} error; dropping: {e}")
                gone.append(pid)
        for pid in gone:
            _clients.pop(pid, None)

        now = time.monotonic()
        if now - _last_sent >= 1.0:
            _last_sent = now
            msg = b"Hello from server\n"
            for pid, client in list(_clients.items()):
                try:
                    client.sock.sendall(msg)
                except Exception:
                    try:
                        client.sock.close()
                    except Exception:
                        pass
                    _clients.pop(pid, None)
        return True
    except Exception as e:
        logger.debug(f"Server frame error: {e}")
        return True
