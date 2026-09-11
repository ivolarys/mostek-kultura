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
- `cache/last_good/` zapisuje jen CI (env `CI`) nebo `build --persist`; lokální živé buildy ho nemění, aby nevznikaly konflikty s commity z CI. Když konflikt přesto vznikne, vezmi novější verzi souboru.
- LLM klasifikace: `OPENAI_API_KEY` (model `OPENAI_MODEL`, výchozí `gpt-5-mini`) nebo `ANTHROPIC_API_KEY` (`claude-haiku-4-5`); `LLM_PROVIDER` vynutí volbu. Bez klíče jen klíčová slova.
- `cache/` je commitovaná (klasifikace z LLM + poslední dobrý fetch per zdroj). CI ji commituje zpět s `[skip ci]`. Ruční oprava kategorie: editovat `cache/classifications.json`.
- Akce z Facebooku (nedají se stahovat) se doplňují ručně do `manual_events.yaml` (zdroj `rucne`, typ `manual`); formát viz komentář v souboru.

## Poznatky (s datem)

- 2026-09-11: GoOut API ignoruje geo parametry na `/schedules`; funguje `/venues?query=<město>` + `/schedules?venueIds[]=`. Max `limit=48`. `languages[]=cs` je povinné.
- 2026-09-11: Public4u má dva šablonové výpisy: mudk.cz (karty, jen datum) a trutnov.cz (tabulka s místem a časem). Pro mudk se dotahuje detail.
- 2026-09-11: mostek.cz (Galileo) vrací 503 na RSS, HTML jde s browser User-Agentem. `data-date-start` s časem 00:00:00 = bez času.
- 2026-09-11: mestovrchlabi.cz (Drupal 9): teaser má `<time datetime>` ISO a typ, detail adresu a konec; stránkování `?page=N` po 12.
- 2026-09-11: Galileo má dvě šablony výpisu: `.event-action__item` (mostek.cz) a starší `div.event.event-message` (bilatremesna.cz, dolnibrusnice.cz, kuks.cz); parser umí obě.
- 2026-09-11: hospital-kuks.cz (NPÚ) renderuje jen aktuální okno akcí, měsíční záložky jsou JS. domovsvatehojosefa.cz má akce na homepage (`article.b-article`), bez času.
- 2026-09-11: hkregion.cz má jinou šablonu než ostatní Public4u weby, zatím nepoužito.
- 2026-09-11: Vismo (WEBHOUSE) – mujicin.cz, munovapaka.cz: `kalendar-akci.asp?hledani=1&kdy=-1&datum_od=D.M.YYYY&datum_do=D.M.YYYY&pocet=100&submit=Vyhledat` (`id_org` není potřeba, dovodí se z domény; `pocet=100` obvykle obejde stránkování, `.strvpred a.aktivni` je záložní další strana). Výpis `#kalendarAkci .dok ul.ui > li`: `.n5-akce-datum` má datum/čas/místo pohromadě ("17.9.2026 18:00, Klenotnice muzea"), `.n5-akce-popis`, `.n5-akce-typ a`; čas i místo jsou rovnou ve výpisu, detail není potřeba. Nedatované "Dlouhodobé akce" se ukážou jen na nefiltrované výchozí stránce, dotaz na rozsah data je automaticky vynechá. mujicin.cz má tento kalendář fakticky mrtvý (poslední záznam z r. 2022) – zdroj `jicin` je zapojený správně, jen momentálně vrací 0 akcí.
- 2026-09-11: kultura-novapaka.cz (kulturní portál MKS a partnerů) je iso-8859-2, server-rendered, bez date-range dotazu i stránkování – vždy jen aktuální okno ~2–3 týdny (podobně jako hospital-kuks.cz). Položky `div.program <kategorie>` (druhá třída bývá se stopovací mezerou navíc), `.datum span` s minutami v `<sup>` ("11.&nbsp;září&nbsp;2026 od&nbsp;20<sup>00</sup>"), místo v `<p><strong>Kde</strong>: ...`.
- 2026-09-11: Přidání obce "Jičín" do `places` odkrylo prioritní chybu v `resolve_places`: dřív vyhrával `place_raw` nad `venue`, takže konkrétní venue jako "Valdštejnská lodžie" (GoOut vrací place_raw = město "Jičín") by spadlo pod obecné "Jičín" místo vlastního bucketu. Opraveno na `venue` napřed, `place_raw` jako fallback (test `test_lodzie_is_its_own_place`).
