
import time
import logging
import socket
from typing import List
from common.runner import run

PORT = 8200
_server_sock: socket.socket | None = None
_client_socks: List[socket.socket] = []
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
    global _server_sock, _client_socks, _last_sent
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
            c.setblocking(False)
            _client_socks.append(c)
            logger.info(f"Accepted connection from {addr}")

        # Read from clients and remove disconnected
        alive: List[socket.socket] = []
        for c in _client_socks:
            try:
                data = c.recv(1)
                if data == b"":
                    try:
                        c.close()
                    except Exception:
                        pass
                    logger.info("Client disconnected")
                    continue
                elif data:
                    # Drain rest quickly
                    try:
                        rest = c.recv(4096)
                        data += rest
                    except BlockingIOError:
                        pass
                    logger.info(f"from client: {data!r}")
                alive.append(c)
            except BlockingIOError:
                alive.append(c)
            except Exception as e:
                try:
                    c.close()
                except Exception:
                    pass
                logger.debug(f"Client error; dropping: {e}")
        _client_socks = alive

        now = time.monotonic()
        if now - _last_sent >= 1.0:
            _last_sent = now
            msg = b"Hello from server\n"
            for c in list(_client_socks):
                try:
                    c.sendall(msg)
                except Exception:
                    try:
                        c.close()
                    except Exception:
                        pass
                    _client_socks.remove(c)
        return True
    except Exception as e:
        logger.debug(f"Server frame error: {e}")
        return True
