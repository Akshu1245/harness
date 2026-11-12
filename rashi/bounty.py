"""Bug-bounty scope guard. Deny by default; out-of-scope beats in-scope; no record, no run."""
import ipaddress, json
from urllib.parse import urlparse


def _match(host, pat):
    host, pat = host.lower().rstrip("."), pat.lower().rstrip(".")
    if pat.startswith("*."):
        return host.endswith(pat[1:]) and host != pat[2:]
    return host == pat


class Scope:
    REQUIRED = ("program", "policy_url", "in_scope", "date")

    def __init__(self, record):
        missing = [k for k in self.REQUIRED if not record.get(k)]
        if missing:
            raise ValueError(f"authorization record missing: {missing}")
        self.r = record

    @classmethod
    def load(cls, path):
        return cls(json.loads(open(path).read()))

    def allows(self, url):
        u = urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname:
            return False, "bad url"
        h = u.hostname
        try:
            ipaddress.ip_address(h)
            return False, "raw IP not allowed"
        except ValueError:
            pass
        if any(_match(h, p) for p in self.r.get("out_of_scope", [])):
            return False, "out of scope"
        if any(_match(h, p) for p in self.r["in_scope"]):
            return True, "in scope"
        return False, "not listed"

    def check(self, url):
        ok, why = self.allows(url)
        if not ok:
            raise PermissionError(f"{url}: {why}")
        return url
