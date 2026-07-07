[Englisch](README.md)

# Model Record Format (MRF) — Version 1

Das **Model Record Format (MRF)** ist ein typisiertes, strukturiertes Datenformat, das speziell für die übersichtliche Speicherung und Validierung komplexer Datenmodelle entwickelt wurde. Im Gegensatz zu Formaten wie JSON oder TOML kombiniert MRF **Schema und Daten direkt in einer einzigen Datei** und orientiert sich syntaktisch am klaren, lesbaren C-Standard.

Dieses Repository enthält die offizielle Spezifikation sowie eine Referenz-Parser-Implementierung zur Validierung der Syntax.

---

## 📂 Projektstruktur

* **[Spezifikation (record_model_definition_v1_DE.md)](record_model_definition_v1_DE.md)**: Das Kerndokument, das die vollständige Definition des Formats, kanonische Regeln, Standardtypen und die formale EBNF-Grammatik enthält.
* **[Referenz-Parser (mrf_parser.py)](mrf_parser.py)**: Eine ausführbare Implementierung eines Recursive-Descent-Parsers, der MRF-Dateien gegen die EBNF-Grammatik validiert. *(Hinweis: Diese Datei wurde mit KI-Unterstützung erstellt).*
* **[Parser-Test-Suite (test_mrf.py)](test_mrf.py)**: Eine Sammlung von Testfällen, die alle gültigen und ungültigen Beispiele aus der Spezifikation überprüft. *(Hinweis: Diese Datei wurde mit KI-Unterstützung erstellt).*
* **[LIZENZ (LICENSE)](LICENSE)**: Die vollständigen [Lizenzbedingungen](LICENSE) für dieses Projekt ansehen.

---

## 💡 Hauptmerkmale von MRF

* **Kombiniertes Schema & Daten:** Validierungsregeln müssen nicht in externen JSON-Schema-Dateien verwaltet werden.
* **C-ähnliche Syntax:** Klar strukturiert, streng typisiert und sowohl für Menschen als auch für Maschinen hervorragend lesbar.
* **Kontextfreie Grammatik:** Ein Interpreter kann MRF-Dateien vollständig lesen und parsen, ohne vorher externe Typen auflösen zu müssen.
* **Erweiterbares Typvokabular:** Unterstützt standardmäßig `String`, `Int`, `Decimal`, `Boolean`, `Any` und `DictionaryItem`.
* **KI-optimiert:** Aufgrund seiner klaren Struktur eignet sich das Format ideal für Kontext- und Trainingsdaten (z. B. für LoRAs und LLM-Feintuning).

---

## 🛠️ Installation & Verwendung

Da der Referenz-Parser in reinem Python geschrieben ist, werden keine externen Abhängigkeiten benötigt. 

### Voraussetzungen (z. B. unter Ubuntu / Debian)
Stellen Sie sicher, dass Python 3 installiert ist:
```bash
sudo apt update
sudo apt install python3
