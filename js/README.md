# mrf-js — MRF → JSON / JavaScript

A dependency-free converter that reads **Model-Record-Format (MRF) v1 / v1.1**
in JavaScript and hands it to you as plain JSON:

- **a) Types** (`type …`) → a JSON schema tree you can use in JS to build forms,
  drive field checks, or evaluate constraints.
- **b) Records** (`record …`) → a JSON data tree, ready to process.

The direction is deliberately **MRF → JS** only. No MRF is written.

Runs in Node (CommonJS + ESM), in the browser (`<script>` → global `MRF`) and as
a CLI. No dependencies, no build step.

*Deutsche Fassung: [README_DE.md](README_DE.md).*

## Files

| File | Purpose |
| --- | --- |
| `mrf.js` | The whole converter (lexer, parser, JSON export, validator, CLI) |
| `mrf.mjs` | ESM wrapper with named exports |
| `test_mrf.js` | Test suite (`node test_mrf.js`) |
| `package.json` | Package metadata so `require`/`import` resolve cleanly |

## Quick start

```js
// Node / CommonJS
const mrf = require("./mrf.js");

// Node / ESM
// import mrf, { parse, validate } from "./mrf.mjs";

const doc = mrf.parse(mrfText);

const types   = doc.typesJSON();     // a) schema as JSON
const records = doc.recordsJSON();   // b) data as JSON
const errors  = mrf.validate(doc);   // [] === valid
```

In the browser:

```html
<script src="mrf.js"></script>
<script>
  const doc = MRF.parse(document.getElementById("src").textContent);
  console.log(doc.recordsJSON());
</script>
```

Reading a file directly in Node: `const doc = mrf.parseFile("data.mrf");`

## a) Types as JSON

Input:

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

A lossless 1:1 image of the MRF type definition:

- `kind` is `"named"` (then there is a `type`, e.g. `String`, `Int`, `Boolean`,
  `Any`, `DictionaryItem`, or a user-defined type name) or `"anonymous"`
  (then there is a `fields` object of the same shape, nested arbitrarily deep).
- `attributes` carries every attribute verbatim (`required`, `maxLength`,
  `minValue`, `maxValue`, plus anything custom). `required` sits next to it
  already evaluated as a boolean.
- `isList` reflects the array marker `field[]:`.
- The declaration order of the fields is preserved in `Object.keys(...)`.

Typical JS use:

```js
for (const f of Object.values(types.Person.fields)) {
  console.log(f.name, f.type ?? "(anonymous)", f.required ? "*" : "", f.isList ? "[]" : "");
}
```

## b) Records as JSON

Input:

```mrf
record jane:Person ( name="Jane Doe" age=25 )

record order1:Order (
    id="X1"
    items = [ (key="A" value="Ananas") (key="B" value="Banana") ]
    customer = jane                              // reference
    header  = :TextH1( id="h" content="Title" )  // typed inline record (v1.1)
)
```

`doc.recordsJSON()` — always an array, with name and type kept apart from the data:

```json
[
  { "name":"jane", "type":"Person", "data": { "name":"Jane Doe", "age":25 } },
  { "name":"order1", "type":"Order", "data": {
      "id":"X1",
      "items":[ {"key":"A","value":"Ananas"}, {"key":"B","value":"Banana"} ],
      "customer": { "name":"Jane Doe", "age":25 },
      "header": { "_type":"TextH1", "id":"h", "content":"Title" }
  } }
]
```

Mapping rules:

| MRF | JSON |
| --- | --- |
| String / number / `true`/`false` | String / Number / Boolean |
| Inline record `( … )` | object |
| Typed inline record `:T( … )` | object with `"_type": "T"` (the discriminator, always emitted) |
| Array `[ … ]` | array |
| Reference `customer = jane` | the data of record `jane`, inlined — or `{"$ref":"jane"}` |
| `record` without name/type | `name` resp. `type` is `null` |

### References: resolve or keep

Switchable at runtime; the default is to resolve (with a cycle guard — a cycle
ends at the second visit as `{"$ref":…}`):

```js
doc.recordsJSON();                        // references inlined
doc.recordsJSON({ resolveRefs: false });  // references as {"$ref":"jane"}
```

### Alternative data view

`doc.toData()` returns the same data in the `json`-module style of the reference
implementation: **one** record → the object itself, **many** → an array.
Byte-identical to `python3 mrf.py to-json`.

```js
doc.toData();                        // data only
doc.toData({ includeMeta: true });   // adds _name / _type per record
doc.toData({ resolveRefs: false });  // keep references
```

`doc.toJSON()` gives you everything at once:
`{ mrf: "1.1", usings: [...], types: {...}, records: [...], data: ... }`.

## Validation

MRF carries its schema in the same file — the validator uses that:

```js
const errors = mrf.validate(doc);                          // [] === valid
const strict = mrf.validate(doc, { strictUnknown: true }); // also reports unknown types
```

It checks `required`, `maxLength`, `minValue`, `maxValue`, basic type agreement
for typed records, nested anonymous types, and — since v1.1 — every typed inline
record at any depth.

Not checked: `using` imports are never resolved (per spec, a file stays valid
without external definitions). Types living in another file therefore count as
unknown and are **skipped silently** — `strictUnknown: true` makes them visible.
Anonymous inline records in `Any()` fields stay unchecked by design.

## CLI

```bash
node mrf.js parse     file.mrf     # full envelope { mrf, usings, types, records, data }
node mrf.js types     file.mrf     # the schema only
node mrf.js records   file.mrf     # the records only: [{ name, type, data }]
node mrf.js to-json   file.mrf     # the data only (1 record -> object)
node mrf.js validate  file.mrf     # constraint check, exit code 1 on errors
```

Options: `-o <file>` (instead of stdout), `--keep-refs` (references as `$ref`),
`--meta` (for `to-json`: include `_name`/`_type`), `--strict` (for `validate`),
`--indent <n>`. Use `-` as the filename to read stdin.

## Errors

Syntax errors throw `MRFSyntaxError` carrying `line` and `col`:

```js
try {
  mrf.parse(text);
} catch (e) {
  if (e instanceof mrf.MRFSyntaxError) console.error(e.message, e.line, e.col);
}
```

## API overview

| Call | Result |
| --- | --- |
| `mrf.parse(text)` | `Document` |
| `mrf.parseFile(path)` | `Document` (Node only) |
| `mrf.typesOf(text)` | schema JSON |
| `mrf.recordsOf(text, opts)` | records JSON |
| `mrf.toJSON(text, opts)` | full envelope |
| `mrf.validate(doc, opts)` | `string[]` |
| `mrf.tokenize(text)` | token list (for editor / highlighting purposes) |
| `doc.usings` / `doc.types` / `doc.records` | structural access to the AST |
| `doc.get(name)` | record by name |

In the AST, values are native JS values plus `RecordRef` (bare-word reference)
and `InlineRecord` (`( … )`, with `.type` for v1.1) — the same building blocks as
in the Python reference.

## Conformance

The parser is a 1:1 image of the v1/v1.1 EBNF and implements the four canonical
rules (`[` after `=` → array, `(` after `:` → anonymous type, a bare word as a
value → reference, `:` before a value → typed inline record).

Verified against the reference implementation `scripts/mrf.py`: for the example
`sample.mrf` and all 13 cases from `test_mrf.py`, the output of
`node mrf.js to-json` is **byte-identical** to `python3 mrf.py to-json` (with and
without `--keep-refs --meta`); the three negative cases are rejected as well.
The validator messages match verbatim (the one difference: on type errors the JS
variant names MRF types, `Int` instead of `int`).

```bash
node test_mrf.js     # 24 tests
```
