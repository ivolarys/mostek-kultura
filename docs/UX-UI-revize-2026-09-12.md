# UX/UI revize · 12. září 2026

## Zadání a směr

Mobilní kulturní průvodce okolím Zadního Mostku, inspirovaný iOS. Zachovat
osobitou značku „střed vesmíru“, teplý světlý podklad a korálový akcent;
upřednostnit snadný výběr programu před dekoracemi. Systémové písmo,
jednotné obrysové SVG ikony, zaoblené plochy, tlumené oddělovače,
čitelná hierarchie a světlý i tmavý režim bez dalších externích závislostí.

## Zjištění v původním rozhraní

- Filtr obcí byl schovaný za ikonou bez viditelného popisku. Ovládací prvky
  kategorií měly výšku 32 px, přepínač mapy 36 px.
- Emoji kategorií se vzhledem lišily od obrysových ikon navigace.
- Kategorie a místo sdílely jediný řádek: obec i venue se na mobilu často
  zkrátily dřív, než je šlo rozpoznat.
- Výchozí seskupení podle typu promíchávalo dny. Chybělo textové hledání,
  souhrn výsledků a společné zrušení aktivních filtrů.
- Panel filtrů měnil výsledky okamžitě a zavíral se pohybem prstu dolů
  kdekoliv v obsahu. Běžné posouvání tak mohlo panel nechtěně zavřít.
- Panel neměl plnohodnotnou správu klávesnicového zaměření ani Escape.
- Počty u filtrů nezahrnovaly některé právě probíhající akce zobrazené v seznamu.
- Chyba načtení mapy zůstávala bez vysvětlení.

## Návrh úprav

- Krátká značková hlavička a výrazné „Kam vyrazíme?“, obsah dostupný bez
  vysokého úvodního banneru. Na desktopu širší, stále soustředěný sloupec.
- Vyhledávání v názvu, obci a místě konání bez ohledu na českou diakritiku.
- Pojmenované tlačítko Filtry, horizontální nabídka kategorií a přepínač
  Seznam / Mapa. Aktivní filtry samostatně odstranitelnými štítky.
- Počet výsledků počítat stejným způsobem v navigaci, kategoriích, panelu
  i mapě, včetně relevantních probíhajících akcí.
- Výchozí seskupení po dnech, čas vlevo a místo oddělené od kategorie.
- Mobilní spodní navigace s bezpečným odstupem od systémového indikátoru;
  desktopová a iframe varianta s přepínačem období nahoře.
- Modalní panel s pracovním výběrem obcí a seskupení, potvrzením počtu
  akcí a zrušením změn při zavření. Posouvání obsahu panel nezavírá.
- Dotykové cíle alespoň 44 px, viditelné zaměření klávesnicí, pojmenované
  ovladače a respektování omezeného pohybu v systému.
- Sdílitelný stav filtrů v URL, zachování mapy a kompaktního Home Assistant režimu.

## Následná preference uživatele

Uživatel 12. září 2026 zvolil jako výchozí seskupení **podle kategorie**.
Tato volba nahrazuje výše uvedený původní návrh seskupení po dnech.
Explicitní výběr seskupení podle dne v URL nebo panelu filtrů zůstává zachovaný.

## Ověření

- Dokončená implementace: 86 úspěšných Python testů, čistý Ruff a
  `git diff --check`. Offline sestavení vytvořilo přehled 309 akcí.
  Existující parser dál vypisuje dvě upozornění BeautifulSoup na XML
  načítané jako HTML; nesouvisejí s úpravou rozhraní.
- Automatizovaný průchod v Chromu: hledání „smolik“ nalezne oba koncerty
  Jakuba Smolíka, prázdné výsledky, průnik obce a kategorie, zrušení všech
  filtrů a shoda 102 týdenních výsledků s daty včetně probíhajících akcí.
- Dialogy: zrušení rozepsaného výběru, potvrzení počtu výsledků, Escape,
  návrat zaměření, cyklus Tab/Shift+Tab a posouvání bez nechtěného zavření.
- URL: historie obnoví výběr, neplatné hodnoty se normalizují a výchozí
  parametry v query nepřebíjejí pozdější změnu zobrazení ani seskupení.
- Mapa: načtení značek, otevření detailu klávesnicí, dostupné potvrzení
  filtrů, simulované selhání načtení Leafletu a funkční opakování.
- Vizuální kontrola hlavní stránky v šířkách 320, 390, 768 a 1440 px;
  světlý i tmavý režim. Stránka zdrojů ověřena v 320, 390 a 1440 px.
  Bez vodorovného přetékání stránky. Ověřen také kompaktní iframe režim.
- Vypočtený kontrast textů kategorií vůči jejich štítkům je alespoň 5,1 : 1
  ve světlém a 5,8 : 1 v tmavém režimu.
- Kontrola proběhla v desktopovém Chromu s mobilními rozměry; skutečný
  iPhone/Safari nebyl v tomto prostředí testován.

## Náhled a změněné soubory

Při revizi sloužil soukromý náhled přes Tailscale. Veřejná verze používá
původní adresu https://ivolarys.github.io/mostek-kultura/ a workflow
`Build & deploy`: push do `main` spustí testy, aktuální sběr akcí,
sestavení složky `site/` a nasazení na GitHub Pages. Denní aktualizace
akcí zůstává zachovaná.

Implementace mění šablony `index.html.j2`, `_base.css.j2` a `zdroje.html.j2`.
Backend, sběr a klasifikace akcí ani datové konfigurace se nemění.
Projektová preference modelů je uložená v `AGENTS.md` a sjednocená v `CLAUDE.md`.
