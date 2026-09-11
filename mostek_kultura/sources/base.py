"""Base class for sources."""

from __future__ import annotations

import re
from typing import Protocol

from bs4 import BeautifulSoup

from ..config import SourceConfig
from ..model import Event


class HttpLike(Protocol):
    def get_text(self, url: str, encoding: str | None = None) -> str: ...
    def get_json(self, url: str) -> dict: ...


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


class Source:
    def __init__(self, cfg: SourceConfig):
        self.cfg = cfg
        self.name = cfg.name

    def fetch(self, http: HttpLike) -> list[Event]:
        raise NotImplementedError

    def event(self, **kw) -> Event:
        """Create an Event with source defaults filled in."""
        kw.setdefault("source", self.name)
        return Event(**kw)
