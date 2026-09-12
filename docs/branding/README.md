# Návrhy názvu a loga · 12. září 2026

Návrhový list: [Tři směry značky](navrhy-log-a-nazvu.png).

## Schválená značka: Mostkultura

**Malý Mostek. Velký dění.**

Název spojuje Mostek a kulturu. Logo tvoří dvojice mostních oblouků,
která současně připomíná malé m; jiskra odkazuje na zážitky a dění v okolí.
Korálová navazuje na novou podobu webu. Samostatný symbol se hodí do
ikony aplikace, celá značka do hlavičky a na plakáty.

## Mostkoviny

**Co se kde šustne.**

Komunitní, sousedský tón. Logo propojuje most a řečovou bublinu.
Tyrkysová představuje barevnou alternativu. Název by se hodil i pro širší
lokální přehled pozvánek, zpráv a zajímavostí.

## Pupek světa

**Všechno se točí kolem nás.**

Nejvýraznější nadsázka, která rozvíjí původní „střed vesmíru“.
Jednoduchý orbitální symbol má v centru Mostek a kolem něj dění regionu.
Pro místní ukotvení patří ke značce doplněk „Mostek a okolí“.

## Stav návrhu

Návrhový list zachycuje původní koncepty vytvořené vestavěným ImageGen.
Uživatel 12. září 2026 vybral **Mostkulturu**. Tento směr se promítá do
názvu webu, vektorového loga, favicony a ikon pro instalaci do telefonu.
Mostkoviny a Pupek světa zůstávají pouze archivními alternativami.

Značka používá korálovou `#E45E3D`, tmavou švestkovou `#211C2B`
a teplý světlý podklad `#FBF7F1`. Samostatný symbol tvoří dvě mostní
klenby čitelné jako malé m a čtyřcípá jiskra. U značky se používá psaní
„Mostkultura“, bez verzálek a bez mezery mezi Mostkem a kulturou.

Finální aktiva ve složce `mostek_kultura/static/`:

- `logo.svg`: samostatný korálový symbol na průhledném podkladu.
- `logo-monochrome.svg`: jednobarevný symbol s `currentColor` pro vložení do SVG/HTML.
- `icon.svg`: bílý symbol na korálovém podkladu pro faviconu.
- `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`: neprůhledné čtvercové
  ikony s bezpečným odstupem pro systémový ořez.

Ikony se obnovují příkazem `.venv/bin/python scripts/make_icons.py`.
Název repozitáře, adresy webu, datových výstupů a identifikátory Home Assistantu
zůstávají zachované.

Ověření implementace: 86 testů prošlo, Ruff a `git diff --check` bez chyb.
Mobilní náhled byl zkontrolovaný v šířkách 320, 390, 768 a 1440 px,
včetně tmavého režimu, nové hlavičky a stránky zdrojů. U všech PNG ikon
je bílá kresba uvnitř bezpečného kruhu s poloměrem 40 % šířky ikony.
Veřejná verze používá původní adresu https://ivolarys.github.io/mostek-kultura/.
Změny se publikují existujícím workflow `Build & deploy` po pushi do `main`.

Původní a opravný prompt jsou v [prompts.md](prompts.md).
