import json
import logging
import socket
import time
from typing import Dict, List

from common.gamestate import GameStatePacket, GameState
from common.packets import encode_packet, Packet, decode_lines, TextPacket

from common.panel import Panel, panel_from_json

class Client:
    def __init__(self, panel: Panel, sock: socket.socket):
        self.panel = panel
        self.sock = sock
        self.ready = False

PORT = 8200
_server_sock: socket.socket | None = None
_clients: Dict[int, Client] = {}
_last_sent: float = 0.0
_rx_buffers: Dict[int, bytes] = {}

def ensure_server_ready(logger: logging.Logger) -> None:
    global _server_sock
    if _server_sock is not None:
        return
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", PORT))
    s.listen(16)
    s.setblocking(False)
    _server_sock = s
    logger.info(f"Server listening on 0.0.0.0:{PORT}")


def accept_new_clients(logger: logging.Logger) -> list[int]:
    global _clients, _rx_buffers
    if _server_sock is None:
        return []

    new_clients = []

    # Bounded accepts per frame to avoid long frames
    for _ in range(32):
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
        except Exception as e:
            try:
                c.close()
            except Exception:
                pass
            logger.info(f"Handshake read failed from {addr}: {e}")
            continue
        finally:
            # Return to blocking mode for initial write; we'll switch to nonblocking later
            c.settimeout(None)

        panel_obj: Panel | None = None
        player_id: int | None = None
        try:
            obj = json.loads(data.decode("utf-8")) if data else {}
            if isinstance(obj, dict) and obj.get("player") is not None:
                panel_obj = panel_from_json(obj)
                player_id = panel_obj.player
        except Exception:
            panel_obj = None
            player_id = None

        if not player_id or not (1 <= player_id <= 9) or panel_obj is None:
            try:
                c.close()
            except Exception:
                pass
            preview = data[:200].decode("utf-8", errors="replace") if data else ""
            logger.info(f"Rejected connection {addr}: invalid handshake; data preview='{preview}'")
            continue

        # Replace any existing client for this player
        old = _clients.pop(player_id, None)
        if old is not None:
            try:
                old.sock.close()
            except Exception:
                pass
            logger.info(f"Player {player_id} replaced existing connection")

        # Send initial RESET in blocking mode to avoid EAGAIN on nonblocking send
        try:
            c.sendall(encode_packet(GameStatePacket(state=GameState.RESET)))
        except Exception as e:
            try:
                c.close()
            except Exception:
                pass
            logger.info(f"Failed to send initial RESET to player {player_id}; dropping: {e}")
            continue
        c.setblocking(False)
        _clients[player_id] = Client(panel=panel_obj, sock=c)
        new_clients.append(player_id)
        _rx_buffers[player_id] = b""
        logger.info(f"Player {player_id} connected from {addr}")
        logger.info(f"Player {player_id} capabilities: {panel_obj.capabilities}")
    return new_clients


def receive_packets(logger: logging.Logger) -> Dict[int, List[Packet]]:
    global _clients, _rx_buffers
    packets_by_player: Dict[int, List[Packet]] = {}
    gone: list[int] = []
    for pid, client in _clients.items():
        c = client.sock
        try:
            data = c.recv(4096)
            if data == b"":
                try:
                    c.close()
                except Exception:
                    pass
                logger.info(f"Player {pid} disconnected")
                gone.append(pid)
                continue
            elif data:
                buf = _rx_buffers.get(pid, b"") + data
                decoded, remainder = decode_lines(buf)
                _rx_buffers[pid] = remainder
                if decoded:
                    packets_by_player[pid] = decoded
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
        _rx_buffers.pop(pid, None)
    return packets_by_player


def send_heartbeat_if_due() -> None:
    global _last_sent
    now = time.monotonic()
    if now - _last_sent < 1.0:
        return
    _last_sent = now
    msg = encode_packet(TextPacket(text="Hello from server"))
    for pid, client in list(_clients.items()):
        try:
            client.sock.sendall(msg)
        except Exception:
            try:
                client.sock.close()
            except Exception:
                pass
            _clients.pop(pid, None)


def send_packet_to_player(player_id: int, packet: Packet) -> bool:
    client = _clients.get(player_id)
    if client is None:
        return False
    try:
        data = encode_packet(packet)
        client.sock.sendall(data)
        return True
    except Exception:
        try:
            client.sock.close()
        except Exception:
            pass
        _clients.pop(player_id, None)
        return False


def send_packet_to_all(packet: Packet) -> int:
    data = encode_packet(packet)
    delivered = 0
    for pid, client in list(_clients.items()):
        try:
            client.sock.sendall(data)
            delivered += 1
        except Exception:
            try:
                client.sock.close()
            except Exception:
                pass
            _clients.pop(pid, None)
    return delivered


def set_client_ready(player_id: int, ready: bool) -> None:
    client = _clients.get(player_id)
    if client is not None:
        client.ready = ready


def all_clients_ready() -> bool:
    if len(_clients) == 0:
        return False
    return all(client.ready for client in _clients.values())


def client_count() -> int:
    return len(_clients)
