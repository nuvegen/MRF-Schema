[Englisch](README.md)

# Model Record Format (MRF) — Version 1.1

Das **Model Record Format (MRF)** ist ein typisiertes, strukturiertes Datenformat, das speziell für die übersichtliche Speicherung und Validierung komplexer Datenmodelle entwickelt wurde. Im Gegensatz zu Formaten wie JSON oder TOML kombiniert MRF **Schema und Daten direkt in einer einzigen Datei** und orientiert sich syntaktisch am klaren, lesbaren C-Standard.

Dieses Repository enthält die offizielle Spezifikation sowie eine Referenz-Parser-Implementierung zur Validierung der Syntax.

> **Version 1.1** ergänzt **typisierte Inline-Records** — ein Element in Wertposition darf seinen eigenen Typnamen tragen, geschrieben `:Type( … )`. Damit werden heterogene Listen (`blocks[]: Any()`) erstmals validierbar. Die Erweiterung ist rein additiv: Jede v1-Datei parst unverändert.

---

## 📂 Projektstruktur

* **[Spezifikation (record_model_definition_v1_DE.md)](record_model_definition_v1_DE.md)**: Das Kerndokument, das die vollständige Definition des Formats, kanonische Regeln, Standardtypen und die formale EBNF-Grammatik enthält.
* **[Referenz-Parser (mrf_parser.py)](mrf_parser.py)**: Eine ausführbare Implementierung eines Recursive-Descent-Parsers, der MRF-Dateien gegen die EBNF-Grammatik validiert. *(Hinweis: Diese Datei wurde mit KI-Unterstützung erstellt).*
* **[Parser-Test-Suite (test_mrf.py)](test_mrf.py)**: Eine Sammlung von Testfällen, die alle gültigen und ungültigen Beispiele aus der Spezifikation überprüft. *(Hinweis: Diese Datei wurde mit KI-Unterstützung erstellt).*
* **[Claude-Skill (skill/mrf-schema/)](skill/mrf-schema/)**: Eine einsatzfertige Skill für Claude (Claude Code / Cowork), die MRF liest, schreibt, validiert und konvertiert. Sie enthält eine **vollständige Python-Implementierung** — `skill/mrf-schema/scripts/mrf.py` parst, prüft Constraints (`required`, `minValue`, `maxValue`, `maxLength`, typisierte Inline-Records in beliebiger Tiefe), formatiert und konvertiert zwischen MRF, JSON und YAML. Siehe [Die Skill verwenden](#skill) weiter unten. *(Hinweis: Diese Dateien wurden mit KI-Unterstützung erstellt).*
* **[LIZENZ (LICENSE)](LICENSE)**: Die vollständigen [Lizenzbedingungen](LICENSE) für dieses Projekt ansehen.

---

## 💡 Hauptmerkmale von MRF

* **Kombiniertes Schema & Daten:** Validierungsregeln müssen nicht in externen JSON-Schema-Dateien verwaltet werden.
* **C-ähnliche Syntax:** Klar strukturiert, streng typisiert und sowohl für Menschen als auch für Maschinen hervorragend lesbar.
* **Kontextfreie Grammatik:** Ein Interpreter kann MRF-Dateien vollständig lesen und parsen, ohne vorher externe Typen auflösen zu müssen.
* **Erweiterbares Typvokabular:** Unterstützt standardmäßig `String`, `Int`, `Decimal`, `Boolean`, `Any` und `DictionaryItem`.
* **Typisierte Inline-Records (v1.1):** Elemente einer heterogenen Liste führen ihren eigenen Vertrag mit — `blocks = [ :TextH1( … ) :CoreImage( … ) ]` — sodass ein Validator sie einzeln prüfen kann.
* **KI-optimiert:** Aufgrund seiner klaren Struktur eignet sich das Format ideal für Kontext- und Trainingsdaten (z. B. für LoRAs und LLM-Feintuning).

---

<a id="skill"></a>

## 🤖 Die Skill verwenden

Der Ordner [`skill/mrf-schema/`](skill/mrf-schema/) ist eine in sich geschlossene Claude-Skill:

| Datei | Zweck |
|---|---|
| [`SKILL.md`](skill/mrf-schema/SKILL.md) | Was Claude liest: das Format auf einem Bildschirm, die vier kanonischen Regeln, Python-API, CLI |
| [`scripts/mrf.py`](skill/mrf-schema/scripts/mrf.py) | Vollständige Implementierung — Parser, Validator, Formatter, JSON-/YAML-Konverter (reine Standardbibliothek) |
| [`reference/mrf_spec_v1.md`](skill/mrf-schema/reference/mrf_spec_v1.md) | Kompakte v1/v1.1-Referenz mit EBNF und Attribut-Tabellen |
| [`examples/sample.mrf`](skill/mrf-schema/examples/sample.mrf) | Eine vollständige, gültige Datei über alle Konstrukte |

`scripts/mrf.py` ist auch ohne Claude nützlich — es ist das praktische Gegenstück
zum rein syntaktischen Referenz-Parser:

```bash
python3 skill/mrf-schema/scripts/mrf.py validate  datei.mrf [--strict]
python3 skill/mrf-schema/scripts/mrf.py to-json   datei.mrf
python3 skill/mrf-schema/scripts/mrf.py from-json datei.json
python3 skill/mrf-schema/scripts/mrf.py fmt       datei.mrf
```

Zur Installation als Skill den Ordner in das Skill-Verzeichnis kopieren (z. B.
`~/.claude/skills/mrf-schema/`) — oder vorher paketieren:

```bash
cd skill && zip -r ../mrf-schema.skill mrf-schema
```

---

## 🛠️ Installation & Verwendung

Da der Referenz-Parser in reinem Python geschrieben ist, werden keine externen Abhängigkeiten benötigt. 

### Voraussetzungen (z. B. unter Ubuntu / Debian)
Stellen Sie sicher, dass Python 3 installiert ist:
```bash
sudo apt update
sudo apt install python3
