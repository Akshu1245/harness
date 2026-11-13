"""URL guard (same logic the cloud runner uses): public http(s) hosts only."""
import ipaddress, socket
from urllib.parse import urlparse

# Ranges Python's is_private/is_reserved flags miss on some versions (verified on 3.10):
# fc00::/7 IPv6 unique-local and 100.64.0.0/10 carrier-grade NAT both passed the old check.
_BLOCKED_NETS = tuple(ipaddress.ip_network(n) for n in ("fc00::/7", "fec0::/10", "100.64.0.0/10"))


def _blocked(ip) -> bool:
    if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
            or ip.is_multicast or ip.is_unspecified):
        return True
    mapped = getattr(ip, "ipv4_mapped", None)  # ::ffff:127.0.0.1 must inherit the v4 verdict
    if mapped is not None:
        return _blocked(mapped)
    return any(ip in n for n in _BLOCKED_NETS)


def url_is_public(url: str, resolver=socket.getaddrinfo) -> bool:
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    try:
        infos = resolver(p.hostname, None)
    except OSError:
        return False
    for info in infos:
        if _blocked(ipaddress.ip_address(info[4][0])):
            return False
    return bool(infos)
