# Pravidla pro Codex v tomto projektu

Komunikuj česky. Respektuj projektové postupy a technické poznatky v `CLAUDE.md`;
následující volba modelů má přednost před jeho staršími pokyny k modelům.

## Modely (preference uživatele, 2026-09-12)

- Hlavní model je GPT-6 Astra (`gpt-6-astra`): navrhuje, analyzuje, připravuje
  zadání, řídí práci, kontroluje, testuje a provádí UX/UI i code review.
- Samotné kódování deleguj levnějším modelům: GPT-5.6 Luna pro jednoduché
  úpravy, GPT-5.6 Terra nebo Sol pro složitější implementaci. Astra připraví
  konkrétní zadání a výsledek zkontroluje a ověří.
- Preference platí pro celý tento projekt všude, kde lze model zvolit.
  Netvrď, že se model běžícího tahu přepnul, pokud se to skutečně nestalo.

## UX/UI

- Schválená značka (2026-09-12): **Mostkultura**. Repo a veřejná URL používají
  název `mostkultura` (`https://ivolarys.github.io/mostkultura/`). Logo propojuje malé m,
  mostní oblouky a čtyřcípou jiskru;
  hlavní barva je korálová. Zachovej název repozitáře a existující URL.
- Web navrhuj primárně pro mobilní telefony, ve svěžím moderním stylu
  inspirovaném iOS. Zachovej přístupnost, tmavý režim a kompaktní iframe režim.
- Používej jednotné jednoduché obrysové ikony a dostatečně velké dotykové prvky.
- Výchozí seskupení akcí je podle **kategorie** (preference uživatele,
  2026-09-12). Zachovej možnost ručního seskupení podle dne a nastavení v URL.
- V kategorii zobraz běžné akce nejdřív a dlouhodobé právě probíhající akce
  až v oddělené, výchozím způsobem rozbalené podsekci.
- Odkaz „Zdroje“ patří do hlavičky.
- Kategorie se posouvají vodorovně a vybraná kategorie zůstává přímo v liště.
- Značka je výraznější; aktualizace a počet akcí se v hlavičce nikdy nezalamují.
- Hlavička má být kompaktní: Mostkultura a „Kultura okolo Mostku“, aktualizace
  vpravo nahoře. Nevracej „Kam vyrazíme?“ ani původní slogan. U akcí bez
  barevné svislé čárky; zdroj na desktopu napravo od štítku kategorie.

## Sdílení náhledů

- Pro náhledy dostupné z notebooku preferuj ověřenou Tailscale adresu.
- Zachovej existující Tailscale routy a zpřístupni jen zamýšlený náhled.
