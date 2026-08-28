[Deutsch](README_DE.md)

# Model Record Format (MRF) — Version 1.1

The **Model Record Format (MRF)** is a typed, structured data format specifically designed for the manageable storage and validation of complex data models. Unlike formats such as JSON or TOML, MRF combines **schema and data directly within a single file** and syntactically aligns with the clear, readable C standard.

This repository contains the official specification as well as a reference parser implementation for validating the syntax.

> **Version 1.1** adds **typed inline records** — an element in value position may carry its own type name, written `:Type( … )`. This makes heterogeneous lists (`blocks[]: Any()`) validatable for the first time. The extension is purely additive: every v1 file parses unchanged.

---

## 📂 Project Structure

* **[Specification (record_model_definition_v1.md)](record_model_definition_v1.md)**: The core document containing the full definition of the format, canonical rules, standard types, and the formal EBNF grammar.
* **[Reference Parser (mrf_parser.py)](mrf_parser.py)**: A runnable implementation of a recursive-descent parser that validates MRF files against the EBNF grammar. *(Note: This file was created with AI assistance).*
* **[Parser Test Suite (test_mrf.py)](test_mrf.py)**: A collection of test cases that verifies all valid and invalid examples from the specification. *(Note: This file was created with AI assistance).*
* **[Claude Skill (skill/mrf-schema/)](skill/mrf-schema/)**: A ready-to-use skill for Claude (Claude Code / Cowork) that reads, writes, validates and converts MRF. It ships a **full Python implementation** — `skill/mrf-schema/scripts/mrf.py` parses, validates constraints (`required`, `minValue`, `maxValue`, `maxLength`, typed inline records at any depth), formats, and converts between MRF, JSON and YAML. See [Using the skill](#skill) below. *(Note: These files were created with AI assistance).*
* **[LICENSE](LICENSE)**: View the full [License terms](LICENSE) for this project.

---

## 💡 Key Features of MRF

* **Combined Schema & Data:** Validation rules do not need to be maintained in external JSON schema files.
* **C-like Syntax:** Clearly structured, strongly typed, and highly readable for both humans and machines.
* **Context-Free Grammar:** An interpreter can fully read and parse MRF files without needing to resolve external types beforehand.
* **Extensible Type Vocabulary:** Supports `String`, `Int`, `Decimal`, `Boolean`, `Any`, and `DictionaryItem` by default.
* **Typed Inline Records (v1.1):** Elements of a heterogeneous list carry their own contract — `blocks = [ :TextH1( … ) :CoreImage( … ) ]` — so a validator can check them individually.
* **AI-Optimized:** Due to its clear structure, the format is ideal for context and training data (e.g., for LoRAs and LLM fine-tuning).

---

<a id="skill"></a>

## 🤖 Using the skill

The folder [`skill/mrf-schema/`](skill/mrf-schema/) is a self-contained Claude skill:

| File | Purpose |
|---|---|
| [`SKILL.md`](skill/mrf-schema/SKILL.md) | What Claude reads: format in one screen, the four canonical rules, Python API, CLI |
| [`scripts/mrf.py`](skill/mrf-schema/scripts/mrf.py) | Full implementation — parser, validator, formatter, JSON/YAML converters (pure stdlib) |
| [`reference/mrf_spec_v1.md`](skill/mrf-schema/reference/mrf_spec_v1.md) | Condensed v1/v1.1 reference with the EBNF and attribute tables |
| [`examples/sample.mrf`](skill/mrf-schema/examples/sample.mrf) | A complete, valid file covering every construct |

`scripts/mrf.py` is useful on its own, without Claude — it is the practical
counterpart to the syntax-only reference parser:

```bash
python3 skill/mrf-schema/scripts/mrf.py validate  file.mrf [--strict]
python3 skill/mrf-schema/scripts/mrf.py to-json   file.mrf
python3 skill/mrf-schema/scripts/mrf.py from-json file.json
python3 skill/mrf-schema/scripts/mrf.py fmt       file.mrf
```

To install it as a skill, copy the folder into your skills directory (e.g.
`~/.claude/skills/mrf-schema/`), or pack it up first:

```bash
cd skill && zip -r ../mrf-schema.skill mrf-schema
```

---

## 🛠️ Installation & Usage

Since the reference parser is written in pure Python, you do not need any external dependencies. 

### Prerequisites (e.g., on Ubuntu / Debian)
Ensure that Python 3 is installed:
```bash
sudo apt update
sudo apt install python3

---

<sub>[Contact & legal notice](https://nuvegen.github.io/MRF-Schema/impressum.html) &middot; [Privacy policy](https://nuvegen.github.io/MRF-Schema/datenschutz.html)</sub>
