"""URL guard (same logic the cloud runner uses): public http(s) hosts only."""
import ipaddress, socket
from urllib.parse import urlparse

def url_is_public(url: str, resolver=socket.getaddrinfo) -> bool:
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    try:
        infos = resolver(p.hostname, None)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return bool(infos)
