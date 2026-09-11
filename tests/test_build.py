import json

from mostek_kultura.build import build


def test_offline_build(root, tmp_path):
    n = build(root, tmp_path, offline=True, use_llm=False)
    assert n > 20
    events = json.loads((tmp_path / "events.json").read_text(encoding="utf-8"))
    assert events["events"] and all(e["place"] or e["venue"] for e in events["events"])
    assert all(e["category"] for e in events["events"])
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    for key in ("today", "tomorrow", "weekend", "week"):
        assert {"count", "ongoing_count", "events"} <= set(summary[key])
        assert len(summary[key]["events"]) <= 10
    assert (tmp_path / "summary.json").stat().st_size < 16_000
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert 'id="data"' in html and "Kultura kolem Mostku" in html
    status = json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))
    assert {s["name"] for s in status["sources"]} >= {"mostek", "lazne-belohrad", "dvur-kralove", "trutnov"}
