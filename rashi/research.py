"""Research department (R28, his 2026-11-12 7:23pm voice note): before writing code or picking
an integration, look for open-source projects that already do it, with their star counts.

Keyless and zero-spend: GitHub's repository search API (10 req/min unauthenticated) over urllib.
(DuckDuckGo's HTML endpoint was tried first and silently returns an anomaly page from datacenter
IPs - observed 2026-11-13; GitHub search is the better fit anyway: stars answer his "good number
of stars" rule directly.)

`fetch(url) -> str` is injectable so tests never touch the network. Failures return an error
note and no results - research is advisory context, never a hard gate, and never invents hits."""
import json
import urllib.parse
import urllib.request

API = "https://api.github.com/search/repositories?sort=stars&order=desc&q="
_UA = {"User-Agent": "rashi-research", "Accept": "application/vnd.github+json"}


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def oss_alternatives(topic, fetcher=fetch, max_results=5):
    """Most-starred repos for a topic: [{name, url, stars, description}]. Honest on failure."""
    query = topic
    try:
        data = json.loads(fetcher(API + urllib.parse.quote(query)))
    except Exception as ex:  # offline / rate-limited / bad JSON: say so, return nothing
        return {"query": query, "results": [], "error": f"{type(ex).__name__}: {str(ex)[:120]}"}
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        message = data.get("message", "invalid search response") if isinstance(data, dict) else "invalid search response"
        return {"query": query, "results": [], "error": str(message)[:120]}
    results = [{"name": it.get("full_name", "?"), "url": it.get("html_url", ""),
                "stars": it.get("stargazers_count", 0),
                "description": (it.get("description") or "")[:140]}
               for it in data.get("items", [])[:max_results]]
    return {"query": query, "results": results, "error": None}


def as_context(found):
    """One text block for brainstorm/spec context; honest when the search failed or found nothing."""
    if found["error"]:
        return f"OSS research for '{found['query']}' FAILED: {found['error']} - no results claimed."
    if not found["results"]:
        return f"OSS research for '{found['query']}' found nothing."
    lines = [f"Existing open-source projects for '{found['query']}' (reuse before building; "
             "prefer the ones with real adoption):"]
    lines += [f"- {r['name']} ({r['stars']} stars): {r['description']} {r['url']}"
              for r in found["results"]]
    return "\n".join(lines)
