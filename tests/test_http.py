import json

import pytest

from mostek_kultura.http import FixtureHttp


def _make(tmp_path, manifest: dict[str, str], contents: dict[str, str]):
    for name, body in contents.items():
        (tmp_path / name).write_text(body, encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return FixtureHttp(tmp_path)


def test_exact_hit(tmp_path):
    http = _make(
        tmp_path,
        {"https://example.cz/x?rok=2026&mesic=9": "a.html"},
        {"a.html": "<p>zari</p>"},
    )
    assert http.get_text("https://example.cz/x?rok=2026&mesic=9") == "<p>zari</p>"


def test_normalized_hit_single_candidate(tmp_path):
    """public4u-style: same path/keys, only rok=/mesic= differ -> unambiguous fallback."""
    http = _make(
        tmp_path,
        {"https://example.cz/redakce/index.php?lanG=cs&subakce=events&rok=2026&mesic=9": "a.html"},
        {"a.html": "<p>zari</p>"},
    )
    # A different month/year than what was recorded still resolves to the only candidate.
    got = http.get_text("https://example.cz/redakce/index.php?lanG=cs&subakce=events&rok=2027&mesic=2")
    assert got == "<p>zari</p>"


def test_normalized_hit_vismo_dates(tmp_path):
    """vismo-style: datum_od=/datum_do= are D.M.YYYY, still ignored as dynamic."""
    http = _make(
        tmp_path,
        {
            "https://example.cz/kalendar-akci.asp?hledani=1&kdy=-1&datum_od=11.09.2026"
            "&datum_do=10.11.2026&pocet=100&submit=Vyhledat": "a.html",
        },
        {"a.html": "<p>akce</p>"},
    )
    got = http.get_text(
        "https://example.cz/kalendar-akci.asp?hledani=1&kdy=-1&datum_od=1.12.2026"
        "&datum_do=30.1.2027&pocet=100&submit=Vyhledat"
    )
    assert got == "<p>akce</p>"


def test_normalized_hit_picks_closest_query_among_several(tmp_path):
    manifest = {
        "https://example.cz/x?rok=2026&mesic=9": "sep.html",
        "https://example.cz/x?rok=2026&mesic=10": "oct.html",
        "https://example.cz/x?rok=2026&mesic=11": "nov.html",
    }
    http = _make(tmp_path, manifest, {
        "sep.html": "zari", "oct.html": "rijen", "nov.html": "listopad",
    })
    # rok=2026&mesic=12 is lexicographically closest to mesic=10 or mesic=11, not mesic=9.
    got = http.get_text("https://example.cz/x?rok=2026&mesic=12")
    assert got in ("rijen", "listopad")
    assert got != "zari"


def test_miss_raises_file_not_found(tmp_path):
    http = _make(
        tmp_path,
        {"https://example.cz/x?rok=2026&mesic=9": "a.html"},
        {"a.html": "<p>zari</p>"},
    )
    with pytest.raises(FileNotFoundError):
        http.get_text("https://example.cz/y?rok=2026&mesic=9")  # different path
    with pytest.raises(FileNotFoundError):
        http.get_text("https://example.cz/x?jina=1")  # different key set


def test_get_json_uses_fallback_too(tmp_path):
    http = _make(
        tmp_path,
        {"https://example.cz/api?page=1": "a.json"},
        {"a.json": '{"ok": true}'},
    )
    assert http.get_json("https://example.cz/api?page=7") == {"ok": True}
