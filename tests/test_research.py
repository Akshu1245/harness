import json

from rashi.research import as_context, oss_alternatives

PAYLOAD = json.dumps({"items": [
    {"full_name": "foo/bar", "html_url": "https://github.com/foo/bar", "stargazers_count": 9000,
     "description": "A thing"},
    {"full_name": "baz/qux", "html_url": "https://github.com/baz/qux", "stargazers_count": 12,
     "description": None},
]})


def test_results_carry_stars_and_cope_with_null_description():
    r = oss_alternatives("screenshot testing", fetcher=lambda url: PAYLOAD)
    assert r["error"] is None
    assert r["results"][0] == {"name": "foo/bar", "url": "https://github.com/foo/bar",
                               "stars": 9000, "description": "A thing"}
    assert r["results"][1]["description"] == ""


def test_fetch_failure_is_honest_not_fatal():
    def down(url):
        raise OSError("offline")
    r = oss_alternatives("x", fetcher=down)
    assert r["results"] == [] and "offline" in r["error"]
    assert "FAILED" in as_context(r) and "no results claimed" in as_context(r)


def test_rate_limit_page_is_an_error_not_empty_success():
    r = oss_alternatives("x", fetcher=lambda url: '{"message": "API rate limit exceeded"}')
    assert r["results"] == [] and r["error"] == "API rate limit exceeded"
    assert "FAILED" in as_context(r)


def test_context_lists_stars():
    ctx = as_context({"query": "q", "results": [
        {"name": "a/b", "url": "https://u", "stars": 5, "description": "d"}], "error": None})
    assert "a/b (5 stars)" in ctx and "reuse before building" in ctx
