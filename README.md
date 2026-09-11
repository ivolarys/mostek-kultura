# Kultura kolem Mostku

Denní přehled kulturních a společenských akcí v okolí obce Mostek (okres Trutnov): dnes, zítra, víkend, tento týden. Členěno podle typu akce a podle obce.

- Veřejná stránka: **https://ivolarys.github.io/mostek-kultura/**
- JSON pro Home Assistant: `https://ivolarys.github.io/mostek-kultura/summary.json`
- Kompaktní režim pro iframe: `?embed=1&tab=week`
- Zdroje podle obce: `https://ivolarys.github.io/mostek-kultura/zdroje.html`

## Jak to funguje

1. GitHub Actions každý den ráno stáhne akce ze zdrojů v `config.yaml` (obecní weby, kalendář Lázní Bělohrad, GoOut).
2. Akce se namapují na obce z whitelistu, sloučí se duplicity napříč zdroji a doplní se kategorie (nativní kategorie zdroje → LLM → klíčová slova). LLM je OpenAI (`gpt-5-mini`) nebo Anthropic (Claude Haiku) podle toho, který klíč je nastavený.
3. Vygeneruje se statický web (`site/`) a nasadí se na GitHub Pages. Klasifikace se ukládá do `cache/` v repu, takže se každá akce klasifikuje jen jednou.

Když nějaký zdroj spadne, použijí se jeho data z posledního úspěšného běhu (`cache/last_good/`), stav je vidět v patičce stránky a v `status.json`.

## Lokální spuštění

```bash
uv venv --python 3.13 .venv && uv pip install --python .venv/bin/python -e .[dev]
.venv/bin/pytest -q
.venv/bin/python -m mostek_kultura build --offline --no-llm   # z fixtures, bez sítě
.venv/bin/python -m mostek_kultura build                      # naživo; OPENAI_API_KEY nebo ANTHROPIC_API_KEY pro klasifikaci
python -m http.server -d site 8000                            # http://localhost:8000/?embed=1
```

## Jak přidat obec nebo zdroj

- **Obec / venue:** přidej položku do `places` (název + aliasy, jak se místo objevuje v textech) nebo do `venues_allow` (konkrétní místo bez ohledu na obec).
- **Zdroj existujícího typu** (`galileo`, `antee_rss`, `public4u`, `goout`, `drupal_events`): přidej záznam do `sources` s `url`, `place` (výchozí obec) a `priority`. Pak `build --record --source <name> --no-llm` nahraje fixture pro testy.
- **Nový typ zdroje:** modul v `mostek_kultura/sources/` s třídou odvozenou od `Source` (metoda `fetch(http) -> list[Event]`), registrace v `sources/__init__.py`, fixture a test v `tests/test_sources.py`.

## Home Assistant

- REST senzory: `ha/configuration.yaml` (stav = počet akcí, atribut `events` = seznam).
- Iframe karta: `ha/lovelace-card.yaml`. Markdown karta bez iframe: `ha/lovelace-markdown-card.yaml`.

Senzory se obnovují každou hodinu, data na Pages jednou denně ráno. Stránka sama počítá „dnes/zítra“ z aktuálního času v prohlížeči, takže je správně i po půlnoci.

## Nasazení

```bash
gh repo create ivolarys/mostek-kultura --public --source . --push
gh secret set OPENAI_API_KEY        # nebo ANTHROPIC_API_KEY; oba = přednost má OpenAI, přepíná LLM_PROVIDER
# Settings → Pages → Source: GitHub Actions
gh workflow run build.yml && gh run watch
```
