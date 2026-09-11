"""Pipeline orchestration: fetch -> normalize -> classify -> render."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from .classify import classify, load_cache, save_cache
from .config import Config, load_config
from .http import FixtureHttp, Http
from .model import Event, SourceStatus
from .normalize import (
    PlaceResolver,
    apply_source_filters,
    dedupe,
    flag_time,
    in_scope,
    resolve_places,
)
from .render import render_site
from .sources import make_source

log = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def load_last_good(path: Path) -> tuple[list[Event], str | None]:
    if not path.exists():
        return [], None
    d = json.loads(path.read_text(encoding="utf-8"))
    return [Event.from_dict(x) for x in d["events"]], d.get("fetched_at")


def save_last_good(path: Path, events: list[Event]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"fetched_at": _utcnow(), "events": [e.to_dict() for e in events]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def fetch_all(cfg: Config, root: Path, offline: bool, only: set[str] | None,
              record: bool = False, persist: bool = True) -> tuple[list[Event], list[SourceStatus]]:
    events: list[Event] = []
    statuses: list[SourceStatus] = []
    for scfg in cfg.sources:
        if only and scfg.name not in only:
            continue
        if not scfg.enabled:
            statuses.append(SourceStatus(scfg.name, "disabled"))
            continue
        fixture_dir = root / "tests" / "fixtures" / scfg.name
        last_good = root / "cache" / "last_good" / f"{scfg.name}.json"
        src = make_source(scfg)
        try:
            http = FixtureHttp(fixture_dir) if offline else Http(record_dir=fixture_dir if record else None)
            got = apply_source_filters(src.fetch(http), scfg)
            if not offline and persist:
                save_last_good(last_good, got)
            statuses.append(SourceStatus(scfg.name, "ok", len(got), _utcnow()))
            log.info("%s: %d events", scfg.name, len(got))
        except Exception as e:
            log.exception("%s: fetch failed", scfg.name)
            got, fetched_at = load_last_good(last_good)
            status = "fallback" if got else "error"
            statuses.append(SourceStatus(scfg.name, status, len(got), fetched_at, str(e)[:300]))
        events.extend(got)
    return events, statuses


def build(root: Path, out_dir: Path, offline: bool = False, use_llm: bool = True,
          only: set[str] | None = None, record: bool = False, persist: bool | None = None) -> int:
    """`persist`: write cache/last_good (default: only in CI, to avoid local/CI commit conflicts)."""
    cfg = load_config(root / "config.yaml")
    if persist is None:
        persist = bool(os.environ.get("CI"))
    events, statuses = fetch_all(cfg, root, offline, only, record, persist)
    log.info("fetched %d raw events", len(events))

    resolver = PlaceResolver(cfg)
    events = flag_time(events, cfg.horizon_days)
    resolve_places(events, resolver, {s.name: s.place for s in cfg.sources})

    cache_path = root / "cache" / "classifications.json"
    cache = load_cache(cache_path)
    cache = classify(events, cfg, cache, use_llm=use_llm)
    save_cache(cache_path, cache)

    before = len(events)
    events = [e for e in events if in_scope(e, resolver)]
    log.info("scope filter: %d -> %d", before, len(events))
    priorities = {s.name: s.priority for s in cfg.sources}
    events = dedupe(events, priorities)
    log.info("after dedup: %d", len(events))

    if not events and not only:
        raise SystemExit("no events at all – refusing to publish an empty site")
    render_site(events, cfg, statuses, out_dir)
    log.info("site written to %s", out_dir)
    return len(events)
