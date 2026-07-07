# Model-Record-Format (MRF)

*A typed, C-flavoured data format that keeps schema and data in a single file.*

The world hardly needs yet another data format — we already have JSON, XML, TOML, and many more. Model-Record-Format grew out of a concrete need, though:

- **JSON** becomes hard to read for more complex structures.
- **TOML** is fairly limited in expressiveness (flat configuration rather than deep nesting).
- And none of these formats keeps **schema and data in one file** — validation rules always live externally (e.g. in a separate JSON Schema).

The format deliberately takes its cues from **C**: it is clearly structured, typed, and designed to be both readable and easy to validate.

> **Version:** v1 (consolidated) · **Status:** internally consistent, reference-validated
>
> **Changes since the initial draft:** attribute syntax unified (attributes live
> **inside** the type's parentheses); anonymous types, arrays and record references are
> now covered by the grammar; a record's name **and** type are optional; comments are
> anchored in the grammar; a single type vocabulary (`String, Int, Decimal, Boolean,
> Any, DictionaryItem` — no more `Number`/`min`/`max`); attribute tables corrected
> (`minValue`/`maxValue` belong to `Int`/`Decimal`, not `String`); typos fixed. The
> grammar (see [EBNF Grammar](#ebnf-grammar)) is checked against a reference parser
> that accepts every complete example in this document.
>
> **Change in this revision:** array/list values are now written with square brackets
> `[ … ]` (instead of `( … )`), making them clearly distinct from inline records
> `( … )`.

## Model Record Definition

The **Model-Record-Format (MRF)** is a typed, structured data format built for the manageable storage and validation of complex data models. Unlike JSON or TOML, MRF offers a clear, C-like syntax, explicit data types, and the ability to define schemas directly alongside the data. It thus combines **readability, expressiveness and tooling support** in a single format, easing both manual editing and automated processing and code generation.

```mrf
using "https://w3-isp.net/mrf/types.mrf"

type Tire (
    brand:   String()
    maxTemp: Int()
    minTemp: Int()
    snow:    Int( minValue=0 maxValue=10 )
    rain:    Int( minValue=0 maxValue=10 )
    dry:     Int( minValue=0 maxValue=10 )
)

type Car (
    name:  String( required=true )
    brand: String()
    tires: Tire()
    motor: ( hasGas: Boolean() hasElectric: Boolean() ) ( required=true )
)

record audiA4Winter:Car (
    name="A4"
    brand="Audi"
    tires=( maxTemp=10 minTemp=-20 rain=5 snow=9 dry=6 )
)

record BMW5er:Car (
    name="540"
    brand="BMW"
    tires=( maxTemp=10 minTemp=-20 )
)
```

A file may contain either one or both (a model definition or a record definition).

A **model definition** is written as:

```text
type <name> ( ... )
```

Within a model, other models can be referenced:

```mrf
type Car (
    brand: String()
)
```

A **record** is written as:

```text
record <name?>:<model?> ( ... )
```

where both `<name>` and `<model>` are **optional**. The following are therefore all valid: named-and-typed (`record audi:Car`), name only (`record opel`), type only (`record :Car`), and anonymous (`record`). Within a record, other records can be referenced:

```mrf
record audi:Car (
    brand="Audi"
)

record opel (
    thebrand="Opel"
)

record (
    brand="Renault"
)
```

```mrf
record winterTire (
    maxTemp=10
    minTemp=-20
    snow=10
    rain=3
    dry=5
)

record car (
    brand="BMW"
    tires=winterTire
)
```

## Model

### Typed and anonymous

Types may be used either typed or anonymously.

> **Typed:**
>
> `brand: String()`
> `tires: Tire()`

> **Anonymous:**
>
> `tires: ( maxTemp: Int() minTemp: Int() snow: Int() rain: Int() dry: Int() )`

An anonymous type may — if it needs attributes of its own — carry a second pair of parentheses with attributes after its field block (see `motor` above: `( … ) ( required=true )`). For **named** types, attributes go directly inside the type's parentheses (`String( required=true )`).

### Standard types and attributes

Attributes further describe a field. They appear in parentheses after the type:

```mrf
type Car (
    brand: String( required=true maxLength=10 )
)
```

The following types and attributes are defined in version 1:

#### String

A sequence of arbitrary characters (text).

| Attribute         | Description             |
|-------------------|-------------------------|
| required: Boolean | Marks the field as required |
| maxLength: Int    | Maximum string length   |

#### Int

A positive or negative integer value.

| Attribute         | Description             |
|-------------------|-------------------------|
| required: Boolean | Marks the field as required |
| minValue: Int     | Minimum allowed value   |
| maxValue: Int     | Maximum allowed value   |

#### Decimal

A positive or negative decimal number.

| Attribute           | Description             |
|---------------------|-------------------------|
| required: Boolean   | Marks the field as required |
| minValue: Decimal   | Minimum allowed value   |
| maxValue: Decimal   | Maximum allowed value   |

#### Boolean

A boolean value: `1`/`true` or `0`/`false`.

| Attribute         | Description             |
|-------------------|-------------------------|
| required: Boolean | Marks the field as required |

#### Any

A placeholder for any type.

| Attribute         | Description             |
|-------------------|-------------------------|
| required: Boolean | Marks the field as required |

#### DictionaryItem

An extended list type with a key and a value.

```mrf
type DictionaryItem (
    key:   String( required=true )
    value: Any()
)
```

Example — used as an array. Array literals are enclosed in square brackets `[ … ]`, which makes them distinguishable from inline records `( … )` without resolving the type (the `[]` marker on the field still documents the list type, but is no longer needed for disambiguation):

```mrf
record (
    myList[]:DictionaryItem = [
        (key="A" value="Ananas")
        (key="B" value="Banana")
    ]
)
```

Elements may also be scalars or references, and empty lists are allowed:

```mrf
record palette (
    tags   = [ "warm" "primary" ]     // scalars
    colors = [ red green ]            // record references
    empty  = [ ]
)
```

### External model definitions

Using the `using "<uri>"` token, external model definitions can be pulled in, where `<uri>` is either a relative path in the current protocol or an absolute URI with a protocol prefix:

```mrf
using "./types.mrf"
using "file://home/alex/types.mrf"
using "https://w3-isp.net/types.mrf"
```

> ⚠️ **Note**
>
> - An interpreter is **NOT** required to use external definitions in order to process MRF files.
> - If external definitions are unavailable or cannot be loaded, the interpreter **MUST** ignore them. (A `using "stdio"`, for instance, is grammatically valid and is treated as a named import that an interpreter may ignore.)
> - MRF is specified such that it remains **valid** and **processable** even **without** external type definitions.

### Comments

Comments are written either with `//` up to the next line break, or with `/* … */` spanning multiple lines:

```mrf
// This is a comment
record config: Configuration(
    path = "./" // inline comment

    /* multi-line
       comment */
)
```

## Canonical rules (v1)

Three rules keep the grammar **context-free** — an interpreter never has to resolve types first in order to keep reading correctly. This is a prerequisite for the guarantee that MRF stays processable without external type definitions.

1. **Array literals are square-bracket delimited.** A value is an array exactly when a `[` follows the `=` (`items = [ … ]`); a `(` instead starts an inline record. The parser therefore decides purely by the opening token, without resolving types. The `[]` marker on a field (`items[]: …`) still documents the list type, but is no longer required for disambiguation.
2. **Named vs. anonymous types are unambiguous after `:`.** If a `TypeIdentifier` follows, it is a named type (parentheses hold attributes `key=value`); if `(` follows, it is an anonymous type (parentheses hold field definitions `key: Type`). An optional second pair of parentheses after an anonymous field block carries that type's attributes.
3. **A bare word used as a value is a record reference.** `true`/`false` are reserved and recognised as booleans, so references never collide with them.

**Open for v1.1:** whether `key=value` entries on a field's type may express **default values** in addition to attributes (`required`, `minValue`, …) is deliberately left unspecified (recommendation: a separate `default=` attribute, to keep constraint and value apart).

## EBNF Grammar

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
Element      ::= ScalarValue | RecordRef | InlineRecord ;
InlineRecord ::= "(" { FieldAssign } ")" ;
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

(* Separators: whitespace OR "," between list items — both optional, interchangeable,
   insignificant.
   Comments: "//" to end of line, or "/* … */" (multi-line).
   Reserved words: using, type, record, true, false. *)
```

## Complete conforming example

The following example exercises every v1 construct and is accepted by the reference parser:

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
)
```

A reference parser (recursive descent, a 1:1 image of the grammar above) together with a test suite covering every complete example in this document is provided as `mrf_parser.py` / `test_mrf.py`. The parser checks **syntax only**; evaluating the attribute constraints (`required`, `minValue`, `maxValue`, `maxLength`) is the job of a downstream validator.
