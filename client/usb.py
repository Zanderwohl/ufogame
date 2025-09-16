import logging
from typing import Dict, List

try:
    import serial  # type: ignore
    from serial.tools import list_ports  # type: ignore
except Exception as e:  # pragma: no cover
    serial = None
    list_ports = None

from common.packets import Packet, decode_lines, encode_packet


# Open USB CDC devices and exchange Packet-framed JSON lines.
_SERIALS: Dict[str, "serial.Serial"] = {}
_RX_BUFFERS: Dict[str, bytes] = {}


def _iter_candidate_ports() -> List[str]:
    if list_ports is None:
        return []
    ports = []
    for p in list_ports.comports():
        dev = getattr(p, "device", None) or getattr(p, "name", None)
        if not dev:
            continue
        ports.append(str(dev))
    return ports


def attempt_connections(logger: logging.Logger) -> bool:
    """Scan for new USB serial devices and open them.

    Returns True if at least one connection is (or remains) available; False if none.
    """
    if serial is None:
        logger.debug("pyserial not installed; USB disabled")
        return False

    any_available = bool(_SERIALS)
    for dev in _iter_candidate_ports():
        if dev in _SERIALS:
            any_available = True
            continue
        try:
            ser = serial.Serial(dev, baudrate=115200, timeout=0)  # Non-blocking
            _SERIALS[dev] = ser
            _RX_BUFFERS[dev] = b""
            any_available = True
            logger.info(f"USB device connected: {dev}")
        except Exception as e:
            logger.debug(f"Failed opening {dev}: {e}")
    # Drop handles that disappeared
    for dev in list(_SERIALS.keys()):
        ser = _SERIALS[dev]
        if not ser.is_open:
            try:
                ser.close()
            except Exception:
                pass
            _SERIALS.pop(dev, None)
            _RX_BUFFERS.pop(dev, None)
            logger.info(f"USB device disconnected: {dev}")
    return any_available


def receive_packets(logger: logging.Logger) -> Dict[str, List[Packet]]:
    """Drain available data from each USB device and decode Packets.

    Returns mapping of device-id (port name) to list of Packets.
    """
    packets_by_dev: Dict[str, List[Packet]] = {}
    for dev, ser in list(_SERIALS.items()):
        try:
            while True:
                data = ser.read(4096)
                if not data:
                    break
                buf = _RX_BUFFERS.get(dev, b"") + data
                decoded, remainder = decode_lines(buf)
                _RX_BUFFERS[dev] = remainder
                if decoded:
                    packets_by_dev.setdefault(dev, []).extend(decoded)
        except Exception as e:
            try:
                ser.close()
            except Exception:
                pass
            _SERIALS.pop(dev, None)
            _RX_BUFFERS.pop(dev, None)
            logger.info(f"USB device error/disconnected: {dev} ({e})")
    return packets_by_dev


def send_packet(dev: str, packet: Packet) -> bool:
    ser = _SERIALS.get(dev)
    if ser is None:
        return False
    try:
        ser.write(encode_packet(packet))
        ser.flush()
        return True
    except Exception:
        try:
            ser.close()
        except Exception:
            pass
        _SERIALS.pop(dev, None)
        _RX_BUFFERS.pop(dev, None)
        return False


def send_packet_all(packet: Packet) -> int:
    data = encode_packet(packet)
    delivered = 0
    for dev, ser in list(_SERIALS.items()):
        try:
            ser.write(data)
            ser.flush()
            delivered += 1
        except Exception:
            try:
                ser.close()
            except Exception:
                pass
            _SERIALS.pop(dev, None)
            _RX_BUFFERS.pop(dev, None)
    return delivered


