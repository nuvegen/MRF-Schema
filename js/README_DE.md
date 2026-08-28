# mrf-js — MRF → JSON / JavaScript

Ein abhängigkeitsfreier Konverter, der **Model-Record-Format (MRF) v1 / v1.1** in
JavaScript einliest und als reines JSON bereitstellt:

- **a) Types** (`type …`) → JSON-Schema-Baum, mit dem du in JS Formulare bauen,
  Felder prüfen oder Constraints auswerten kannst.
- **b) Records** (`record …`) → JSON-Datenbaum, direkt verarbeitbar.

Richtung ist bewusst nur **MRF → JS**. Es wird kein MRF geschrieben.

Läuft in Node (CommonJS + ESM), im Browser (`<script>` → globales `MRF`) und als CLI.
Keine Abhängigkeiten, keine Build-Schritte.

*English version: [README.md](README.md).*

## Dateien

| Datei | Zweck |
| --- | --- |
| `mrf.js` | Der komplette Konverter (Lexer, Parser, JSON-Export, Validator, CLI) |
| `mrf.mjs` | ESM-Wrapper mit Named Exports |
| `test_mrf.js` | Testsuite (`node test_mrf.js`) |
| `package.json` | Paket-Metadaten, damit `require`/`import` sauber auflösen |

## Schnellstart

```js
// Node / CommonJS
const mrf = require("./mrf.js");

// Node / ESM
// import mrf, { parse, validate } from "./mrf.mjs";

const doc = mrf.parse(mrfText);

const types   = doc.typesJSON();     // a) Schema als JSON
const records = doc.recordsJSON();   // b) Daten als JSON
const errors  = mrf.validate(doc);   // [] === gültig
```

Im Browser:

```html
<script src="mrf.js"></script>
<script>
  const doc = MRF.parse(document.getElementById("src").textContent);
  console.log(doc.recordsJSON());
</script>
```

In Node eine Datei direkt lesen: `const doc = mrf.parseFile("daten.mrf");`

## a) Types als JSON

Eingabe:

```mrf
type Person (
    name:   String( required=true maxLength=60 )
    age:    Int( minValue=0 maxValue=150 )
    tags[]: String()
    shipping: ( express: Boolean() note: String() ) ( required=true )
)
```

`doc.typesJSON()`:

```json
{
  "Person": {
    "name": "Person",
    "fields": {
      "name":   { "name":"name", "isList":false, "kind":"named", "type":"String",
                  "attributes":{ "required":true, "maxLength":60 }, "required":true },
      "age":    { "name":"age", "isList":false, "kind":"named", "type":"Int",
                  "attributes":{ "minValue":0, "maxValue":150 }, "required":false },
      "tags":   { "name":"tags", "isList":true, "kind":"named", "type":"String",
                  "attributes":{}, "required":false },
      "shipping": { "name":"shipping", "isList":false, "kind":"anonymous",
                    "attributes":{ "required":true }, "required":true,
                    "fields": { "express": { … }, "note": { … } } }
    }
  }
}
```

Verlustfreies 1:1-Abbild der MRF-Typdefinition:

- `kind` ist `"named"` (dann gibt es `type`, z. B. `String`, `Int`, `Boolean`,
  `Any`, `DictionaryItem` oder ein eigener Typname) oder `"anonymous"`
  (dann gibt es `fields` mit demselben Aufbau, beliebig tief).
- `attributes` enthält alle Attribute wörtlich (`required`, `maxLength`,
  `minValue`, `maxValue`, plus alles Eigene). `required` liegt zusätzlich
  ausgewertet als Boolean daneben.
- `isList` spiegelt den Array-Marker `feld[]:`.
- Die Feld-Reihenfolge der Definition bleibt in `Object.keys(...)` erhalten.

Typisch in JS:

```js
for (const f of Object.values(types.Person.fields)) {
  console.log(f.name, f.type ?? "(anonym)", f.required ? "*" : "", f.isList ? "[]" : "");
}
```

## b) Records als JSON

Eingabe:

```mrf
record jane:Person ( name="Jane Doe" age=25 )

record order1:Order (
    id="X1"
    items = [ (key="A" value="Ananas") (key="B" value="Banana") ]
    customer = jane                              // Referenz
    header  = :TextH1( id="h" content="Titel" )  // typisierter Inline-Record (v1.1)
)
```

`doc.recordsJSON()` — immer ein Array, Name und Typ getrennt von den Daten:

```json
[
  { "name":"jane", "type":"Person", "data": { "name":"Jane Doe", "age":25 } },
  { "name":"order1", "type":"Order", "data": {
      "id":"X1",
      "items":[ {"key":"A","value":"Ananas"}, {"key":"B","value":"Banana"} ],
      "customer": { "name":"Jane Doe", "age":25 },
      "header": { "_type":"TextH1", "id":"h", "content":"Titel" }
  } }
]
```

Abbildungsregeln:

| MRF | JSON |
| --- | --- |
| String / Zahl / `true`/`false` | String / Number / Boolean |
| Inline-Record `( … )` | Objekt |
| Typisierter Inline-Record `:T( … )` | Objekt mit `"_type": "T"` (Diskriminator, immer dabei) |
| Array `[ … ]` | Array |
| Referenz `customer = jane` | eingesetzte Daten des Records `jane` — oder `{"$ref":"jane"}` |
| `record` ohne Name/Typ | `name` bzw. `type` ist `null` |

### Referenzen: auflösen oder behalten

Zur Laufzeit umschaltbar, Default ist auflösen (mit Zyklusschutz — ein Zyklus
endet beim zweiten Besuch als `{"$ref":…}`):

```js
doc.recordsJSON();                        // Referenzen eingesetzt
doc.recordsJSON({ resolveRefs: false });  // Referenzen als {"$ref":"jane"}
```

### Alternative Datenansicht

`doc.toData()` liefert dieselben Daten im Stil des `json`-Moduls der
Referenzimplementierung: **ein** Record → das Objekt selbst, **mehrere** →
ein Array. Byte-identisch zu `python3 mrf.py to-json`.

```js
doc.toData();                                    // Daten pur
doc.toData({ includeMeta: true });               // zusätzlich _name / _type je Record
doc.toData({ resolveRefs: false });              // Referenzen behalten
```

`doc.toJSON()` gibt alles auf einmal:
`{ mrf: "1.1", usings: [...], types: {...}, records: [...], data: ... }`.

## Validierung

MRF trägt sein Schema in derselben Datei — der Validator nutzt das:

```js
const errors = mrf.validate(doc);                        // [] === gültig
const strict = mrf.validate(doc, { strictUnknown: true }); // meldet auch unbekannte Typen
```

Geprüft werden `required`, `maxLength`, `minValue`, `maxValue`, die
Basistyp-Übereinstimmung typisierter Records, verschachtelte anonyme Typen und —
seit v1.1 — jeder typisierte Inline-Record in beliebiger Tiefe.

Nicht geprüft: `using`-Importe werden nie aufgelöst (Spec: eine Datei bleibt auch
ohne externe Definitionen gültig). Typen aus anderen Dateien gelten damit als
unbekannt und werden **still übersprungen** — `strictUnknown: true` macht sie
sichtbar. Anonyme Inline-Records in `Any()`-Feldern bleiben absichtlich ungeprüft.

## CLI

```bash
node mrf.js parse     datei.mrf     # komplettes Envelope { mrf, usings, types, records, data }
node mrf.js types     datei.mrf     # nur das Schema
node mrf.js records   datei.mrf     # nur die Records: [{ name, type, data }]
node mrf.js to-json   datei.mrf     # nur die Daten (1 Record -> Objekt)
node mrf.js validate  datei.mrf     # Constraint-Prüfung, Exit-Code 1 bei Fehlern
```

Optionen: `-o <datei>` (statt stdout), `--keep-refs` (Referenzen als `$ref`),
`--meta` (bei `to-json`: `_name`/`_type` mitnehmen), `--strict` (bei `validate`),
`--indent <n>`. `-` als Dateiname liest von stdin.

## Fehler

Syntaxfehler werfen `MRFSyntaxError` mit `line` und `col`:

```js
try {
  mrf.parse(text);
} catch (e) {
  if (e instanceof mrf.MRFSyntaxError) console.error(e.message, e.line, e.col);
}
```

## API-Übersicht

| Aufruf | Ergebnis |
| --- | --- |
| `mrf.parse(text)` | `Document` |
| `mrf.parseFile(pfad)` | `Document` (nur Node) |
| `mrf.typesOf(text)` | Schema-JSON |
| `mrf.recordsOf(text, opts)` | Records-JSON |
| `mrf.toJSON(text, opts)` | komplettes Envelope |
| `mrf.validate(doc, opts)` | `string[]` |
| `mrf.tokenize(text)` | Token-Liste (für Editor-/Highlighting-Zwecke) |
| `doc.usings` / `doc.types` / `doc.records` | strukturierter Zugriff auf den AST |
| `doc.get(name)` | Record nach Namen |

Im AST sind Werte native JS-Werte plus `RecordRef` (Bare-Word-Referenz) und
`InlineRecord` (`( … )`, mit `.type` für v1.1) — dieselben Bausteine wie in der
Python-Referenz.

## Konformität

Der Parser ist ein 1:1-Abbild der v1/v1.1-EBNF und setzt die vier kanonischen
Regeln um (`[` nach `=` → Array, `(` nach `:` → anonymer Typ, Bare Word als Wert
→ Referenz, `:` vor einem Wert → typisierter Inline-Record).

Verifiziert gegen die Referenzimplementierung `scripts/mrf.py`: für das
Beispiel `sample.mrf` und alle 13 Fälle aus `test_mrf.py` ist die Ausgabe von
`node mrf.js to-json` **byte-identisch** zu `python3 mrf.py to-json` (mit und ohne
`--keep-refs --meta`); die drei Negativfälle werden ebenso abgelehnt. Die
Validator-Meldungen stimmen wörtlich überein (einziger Unterschied: bei
Typfehlern nennt die JS-Variante MRF-Typnamen, `Int` statt `int`).

```bash
node test_mrf.js     # 24 Tests
```
