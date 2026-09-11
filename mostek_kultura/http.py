"""HTTP client with browser UA, retries and a fixture mode for offline runs."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0 Safari/537.36"
)
RETRY_STATUS = {429, 500, 502, 503, 504}


def _key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


class Http:
    """Live client. `get_text` returns decoded body, `get_json` parsed JSON."""

    def __init__(self, timeout: float = 20.0, retries: int = 3, record_dir: Path | None = None):
        self.client = httpx.Client(
            headers={"User-Agent": UA, "Accept-Language": "cs,en;q=0.5"},
            timeout=timeout,
            follow_redirects=True,
            # bind IPv4: GitHub runners have no IPv6 route and httpx does not fall back
            # from an AAAA record to A ("Network is unreachable" on mestovrchlabi.cz)
            transport=httpx.HTTPTransport(local_address="0.0.0.0", retries=1),
        )
        self.retries = retries
        self.record_dir = record_dir

    def _get(self, url: str) -> httpx.Response:
        last: Exception | None = None
        for attempt in range(self.retries):
            try:
                r = self.client.get(url)
                if r.status_code in RETRY_STATUS:
                    raise httpx.HTTPStatusError(f"status {r.status_code}", request=r.request, response=r)
                r.raise_for_status()
                return r
            except (httpx.HTTPError, httpx.TransportError) as e:
                last = e
                wait = 2 ** attempt
                log.warning("GET %s failed (%s), retry in %ss", url, e, wait)
                time.sleep(wait)
        raise RuntimeError(f"GET {url} failed after {self.retries} attempts: {last}")

    def _record(self, url: str, body: str, ext: str) -> None:
        if not self.record_dir:
            return
        self.record_dir.mkdir(parents=True, exist_ok=True)
        (self.record_dir / f"{_key(url)}.{ext}").write_text(body, encoding="utf-8")
        manifest = self.record_dir / "manifest.json"
        data = json.loads(manifest.read_text()) if manifest.exists() else {}
        data[url] = f"{_key(url)}.{ext}"
        manifest.write_text(json.dumps(data, indent=1, ensure_ascii=False))

    def get_text(self, url: str, encoding: str | None = None) -> str:
        r = self._get(url)
        if encoding:
            r.encoding = encoding
        body = r.text
        self._record(url, body, "html")
        return body

    def get_json(self, url: str) -> dict:
        r = self._get(url)
        self._record(url, r.text, "json")
        return r.json()


class FixtureHttp:
    """Offline client: serves recorded responses from `tests/fixtures/<source>/`."""

    def __init__(self, fixture_dir: Path):
        self.dir = fixture_dir
        manifest = fixture_dir / "manifest.json"
        self.manifest: dict[str, str] = json.loads(manifest.read_text()) if manifest.exists() else {}

    def _read(self, url: str) -> str:
        name = self.manifest.get(url)
        if not name:
            raise FileNotFoundError(f"no fixture for {url} in {self.dir}")
        return (self.dir / name).read_text(encoding="utf-8")

    def get_text(self, url: str, encoding: str | None = None) -> str:
        return self._read(url)

    def get_json(self, url: str) -> dict:
        return json.loads(self._read(url))
