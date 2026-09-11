# mostek-kultura — pravidla projektu

Komunikuj česky. Stručnost a přímost, minimum omáčky. Identifikátory v kódu a docstringy anglicky, prózu (README, komentáře k rozhodnutím, commity) česky.

## Co to je

Denní agregátor kulturních akcí v okolí obce Mostek. GitHub Actions (cron 04:30 UTC) spustí `python -m mostek_kultura build`, výsledek (`site/`) jde na GitHub Pages: https://ivolarys.github.io/mostek-kultura/. Home Assistant čte `summary.json` (REST senzory) a stránku zobrazuje v iframe (`?embed=1`). Plán: `~/.claude/plans/cht-l-bych-ud-lat-aplikaci-validated-quasar.md`.

## Delegování práce na subagenty (modely)

- **Fable** (fallback Opus 5): návrhy, plány, review, testy, kontroly, orchestrace.
- **Sonnet / Haiku**: implementace, rutinní kód, mechanické editace.

## Jak pracovat

- Prostředí: `.venv` vytvořený přes `uv venv --python 3.13 .venv`, závislosti `uv pip install -e .[dev]`.
- Testy: `.venv/bin/pytest -q` (offline, fixtures v `tests/fixtures/<zdroj>/`). Lint: `.venv/bin/ruff check mostek_kultura`.
- Lokální build bez sítě a bez LLM: `python -m mostek_kultura build --offline --no-llm`.
- Nový zdroj existujícího typu = jen záznam v `config.yaml`. Nový typ = modul v `mostek_kultura/sources/` + registrace v `sources/__init__.py` + fixture (`build --record --source <name> --no-llm`) + test.
- Fixtures se nahrávají příkazem `build --record` (zapíše `tests/fixtures/<zdroj>/manifest.json` + soubory). Po změně URL v configu nahrát znovu.
- `cache/` je commitovaná (klasifikace z Haiku + poslední dobrý fetch per zdroj). CI ji commituje zpět s `[skip ci]`. Ruční oprava kategorie: editovat `cache/classifications.json`.

## Poznatky (s datem)

- 2026-09-11: GoOut API ignoruje geo parametry na `/schedules`; funguje `/venues?query=<město>` + `/schedules?venueIds[]=`. Max `limit=48`. `languages[]=cs` je povinné.
- 2026-09-11: Public4u má dva šablonové výpisy: mudk.cz (karty, jen datum) a trutnov.cz (tabulka s místem a časem). Pro mudk se dotahuje detail.
- 2026-09-11: mostek.cz (Galileo) vrací 503 na RSS, HTML jde s browser User-Agentem. `data-date-start` s časem 00:00:00 = bez času.
- 2026-09-11: mestovrchlabi.cz (Drupal 9): teaser má `<time datetime>` ISO a typ, detail adresu a konec; stránkování `?page=N` po 12.
- 2026-09-11: hkregion.cz má jinou šablonu než ostatní Public4u weby, zatím nepoužito.
