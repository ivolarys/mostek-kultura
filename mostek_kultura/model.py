"""Core data model."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class Event:
    title: str
    start: datetime
    source: str
    url: str = ""
    end: datetime | None = None
    all_day: bool = False
    place: str | None = None          # canonical municipality (after normalization)
    place_raw: str | None = None      # place hint as given by the source
    venue: str | None = None
    category: str | None = None       # canonical slug
    native_category: str | None = None
    description: str = ""
    image: str | None = None
    native_id: str | None = None
    ongoing: bool = False
    sources: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    needs_review: bool = False
    lat: float | None = None
    lon: float | None = None
    geo: str | None = None            # "venue" | "place" | None (precision of lat/lon)

    @property
    def source_id(self) -> str:
        key = self.native_id or self.url or f"{self.title}|{self.start.isoformat()}"
        return f"{self.source}:{hashlib.sha1(key.encode('utf-8')).hexdigest()[:12]}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["id"] = self.source_id
        d["start"] = self.start.isoformat()
        d["end"] = self.end.isoformat() if self.end else None
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Event:
        d = dict(d)
        d.pop("id", None)
        d["start"] = datetime.fromisoformat(d["start"])
        d["end"] = datetime.fromisoformat(d["end"]) if d.get("end") else None
        return cls(**d)


@dataclass
class SourceStatus:
    name: str
    status: str            # ok | fallback | error | disabled
    count: int = 0
    fetched_at: str | None = None
    error: str | None = None
