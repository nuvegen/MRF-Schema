# Model-Record-Format (MRF) — v1 / v1.1 reference

Condensed, tool-oriented reference for the skill. Canonical source:
<https://nuvegen.github.io/MRF-Schema/record_model_definition_v1.html>.
The EBNF grammar and attribute tables below are reproduced so the parser and any
hand-authoring stay exactly aligned with the spec.

**v1.1** adds one production — typed inline records, `:Type( … )` in value position
— and is purely additive: a v1.1 parser reads every v1 file unchanged (a `:` at the
start of a value was a syntax error in v1), while a v1 parser rejects `:Type( … )`.

## Table of contents
- [Concepts](#concepts)
- [Declarations](#declarations)
- [Values](#values)
- [Typed inline records (v1.1)](#typed-inline-records-v11)
- [Standard types & attributes](#standard-types--attributes)
- [Canonical rules](#canonical-rules)
- [Lexical details](#lexical-details)
- [EBNF grammar](#ebnf-grammar)
- [Worked example](#worked-example)

## Concepts

MRF stores **schema and data in one file**. Two top-level declarations:

- `type <Name> ( … )` — a **model** (schema). Fields are `name: TypeExpr`.
- `record <name?>:<Type?> ( … )` — **data**. Fields are `name = value`.

Both a record's name and its `:Type` are optional. External models can be pulled
in with `using "<uri>"`, but an interpreter may ignore imports; a file must stay
valid and processable without them.

## Declarations

Type (schema):

```mrf
type Car (
    name:  String( required=true )   // named type -> parens hold ATTRIBUTES (key=value)
    tires: Tire()                    // reference to another type
    motor: ( hasGas: Boolean() hasElectric: Boolean() ) ( required=true )
    //     ^ anonymous type: 1st parens = FIELDS, optional 2nd parens = attributes
)
```

Record (data):

```mrf
record audi:Car (      // named + typed
    name="A4"
    tires=( maxTemp=10 minTemp=-20 )   // inline record (a '(' after '=')
)
record opel  ( brand="Opel" )     // name only
record :Car  ( brand="Renault" )  // type only
record       ( brand="Skoda" )    // anonymous
```

Field-level array marker and optional inline type on assignment:

```mrf
record (
    myList[]:DictionaryItem = [ (key="A" value="Ananas") (key="B" value="Banana") ]
)
```

## Values

- **Scalars**: string `"…"`, number (`-3.14`, `1.5e3`), boolean (`true`/`false`).
- **Inline record**: `( key=value … )` — a `(` right after `=`.
- **Array**: `[ element … ]` — a `[` right after `=`. Elements may be scalars,
  record references, or inline records; empty `[ ]` is allowed.
- **Record reference**: a bare identifier used as a value (`customer = jane`).

```mrf
record palette (
    tags   = [ "warm" "primary" ]   // scalars
    colors = [ red green ]          // references
    empty  = [ ]                    // empty list
)
```

## Typed inline records (v1.1)

An inline record may carry its own type name. This is the only way to validate a
**heterogeneous list** — a field of type `Any()` whose elements have different
shapes — because only the element itself knows which contract applies:

```mrf
type TextH1   ( id: String( required=true ) content: String( required=true maxLength=20 ) )
type CoreImage( id: String( required=true ) path:    String( required=true ) )

record page (
    blocks[]:Any = [
        :TextH1( id="b1" content="Headline" )
        :CoreImage( id="b2" path="/image.jpg" )
        ( id="b3" style="free" )          // anonymous element stays valid, stays unchecked
    ]
    header = :TextH1( id="h" content="Title" )   // works for single values too
)
```

What `mrf.validate()` does with it:

- A typed inline record is always checked against **its own** type — at any nesting
  depth, in `Any()` fields included.
- If the field declares a different named type than the value carries, that is an
  error (`field declares 'X', value is typed 'Y'`).
- Anonymous inline records stay valid and unchecked; typing is optional.
- Unknown types are skipped silently, as in v1 — `--strict` / `strict_unknown=True`
  makes them visible. **Pitfall:** `using` is never resolved, so types living in
  another file count as unknown; a file full of typed blocks can then wrongly report
  `OK`. Merge the type definitions into one `Document`, or use `--strict`.
- No inheritance: a shared field such as `id` must be declared by every type itself.
  Fields not present in the type stay permitted.

**JSON mapping.** In the data tree a typed inline record becomes a dict with a
`_type` key. For a *record*, `_type` is metadata (emitted only with
`include_meta=True` / `--meta`); for an *inline record* it is the discriminator and
therefore **content** — it is emitted always, and `from-json` turns it back into
`:Type( … )`. Without that, every JSON round trip would be lossy.

## Standard types & attributes

Attributes appear in parentheses after a **named** type: `String( required=true maxLength=10 )`.

### String — arbitrary text
| Attribute | Meaning |
| --- | --- |
| `required: Boolean` | field must be present |
| `maxLength: Int` | maximum string length |

### Int — signed integer
| Attribute | Meaning |
| --- | --- |
| `required: Boolean` | field must be present |
| `minValue: Int` | minimum allowed value |
| `maxValue: Int` | maximum allowed value |

### Decimal — signed decimal number
| Attribute | Meaning |
| --- | --- |
| `required: Boolean` | field must be present |
| `minValue: Decimal` | minimum allowed value |
| `maxValue: Decimal` | maximum allowed value |

### Boolean — `true`/`1` or `false`/`0`
| Attribute | Meaning |
| --- | --- |
| `required: Boolean` | field must be present |

### Any — placeholder for any type
| Attribute | Meaning |
| --- | --- |
| `required: Boolean` | field must be present |

### DictionaryItem — key/value entry (extended list type)
```mrf
type DictionaryItem (
    key:   String( required=true )
    value: Any()
)
```

## Canonical rules

Four rules keep the grammar context-free (decide by the next token only):

1. **Array vs. inline record**: `[` after `=` ⇒ array; `(` after `=` ⇒ inline record.
2. **Named vs. anonymous type after `:`**: a *TypeIdentifier* ⇒ named type (parens =
   attributes `key=value`); a `(` ⇒ anonymous type (parens = field defs `key: Type`),
   with an optional 2nd parens for that type's attributes.
3. **Bare word as value ⇒ record reference**; `true`/`false` are reserved booleans.
4. **`:` at the start of a value ⇒ typed inline record** *(v1.1)*. `blocks = [
   :TextH1( … ) ]` binds the element to type `TextH1`. No collision with rule 2:
   there the `:` stands *after a field name*, here *before a value*.

**Open for a later version**: whether `key=value` on a field's type may also express
default values (in addition to constraints) is intentionally unspecified —
recommendation is a separate `default=` attribute to keep constraint and value apart.

## Lexical details

- **Separators**: whitespace or `,`, interchangeable and insignificant.
- **Comments**: `//` to end of line; `/* … */` multi-line.
- **Reserved words**: `using`, `type`, `record`, `true`, `false`.
- **Strings**: double-quoted with `\`-escapes (`\n \t \r \" \\ \/ \b \f`).
- **Numbers**: optional `-`, integer part, optional `.fraction`, optional `e`/`E`
  exponent with optional sign.
- **Identifiers / TypeIdentifiers**: `Letter { Letter | Digit | "_" }`.

## EBNF grammar

```ebnf
(* ===== Structure ===== *)
Program      ::= { Using | TypeDef | RecordDef } ;

Using        ::= "using" StringLiteral ;

TypeDef      ::= "type" TypeIdentifier "(" { FieldDef } ")" ;

FieldDef     ::= Identifier [ ArrayMarker ] ":" TypeExpr ;

TypeExpr     ::= NamedType | AnonType ;
NamedType    ::= TypeIdentifier "(" { Param } ")" ;
AnonType     ::= "(" { FieldDef } ")" [ "(" { Param } ")" ] ;   (* 2nd pair = attributes *)

Param        ::= Identifier "=" ScalarValue ;

RecordDef    ::= "record" [ Identifier ] [ ":" TypeIdentifier ] "(" { FieldAssign } ")" ;

FieldAssign  ::= Identifier [ ArrayMarker ] [ ":" TypeIdentifier ] "=" Value ;

(* A "[" after "=" starts an array literal, otherwise SingleValue. *)
Value        ::= ArrayValue | SingleValue ;
ArrayValue   ::= "[" { Element } "]" ;
SingleValue  ::= Element ;
Element      ::= ScalarValue | RecordRef | InlineRecord | TypedInlineRecord ;
InlineRecord ::= "(" { FieldAssign } ")" ;
TypedInlineRecord ::= ":" TypeIdentifier "(" { FieldAssign } ")" ;   (* v1.1 *)
RecordRef    ::= Identifier ;

ArrayMarker  ::= "[" "]" ;
ScalarValue  ::= StringLiteral | NumberLiteral | BooleanLiteral ;

(* ===== Lexical ===== *)
Identifier     ::= Letter { Letter | Digit | "_" } ;
TypeIdentifier ::= Letter { Letter | Digit | "_" } ;

StringLiteral  ::= '"' { EscapeSeq | ( ANY_CHAR - '"' - '\' ) } '"' ;
EscapeSeq      ::= '\' ANY_CHAR ;

NumberLiteral  ::= [ "-" ] Digit { Digit } [ "." Digit { Digit } ] [ ExponentPart ] ;
ExponentPart   ::= ( "e" | "E" ) [ "+" | "-" ] Digit { Digit } ;

BooleanLiteral ::= "true" | "false" ;

Letter         ::= "A".."Z" | "a".."z" ;
Digit          ::= "0".."9" ;

(* Separators: whitespace OR "," between items — optional, interchangeable.
   Comments: "//" to end of line, or "/* … */".
   Reserved words: using, type, record, true, false. *)
```

The reference parser checks **syntax only**; constraint evaluation (`required`,
`minValue`, `maxValue`, `maxLength`) belongs to a downstream validator — here,
`mrf.validate()`.

## Worked example

Exercises every v1 and v1.1 construct (accepted by the reference parser):

```mrf
using "https://w3-isp.net/mrf/types.mrf"

type Person (
    name:   String( required=true )
    age:    Int( minValue=0 maxValue=150 )
    active: Boolean()
)

type Order (
    id:       String( required=true )
    items[]:  DictionaryItem()
    customer: Person()
    blocks[]: Any()
)

type TextH1 (
    id:      String( required=true )
    content: String( required=true maxLength=20 )
)

record jane: Person (
    name="Jane Doe",
    age=25,
    active=false
)

record (                                    // anonymous record
    id="X1"
    items = [ (key="A" value="Ananas") (key="B" value="Banana") ]
    customer = jane                          // record reference
    blocks = [ :TextH1( id="b1" content="Headline" ) ]   // typed inline record (v1.1)
)
```
