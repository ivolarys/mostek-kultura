"""Load and validate config.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Place:
    name: str
    aliases: list[str] = field(default_factory=list)


@dataclass
class Category:
    slug: str
    label: str
    keywords: list[str] = field(default_factory=list)


@dataclass
class SourceConfig:
    name: str
    type: str
    url: str = ""
    enabled: bool = True
    priority: int = 5
    place: str | None = None
    exclude_title: str | None = None
    max_events: int | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class Config:
    timezone: str
    horizon_days: int
    summary_top_n: int
    places: list[Place]
    venues_allow: list[str]
    categories: list[Category]
    category_map: dict[str, str]
    sources: list[SourceConfig]

    @property
    def category_slugs(self) -> list[str]:
        return [c.slug for c in self.categories]

    def category_label(self, slug: str | None) -> str:
        for c in self.categories:
            if c.slug == slug:
                return c.label
        return "Jiné"


KNOWN_SOURCE_KEYS = {"name", "type", "url", "enabled", "priority", "place", "exclude_title", "max_events"}


def load_config(path: Path) -> Config:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    places = [Place(p["name"], p.get("aliases") or []) for p in raw.get("places", [])]
    cats = [Category(c["slug"], c["label"], c.get("keywords") or []) for c in raw["categories"]]
    slugs = {c.slug for c in cats}
    cmap = {str(k).lower(): v for k, v in (raw.get("category_map") or {}).items()}
    for k, v in cmap.items():
        if v not in slugs:
            raise ValueError(f"category_map: '{k}' -> unknown category '{v}'")
    sources = []
    names = set()
    for s in raw.get("sources", []):
        if s["name"] in names:
            raise ValueError(f"duplicate source name {s['name']}")
        names.add(s["name"])
        extra = {k: v for k, v in s.items() if k not in KNOWN_SOURCE_KEYS}
        sources.append(SourceConfig(
            name=s["name"], type=s["type"], url=s.get("url", ""), enabled=s.get("enabled", True),
            priority=int(s.get("priority", 5)), place=s.get("place"),
            exclude_title=s.get("exclude_title"), max_events=s.get("max_events"), extra=extra,
        ))
    return Config(
        timezone=raw.get("timezone", "Europe/Prague"),
        horizon_days=int(raw.get("horizon_days", 60)),
        summary_top_n=int(raw.get("summary_top_n", 10)),
        places=places,
        venues_allow=raw.get("venues_allow") or [],
        categories=cats,
        category_map=cmap,
        sources=sources,
    )
