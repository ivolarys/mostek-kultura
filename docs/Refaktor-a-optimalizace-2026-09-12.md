# Refaktoring a optimalizace — 12. 9. 2026

Výchozí revize: `c83d9ac`. Změna zachovává veřejné URL, strukturu dat,
vzhled, filtry, seskupování, mapu a instalaci aplikace.

## Změny

- Rozhraní sdílí formátovače data a času. Nevytváří je znovu pro každou akci.
- Jeden výpočet při vykreslení připraví viditelné akce, počty kategorií
  a období. Desktop i mobil používají stejná počítadla. Vyhledávací dotaz
  se normalizuje jednou pro operaci.
- Sestavení používá jeden HTTP transport a úspěšné odpovědi GET sdílí pouze
  v rámci daného běhu. Úplná URL včetně parametrů zůstává klíčem.
  Tři zdroje HKinfo tak pro tři měsíce potřebují 3 požadavky místo 9.
- Transport se uzavírá i při chybě. Testovací vzorky se nadále zapisují
  pro každý zdroj samostatně, včetně odpovědí získaných z paměti.
- POST se nesdílí a vyprázdní předchozí GET cache. Chyby se neukládají.
  Samostatně vytvořený `Http` má sdílení vypnuté, pokud se výslovně nezapne.

## Ověření

- Offline výstupy `events.json` a `summary.json` jsou shodné před změnou
  a po ní; výstup obsahuje 805 akcí při `MOSTEK_NOW=2026-09-11`.
- Porovnání 42 scénářů v prohlížeči: všechna období, kombinované kategorie
  a obce, hledání s diakritikou, prázdné výsledky, neplatný stav v URL,
  změna rozepsaného filtru, seskupení podle dne, dlouhodobé výstavy,
  mapa a její ovládání klávesnicí. Shodné HTML výsledků a počítadel,
  žádné chyby JavaScriptu ani vodorovné přetékání stránky.
- HTTP regresní testy ověřují kompresi, kódování, nezávislé JSON objekty,
  obnovení po chybě, POST, oddělené vzorky, životnost cache a záložní data.

Jedno kontrolní měření v headless Chrome, viewport 390 × 844, shodná data,
bez externích obrázků. Medián 6 načtení po zahřátí a 56 změn vyhledávání:

| Operace | Před | Po |
| --- | ---: | ---: |
| Načtení do DOMContentLoaded | 310 ms | 115 ms |
| Obsluha vyhledávání včetně překreslení | 41,7 ms | 34,2 ms |

Čísla popisují toto lokální měření; závisí na zařízení, datech a síti.
Celkovou dobu sestavení nadále ovlivňují dostupnost jednotlivých zdrojů,
jejich opakované pokusy a klasifikace akcí.

Standardní kontrola: `.venv/bin/pytest -q` a
`.venv/bin/ruff check mostek_kultura tests`.
