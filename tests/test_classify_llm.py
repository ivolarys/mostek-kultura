"""LLM path with a mocked API call: cache writes, confidence gate, place fill-in."""

from datetime import datetime

from mostek_kultura import classify as C
from mostek_kultura.dates import TZ
from mostek_kultura.model import Event


def _ev(title, **kw):
    return Event(title=title, start=datetime(2026, 9, 12, 19, tzinfo=TZ), source="t", url=f"u/{title}", **kw)


def test_llm_results_cached_and_applied(cfg, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    a = _ev("Slovanský vampyrismus", native_category="Ostatní", place="Trutnov")
    b = _ev("Něco v Hostinném", native_category=None, place=None, venue="Sokolovna")
    c = _ev("Nejisté", native_category=None, place="Mostek")
    calls = []

    def fake(cfg_, items):
        calls.append(items)
        return [
            C.Classification(id=a.source_id, category="prednaska", place="Trutnov", confidence=0.9),
            C.Classification(id=b.source_id, category="koncert", place="Hostinné", confidence=0.8),
            C.Classification(id=c.source_id, category="divadlo", place="Mostek", confidence=0.3),
            C.Classification(id="unknown", category="film", place=None, confidence=1),
        ]

    monkeypatch.setattr(C, "_call_llm", fake)
    cache = C.classify([a, b, c], cfg, {}, use_llm=True)
    assert len(calls) == 1 and {i["id"] for i in calls[0]} == {a.source_id, b.source_id, c.source_id}
    assert a.category == "prednaska"
    assert b.category == "koncert" and b.place == "Hostinné"
    assert c.category == "jine" and c.needs_review and cache[c.source_id]["needs_review"]
    assert "unknown" not in cache

    # second run: nothing pending, no API call
    calls.clear()
    C.classify([a, b, c], cfg, cache, use_llm=True)
    assert not calls and a.category == "prednaska"


def test_llm_failure_falls_back_to_keywords(cfg, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    e = _ev("Podzimní jarmark", place="Mostek")

    def boom(cfg_, items):
        raise RuntimeError("api down")

    monkeypatch.setattr(C, "_call_llm", boom)
    cache = C.classify([e], cfg, {}, use_llm=True)
    assert e.category == "trh" and cache == {}


def test_no_key_skips_llm(cfg, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    e = _ev("Koncert kapely", place="Mostek")
    monkeypatch.setattr(C, "_call_llm", lambda *_: (_ for _ in ()).throw(AssertionError("called")))
    C.classify([e], cfg, {}, use_llm=True)
    assert e.category == "koncert"
