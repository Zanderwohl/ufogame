from threading import Event, Thread
from typing import Optional
from zeroconf import IPVersion, ServiceInfo, Zeroconf
import socket


def start_mdns_advertiser(instance: str, port: int, properties: Optional[dict] = None) -> Event:
    stop_event = Event()
    t = Thread(target=_advertise_mdns, args=(instance, port, properties or {}, stop_event), daemon=True)
    t.start()
    return stop_event


def _advertise_mdns(instance: str, port: int, properties: dict, stop_event: Event) -> None:
    zeroconf = Zeroconf(ip_version=IPVersion.All)
    asc = socket.gethostname()
    type_ = "_ufogame._tcp.local."
    name = f"{instance}.{type_}"
    ip = _get_local_ip()
    info = ServiceInfo(
        type_,
        name,
        addresses=[socket.inet_aton(ip)],
        port=port,
        weight=0,
        priority=0,
        properties={"host": asc, **properties},
        server=f"{instance}.local.",
    )
    zeroconf.register_service(info)
    try:
        stop_event.wait()
    finally:
        zeroconf.unregister_service(info)
        zeroconf.close()


def _get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("224.0.0.251", 5353))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


