# Model Record Format (MRF) — Version 1

Das **Model-Record-Format (MRF)** ist ein typisiertes, strukturiertes Datenformat, das speziell für die handhabbare Speicherung und Validierung komplexer Datenmodelle entwickelt wurde. Im Gegensatz zu Formaten wie JSON oder TOML kombiniert MRF **Schema und Daten direkt in einer einzigen Datei** und orientiert sich syntaktisch am klaren, lesbaren C-Standard.

Dieses Repository enthält die offizielle Spezifikation sowie eine referenzierte Parser-Implementierung zur Validierung der Syntax.

---

## 📂 Projektstruktur

* **[Spezifikation (record_model_definition_v1.md)](record_model_definition_v1.md)**: Das Kerndokument mit der vollständigen Definition des Formats, den kanonischen Regeln, Standard-Typen und der formalen EBNF-Grammatik.
* **[Referenz-Parser (mrf_parser.py)](mrf_parser.py)**: Eine lauffähige Implementierung eines Rekursiven-Abstieg-Parsers (Recursive Descent), der MRF-Dateien gegen die EBNF-Grammatik prüft. *(Hinweis: Diese Datei wurde mit Unterstützung einer KI erstellt).*
* **[Parser-Testsuite (test_mrf.py)](test_mrf.py)**: Eine Sammlung von Testfällen, die alle validen und invaliden Beispiele der Spezifikation überprüft. *(Hinweis: Diese Datei wurde mit Unterstützung einer KI erstellt).*

---

## 💡 Hauptmerkmale von MRF

* **Schema & Daten vereint:** Validierungsregeln müssen nicht in externen JSON-Schema-Dateien gepflegt werden.
* **C-ähnliche Syntax:** Klar strukturiert, stark typisiert und sowohl für Menschen als auch für Maschinen hervorragend lesbar.
* **Kontextfreie Grammatik:** Ein Interpreter kann MRF-Dateien vollständig lesen und parsen, ohne vorab externe Typen auflösen zu müssen.
* **Erweiterbares Typ-Vokabular:** Standardmäßig werden `String`, `Int`, `Decimal`, `Boolean`, `Any` und `DictionaryItem` unterstützt.
* **KI-Optimiert:** Durch die klare Strukturierung eignet sich das Format ideal als Kontext- und Trainingsdaten-Format (z. B. für LoRAs und LLM-Feintuning).

---

## 🛠️ Installation & Nutzung

Da der Referenz-Parser in purem Python geschrieben ist, benötigst du keine externen Abhängigkeiten. 

### Voraussetzungen (z. B. unter Ubuntu / Debian)
Stelle sicher, dass Python 3 installiert ist:
```bash
sudo apt update
sudo apt install python3
