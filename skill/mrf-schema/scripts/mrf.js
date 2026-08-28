/*!
 * mrf.js — Model-Record-Format (MRF) v1 / v1.1  ->  JSON / JavaScript
 *
 * A dependency-free MRF reader for JavaScript. Direction: MRF -> JS only.
 * Runs in Node (require / import) and in the browser (<script>, global `MRF`).
 *
 *   const mrf = require("./mrf.js");
 *   const doc = mrf.parse(text);
 *
 *   doc.typesJSON()      // a) the schema  (type ...)   as plain JSON
 *   doc.recordsJSON()    // b) the data    (record ...) as plain JSON
 *   doc.toData()         // data only, json-module style (1 record -> object)
 *   mrf.validate(doc)    // [] === valid
 *
 * The parser is a 1:1 image of the v1/v1.1 EBNF and mirrors the reference
 * implementation (scripts/mrf.py) construct for construct.
 */
(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;                    // Node / CommonJS / bundlers
  } else {
    root.MRF = api;                          // browser global
  }
  // Node CLI: `node mrf.js <cmd> file.mrf`
  if (typeof module === "object" && module.exports && require.main === module) {
    api._cli(process.argv.slice(2));
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var VERSION = "1.1";
  var RESERVED = { using: 1, type: 1, record: 1, true: 1, false: 1 };
  var PUNCT = "()[]:=";

  // ------------------------------------------------------------------ //
  // Errors
  // ------------------------------------------------------------------ //
  function MRFSyntaxError(msg, line, col) {
    var e = Error.call(this, "MRF syntax error at " + (line || 0) + ":" + (col || 0) + ": " + msg);
    this.name = "MRFSyntaxError";
    this.message = e.message;
    this.line = line || 0;
    this.col = col || 0;
    if (Error.captureStackTrace) Error.captureStackTrace(this, MRFSyntaxError);
  }
  MRFSyntaxError.prototype = Object.create(Error.prototype);
  MRFSyntaxError.prototype.constructor = MRFSyntaxError;

  // ------------------------------------------------------------------ //
  // Lexer
  // ------------------------------------------------------------------ //
  var RE_LETTER = /[\p{L}]/u;                 // Letter (spec: A-Za-z; unicode-tolerant)
  var RE_WORD = /[\p{L}\p{N}_]/u;             // Letter | Digit | "_"
  var ESCAPES = { n: "\n", t: "\t", r: "\r", '"': '"', "\\": "\\", "/": "/", b: "\b", f: "\f" };

  function isDigit(c) { return c >= "0" && c <= "9"; }

  /** Tokenize MRF source. Returns [{kind,value,line,col}] ending with EOF. */
  function tokenize(src) {
    var toks = [], i = 0, n = src.length, line = 1, col = 1;

    function adv(k) {
      k = k === undefined ? 1 : k;
      for (var x = 0; x < k; x++) {
        if (i < n && src[i] === "\n") { line++; col = 1; } else { col++; }
        i++;
      }
    }

    while (i < n) {
      var c = src[i];

      // separators: whitespace and ',' are interchangeable and insignificant
      if (c === " " || c === "\t" || c === "\r" || c === "\n" || c === "," || c === "\uFEFF") {
        adv(); continue;
      }
      // comments
      if (c === "/" && src[i + 1] === "/") {
        while (i < n && src[i] !== "\n") adv();
        continue;
      }
      if (c === "/" && src[i + 1] === "*") {
        var cl = line, cc = col;
        adv(2);
        while (i < n && !(src[i] === "*" && src[i + 1] === "/")) adv();
        if (i >= n) throw new MRFSyntaxError("unterminated block comment", cl, cc);
        adv(2);
        continue;
      }
      // string literal
      if (c === '"') {
        var sl = line, sc = col, buf = "";
        adv();
        while (i < n && src[i] !== '"') {
          if (src[i] === "\\") {
            adv();
            if (i >= n) break;
            var esc = src[i];
            buf += Object.prototype.hasOwnProperty.call(ESCAPES, esc) ? ESCAPES[esc] : esc;
            adv();
          } else {
            buf += src[i];
            adv();
          }
        }
        if (i >= n) throw new MRFSyntaxError("unterminated string", sl, sc);
        adv();                                   // closing quote
        toks.push({ kind: "STRING", value: buf, line: sl, col: sc });
        continue;
      }
      // number literal
      if (c === "-" || isDigit(c)) {
        var nl = line, nc = col, j = i, hasDigit = false;
        if (src[j] === "-") j++;
        while (j < n && isDigit(src[j])) { j++; hasDigit = true; }
        if (j < n && src[j] === ".") {
          j++;
          while (j < n && isDigit(src[j])) { j++; hasDigit = true; }
        }
        if (j < n && (src[j] === "e" || src[j] === "E")) {
          var k = j + 1;
          if (k < n && (src[k] === "+" || src[k] === "-")) k++;
          if (k < n && isDigit(src[k])) {
            j = k;
            while (j < n && isDigit(src[j])) j++;
          }
        }
        if (!hasDigit) throw new MRFSyntaxError("unexpected character '" + c + "'", line, col);
        var raw = src.slice(i, j);
        adv(j - i);
        toks.push({ kind: "NUMBER", value: Number(raw), line: nl, col: nc });
        continue;
      }
      // identifier / keyword
      if (RE_LETTER.test(c)) {
        var il = line, ic = col, p = i;
        while (p < n && RE_WORD.test(src[p])) p++;
        var word = src.slice(i, p);
        adv(p - i);
        toks.push({ kind: "IDENT", value: word, line: il, col: ic });
        continue;
      }
      // punctuation
      if (PUNCT.indexOf(c) !== -1) {
        toks.push({ kind: "PUNCT", value: c, line: line, col: col });
        adv();
        continue;
      }
      throw new MRFSyntaxError("unexpected character '" + c + "'", line, col);
    }
    toks.push({ kind: "EOF", value: null, line: line, col: col });
    return toks;
  }

  // ------------------------------------------------------------------ //
  // Semantic model
  // ------------------------------------------------------------------ //
  function NamedType(name, params) { this.kind = "named"; this.name = name; this.params = params || {}; }
  function AnonType(fields, params) { this.kind = "anonymous"; this.fields = fields || []; this.params = params || {}; }
  function FieldDef(name, type, isArray) { this.name = name; this.type = type; this.isArray = !!isArray; }
  function TypeDef(name, fields) { this.name = name; this.fields = fields || []; }
  function RecordRef(name) { this.name = name; }
  function InlineRecord(fields, type) { this.fields = fields || {}; this.type = type || null; }
  function Record(name, type, fields) { this.name = name || null; this.type = type || null; this.fields = fields || {}; }

  TypeDef.prototype.fieldMap = function () {
    var m = Object.create(null);
    this.fields.forEach(function (f) { m[f.name] = f; });
    return m;
  };

  function isInline(v) { return v instanceof InlineRecord; }
  function isRef(v) { return v instanceof RecordRef; }

  // ------------------------------------------------------------------ //
  // Document
  // ------------------------------------------------------------------ //
  function Document(usings, types, records) {
    this.usings = usings || [];
    this.types = types || {};          // { TypeName: TypeDef }
    this.records = records || [];      // [Record]
  }

  Document.prototype.get = function (name) {
    for (var i = 0; i < this.records.length; i++) {
      if (this.records[i].name === name) return this.records[i];
    }
    return null;
  };

  Document.prototype.recordsByName = function () {
    var m = Object.create(null);
    this.records.forEach(function (r) { if (r.name) m[r.name] = r; });
    return m;
  };

  // -- a) TYPES as JSON ------------------------------------------------ //
  function typeExprJSON(te) {
    if (te instanceof AnonType) {
      return {
        kind: "anonymous",
        attributes: shallowCopy(te.params),
        required: !!te.params.required,
        fields: fieldsJSON(te.fields)
      };
    }
    return {
      kind: "named",
      type: te.name,
      attributes: shallowCopy(te.params),
      required: !!te.params.required
    };
  }

  function fieldsJSON(fieldDefs) {
    var out = {};
    fieldDefs.forEach(function (f) {
      var j = { name: f.name, isList: f.isArray };
      var t = typeExprJSON(f.type);
      Object.keys(t).forEach(function (k) { j[k] = t[k]; });
      out[f.name] = j;
    });
    return out;
  }

  /**
   * The schema as plain JSON:
   *   { Person: { name:"Person",
   *               fields: { age: { name, kind:"named", type:"Int", isList:false,
   *                                required:false, attributes:{minValue:0,maxValue:150} } } } }
   * Anonymous field types carry `kind:"anonymous"` and their own nested `fields`.
   */
  Document.prototype.typesJSON = function () {
    var out = {}, types = this.types;
    Object.keys(types).forEach(function (name) {
      out[name] = { name: name, fields: fieldsJSON(types[name].fields) };
    });
    return out;
  };

  // -- b) RECORDS as JSON ---------------------------------------------- //
  /**
   * Plain data tree, json-module style (mirrors the Python reference):
   *   one record  -> its fields as an object
   *   many records-> an array of such objects
   * opts: { resolveRefs = true, includeMeta = false }
   */
  Document.prototype.toData = function (opts) {
    opts = opts || {};
    var resolveRefs = opts.resolveRefs !== false;
    var includeMeta = !!opts.includeMeta;
    var byName = this.recordsByName();

    function conv(v, seen) {
      if (isRef(v)) {
        if (resolveRefs && byName[v.name] && seen.indexOf(v.name) === -1) {
          return recData(byName[v.name], seen.concat([v.name]));
        }
        return { $ref: v.name };
      }
      if (isInline(v)) {
        // v1.1: the type name is the discriminator -> content, always emitted
        var o = v.type ? { _type: v.type } : {};
        Object.keys(v.fields).forEach(function (k) { o[k] = conv(v.fields[k], seen); });
        return o;
      }
      if (Array.isArray(v)) return v.map(function (e) { return conv(e, seen); });
      return v;
    }

    function recData(r, seen) {
      var d = {};
      if (includeMeta) {
        if (r.name) d._name = r.name;
        if (r.type) d._type = r.type;
      }
      Object.keys(r.fields).forEach(function (k) { d[k] = conv(r.fields[k], seen); });
      return d;
    }

    var datas = this.records.map(function (r) { return recData(r, r.name ? [r.name] : []); });
    return datas.length === 1 ? datas[0] : datas;
  };

  /**
   * Records as an explicit, always-uniform array — usually the friendlier shape
   * for JavaScript because name and type stay separate from the payload:
   *   [ { name:"jane", type:"Person", data:{ name:"Jane Doe", age:25 } }, ... ]
   * opts: { resolveRefs = true }
   */
  Document.prototype.recordsJSON = function (opts) {
    opts = opts || {};
    var resolveRefs = opts.resolveRefs !== false;
    var self = this;
    var byName = this.recordsByName();

    function conv(v, seen) {
      if (isRef(v)) {
        if (resolveRefs && byName[v.name] && seen.indexOf(v.name) === -1) {
          return body(byName[v.name], seen.concat([v.name]));
        }
        return { $ref: v.name };
      }
      if (isInline(v)) {
        var o = v.type ? { _type: v.type } : {};
        Object.keys(v.fields).forEach(function (k) { o[k] = conv(v.fields[k], seen); });
        return o;
      }
      if (Array.isArray(v)) return v.map(function (e) { return conv(e, seen); });
      return v;
    }
    function body(r, seen) {
      var d = {};
      Object.keys(r.fields).forEach(function (k) { d[k] = conv(r.fields[k], seen); });
      return d;
    }
    return self.records.map(function (r) {
      return { name: r.name, type: r.type, data: body(r, r.name ? [r.name] : []) };
    });
  };

  /** Everything at once: { mrf, usings, types, records, data }. */
  Document.prototype.toJSON = function (opts) {
    opts = opts || {};
    return {
      mrf: VERSION,
      usings: this.usings.slice(),
      types: this.typesJSON(),
      records: this.recordsJSON(opts),
      data: this.toData(opts)
    };
  };

  // ------------------------------------------------------------------ //
  // Parser (recursive descent, 1:1 with the v1 / v1.1 EBNF)
  // ------------------------------------------------------------------ //
  function Parser(toks) { this.toks = toks; this.p = 0; }

  Parser.prototype.peek = function () { return this.toks[this.p]; };
  Parser.prototype.next = function () { return this.toks[this.p++]; };
  Parser.prototype.atPunct = function (ch) {
    var t = this.peek();
    return t.kind === "PUNCT" && t.value === ch;
  };
  Parser.prototype.desc = function (t) {
    return t.kind === "EOF" ? "end of input" : t.kind + " " + JSON.stringify(t.value);
  };
  Parser.prototype.eatPunct = function (ch) {
    var t = this.peek();
    if (t.kind === "PUNCT" && t.value === ch) return this.next();
    throw new MRFSyntaxError("expected '" + ch + "', got " + this.desc(t), t.line, t.col);
  };
  Parser.prototype.ident = function () {
    var t = this.peek();
    if (t.kind !== "IDENT") {
      throw new MRFSyntaxError("expected identifier, got " + this.desc(t), t.line, t.col);
    }
    this.next();
    return t.value;
  };

  // Program ::= { Using | TypeDef | RecordDef }
  Parser.prototype.parse = function () {
    var doc = new Document();
    while (this.peek().kind !== "EOF") {
      var t = this.peek();
      if (t.kind === "IDENT" && t.value === "using") {
        this.next();
        var s = this.peek();
        if (s.kind !== "STRING") throw new MRFSyntaxError("using expects a string literal", s.line, s.col);
        this.next();
        doc.usings.push(s.value);
      } else if (t.kind === "IDENT" && t.value === "type") {
        var td = this.typeDef();
        doc.types[td.name] = td;
      } else if (t.kind === "IDENT" && t.value === "record") {
        doc.records.push(this.recordDef());
      } else {
        throw new MRFSyntaxError(
          "expected 'using', 'type' or 'record', got " + this.desc(t), t.line, t.col);
      }
    }
    return doc;
  };

  // TypeDef ::= "type" TypeIdentifier "(" { FieldDef } ")"
  Parser.prototype.typeDef = function () {
    this.next();                                   // 'type'
    var name = this.ident();
    this.eatPunct("(");
    var fields = [];
    while (!this.atPunct(")")) fields.push(this.fieldDef());
    this.eatPunct(")");
    return new TypeDef(name, fields);
  };

  // FieldDef ::= Identifier [ ArrayMarker ] ":" TypeExpr
  Parser.prototype.fieldDef = function () {
    var name = this.ident();
    var isArr = this.maybeArrayMarker();
    this.eatPunct(":");
    return new FieldDef(name, this.typeExpr(), isArr);
  };

  Parser.prototype.maybeArrayMarker = function () {
    if (this.atPunct("[")) { this.eatPunct("["); this.eatPunct("]"); return true; }
    return false;
  };

  // TypeExpr ::= NamedType | AnonType     (rule 2: '(' after ':' => anonymous)
  Parser.prototype.typeExpr = function () {
    return this.atPunct("(") ? this.anonType() : this.namedType();
  };

  // NamedType ::= TypeIdentifier "(" { Param } ")"
  Parser.prototype.namedType = function () {
    var name = this.ident();
    this.eatPunct("(");
    var params = this.params();
    this.eatPunct(")");
    return new NamedType(name, params);
  };

  // AnonType ::= "(" { FieldDef } ")" [ "(" { Param } ")" ]
  Parser.prototype.anonType = function () {
    this.eatPunct("(");
    var fields = [];
    while (!this.atPunct(")")) fields.push(this.fieldDef());
    this.eatPunct(")");
    var params = {};
    if (this.atPunct("(")) {
      this.eatPunct("(");
      params = this.params();
      this.eatPunct(")");
    }
    return new AnonType(fields, params);
  };

  // { Param }   Param ::= Identifier "=" ScalarValue
  Parser.prototype.params = function () {
    var params = {};
    while (!this.atPunct(")")) {
      var key = this.ident();
      this.eatPunct("=");
      params[key] = this.scalar();
    }
    return params;
  };

  Parser.prototype.scalar = function () {
    var t = this.peek();
    if (t.kind === "STRING" || t.kind === "NUMBER") { this.next(); return t.value; }
    if (t.kind === "IDENT" && (t.value === "true" || t.value === "false")) {
      this.next();
      return t.value === "true";
    }
    throw new MRFSyntaxError("expected a scalar value, got " + this.desc(t), t.line, t.col);
  };

  // RecordDef ::= "record" [ Identifier ] [ ":" TypeIdentifier ] "(" { FieldAssign } ")"
  Parser.prototype.recordDef = function () {
    this.next();                                   // 'record'
    var name = null, rtype = null;
    var t = this.peek();
    if (t.kind === "IDENT" && !RESERVED[t.value]) name = this.ident();
    if (this.atPunct(":")) { this.eatPunct(":"); rtype = this.ident(); }
    this.eatPunct("(");
    var fields = this.fieldAssigns();
    this.eatPunct(")");
    return new Record(name, rtype, fields);
  };

  // FieldAssign ::= Identifier [ ArrayMarker ] [ ":" TypeIdentifier ] "=" Value
  Parser.prototype.fieldAssigns = function () {
    var fields = {};
    while (!this.atPunct(")")) {
      var fname = this.ident();
      this.maybeArrayMarker();                     // ArrayMarker is documentation only
      if (this.atPunct(":")) { this.eatPunct(":"); this.ident(); }   // optional ':Type'
      this.eatPunct("=");
      fields[fname] = this.value();
    }
    return fields;
  };

  // Value ::= ArrayValue | SingleValue   (rule 1: '[' after '=' => array)
  Parser.prototype.value = function () {
    return this.atPunct("[") ? this.array() : this.element();
  };

  Parser.prototype.array = function () {
    this.eatPunct("[");
    var out = [];
    while (!this.atPunct("]")) out.push(this.element());
    this.eatPunct("]");
    return out;
  };

  // Element ::= ScalarValue | RecordRef | InlineRecord | TypedInlineRecord
  Parser.prototype.element = function () {
    var t = this.peek();
    if (this.atPunct(":")) {                       // v1.1 typed inline record (rule 4)
      this.eatPunct(":");
      var rtype = this.ident();
      if (!this.atPunct("(")) {
        var bad = this.peek();
        throw new MRFSyntaxError(
          "typed inline record ':" + rtype + "' expects '(', got " + this.desc(bad),
          bad.line, bad.col);
      }
      return this.inlineRecord(rtype);
    }
    if (this.atPunct("(")) return this.inlineRecord(null);
    if (t.kind === "STRING" || t.kind === "NUMBER") { this.next(); return t.value; }
    if (t.kind === "IDENT") {
      this.next();
      if (t.value === "true" || t.value === "false") return t.value === "true";
      return new RecordRef(t.value);               // rule 3: bare word = reference
    }
    throw new MRFSyntaxError("expected a value, got " + this.desc(t), t.line, t.col);
  };

  Parser.prototype.inlineRecord = function (rtype) {
    this.eatPunct("(");
    var fields = this.fieldAssigns();
    this.eatPunct(")");
    return new InlineRecord(fields, rtype);
  };

  // ------------------------------------------------------------------ //
  // Public parse API
  // ------------------------------------------------------------------ //
  /** Parse MRF text -> Document. Throws MRFSyntaxError. */
  function parse(text) { return new Parser(tokenize(String(text))).parse(); }

  /** Parse MRF text -> plain JSON envelope { mrf, usings, types, records, data }. */
  function toJSON(text, opts) { return parse(text).toJSON(opts); }

  /** Parse MRF text -> only the schema, as JSON. */
  function typesOf(text) { return parse(text).typesJSON(); }

  /** Parse MRF text -> only the records, as JSON. */
  function recordsOf(text, opts) { return parse(text).recordsJSON(opts); }

  /** Node only: read and parse a file. */
  function parseFile(path, encoding) {
    var fs = require("fs");
    return parse(fs.readFileSync(path, encoding || "utf8"));
  }

  // ------------------------------------------------------------------ //
  // Schema-constraint validation
  // ------------------------------------------------------------------ //
  function typeNameOf(v) {
    if (v === null) return "null";
    if (Array.isArray(v)) return "list";
    if (isRef(v)) return "reference";
    if (isInline(v)) return "record";
    if (typeof v === "boolean") return "Boolean";
    if (typeof v === "number") return Number.isInteger(v) ? "Int" : "Decimal";
    if (typeof v === "string") return "String";
    return typeof v;
  }
  function isNum(x) { return typeof x === "number" && !isNaN(x); }
  function shallowCopy(o) {
    var out = {};
    Object.keys(o || {}).forEach(function (k) { out[k] = o[k]; });
    return out;
  }

  /**
   * Check every typed record against its type's constraints
   * (required / minValue / maxValue / maxLength / basic type agreement,
   *  plus every v1.1 typed inline record at any depth).
   * Returns an array of human-readable messages; empty === valid.
   * opts: { strictUnknown = false }
   */
  function validate(doc, opts) {
    opts = opts || {};
    var strictUnknown = !!opts.strictUnknown;
    var errors = [];
    var types = doc.types;

    function checkField(where, fdef, value) {
      if (Array.isArray(value)) {
        value.forEach(function (el, idx) { checkScalarOrRef(where + "[" + idx + "]", fdef.type, el); });
        return;
      }
      checkScalarOrRef(where, fdef.type, value);
    }

    function checkScalarOrRef(where, te, value) {
      if (isRef(value)) return;                    // target's type unknown here
      if (te instanceof AnonType) {
        if (isInline(value)) checkBody(where, te.fields, value.fields);
        return;
      }
      var tname = te.name, p = te.params || {};
      if (tname === "String") {
        if (typeof value !== "string") {
          errors.push(where + ": expected String, got " + typeNameOf(value));
        } else if (isNum(p.maxLength) && value.length > p.maxLength) {
          errors.push(where + ": String longer than maxLength=" + p.maxLength);
        }
      } else if (tname === "Int" || tname === "Decimal") {
        if (typeof value !== "number" || isNaN(value)) {
          errors.push(where + ": expected " + tname + ", got " + typeNameOf(value));
        } else {
          if (tname === "Int" && !Number.isInteger(value)) {
            errors.push(where + ": expected Int, got fractional " + value);
          }
          if (isNum(p.minValue) && value < p.minValue) {
            errors.push(where + ": " + value + " < minValue=" + p.minValue);
          }
          if (isNum(p.maxValue) && value > p.maxValue) {
            errors.push(where + ": " + value + " > maxValue=" + p.maxValue);
          }
        }
      } else if (tname === "Boolean") {
        if (typeof value !== "boolean") {
          errors.push(where + ": expected Boolean, got " + typeNameOf(value));
        }
      } else if (tname === "Any" || tname === "DictionaryItem") {
        /* Any: unchecked. DictionaryItem: structural, left to inline checks. */
      } else if (Object.prototype.hasOwnProperty.call(types, tname)) {
        if (isInline(value)) {
          if (value.type && value.type !== tname) {
            errors.push(where + ": field declares '" + tname + "', value is typed '" + value.type + "'");
          } else if (value.type === null) {
            checkBody(where, types[tname].fields, value.fields);
          }
          // typed values are checked by walkTyped below (no double report)
        }
      } else if (strictUnknown) {
        errors.push(where + ": unknown type '" + tname + "'");
      }
    }

    function checkBody(where, fdefs, values) {
      var fmap = Object.create(null);
      fdefs.forEach(function (f) { fmap[f.name] = f; });
      fdefs.forEach(function (f) {
        if (f.type && f.type.params && f.type.params.required &&
            !Object.prototype.hasOwnProperty.call(values, f.name)) {
          errors.push(where + "." + f.name + ": required field missing");
        }
      });
      Object.keys(values).forEach(function (k) {
        if (fmap[k]) checkField(where + "." + k, fmap[k], values[k]);
      });
    }

    // v1.1: check every typed inline record against its own type, at any depth
    function walkTyped(value, where) {
      if (isInline(value)) {
        var label = value.type ? where + ":" + value.type : where;
        if (value.type) {
          if (Object.prototype.hasOwnProperty.call(types, value.type)) {
            checkBody(label, types[value.type].fields, value.fields);
          } else if (strictUnknown) {
            errors.push(where + ": unknown type '" + value.type + "'");
          }
        }
        Object.keys(value.fields).forEach(function (k) {
          walkTyped(value.fields[k], label + "." + k);
        });
      } else if (Array.isArray(value)) {
        value.forEach(function (el, i) { walkTyped(el, where + "[" + i + "]"); });
      }
    }

    doc.records.forEach(function (r) {
      var label = r.name || "<anonymous>";
      if (r.type && Object.prototype.hasOwnProperty.call(types, r.type)) {
        checkBody(label, types[r.type].fields, r.fields);
      } else if (r.type && strictUnknown) {
        errors.push(label + ": unknown type '" + r.type + "'");
      }
      Object.keys(r.fields).forEach(function (k) { walkTyped(r.fields[k], label + "." + k); });
    });

    return errors;
  }

  // ------------------------------------------------------------------ //
  // CLI (Node)
  // ------------------------------------------------------------------ //
  var USAGE = [
    "mrf.js — MRF v1/v1.1 -> JSON (read-only)",
    "",
    "usage: node mrf.js <command> <file.mrf|-> [options]",
    "",
    "commands:",
    "  parse     <file>   full envelope { mrf, usings, types, records, data }",
    "  types     <file>   only the schema, as JSON",
    "  records   <file>   only the records: [{ name, type, data }]",
    "  to-json   <file>   data only, json-module style (1 record -> object)",
    "  validate  <file>   constraint check; exit code 1 if invalid",
    "",
    "options:",
    "  -o <out>      write to a file instead of stdout",
    "  --keep-refs   keep record references as {\"$ref\":\"name\"} (default: resolve)",
    "  --meta        to-json: keep _name / _type of records",
    "  --strict      validate: report unknown / unresolved types",
    "  --indent <n>  JSON indentation (default 2)"
  ].join("\n");

  function _cli(argv) {
    var fs = require("fs");
    var cmd = argv[0];
    if (!cmd || cmd === "-h" || cmd === "--help") { console.log(USAGE); return 0; }

    var flags = { keepRefs: false, meta: false, strict: false, indent: 2, out: null };
    var positional = [];
    for (var i = 1; i < argv.length; i++) {
      var a = argv[i];
      if (a === "--keep-refs") flags.keepRefs = true;
      else if (a === "--meta") flags.meta = true;
      else if (a === "--strict") flags.strict = true;
      else if (a === "-o") flags.out = argv[++i];
      else if (a === "--indent") flags.indent = parseInt(argv[++i], 10);
      else positional.push(a);
    }
    var file = positional[0];
    if (!file) { console.error("error: missing input file\n\n" + USAGE); process.exitCode = 2; return 2; }

    var text = file === "-" ? fs.readFileSync(0, "utf8") : fs.readFileSync(file, "utf8");
    var doc;
    try {
      doc = parse(text);
    } catch (e) {
      console.error(String(e.message || e));
      process.exitCode = 1;
      return 1;
    }

    var opts = { resolveRefs: !flags.keepRefs, includeMeta: flags.meta };
    var out;
    switch (cmd) {
      case "parse": out = doc.toJSON(opts); break;
      case "types": out = doc.typesJSON(); break;
      case "records": out = doc.recordsJSON(opts); break;
      case "to-json": out = doc.toData(opts); break;
      case "validate": {
        var errs = validate(doc, { strictUnknown: flags.strict });
        if (errs.length === 0) { console.log("OK — " + file + " is valid"); return 0; }
        console.error(file + ": " + errs.length + " problem(s)");
        errs.forEach(function (e) { console.error("  - " + e); });
        process.exitCode = 1;
        return 1;
      }
      default:
        console.error("error: unknown command '" + cmd + "'\n\n" + USAGE);
        process.exitCode = 2;
        return 2;
    }
    var json = JSON.stringify(out, null, flags.indent);
    if (flags.out) fs.writeFileSync(flags.out, json + "\n", "utf8");
    else console.log(json);
    return 0;
  }

  // ------------------------------------------------------------------ //
  return {
    VERSION: VERSION,
    parse: parse,
    parseFile: parseFile,
    tokenize: tokenize,
    toJSON: toJSON,
    typesOf: typesOf,
    recordsOf: recordsOf,
    validate: validate,
    Document: Document,
    Record: Record,
    RecordRef: RecordRef,
    InlineRecord: InlineRecord,
    TypeDef: TypeDef,
    NamedType: NamedType,
    AnonType: AnonType,
    FieldDef: FieldDef,
    MRFSyntaxError: MRFSyntaxError,
    _cli: _cli
  };
});
