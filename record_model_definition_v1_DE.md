# Model-Record-Format (MRF)

Es braucht doch nicht noch ein weiteres Datenformat – schließlich haben wir bereits JSON, XML, TOML und viele weitere.

Das *Model-Record-Format* ist jedoch aus einem konkreten Bedarf heraus entstanden:

- **JSON** wird bei komplexeren Strukturen schnell unübersichtlich.
- **TOML** ist in seinen Ausdrucksmöglichkeiten eher eingeschränkt (flache Konfiguration statt tiefer Verschachtelung).
- Und keines dieser Formate legt **Schema und Daten in einer Datei** zusammen — Validierungsregeln leben stets extern (etwa in einem separaten JSON-Schema).

Das neue Format orientiert sich bewusst am **C-Standard**: es ist klar strukturiert, typisiert und darauf ausgelegt, sowohl lesbar als auch leicht validierbar zu sein.

> **Version:** v1 (konsolidiert) · **Status:** in sich konsistent, referenz-validiert
>
> **Änderungen ggü. Erst-Entwurf:** Attribut-Syntax vereinheitlicht (Attribute stehen
> **in** den Typ-Klammern); anonyme Typen, Arrays und Record-Referenzen sind nun
> grammatisch abgedeckt; Record-Name **und** -Typ sind optional; Kommentare in der
> Grammatik verankert; **ein** Typ-Vokabular (`String, Int, Decimal, Boolean, Any,
> DictionaryItem` — kein `Number`/`min`/`max` mehr); Attribut-Tabellen korrigiert
> (`minValue`/`maxValue` gehören zu `Int`/`Decimal`, nicht zu `String`); Tippfehler
> bereinigt. Die EBNF (§EBNF) ist gegen einen Referenz-Parser geprüft, der alle
> vollständigen Beispiele dieses Dokuments akzeptiert.
>
> **Änderung in dieser Revision:** Array-/Listenwerte werden jetzt mit eckigen
> Klammern `[ … ]` geschrieben (statt `( … )`) — dadurch sind sie klar von
> Inline-Records `( … )` unterscheidbar.

## Model Record Definition

Das **Model-Record-Format (MRF)** ist ein typisiertes, strukturiertes Datenformat, das speziell für die handhabbare Speicherung und Validierung komplexer Datenmodelle entwickelt wurde. Im Gegensatz zu JSON oder TOML bietet MRF eine klare, C-ähnliche Syntax, explizite Datentypen und die Möglichkeit, Schemas direkt in den Daten zu definieren. Dadurch kombiniert MRF **Lesbarkeit, Ausdrucksstärke und Werkzeugunterstützung** in einem einheitlichen Format und erleichtert sowohl die manuelle Bearbeitung als auch automatisierte Verarbeitung und Codegenerierung.

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

Eine Datei kann entweder eines oder beides enthalten (Model-Definition oder Record-Definition).

Eine **Modeldefinition** wird mit

```text
type <name> ( ... )
```

beschrieben. Innerhalb eines Models kann auf andere Models verwiesen werden:

```mrf
type Car (
    brand: String()
)
```

Ein **Record** wird mit

```text
record <name?>:<model?> ( ... )
```

beschrieben, wobei sowohl `<name>` als auch `<model>` **optional** sind. Zulässig sind also: benannt-und-getypt (`record audi:Car`), nur benannt (`record opel`), nur getypt (`record :Car`) und anonym (`record`). Innerhalb eines Records kann auf andere Records verwiesen werden:

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

### Typisiert und anonym

Typen können typisiert oder anonym verwendet werden.

> **Typisiert:**
>
> `brand: String()`
> `tires: Tire()`

> **Anonym:**
>
> `tires: ( maxTemp: Int() minTemp: Int() snow: Int() rain: Int() dry: Int() )`

Ein anonymer Typ kann — falls er selbst Attribute tragen soll — nach dem Feld-Block ein zweites Klammernpaar mit Attributen führen (siehe `motor` oben: `( … ) ( required=true )`). Bei **benannten** Typen stehen Attribute dagegen direkt in den Typ-Klammern (`String( required=true )`).

### Standard-Typen und Attribute

Mittels Attributen kann das Feld näher beschrieben werden. Diese stehen in Klammern nach dem Typ:

```mrf
type Car (
    brand: String( required=true maxLength=10 )
)
```

Folgende Typen und Attribute sind in Version 1 definiert:

#### String

Eine Folge beliebiger Zeichen (Text).

| Attribut          | Beschreibung              |
|-------------------|---------------------------|
| required: Boolean | Definiert ein Pflichtfeld |
| maxLength: Int    | Maximale Länge des Strings |

#### Int

Ein positiver oder negativer ganzzahliger Wert.

| Attribut          | Beschreibung              |
|-------------------|---------------------------|
| required: Boolean | Definiert ein Pflichtfeld |
| minValue: Int     | Möglicher minimaler Wert  |
| maxValue: Int     | Möglicher maximaler Wert  |

#### Decimal

Eine positive oder negative Dezimalzahl.

| Attribut            | Beschreibung              |
|---------------------|---------------------------|
| required: Boolean   | Definiert ein Pflichtfeld |
| minValue: Decimal   | Möglicher minimaler Wert  |
| maxValue: Decimal   | Möglicher maximaler Wert  |

#### Boolean

Ein boolescher Wert: `1`/`true` oder `0`/`false`.

| Attribut          | Beschreibung              |
|-------------------|---------------------------|
| required: Boolean | Definiert ein Pflichtfeld |

#### Any

Ein Platzhalter für sämtliche Typen.

| Attribut          | Beschreibung              |
|-------------------|---------------------------|
| required: Boolean | Definiert ein Pflichtfeld |

#### DictionaryItem

Ein erweiterter Listentyp mit Key und Value.

```mrf
type DictionaryItem (
    key:   String( required=true )
    value: Any()
)
```

Beispiel — als Array verwendet. Array-Literale stehen in eckigen Klammern `[ … ]` und sind damit ohne Typauflösung von Inline-Records `( … )` unterscheidbar (der `[]`-Marker am Feld dokumentiert weiterhin den Listen-Typ, ist zur Abgrenzung aber nicht mehr nötig):

```mrf
record (
    myList[]:DictionaryItem = [
        (key="A" value="Ananas")
        (key="B" value="Banana")
    ]
)
```

Elemente können auch Skalare oder Referenzen sein, und leere Listen sind zulässig:

```mrf
record palette (
    tags   = [ "warm" "primary" ]     // Skalare
    colors = [ red green ]            // Record-Referenzen
    empty  = [ ]
)
```

### Externe Modeldefinitionen

Mittels des Tokens `using "<uri>"` können externe Modeldefinitionen eingebunden werden, wobei `<uri>` eine relative Pfadangabe im aktuellen Protokoll oder eine absolute URI mit Protokollangabe ist:

```mrf
using "./types.mrf"
using "file://home/alex/types.mrf"
using "https://w3-isp.net/types.mrf"
```

⚠️ Hinweis

- Ein Interpreter **MUSS** externe Definitionen nicht verwenden, um MRF-Dateien zu verarbeiten.
- Falls externe Definitionen nicht verfügbar oder nicht ladbar sind, **MUSS** der Interpreter diese ignorieren. (Ein `using "stdio"` etwa ist grammatisch gültig und wird als benannter Import behandelt, den ein Interpreter ignorieren darf.)
- Das Model-Record-Format ist so spezifiziert, dass es auch **ohne** externe Typdefinitionen **gültig** und **verarbeitbar** ist.

### Kommentare

Kommentare werden entweder mit `//` bis zum nächsten Zeilenvorschub oder mit `/* … */` über mehrere Zeilen gesetzt:

```mrf
// Dies ist ein Kommentar
record config: Configuration(
    path = "./" // Kommentar in einer Zeile

    /* Kommentar über mehrere
       Zeilen */
)
```

## Kanonische Regeln (v1)

Drei Regeln halten die Grammatik **kontextfrei** — der Interpreter muss nie erst Typen auflösen, um korrekt weiterzulesen. Das ist Voraussetzung für die Zusage, dass MRF auch ohne externe Typdefinitionen verarbeitbar bleibt.

1. **Array-Literale sind eckig-klammer-abgegrenzt.** Ein Wert ist genau dann ein Array, wenn nach `=` ein `[` folgt (`items = [ … ]`); ein `(` leitet dagegen einen Inline-Record ein. Der Parser entscheidet also allein am öffnenden Token, ohne Typauflösung. Der `[]`-Marker am Feld (`items[]: …`) dokumentiert weiterhin den Listen-Typ, ist zur Abgrenzung aber nicht mehr erforderlich.
2. **Benannte vs. anonyme Typen sind nach `:` eindeutig.** Folgt ein `TypeIdentifier`, ist es ein benannter Typ (Klammern enthalten Attribute `key=value`); folgt `(`, ist es ein anonymer Typ (Klammern enthalten Feld-Definitionen `key: Type`). Ein optionales zweites Klammernpaar nach einem anonymen Feld-Block trägt dessen Attribute.
3. **Ein Bareword als Wert ist eine Record-Referenz.** `true`/`false` sind reserviert und werden als Boolean erkannt, sodass Referenzen nie mit ihnen kollidieren.

**Offen für v1.1:** Ob `key=value`-Angaben am Typ eines Feldes neben Attributen (`required`, `minValue` …) auch **Default-Werte** ausdrücken dürfen, ist bewusst noch nicht festgelegt (Empfehlung: separates `default=`-Attribut, um Constraint und Wert zu trennen).

## EBNF-Grammatik

```ebnf
(* ===== Struktur ===== *)
Program      ::= { Using | TypeDef | RecordDef } ;

Using        ::= "using" StringLiteral ;

TypeDef      ::= "type" TypeIdentifier "(" { FieldDef } ")" ;

FieldDef     ::= Identifier [ ArrayMarker ] ":" TypeExpr ;

TypeExpr     ::= NamedType | AnonType ;
NamedType    ::= TypeIdentifier "(" { Param } ")" ;
AnonType     ::= "(" { FieldDef } ")" [ "(" { Param } ")" ] ;   (* 2. Paar = Attribute *)

Param        ::= Identifier "=" ScalarValue ;

RecordDef    ::= "record" [ Identifier ] [ ":" TypeIdentifier ] "(" { FieldAssign } ")" ;

FieldAssign  ::= Identifier [ ArrayMarker ] [ ":" TypeIdentifier ] "=" Value ;

(* Ein "[" nach "=" leitet ein Array-Literal ein, sonst SingleValue. *)
Value        ::= ArrayValue | SingleValue ;
ArrayValue   ::= "[" { Element } "]" ;
SingleValue  ::= Element ;
Element      ::= ScalarValue | RecordRef | InlineRecord ;
InlineRecord ::= "(" { FieldAssign } ")" ;
RecordRef    ::= Identifier ;

ArrayMarker  ::= "[" "]" ;
ScalarValue  ::= StringLiteral | NumberLiteral | BooleanLiteral ;

(* ===== Lexik ===== *)
Identifier     ::= Letter { Letter | Digit | "_" } ;
TypeIdentifier ::= Letter { Letter | Digit | "_" } ;

StringLiteral  ::= '"' { EscapeSeq | ( ANY_CHAR - '"' - '\' ) } '"' ;
EscapeSeq      ::= '\' ANY_CHAR ;

NumberLiteral  ::= [ "-" ] Digit { Digit } [ "." Digit { Digit } ] [ ExponentPart ] ;
ExponentPart   ::= ( "e" | "E" ) [ "+" | "-" ] Digit { Digit } ;

BooleanLiteral ::= "true" | "false" ;

Letter         ::= "A".."Z" | "a".."z" ;
Digit          ::= "0".."9" ;

(* Separatoren: Whitespace ODER "," zwischen Listenelementen — beides optional,
   austauschbar, ohne Bedeutung.
   Kommentare: "//" bis Zeilenende, oder "/* … */" (mehrzeilig).
   Reservierte Wörter: using, type, record, true, false. *)
```

## Konformes Gesamtbeispiel

Das folgende Beispiel nutzt alle v1-Konstrukte und wird vom Referenz-Parser akzeptiert:

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

record (                                    // anonymer Record
    id="X1"
    items = [ (key="A" value="Ananas") (key="B" value="Banana") ]
    customer = jane                          // Record-Referenz
)
```

Ein Referenz-Parser (rekursiver Abstieg, 1:1-Abbild der obigen EBNF) sowie eine Testsuite über alle vollständigen Beispiele dieses Dokuments liegen als `mrf_parser.py` / `test_mrf.py` bei. Der Parser prüft ausschließlich die **Syntax**; die Auswertung der Attribut-Constraints (`required`, `minValue`, `maxValue`, `maxLength`) ist Aufgabe eines nachgelagerten Validators.
