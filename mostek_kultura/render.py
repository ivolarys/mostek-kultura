"""Render site/: index.html (data inlined), events.json, summary.json, status.json."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import Config
from .dates import now, today
from .model import Event, SourceStatus

TEMPLATES = Path(__file__).parent / "templates"


def _ev_public(e: Event, cfg: Config) -> dict:
    return {
        "id": e.source_id,
        "title": e.title,
        "start": e.start.isoformat(),
        "end": e.end.isoformat() if e.end else None,
        "all_day": e.all_day,
        "ongoing": e.ongoing,
        "place": e.place,
        "venue": e.venue,
        "category": e.category or "jine",
        "category_label": cfg.category_label(e.category),
        "url": e.url,
        "image": e.image,
        "description": (e.description or "")[:300],
        "sources": [e.source, *e.sources],
    }


def _bucket(events: list[Event], d_from: date, d_to: date) -> tuple[list[Event], list[Event]]:
    """Events starting in [d_from, d_to] and ongoing events overlapping it."""
    main, ongoing = [], []
    for e in events:
        sd = e.start.date()
        if e.ongoing and not (d_from <= sd <= d_to):
            ed = e.end.date() if e.end else sd
            if sd <= d_to and ed >= d_from:
                ongoing.append(e)
        elif d_from <= sd <= d_to:
            main.append(e)
    return main, ongoing


def build_summary(events: list[Event], cfg: Config, statuses: list[SourceStatus]) -> dict:
    t = today()
    weekend_start = t + timedelta(days=(5 - t.weekday()) % 7) if t.weekday() < 5 else t - timedelta(days=t.weekday() - 5)
    ranges = {
        "today": (t, t),
        "tomorrow": (t + timedelta(days=1), t + timedelta(days=1)),
        "weekend": (weekend_start, weekend_start + timedelta(days=1)),
        "week": (t, t + timedelta(days=6)),
    }
    out = {"generated_at": now().isoformat(timespec="seconds"), "date": t.isoformat()}
    for key, (a, b) in ranges.items():
        main, ongoing = _bucket(events, a, b)
        out[key] = {
            "count": len(main),
            "ongoing_count": len(ongoing),
            "events": [{
                "title": e.title,
                "date": e.start.date().isoformat(),
                "time": None if e.all_day else e.start.strftime("%H:%M"),
                "place": e.place, "venue": e.venue,
                "category": cfg.category_label(e.category), "url": e.url,
            } for e in main[: cfg.summary_top_n]],
        }
    out["sources_ok"] = [s.name for s in statuses if s.status == "ok"]
    out["sources_failed"] = [s.name for s in statuses if s.status in ("fallback", "error")]
    return out


def render_site(events: list[Event], cfg: Config, statuses: list[SourceStatus], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    events = sorted(events, key=lambda e: (e.start, e.title))
    payload = {
        "generated_at": now().isoformat(timespec="seconds"),
        "tz": cfg.timezone,
        "categories": [{"slug": c.slug, "label": c.label} for c in cfg.categories],
        "places": [p.name for p in cfg.places],
        "events": [_ev_public(e, cfg) for e in events],
    }
    status = {"generated_at": payload["generated_at"], "sources": [asdict(s) for s in statuses]}
    summary = build_summary(events, cfg, statuses)

    (out_dir / "events.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")

    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2"]))
    tpl = env.get_template("index.html.j2")
    html = tpl.render(
        data_json=json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"),
        status=status, generated_at=payload["generated_at"], count=len(events),
    )
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("")
