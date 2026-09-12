import json

from mostek_kultura.build import build


def test_offline_build(root, tmp_path):
    n = build(root, tmp_path, offline=True, use_llm=False)
    assert n > 20
    events = json.loads((tmp_path / "events.json").read_text(encoding="utf-8"))
    assert events["events"] and all(e["place"] or e["venue"] for e in events["events"])
    assert all(e["category"] for e in events["events"])
    assert all(e["source_labels"] for e in events["events"])
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    for key in ("today", "tomorrow", "weekend", "week"):
        assert {"count", "ongoing_count", "events"} <= set(summary[key])
        assert len(summary[key]["events"]) <= 10
    assert (tmp_path / "summary.json").stat().st_size < 16_000
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert 'id="data"' in html and "Mostkultura · Kam vyrazíme?" in html
    assert "Malý Mostek. Velký dění." in html
    assert "color-mix" not in html
    assert "source_labels" in html
    assert 'rel="manifest"' in html
    assert (tmp_path / "manifest.webmanifest").exists()
    manifest = json.loads((tmp_path / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["name"] == manifest["short_name"] == "Mostkultura"
    for icon in manifest["icons"]:
        assert (tmp_path / icon["src"].split("?")[0]).is_file()
    assert (tmp_path / "logo.svg").is_file()
    assert (tmp_path / "icon.svg").exists()
    assert (tmp_path / "apple-touch-icon.png").exists() and (tmp_path / "icon-512.png").exists()
    assert 'rel="apple-touch-icon"' in html
    zdroje = (tmp_path / "zdroje.html").read_text(encoding="utf-8")
    assert "Vrchlabí" in zdroje and "Město Trutnov" in zdroje and "Regionální zdroje" in zdroje
    assert "Zatím bez vlastního zdroje" in zdroje  # e.g. Hostinné has no source yet
    status = json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))
    assert {s["name"] for s in status["sources"]} >= {"mostek", "lazne-belohrad", "dvur-kralove", "trutnov"}

    # Map view: every event carries geocoding fields, the committed cache resolves at least one
    # to venue precision offline, and Leaflet is vendored alongside the rendered site.
    assert all({"lat", "lon", "geo"} <= set(e) for e in events["events"])
    assert any(e["geo"] == "venue" for e in events["events"])
    assert (tmp_path / "leaflet" / "leaflet.js").exists()
    assert (tmp_path / "leaflet" / "leaflet.css").exists()
    assert "Mapa" in html
