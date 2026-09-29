"""verify-claims: an archive.org error page or refusal is "could not check", never reported as a content mismatch."""

from types import SimpleNamespace

import requests

from nflcast.predict.verify_claims import _redownload


def test_archive_error_page_is_not_a_mismatch():
    page = lambda code, body: (lambda *a, **k: SimpleNamespace(status_code=code, content=body))
    assert _redownload("u", b"abc", page(200, b"abc")) == (True, "")
    assert _redownload("u", b"abc", page(200, b"xyz")) == (False, "")       # a real mismatch is still a mismatch
    assert _redownload("u", b"abc", page(429, b"slow down")) == (None, "HTTP 429")

    def refused(*a, **k):
        raise requests.ConnectionError("refused")
    assert _redownload("u", b"abc", refused) == (None, "ConnectionError")
