[Deutsch](README_DE.md)

# Model Record Format (MRF) — Version 1

The **Model Record Format (MRF)** is a typed, structured data format specifically designed for the manageable storage and validation of complex data models. Unlike formats such as JSON or TOML, MRF combines **schema and data directly within a single file** and syntactically aligns with the clear, readable C standard.

This repository contains the official specification as well as a reference parser implementation for validating the syntax.

---

## 📂 Project Structure

* **[Specification (record_model_definition_v1.md)](record_model_definition_v1.md)**: The core document containing the full definition of the format, canonical rules, standard types, and the formal EBNF grammar.
* **[Reference Parser (mrf_parser.py)](mrf_parser.py)**: A runnable implementation of a recursive-descent parser that validates MRF files against the EBNF grammar. *(Note: This file was created with AI assistance).*
* **[Parser Test Suite (test_mrf.py)](test_mrf.py)**: A collection of test cases that verifies all valid and invalid examples from the specification. *(Note: This file was created with AI assistance).*

---

## 💡 Key Features of MRF

* **Combined Schema & Data:** Validation rules do not need to be maintained in external JSON schema files.
* **C-like Syntax:** Clearly structured, strongly typed, and highly readable for both humans and machines.
* **Context-Free Grammar:** An interpreter can fully read and parse MRF files without needing to resolve external types beforehand.
* **Extensible Type Vocabulary:** Supports `String`, `Int`, `Decimal`, `Boolean`, `Any`, and `DictionaryItem` by default.
* **AI-Optimized:** Due to its clear structure, the format is ideal for context and training data (e.g., for LoRAs and LLM fine-tuning).

---

## 🛠️ Installation & Usage

Since the reference parser is written in pure Python, you do not need any external dependencies. 

### Prerequisites (e.g., on Ubuntu / Debian)
Ensure that Python 3 is installed:
```bash
sudo apt update
sudo apt install python3
