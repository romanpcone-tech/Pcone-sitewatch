"""Polite GET/HEAD. Two requests per second, no other methods."""

from __future__ import annotations

import time
import urllib.error
import urllib.request

UA = "PCone-sitewatch"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, rps: float = 2.0):
        self.interval = 1.0 / rps if rps else 0
        self._next = 0.0
        self.opener = urllib.request.build_opener(_NoRedirect)

    def get_text(self, url: str, timeout: float = 20) -> tuple[int, str]:
        status, _headers, body, _err = self.request(url, "GET", timeout=timeout)
        return status, body

    def request(self, url: str, method: str = "GET", timeout: float = 20, limit: int = 1_500_000):
        if method not in {"GET", "HEAD"}:
            raise ValueError("only GET and HEAD")
        self._wait()
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": "*/*"})
        try:
            with self.opener.open(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200) or 200
                body = ""
                if method != "HEAD":
                    raw = resp.read(limit)
                    charset = resp.headers.get_content_charset() or "utf-8"
                    body = raw.decode(charset, "replace")
                return status, {k.lower(): v for k, v in resp.headers.items()}, body, ""
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read(65536).decode("utf-8", "replace")
            except Exception:
                body = ""
            return int(exc.code or 0), {}, body, ""
        except Exception as exc:
            return 0, {}, "", f"{type(exc).__name__}"

    def _wait(self) -> None:
        if self.interval <= 0:
            return
        now = time.monotonic()
        if now < self._next:
            time.sleep(self._next - now)
        self._next = time.monotonic() + self.interval
