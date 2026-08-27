# Model-Record-Format (MRF)

Es braucht doch nicht noch ein weiteres Datenformat – schließlich haben wir bereits JSON, XML, TOML und viele weitere.

Das *Model-Record-Format* ist jedoch aus einem konkreten Bedarf heraus entstanden:

- **JSON** wird bei komplexeren Strukturen schnell unübersichtlich.
- **TOML** ist in seinen Ausdrucksmöglichkeiten eher eingeschränkt (flache Konfiguration statt tiefer Verschachtelung).
- Und keines dieser Formate legt **Schema und Daten in einer Datei** zusammen — Validierungsregeln leben stets extern (etwa in einem separaten JSON-Schema).

Das neue Format orientiert sich bewusst am **C-Standard**: es ist klar strukturiert, typisiert und darauf ausgelegt, sowohl lesbar als auch leicht validierbar zu sein.

> **Version:** v1.1 · **Status:** in sich konsistent, referenz-validiert
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
>
> **Neu in v1.1 — typisierte Inline-Records:** Ein Element in Wertposition darf einen
> Typnamen tragen, geschrieben `:Type( … )` (siehe
> [Typisierte Inline-Records](#typisierte-inline-records-v11)). Die Erweiterung ist
> **rein additiv**: Ein v1.1-Parser liest jede v1-Datei unverändert, denn ein `:` am
> Wertanfang war in v1 ein Syntaxfehler. Ein v1-Parser lehnt umgekehrt `:Type( … )`
> mit einem Syntaxfehler ab. Es wurde nichts entfernt und keine bestehende Regel
> umgedeutet.

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

### Typisierte Inline-Records (v1.1)

In v1 ist ein Inline-Record anonym: `( key="A" value="Ananas" )`. Sein Inhalt lässt
sich nur prüfen, wenn das **umgebende Feld** einen benannten Typ deklariert. Für
heterogene Listen — ein Feld vom Typ `Any()`, das Elemente unterschiedlicher Gestalt
enthält — geht das prinzipbedingt nicht: Erst das Element selbst weiß, welcher Vertrag
gilt.

Seit v1.1 darf ein Element deshalb seinen eigenen Typnamen mitführen:

```mrf
type TextH1 (
    id:      String( required=true )
    content: String( required=true maxLength=20 )
)

type CoreImage (
    id:   String( required=true )
    path: String( required=true )
)

record seite (
    blocks[]:Any = [
        :TextH1( id="b1" content="Überschrift" )
        :CoreImage( id="b2" path="/bild.jpg" )
        ( id="b3" style="frei" )              // anonyme Elemente bleiben gültig
    ]
)
```

Der Typname bindet das Element an diesen Typ, und ein Validator prüft es dagegen —
in beliebiger Schachtelungstiefe und auch in `Any()`-Feldern. Die Form gilt ebenso für
Einzelwerte (`header = :TextH1( … )`), nicht nur innerhalb von Arrays.

> **Regeln für die Validierung**
>
> - Ein typisierter Inline-Record wird immer gegen **seinen eigenen** Typ geprüft.
> - Deklariert das Feld einen anderen benannten Typ als der Wert trägt, ist das ein
>   Fehler.
> - Anonyme Inline-Records bleiben gültig und bleiben **ungeprüft** — die Typisierung
>   ist optional.
> - Unbekannte Typen werden wie in v1 stillschweigend übersprungen (siehe Hinweis
>   unter [Externe Modeldefinitionen](#externe-modeldefinitionen)); ein Strict-Modus
>   darf sie melden.
> - Es gibt keine Vererbung: Ein gemeinsames Feld wie `id` muss jeder Typ selbst
>   deklarieren. Felder, die im Typ nicht vorkommen, bleiben erlaubt — deren Prüfung
>   ist Sache der aufsetzenden Anwendung.

In einer JSON-Abbildung gehört der Typname zu den **Nutzdaten**, nicht zu den
Metadaten: Er ist der Diskriminator, der die Elemente einer heterogenen Liste
auseinanderhält. Eine Abbildung, die ihn verwirft, ist verlustbehaftet. Empfohlen ist
ein `_type`-Schlüssel im Objekt, aus dem sich `:Type( … )` wieder herstellen lässt.

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
- **Fallstrick für Validatoren:** Weil `using` nicht aufgelöst wird, gelten Typen aus
  einer anderen Datei als unbekannt und werden **stillschweigend** übersprungen. Eine
  Datei voller typisierter Blöcke (`:TextH1( … )`) kann deshalb fälschlich `OK`
  melden. Wer über Dateigrenzen hinweg prüfen will, muss die Typdefinitionen in einem
  Dokument zusammenführen oder einen Strict-Modus verwenden, der unbekannte Typen
  sichtbar macht.

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

## Kanonische Regeln

Vier Regeln halten die Grammatik **kontextfrei** — der Interpreter muss nie erst Typen auflösen, um korrekt weiterzulesen. Das ist Voraussetzung für die Zusage, dass MRF auch ohne externe Typdefinitionen verarbeitbar bleibt.

1. **Array-Literale sind eckig-klammer-abgegrenzt.** Ein Wert ist genau dann ein Array, wenn nach `=` ein `[` folgt (`items = [ … ]`); ein `(` leitet dagegen einen Inline-Record ein. Der Parser entscheidet also allein am öffnenden Token, ohne Typauflösung. Der `[]`-Marker am Feld (`items[]: …`) dokumentiert weiterhin den Listen-Typ, ist zur Abgrenzung aber nicht mehr erforderlich.
2. **Benannte vs. anonyme Typen sind nach `:` eindeutig.** Folgt ein `TypeIdentifier`, ist es ein benannter Typ (Klammern enthalten Attribute `key=value`); folgt `(`, ist es ein anonymer Typ (Klammern enthalten Feld-Definitionen `key: Type`). Ein optionales zweites Klammernpaar nach einem anonymen Feld-Block trägt dessen Attribute.
3. **Ein Bareword als Wert ist eine Record-Referenz.** `true`/`false` sind reserviert und werden als Boolean erkannt, sodass Referenzen nie mit ihnen kollidieren.
4. **Ein `:` am Wertanfang leitet einen typisierten Inline-Record ein** *(v1.1)*. `blocks = [ :TextH1( … ) ]` bindet das Element an den Typ `TextH1`, und ein Validator prüft es dagegen. Das kollidiert nicht mit Regel 2: Dort steht das `:` **nach einem Feldnamen**, hier **vor einem Wert**. Ein einziges Lookahead-Token entscheidet — keine Mehrdeutigkeit, kein Backtracking.

**Offen für eine spätere Version:** Ob `key=value`-Angaben am Typ eines Feldes neben Attributen (`required`, `minValue` …) auch **Default-Werte** ausdrücken dürfen, ist bewusst noch nicht festgelegt (Empfehlung: separates `default=`-Attribut, um Constraint und Wert zu trennen).

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
Element      ::= ScalarValue | RecordRef | InlineRecord | TypedInlineRecord ;
InlineRecord ::= "(" { FieldAssign } ")" ;
TypedInlineRecord ::= ":" TypeIdentifier "(" { FieldAssign } ")" ;   (* v1.1 *)
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

Das folgende Beispiel nutzt alle v1- und v1.1-Konstrukte und wird vom Referenz-Parser akzeptiert:

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

type CoreImage (
    id:   String( required=true )
    path: String( required=true )
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
    blocks = [                               // heterogene Liste (v1.1)
        :TextH1( id="b1" content="Überschrift" )
        :CoreImage( id="b2" path="/bild.jpg" )
        ( id="b3" style="frei" )             // anonymes Element, ungeprüft
    ]
)
```

Ein Referenz-Parser (rekursiver Abstieg, 1:1-Abbild der obigen EBNF) sowie eine Testsuite über alle vollständigen Beispiele dieses Dokuments liegen als `mrf_parser.py` / `test_mrf.py` bei. Die Testsuite enthält zusätzlich Eingaben, die **abgelehnt** werden müssen (etwa `:Foo` ohne Klammern). Der Parser prüft ausschließlich die **Syntax**; die Auswertung der Attribut-Constraints (`required`, `minValue`, `maxValue`, `maxLength`) ist Aufgabe eines nachgelagerten Validators.
