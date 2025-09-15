import logging
import socket
import json

from zeroconf import Zeroconf, IPVersion

from common.panel import Panel, panel_to_json
from common.packets import Packet, TextPacket, decode_lines
from common.runner import run

SOCKET: socket.socket | None = None
PANEL: Panel | None = None

def main(player: int | None):
    global PANEL
    if player is None:
        print("No player specified")
        return 1
    PANEL = Panel(player)
    return run(
        logger_name=f"panel-{player}",
        advertise_instance=f"ufogame-{player}",
        advertise_port=8200 + player,
        advertise_properties={"player": str(player)},
        run_frame=run_frame,
    )

def attempt_connection(logger: logging.Logger) -> bool:
    global SOCKET, PANEL
    if SOCKET is None:
        try:
            service_type = "_ufogame._tcp.local."
            instance_name = f"ufogame-0.{service_type}"
            zc = Zeroconf(ip_version=IPVersion.All)
            try:
                info = zc.get_service_info(service_type, instance_name, timeout=1000)
            finally:
                zc.close()
            if not info or not info.addresses:
                logger.debug("No ufogame-0 service found via mDNS")
                return False
            ip_bytes = info.addresses[0]
            ip_str = socket.inet_ntoa(ip_bytes)
            port = info.port
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.75)
            s.connect((ip_str, port))
            # Send PANEL handshake as JSON line before switching to nonblocking
            try:
                payload = json.dumps(panel_to_json(PANEL) if PANEL else {}) + "\n"
                s.sendall(payload.encode("utf-8"))
            except Exception as e:
                try:
                    s.close()
                except Exception:
                    pass
                logger.debug(f"Failed sending handshake: {e}")
                return False
            s.setblocking(False)
            SOCKET = s
            logger.info(f"Connected to server at {ip_str}:{port}")
        except Exception as e:
            if SOCKET is not None:
                try:
                    SOCKET.close()
                except Exception:
                    pass
                SOCKET = None
            logger.debug(f"Connect attempt failed: {e}")
            return False
        return True

_RX_BUFFER: bytes = b""


def receive_packets(logger: logging.Logger) -> list[Packet]:
    global SOCKET, _RX_BUFFER
    packets: list[Packet] = []
    if SOCKET is None:
        return packets
    try:
        while True:
            try:
                data = SOCKET.recv(4096)
            except BlockingIOError:
                break
            if not data:
                try:
                    SOCKET.close()
                except Exception:
                    pass
                SOCKET = None
                logger.info("Server closed connection; will retry")
                break
            _RX_BUFFER += data
            decoded, remainder = decode_lines(_RX_BUFFER)
            _RX_BUFFER = remainder
            packets.extend(decoded)
    except Exception as e:
        try:
            SOCKET.close()
        except Exception:
            pass
        SOCKET = None
        logger.debug(f"Socket error; resetting: {e}")
    return packets


def run_frame(logger: logging.Logger) -> bool:
    global SOCKET

    if SOCKET is None:
        if not attempt_connection(logger):
            return True

    packets = receive_packets(logger)
    for p in packets:
        if isinstance(p, TextPacket):
            logger.info(f"recv: {p.text}")
    return True
