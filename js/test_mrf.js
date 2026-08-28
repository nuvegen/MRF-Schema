/* Test suite for mrf.js — run: node test_mrf.js */
"use strict";
var assert = require("assert");
var mrf = require("./mrf.js");

var passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log("  ok   " + name); }
  catch (e) { failed++; console.log("  FAIL " + name + "\n       " + (e.message || e)); }
}

// --------------------------------------------------------------------- //
var SAMPLE = [
  'using "./types.mrf"',
  '',
  'type Person (',
  '    name:   String( required=true maxLength=60 )',
  '    age:    Int( minValue=0 maxValue=150 )',
  '    active: Boolean()',
  ')',
  '',
  'type Order (',
  '    id:        String( required=true )',
  '    items[]:   DictionaryItem()',
  '    customer:  Person()',
  '    shipping:  ( express: Boolean() note: String() ) ( required=true )',
  ')',
  '',
  'record jane:Person ( name="Jane Doe" age=25 active=false )',
  '',
  'record order1:Order (',
  '    id="X1"',
  '    items = [ (key="A" value="Ananas") (key="B" value="Banana") ]',
  '    customer = jane',
  '    shipping = ( express=true note="leave at door" )',
  ')'
].join("\n");

test("parse: usings / types / records collected", function () {
  var doc = mrf.parse(SAMPLE);
  assert.deepStrictEqual(doc.usings, ["./types.mrf"]);
  assert.deepStrictEqual(Object.keys(doc.types), ["Person", "Order"]);
  assert.strictEqual(doc.records.length, 2);
  assert.strictEqual(doc.get("jane").type, "Person");
});

test("a) typesJSON: named types with attributes", function () {
  var t = mrf.parse(SAMPLE).typesJSON();
  assert.deepStrictEqual(t.Person.fields.name, {
    kind: "named", type: "String",
    attributes: { required: true, maxLength: 60 },
    required: true, name: "name", isList: false
  });
  assert.deepStrictEqual(t.Person.fields.age.attributes, { minValue: 0, maxValue: 150 });
  assert.strictEqual(t.Person.fields.age.required, false);
});

test("a) typesJSON: array marker and anonymous type", function () {
  var t = mrf.parse(SAMPLE).typesJSON();
  assert.strictEqual(t.Order.fields.items.isList, true);
  assert.strictEqual(t.Order.fields.items.type, "DictionaryItem");
  var sh = t.Order.fields.shipping;
  assert.strictEqual(sh.kind, "anonymous");
  assert.strictEqual(sh.required, true);
  assert.deepStrictEqual(Object.keys(sh.fields), ["express", "note"]);
  assert.strictEqual(sh.fields.express.type, "Boolean");
});

test("b) recordsJSON: name/type/data, refs resolved by default", function () {
  var recs = mrf.parse(SAMPLE).recordsJSON();
  assert.strictEqual(recs.length, 2);
  assert.deepStrictEqual(recs[0], {
    name: "jane", type: "Person",
    data: { name: "Jane Doe", age: 25, active: false }
  });
  assert.deepStrictEqual(recs[1].data.customer, { name: "Jane Doe", age: 25, active: false });
  assert.deepStrictEqual(recs[1].data.items, [
    { key: "A", value: "Ananas" }, { key: "B", value: "Banana" }
  ]);
  assert.deepStrictEqual(recs[1].data.shipping, { express: true, note: "leave at door" });
});

test("b) recordsJSON: resolveRefs=false keeps $ref", function () {
  var recs = mrf.parse(SAMPLE).recordsJSON({ resolveRefs: false });
  assert.deepStrictEqual(recs[1].data.customer, { $ref: "jane" });
});

test("toData: many records -> array, one record -> object", function () {
  assert.ok(Array.isArray(mrf.parse(SAMPLE).toData()));
  var one = mrf.parse('record solo ( a=1 )').toData();
  assert.deepStrictEqual(one, { a: 1 });
});

test("toData: includeMeta adds _name/_type", function () {
  var d = mrf.parse('record jane:Person ( age=1 )').toData({ includeMeta: true });
  assert.deepStrictEqual(d, { _name: "jane", _type: "Person", age: 1 });
});

test("v1.1: typed inline records keep _type as content", function () {
  var doc = mrf.parse([
    'type TextH1 ( id: String( required=true ) content: String( required=true maxLength=20 ) )',
    'record page (',
    '  blocks[]:Any = [ :TextH1( id="b1" content="Headline" ) ( id="b3" style="free" ) ]',
    '  header = :TextH1( id="h" content="Title" )',
    ')'
  ].join("\n"));
  var d = doc.toData();
  assert.deepStrictEqual(d.blocks[0], { _type: "TextH1", id: "b1", content: "Headline" });
  assert.deepStrictEqual(d.blocks[1], { id: "b3", style: "free" });   // anonymous: no _type
  assert.strictEqual(d.header._type, "TextH1");
  assert.deepStrictEqual(mrf.validate(doc), []);
});

test("record name/type both optional", function () {
  var doc = mrf.parse('record audi:Car(a=1) record opel(a=2) record :Car(a=3) record (a=4)');
  assert.deepStrictEqual(doc.records.map(function (r) { return [r.name, r.type]; }),
    [["audi", "Car"], ["opel", null], [null, "Car"], [null, null]]);
});

test("scalars: numbers, exponents, negatives, booleans, escapes", function () {
  var d = mrf.parse('record ( a=-3.14 b=1.5e3 c=0 d=true e=false f="li\\tne\\n\\"q\\"" )').toData();
  assert.deepStrictEqual(d, { a: -3.14, b: 1500, c: 0, d: true, e: false, f: 'li\tne\n"q"' });
});

test("arrays: scalars, refs, empty", function () {
  var d = mrf.parse('record red(v="r") record p( tags=["warm" "primary"] colors=[red] empty=[] )')
    .toData()[1];
  assert.deepStrictEqual(d.tags, ["warm", "primary"]);
  assert.deepStrictEqual(d.colors, [{ v: "r" }]);
  assert.deepStrictEqual(d.empty, []);
});

test("comments and comma separators are insignificant", function () {
  var d = mrf.parse('/* head */ record ( a=1, b=2 ) // tail').toData();
  assert.deepStrictEqual(d, { a: 1, b: 2 });
});

test("reference cycles terminate", function () {
  var d = mrf.parse('record a( peer=b ) record b( peer=a )').toData();
  assert.deepStrictEqual(d[0].peer.peer, { $ref: "a" });
});

test("validate: catches required / maxLength / min / max / type", function () {
  var doc = mrf.parse([
    'type P ( name: String( required=true maxLength=3 ) age: Int( minValue=0 maxValue=10 ) )',
    'record a:P ( name="toolong" age=99 )',
    'record b:P ( age=-1 )',
    'record c:P ( name=5 age=1 )'
  ].join("\n"));
  var errs = mrf.validate(doc);
  assert.ok(errs.some(function (e) { return /maxLength=3/.test(e); }), "maxLength");
  assert.ok(errs.some(function (e) { return /> maxValue=10/.test(e); }), "maxValue");
  assert.ok(errs.some(function (e) { return /required field missing/.test(e); }), "required");
  assert.ok(errs.some(function (e) { return /< minValue=0/.test(e); }), "minValue");
  assert.ok(errs.some(function (e) { return /expected String, got Int/.test(e); }), "type");
});

test("validate: typed inline record mismatching its field type", function () {
  var errs = mrf.validate(mrf.parse([
    'type A ( x: String() ) type B ( x: String() )',
    'type Holder ( slot: A() )',
    'record h:Holder ( slot = :B( x="v" ) )'
  ].join("\n")));
  assert.ok(errs.some(function (e) { return /declares 'A', value is typed 'B'/.test(e); }), errs.join(";"));
});

test("validate: strictUnknown surfaces unresolved types", function () {
  var doc = mrf.parse('record x:Imported ( a=1 )');
  assert.deepStrictEqual(mrf.validate(doc), []);
  assert.ok(mrf.validate(doc, { strictUnknown: true }).length === 1);
});

test("syntax errors carry line and column", function () {
  try {
    mrf.parse('record ( a= )');
    throw new Error("should have thrown");
  } catch (e) {
    assert.strictEqual(e.name, "MRFSyntaxError");
    assert.strictEqual(e.line, 1);
    assert.ok(e.col > 0);
  }
});

test("syntax error: typed inline record without parens", function () {
  assert.throws(function () { mrf.parse('record ( a = :Foo )'); }, /expects '\('/);
});

test("toJSON envelope carries everything", function () {
  var j = mrf.parse(SAMPLE).toJSON();
  assert.deepStrictEqual(Object.keys(j), ["mrf", "usings", "types", "records", "data"]);
  assert.strictEqual(j.mrf, "1.1");
  JSON.parse(JSON.stringify(j));   // must be pure JSON
});

// --- conformance with the reference corpus (test_mrf.py) --------------- //
test("corpus: car/tire example with anonymous motor type", function () {
  var doc = mrf.parse([
    'using "https://w3-isp.net/mrf/types.mrf"',
    'type Tire ( brand: String() maxTemp: Int() minTemp: Int() snow: Int( minValue=0 maxValue=10 ) )',
    'type Car (',
    '    name: String( required=true )',
    '    tires: Tire()',
    '    motor: ( hasGas: Boolean() hasElectric: Boolean() )',
    '           ( required=true )',
    ')',
    'record audiA4Winter:Car ( name="A4" tires=( maxTemp=10 minTemp=-20 snow=9 ) )'
  ].join("\n"));
  assert.deepStrictEqual(doc.toData(), {
    name: "A4", tires: { maxTemp: 10, minTemp: -20, snow: 9 }
  });
  assert.ok(mrf.validate(doc).some(function (e) { return /motor: required field missing/.test(e); }));
});

test("corpus: deeply nested typed inline records", function () {
  var d = mrf.parse(
    'record page ( body = :Box( items = [ :Box( items = [ :TextH1( id="deep" ) ] ) ] ) )'
  ).toData();
  assert.strictEqual(d.body.items[0].items[0]._type, "TextH1");
});

[
  ['record ( x = :Foo "no paren" )', "typed inline record without parens"],
  ['record ( x = :( id="a" ) )', "typed inline record without type name"],
  ['record ( xs = [ : ] )', "lone colon in array"]
].forEach(function (c) {
  test("corpus: rejects " + c[1], function () {
    assert.throws(function () { mrf.parse(c[0]); }, mrf.MRFSyntaxError);
  });
});

// --------------------------------------------------------------------- //
console.log("\n" + passed + " passed, " + failed + " failed");
process.exit(failed ? 1 : 0);
