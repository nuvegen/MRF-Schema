#!/usr/bin/env python3
from mrf_parser import parse

CASES = {}

# 1. Main Car/Tire example. Original had two bugs: BMW' (quote mismatch) and
#    it otherwise relies on inline-attribute form + anonymous 'motor' type.
CASES["car_tire_main"] = r'''
using "https://w3-isp.net/mrf/types.mrf"

type Tire (
    brand: String()
    maxTemp: Int()
    minTemp: Int()
    snow: Int( minValue=0 maxValue=10 )
    rain: Int( minValue=0 maxValue=10 )
    dry: Int( minValue=0 maxValue=10 )
)

type Car (
    name: String( required=true )
    brand: String()
    tires: Tire()
    motor: ( hasGas: Boolean() hasElectric: Boolean() )
           ( required=true )
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
'''

# 2. Record reference by bareword (tires=winterTire)
CASES["record_reference"] = r'''
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
'''

# 3. Named / anonymous type mix
CASES["anonymous_and_typed"] = r'''
type Wheel (
    typed: String()
    anon: ( maxTemp: Int() minTemp: Int() )
)
'''

# 4. Array of DictionaryItem (bracket-delimited literal, marker on assignment)
CASES["array_dictionary"] = r'''
record (
    myList[]:DictionaryItem = [
        (key="A" value="Ananas")
        (key="B" value="Banana")
    ]
)
'''

# 5. Optional name/type on record: name-only, anonymous, type-only
CASES["record_name_variants"] = r'''
record audi:Car (
    brand="Audi"
)

record opel (
    thebrand="Opel"
)

record (
    brand="Renault"
)
'''

# 6. Comments (line + block)
CASES["comments"] = r'''
// Dies ist ein Kommentar
record config: Configuration(
    path = "./" // Kommentar in einer Zeile

    /* Kommentar ueber mehrere
    Zeilen */
)
'''

# 7. using variants
CASES["using_variants"] = r'''
using "./types.mrf"
using "file://home/alex/types.mrf"
using "https://w3-isp.net/types.mrf"
using "stdio"
'''

# 8. Comma-separated fields (test-harness style), canonicalised types
CASES["comma_separated"] = r'''
type Person( name: String(), age: Int(), active: Boolean() )

record jane: Person(
    name="Jane Doe",
    age=25,
    active=false
)
'''

# 9. Nested inline record value + array + ref together.
#    Array has NO field marker here -> tests that "[" alone drives array detection.
CASES["mixed_values"] = r'''
type Order (
    id: String( required=true )
    items[]: Item()
    customer: Customer()
)

record c1 ( name="Alex" )

record ( 
    id="X1"
    items = [ (sku="A" qty=2) (sku="B" qty=1) ]
    customer = c1
)
'''

# 9b. Array of scalars and array of references
CASES["scalar_and_ref_arrays"] = r'''
record red ( hex="#ff0000" )

record palette (
    tags   = [ "warm" "primary" ]
    colors = [ red red ]
    empty  = [ ]
)
'''

# 10. Escaped string in a value
CASES["escaped_string"] = r'''
record ( msg = "Escaped: \"Hello, world!\"" )
'''


def main():
    ok = 0
    for name, src in CASES.items():
        try:
            parse(src)
            print(f"[PASS] {name}")
            ok += 1
        except SyntaxError as e:
            print(f"[FAIL] {name}: {e}")
    print(f"\n{ok}/{len(CASES)} examples accepted by the reconciled grammar.")


if __name__ == "__main__":
    main()
