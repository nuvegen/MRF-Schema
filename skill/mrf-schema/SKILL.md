---
name: mrf-schema
description: >-
  Read, write, validate, and convert Model-Record-Format (MRF) v1 / v1.1 files — a
  typed, C-flavoured data format that keeps schema and data in ONE file (a
  JSON / YAML / TOML alternative). Use this skill whenever an .mrf file is
  involved, whenever the user mentions MRF, Model-Record-Format, "record"/"type"
  definitions in that syntax, typed inline records (":Type( … )"), or wants to
  treat MRF like JSON/YAML: parse it into
  a data structure, serialise data to it, validate it against the EBNF grammar
  and its schema constraints (required / minValue / maxValue / maxLength), or
  convert between MRF, JSON, and YAML. Also use to hand-author correct MRF (applying the
  four canonical rules) or to generate .mrf test fixtures. Prefer the bundled
  parser over eyeballing syntax — it is a 1:1 image of the grammar. A read-only
  JavaScript twin ships alongside it for MRF that has to be consumed in the
  browser or in Node.
---

# MRF — Model-Record-Format v1 / v1.1

MRF is a typed, C-like data format. Its defining trait: **schema (`type`) and
data (`record`) live in the same file**, so validation rules do not need an
external JSON Schema. Treat it exactly like JSON or YAML — parse to a Python
structure, mutate, serialise back, convert across formats — using the bundled
module `scripts/mrf.py` (pure stdlib, no dependencies).

Full grammar and type reference: `reference/mrf_spec_v1.md`. A complete, working
`.mrf` file is in `examples/sample.mrf`. Read the reference when you need the
exact EBNF or an attribute table; the essentials below are enough for most work.

## MRF in one screen

```mrf
using "https://w3-isp.net/mrf/types.mrf"   // optional import; may be ignored

type Person (                    // a MODEL definition = schema
    name:   String( required=true )
    age:    Int( minValue=0 maxValue=150 )
    active: Boolean()
)

record jane:Person (             // a RECORD = data, optionally :typed
    name="Jane Doe"
    age=25
    active=false
)

record (                         // anonymous record
    id="X1"
    items = [ (key="A" value="Ananas") (key="B" value="Banana") ]  // array of inline records
    blocks = [ :Person( name="Max" ) ]   // v1.1: typed inline record, checked against Person
    customer = jane              // bare word = reference to record 'jane'
)
```

A file may contain any mix of `using`, `type`, and `record` declarations, in any
order. Both a record's **name** and its **:type** are optional, so all of these
are valid: `record audi:Car`, `record opel`, `record :Car`, `record`.

## Four canonical rules (never guess — apply these)

The grammar is context-free precisely because of these rules. They resolve every
ambiguity by looking at the *next token only*, without resolving any type:

1. **Arrays are square brackets.** A `[` after `=` starts an array literal
   (`items = [ … ]`); a `(` after `=` starts an **inline record** (`tires = ( … )`).
   The `[]` marker on a field name (`items[]: …`) documents the list type but is
   not needed to disambiguate.
2. **After `:`, the next token decides named vs. anonymous.** A *TypeIdentifier*
   → named type, and its parentheses hold **attributes** as `key=value`
   (`String( required=true )`). A `(` → anonymous type, and its parentheses hold
   **field definitions** as `key: Type`. An anonymous field block may carry a
   *second* pair of parens for its own attributes: `( … ) ( required=true )`.
3. **A bare word used as a value is a record reference.** `customer = jane`
   references the record named `jane`. `true` / `false` are reserved booleans, so
   references never collide with them.
4. **A `:` at the start of a value introduces a typed inline record** *(v1.1)*.
   `blocks = [ :TextH1( … ) ]` binds the element to type `TextH1`, and `validate`
   checks it against that type. No collision with rule 2: there the `:` stands
   after a *field name*, here before a *value*.

Reserved words: `using`, `type`, `record`, `true`, `false`. Separators
(whitespace or `,`) are interchangeable and insignificant. Comments: `//` to end
of line, or `/* … */` across lines. Strings use C-style escapes (`\n`, `\"`, …).

## Standard types (v1)

`String` (attrs: `required`, `maxLength`) · `Int` / `Decimal` (attrs: `required`,
`minValue`, `maxValue`) · `Boolean` (`required`) · `Any` (`required`) ·
`DictionaryItem` (a `key: String` + `value: Any`, used for list/dict entries).
User-defined `type`s compose freely. See the reference for the attribute tables.

## Using it like JSON / YAML (the Python API)

`scripts/mrf.py` mirrors the `json` module. **Import it, or run its CLI — do not
hand-parse MRF.**

```python
import sys; sys.path.insert(0, "scripts")   # or copy mrf.py next to your code
import mrf

doc  = mrf.loads(text)          # parse text  -> Document   (raises MRFSyntaxError)
doc  = mrf.load("file.mrf")     # parse a path or file object
data = doc.data                 # plain dict / list, ready for json.dumps / yaml.dump
                                #   (one record -> dict, many -> list; refs resolved)

text = mrf.dumps(some_dict)     # dict  -> one `record ( … )`
text = mrf.dumps(list_of_dicts) # list  -> several records
text = mrf.dumps(doc)           # Document -> full MRF (types + records + usings)
mrf.dump(doc, "out.mrf")

errors = mrf.validate(doc)      # [] means valid; else human-readable constraint errors
```

The `Document` object gives structural access: `doc.types` (dict of `TypeDef`),
`doc.records` (list of `Record` with `.name`, `.type`, `.fields`),
`doc.get("jane")`, `doc.records_by_name`, `doc.usings`. In `.fields`, values are
native Python plus `RecordRef(name)` for bare-word references and `InlineRecord`
for `( … )` blocks — `InlineRecord.type` holds the v1.1 type name or `None`.
`doc.to_data(resolve_refs=False)` keeps references as `{"$ref": name}` instead of
inlining them. In the data tree, a typed inline record becomes a dict with a
`_type` key; that key is content (the discriminator), so it is emitted always,
not only with `--meta` — and `from-json` turns it back into `:Type( … )`.

## CLI

```bash
python3 scripts/mrf.py parse     file.mrf              # -> parsed data as JSON
python3 scripts/mrf.py validate  file.mrf [--strict]   # syntax + schema constraints
python3 scripts/mrf.py fmt       file.mrf [-o out.mrf] # canonical re-formatting
python3 scripts/mrf.py to-json   file.mrf [-o out.json] [--keep-refs] [--meta]
python3 scripts/mrf.py to-yaml   file.mrf [-o out.yaml]
python3 scripts/mrf.py from-json file.json [--name N] [--type T] [-o out.mrf]
python3 scripts/mrf.py from-yaml file.yaml [--name N] [--type T]
```

Use `-` as the filename to read stdin. `validate` returns exit code 1 with the
list of violations if invalid; `--strict` also flags unknown/unresolved types
(by default unknown or imported-via-`using` types are skipped, because the spec
guarantees a file stays valid even when external definitions are unavailable).
YAML sub-commands need `pyyaml`; everything else is pure stdlib.

## Shipping MRF to JavaScript (`scripts/mrf.js`)

`scripts/mrf.js` is a read-only JS twin of the parser: same EBNF, same data
mapping, no dependencies. It runs in Node (`require`, or `import mrf from
"./mrf.js"`) and in the browser (`<script>` -> global `MRF`), and it has its own
CLI (`parse | types | records | to-json | validate`). It **parses only** — no
writer, no `fmt`, no `from-json`.

**Rule of thumb: for your own parsing, validating and converting, always use
`mrf.py`.** Reach for `mrf.js` only when the *deliverable itself* runs in
JavaScript — an HTML preview that reads `.mrf` at runtime, a browser tool, a Node
script for the user. Then copy or inline that file; never hand-write a second
parser.

```js
const mrf = require("./mrf.js");        // browser: global MRF
const doc = mrf.parse(text);

doc.typesJSON();      // schema: { Type: { fields: { f: {kind,type,isList,required,attributes} } } }
doc.recordsJSON();    // data:   [ { name, type, data } ]   (refs resolved; {resolveRefs:false} keeps $ref)
doc.toData();         // identical output to mrf.py's to_data / `to-json`
mrf.validate(doc);    // same constraint messages as mrf.py
```

Two implementations of one grammar drift. After touching either, check them
against each other — the outputs must be byte-identical:

```bash
python3 scripts/mrf.py to-json examples/sample.mrf > /tmp/py.json
node     scripts/mrf.js to-json examples/sample.mrf > /tmp/js.json
diff /tmp/py.json /tmp/js.json
```

## Authoring workflow

When writing MRF by hand or generating it:

1. Put the schema first (`type …`), then the data (`record …`) — though order is
   free, this reads best and lets `validate` check constraints.
2. Apply the four canonical rules above; when unsure whether a `(` is a record
   or a type, decide by position (after `=` = value/inline record; after `:` =
   type expression).
3. Prefer named `type`s with `required` / min / max attributes so `validate`
   actually enforces something — MRF's whole point is co-located validation.
4. For **heterogeneous lists** (`blocks[]: Any()`), write typed inline records
   `:Type( … )` — only then does `validate` check the elements. An anonymous
   `( … )` element in an `Any()` field is accepted unchecked.
5. After writing, run `python3 scripts/mrf.py validate file.mrf`. If it parses,
   also run `fmt` to normalise formatting for clean diffs.
   **Caveat:** `using` imports are never resolved, so types defined in another
   file count as unknown and are skipped **silently** — a file full of typed
   blocks can then wrongly report `OK`. Merge the type definitions into one
   `Document`, or run `--strict` to make unknown types visible.

## What the tool does and doesn't do

The parser is a faithful image of the v1 EBNF and checks **syntax**. `validate()`
is the downstream constraint checker: it enforces `required`, `minValue`,
`maxValue`, `maxLength` and basic type agreement for typed records, nested
anonymous types, and — since v1.1 — every typed inline record at any depth
(a value typed differently from its declared field type is an error). Untyped
inline records in `Any()` fields stay unchecked by design. It does **not** fetch
`using` imports (per spec, an interpreter
must remain valid without them) and does not evaluate defaults (left open for
v1.1). Reference resolution has a cycle guard, so self-referential data won't
loop.
