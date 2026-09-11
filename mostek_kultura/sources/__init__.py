"""Source registry: config `type` -> parser class."""

from __future__ import annotations

from .antee_rss import AnteeRssSource
from .base import Source
from .galileo import GalileoSource
from .goout import GoOutSource
from .public4u import Public4uSource

REGISTRY: dict[str, type[Source]] = {
    "galileo": GalileoSource,
    "antee_rss": AnteeRssSource,
    "public4u": Public4uSource,
    "goout": GoOutSource,
}


def make_source(cfg) -> Source:
    try:
        cls = REGISTRY[cfg.type]
    except KeyError as e:
        raise ValueError(f"unknown source type '{cfg.type}' for source '{cfg.name}'") from e
    return cls(cfg)
