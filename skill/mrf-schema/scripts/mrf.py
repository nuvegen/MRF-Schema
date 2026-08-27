#!/usr/bin/env python3
"""
mrf.py — Model-Record-Format (MRF) v1 / v1.1 for Python.

Use MRF the way you use ``json`` or ``yaml``:

    import mrf
    doc = mrf.loads(text)          # parse text  -> Document
    doc = mrf.load(open("f.mrf"))  # parse file  -> Document
    data = doc.data                # plain dict/list, ready for JSON/YAML
    text = mrf.dumps(obj)          # serialise dict/list/Document -> MRF text

Pure standard library. No third-party dependencies (PyYAML is used lazily and
only for the YAML sub-commands; everything else works without it).

Spec: https://nuvegen.github.io/MRF-Schema/record_model_definition_v1.html
The parser follows the v1 EBNF grammar exactly (recursive descent), plus the
additive v1.1 production for typed inline records (``:Type( … )`` in value
position). It checks *syntax*; ``validate()`` additionally checks the schema
constraints (required / minValue / maxValue / maxLength) that a downstream
validator owns, including every typed inline record at any depth.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

__all__ = [
    "loads", "load", "dumps", "dump",
    "Document", "TypeDef", "FieldDef", "NamedType", "AnonType",
    "Record", "RecordRef", "InlineRecord",
    "MRFError", "MRFSyntaxError", "MRFValidationError",
    "validate", "to_json", "from_json",
]

RESERVED = {"using", "type", "record", "true", "false"}
STD_TYPES = {"String", "Int", "Decimal", "Boolean", "Any", "DictionaryItem"}


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
class MRFError(Exception):
    """Base class for all MRF errors."""


class MRFSyntaxError(MRFError):
    def __init__(self, msg: str, line: int = 0, col: int = 0):
        self.line, self.col = line, col
        super().__init__(f"line {line}, col {col}: {msg}" if line else msg)


class MRFValidationError(MRFError):
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors) if errors else "validation failed")


# --------------------------------------------------------------------------- #
# Lexer
# --------------------------------------------------------------------------- #
@dataclass
class Tok:
    kind: str          # STRING NUMBER IDENT PUNCT EOF
    value: Any
    line: int
    col: int


_PUNCT = set("()[]:=")


def tokenize(src: str) -> List[Tok]:
    toks: List[Tok] = []
    i, n = 0, len(src)
    line, col = 1, 1

    def adv(k: int = 1):
        nonlocal i, line, col
        for _ in range(k):
            if i < n and src[i] == "\n":
                line += 1
                col = 1
            else:
                col += 1
            i += 1

    while i < n:
        c = src[i]
        # whitespace and commas are insignificant separators
        if c in " \t\r\n," or c == "\ufeff":
            adv()
            continue
        # comments
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            while i < n and src[i] != "\n":
                adv()
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            start_l, start_c = line, col
            adv(2)
            while i < n and not (src[i] == "*" and i + 1 < n and src[i + 1] == "/"):
                adv()
            if i >= n:
                raise MRFSyntaxError("unterminated block comment", start_l, start_c)
            adv(2)
            continue
        # string
        if c == '"':
            start_l, start_c = line, col
            adv()
            buf: List[str] = []
            while i < n and src[i] != '"':
                if src[i] == "\\":
                    adv()
                    if i >= n:
                        break
                    esc = src[i]
                    buf.append({"n": "\n", "t": "\t", "r": "\r",
                                '"': '"', "\\": "\\", "/": "/",
                                "b": "\b", "f": "\f"}.get(esc, esc))
                    adv()
                else:
                    buf.append(src[i])
                    adv()
            if i >= n:
                raise MRFSyntaxError("unterminated string", start_l, start_c)
            adv()  # closing quote
            toks.append(Tok("STRING", "".join(buf), start_l, start_c))
            continue
        # number
        if c == "-" or c.isdigit():
            start_l, start_c = line, col
            j = i
            if src[j] == "-":
                j += 1
            has_digit = False
            while j < n and src[j].isdigit():
                j += 1
                has_digit = True
            if j < n and src[j] == ".":
                j += 1
                while j < n and src[j].isdigit():
                    j += 1
                    has_digit = True
            if j < n and src[j] in "eE":
                k = j + 1
                if k < n and src[k] in "+-":
                    k += 1
                if k < n and src[k].isdigit():
                    j = k
                    while j < n and src[j].isdigit():
                        j += 1
            if not has_digit:
                # a lone '-' is not a valid token
                raise MRFSyntaxError(f"unexpected character {c!r}", line, col)
            raw = src[i:j]
            adv(j - i)
            val: Union[int, float] = int(raw) if raw.lstrip("-").isdigit() else float(raw)
            toks.append(Tok("NUMBER", val, start_l, start_c))
            continue
        # identifier / keyword
        if c.isalpha():
            start_l, start_c = line, col
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            word = src[i:j]
            adv(j - i)
            toks.append(Tok("IDENT", word, start_l, start_c))
            continue
        # punctuation
        if c in _PUNCT:
            toks.append(Tok("PUNCT", c, line, col))
            adv()
            continue
        raise MRFSyntaxError(f"unexpected character {c!r}", line, col)

    toks.append(Tok("EOF", None, line, col))
    return toks


# --------------------------------------------------------------------------- #
# Semantic model
# --------------------------------------------------------------------------- #
@dataclass
class NamedType:
    name: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnonType:
    fields: List["FieldDef"] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)


TypeExpr = Union[NamedType, AnonType]


@dataclass
class FieldDef:
    name: str
    type: TypeExpr
    is_array: bool = False


@dataclass
class TypeDef:
    name: str
    fields: List[FieldDef] = field(default_factory=list)

    def field_map(self) -> Dict[str, FieldDef]:
        return {f.name: f for f in self.fields}


@dataclass
class RecordRef:
    name: str


@dataclass
class InlineRecord:
    fields: "Dict[str, Any]" = field(default_factory=dict)
    type: Optional[str] = None      # v1.1: typed inline record  :Type( … )


Value = Union[str, int, float, bool, RecordRef, InlineRecord, list]


@dataclass
class Record:
    name: Optional[str]
    type: Optional[str]
    fields: Dict[str, Value] = field(default_factory=dict)


@dataclass
class Document:
    usings: List[str] = field(default_factory=list)
    types: Dict[str, TypeDef] = field(default_factory=dict)
    records: List[Record] = field(default_factory=list)

    # -- lookups ----------------------------------------------------------- #
    def get(self, name: str) -> Optional[Record]:
        for r in self.records:
            if r.name == name:
                return r
        return None

    @property
    def records_by_name(self) -> Dict[str, Record]:
        return {r.name: r for r in self.records if r.name}

    # -- plain-data view (JSON/YAML friendly) ------------------------------ #
    def to_data(self, *, resolve_refs: bool = True, include_meta: bool = False) -> Any:
        """Return a plain dict/list tree, ready for json.dumps / yaml.dump.

        - one record   -> its fields as a dict
        - many records -> a list of such dicts
        Record references are inlined (resolve_refs, with cycle guard);
        set include_meta=True to keep _name/_type keys.
        """
        by_name = self.records_by_name

        def conv(v: Any, seen: Tuple[str, ...]) -> Any:
            if isinstance(v, RecordRef):
                if resolve_refs and v.name in by_name and v.name not in seen:
                    return rec_data(by_name[v.name], seen + (v.name,))
                return {"$ref": v.name}
            if isinstance(v, InlineRecord):
                # v1.1: the type name is the discriminator -> payload, not meta
                out = {"_type": v.type} if v.type else {}
                out.update({k: conv(val, seen) for k, val in v.fields.items()})
                return out
            if isinstance(v, list):
                return [conv(e, seen) for e in v]
            return v

        def rec_data(r: Record, seen: Tuple[str, ...]) -> Dict[str, Any]:
            d: Dict[str, Any] = {}
            if include_meta:
                if r.name:
                    d["_name"] = r.name
                if r.type:
                    d["_type"] = r.type
            for k, val in r.fields.items():
                d[k] = conv(val, seen)
            return d

        datas = [rec_data(r, (r.name,) if r.name else ()) for r in self.records]
        if len(datas) == 1:
            return datas[0]
        return datas

    @property
    def data(self) -> Any:
        return self.to_data()


# --------------------------------------------------------------------------- #
# Parser (recursive descent, 1:1 with the v1 / v1.1 EBNF)
# --------------------------------------------------------------------------- #
class _Parser:
    def __init__(self, toks: List[Tok]):
        self.toks = toks
        self.p = 0

    # token helpers
    def peek(self) -> Tok:
        return self.toks[self.p]

    def next(self) -> Tok:
        t = self.toks[self.p]
        self.p += 1
        return t

    def at_punct(self, ch: str) -> bool:
        t = self.peek()
        return t.kind == "PUNCT" and t.value == ch

    def eat_punct(self, ch: str) -> Tok:
        t = self.peek()
        if t.kind == "PUNCT" and t.value == ch:
            return self.next()
        raise MRFSyntaxError(f"expected {ch!r}, got {self._desc(t)}", t.line, t.col)

    def _desc(self, t: Tok) -> str:
        if t.kind == "EOF":
            return "end of input"
        return f"{t.kind} {t.value!r}"

    def ident(self) -> str:
        t = self.peek()
        if t.kind != "IDENT":
            raise MRFSyntaxError(f"expected identifier, got {self._desc(t)}", t.line, t.col)
        self.next()
        return t.value

    # Program ::= { Using | TypeDef | RecordDef }
    def parse(self) -> Document:
        doc = Document()
        while self.peek().kind != "EOF":
            t = self.peek()
            if t.kind == "IDENT" and t.value == "using":
                self.next()
                s = self.peek()
                if s.kind != "STRING":
                    raise MRFSyntaxError("using expects a string literal", s.line, s.col)
                self.next()
                doc.usings.append(s.value)
            elif t.kind == "IDENT" and t.value == "type":
                td = self._type_def()
                doc.types[td.name] = td
            elif t.kind == "IDENT" and t.value == "record":
                doc.records.append(self._record_def())
            else:
                raise MRFSyntaxError(
                    f"expected 'using', 'type' or 'record', got {self._desc(t)}",
                    t.line, t.col)
        return doc

    # TypeDef ::= "type" TypeIdentifier "(" { FieldDef } ")"
    def _type_def(self) -> TypeDef:
        self.next()  # 'type'
        name = self.ident()
        self.eat_punct("(")
        fields: List[FieldDef] = []
        while not self.at_punct(")"):
            fields.append(self._field_def())
        self.eat_punct(")")
        return TypeDef(name, fields)

    # FieldDef ::= Identifier [ ArrayMarker ] ":" TypeExpr
    def _field_def(self) -> FieldDef:
        name = self.ident()
        is_arr = self._maybe_array_marker()
        self.eat_punct(":")
        texpr = self._type_expr()
        return FieldDef(name, texpr, is_arr)

    def _maybe_array_marker(self) -> bool:
        if self.at_punct("["):
            self.eat_punct("[")
            self.eat_punct("]")
            return True
        return False

    # TypeExpr ::= NamedType | AnonType   (rule 2: after ':' , '(' => anon)
    def _type_expr(self) -> TypeExpr:
        if self.at_punct("("):
            return self._anon_type()
        return self._named_type()

    # NamedType ::= TypeIdentifier "(" { Param } ")"
    def _named_type(self) -> NamedType:
        name = self.ident()
        self.eat_punct("(")
        params = self._params()
        self.eat_punct(")")
        return NamedType(name, params)

    # AnonType ::= "(" { FieldDef } ")" [ "(" { Param } ")" ]
    def _anon_type(self) -> AnonType:
        self.eat_punct("(")
        fields: List[FieldDef] = []
        while not self.at_punct(")"):
            fields.append(self._field_def())
        self.eat_punct(")")
        params: Dict[str, Any] = {}
        if self.at_punct("("):
            self.eat_punct("(")
            params = self._params()
            self.eat_punct(")")
        return AnonType(fields, params)

    # { Param }   Param ::= Identifier "=" ScalarValue
    def _params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        while not self.at_punct(")"):
            key = self.ident()
            self.eat_punct("=")
            params[key] = self._scalar()
        return params

    def _scalar(self) -> Any:
        t = self.peek()
        if t.kind == "STRING" or t.kind == "NUMBER":
            self.next()
            return t.value
        if t.kind == "IDENT" and t.value in ("true", "false"):
            self.next()
            return t.value == "true"
        raise MRFSyntaxError(f"expected a scalar value, got {self._desc(t)}", t.line, t.col)

    # RecordDef ::= "record" [ Identifier ] [ ":" TypeIdentifier ] "(" { FieldAssign } ")"
    def _record_def(self) -> Record:
        self.next()  # 'record'
        name: Optional[str] = None
        rtype: Optional[str] = None
        t = self.peek()
        if t.kind == "IDENT" and t.value not in RESERVED:
            name = self.ident()
        if self.at_punct(":"):
            self.eat_punct(":")
            rtype = self.ident()
        self.eat_punct("(")
        fields = self._field_assigns()
        self.eat_punct(")")
        return Record(name, rtype, fields)

    def _field_assigns(self) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}
        while not self.at_punct(")"):
            fname = self.ident()
            self._maybe_array_marker()          # ArrayMarker is documentation only
            if self.at_punct(":"):              # optional inline ':Type'
                self.eat_punct(":")
                self.ident()
            self.eat_punct("=")
            fields[fname] = self._value()
        return fields

    # Value ::= ArrayValue | SingleValue
    def _value(self) -> Value:
        if self.at_punct("["):
            return self._array()
        return self._element()

    def _array(self) -> list:
        self.eat_punct("[")
        out: list = []
        while not self.at_punct("]"):
            out.append(self._element())
        self.eat_punct("]")
        return out

    # Element ::= ScalarValue | RecordRef | InlineRecord | TypedInlineRecord
    def _element(self) -> Value:
        t = self.peek()
        if self.at_punct(":"):                      # v1.1 typed inline record
            self.eat_punct(":")
            rtype = self.ident()
            if not self.at_punct("("):
                bad = self.peek()
                raise MRFSyntaxError(
                    f"typed inline record ':{rtype}' expects '(', got {self._desc(bad)}",
                    bad.line, bad.col)
            return self._inline_record(rtype)
        if self.at_punct("("):
            return self._inline_record()
        if t.kind in ("STRING", "NUMBER"):
            self.next()
            return t.value
        if t.kind == "IDENT":
            self.next()
            if t.value in ("true", "false"):
                return t.value == "true"
            return RecordRef(t.value)
        raise MRFSyntaxError(f"expected a value, got {self._desc(t)}", t.line, t.col)

    def _inline_record(self, rtype: Optional[str] = None) -> InlineRecord:
        self.eat_punct("(")
        fields = self._field_assigns()
        self.eat_punct(")")
        return InlineRecord(fields, rtype)


# --------------------------------------------------------------------------- #
# Public parse API
# --------------------------------------------------------------------------- #
def loads(text: str) -> Document:
    """Parse MRF text into a Document (raises MRFSyntaxError on bad syntax)."""
    return _Parser(tokenize(text)).parse()


def load(fp) -> Document:
    """Parse MRF from a file-like object or path."""
    if hasattr(fp, "read"):
        return loads(fp.read())
    with open(fp, "r", encoding="utf-8") as fh:
        return loads(fh.read())


# --------------------------------------------------------------------------- #
# Serialiser
# --------------------------------------------------------------------------- #
def _fmt_scalar(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v) if isinstance(v, float) else str(v)
    if v is None:
        return '""'
    s = str(v)
    s = (s.replace("\\", "\\\\").replace('"', '\\"')
          .replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r"))
    return f'"{s}"'


def _dump_value(v: Any, indent: int) -> str:
    pad = "    " * indent
    if isinstance(v, RecordRef):
        return v.name
    if isinstance(v, InlineRecord):
        head = f":{v.type}" if v.type else ""
        return head + _dump_fields(v.fields, indent)
    if isinstance(v, dict):
        if "$ref" in v and len(v) == 1:
            return str(v["$ref"])
        d = dict(v)
        rtype = d.pop("_type", None)          # round-trip JSON -> MRF
        head = f":{rtype}" if rtype else ""
        return head + _dump_fields(d, indent)
    if isinstance(v, (list, tuple)):
        if not v:
            return "[ ]"
        parts = [_dump_value(e, indent + 1) for e in v]
        inner = "\n".join(f"{pad}    {p}" for p in parts)
        return f"[\n{inner}\n{pad}]"
    return _fmt_scalar(v)


def _dump_fields(fields: Dict[str, Any], indent: int) -> str:
    """Render a '( key=value ... )' block."""
    pad = "    " * indent
    lines = []
    for k, val in fields.items():
        if val is None:
            continue
        lines.append(f"{pad}    {k}={_dump_value(val, indent + 1)}")
    body = "\n".join(lines)
    return f"(\n{body}\n{pad})" if body else "( )"


def _dump_record(r: "Record | dict", indent: int = 0) -> str:
    if isinstance(r, Record):
        name, rtype, fields = r.name, r.type, r.fields
    else:
        d = dict(r)
        name = d.pop("_name", None)
        rtype = d.pop("_type", None)
        fields = d
    head = "record"
    if name:
        head += f" {name}"
    if rtype:
        head += f":{rtype}"
    return f"{head} {_dump_fields(fields, indent)}"


def dumps(obj: Any, *, name: Optional[str] = None, type: Optional[str] = None) -> str:
    """Serialise a Document / Record / dict / list into MRF text.

    A dict becomes one record; a list of dicts becomes several records.
    ``name`` / ``type`` set the record head for a single dict.
    """
    if isinstance(obj, Document):
        chunks = [f'using {_fmt_scalar(u)}' for u in obj.usings]
        chunks += [_dump_type(t) for t in obj.types.values()]
        chunks += [_dump_record(r) for r in obj.records]
        return "\n\n".join(chunks) + "\n"
    if isinstance(obj, Record):
        return _dump_record(obj) + "\n"
    if isinstance(obj, dict):
        d = dict(obj)
        if name and "_name" not in d:
            d["_name"] = name
        if type and "_type" not in d:
            d["_type"] = type
        return _dump_record(d) + "\n"
    if isinstance(obj, (list, tuple)):
        return "\n\n".join(_dump_record(dict(x)) for x in obj) + "\n"
    raise MRFError(f"cannot serialise object of type {type_name(obj)}")


def dump(obj: Any, fp, **kw) -> None:
    text = dumps(obj, **kw)
    if hasattr(fp, "write"):
        fp.write(text)
    else:
        with open(fp, "w", encoding="utf-8") as fh:
            fh.write(text)


def type_name(o: Any) -> str:
    return o.__class__.__name__


def _dump_type(td: TypeDef) -> str:
    lines = [f"type {td.name} ("]
    for f in td.fields:
        lines.append(f"    {_dump_field_def(f)}")
    lines.append(")")
    return "\n".join(lines)


def _dump_field_def(f: FieldDef) -> str:
    marker = "[]" if f.is_array else ""
    te = f.type
    if isinstance(te, NamedType):
        p = " ".join(f"{k}={_fmt_scalar(v)}" for k, v in te.params.items())
        return f"{f.name}{marker}: {te.name}({(' ' + p + ' ') if p else ''})"
    # AnonType
    inner = " ".join(_dump_field_def(sf) for sf in te.fields)
    attrs = ""
    if te.params:
        p = " ".join(f"{k}={_fmt_scalar(v)}" for k, v in te.params.items())
        attrs = f" ( {p} )"
    return f"{f.name}{marker}: ( {inner} ){attrs}"


# --------------------------------------------------------------------------- #
# Schema-constraint validation (the downstream validator's job)
# --------------------------------------------------------------------------- #
def _resolve_scalar_type(texpr: TypeExpr) -> Optional[str]:
    if isinstance(texpr, NamedType):
        return texpr.name
    return None


def validate(doc: Document, *, strict_unknown: bool = False) -> List[str]:
    """Check every typed record against its type's constraints.

    Returns a list of human-readable error strings (empty == valid).
    Unknown / imported types are skipped (spec: MRF stays valid without
    external defs) unless strict_unknown=True.
    """
    errors: List[str] = []
    types = doc.types

    def check_field(where: str, fdef: FieldDef, value: Any):
        te = fdef.type
        # array field
        if isinstance(value, list):
            if not fdef.is_array:
                pass  # value happens to be a list; allow (spec is lenient)
            for idx, el in enumerate(value):
                check_scalar_or_ref(f"{where}[{idx}]", te, el)
            return
        check_scalar_or_ref(where, te, value)

    def check_scalar_or_ref(where: str, te: TypeExpr, value: Any):
        if isinstance(value, RecordRef):
            return  # reference; deeper checking would need the target's type
        if isinstance(te, AnonType):
            if isinstance(value, InlineRecord):
                check_body(where, te.fields, value.fields)
            return
        tname = te.name  # NamedType
        req = te.params.get("required", False)
        if tname == "String":
            if not isinstance(value, str):
                errors.append(f"{where}: expected String, got {type_name(value)}")
            else:
                ml = te.params.get("maxLength")
                if isinstance(ml, (int, float)) and len(value) > ml:
                    errors.append(f"{where}: String longer than maxLength={ml}")
        elif tname in ("Int", "Decimal"):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"{where}: expected {tname}, got {type_name(value)}")
            else:
                if tname == "Int" and not float(value).is_integer():
                    errors.append(f"{where}: expected Int, got fractional {value}")
                mn, mx = te.params.get("minValue"), te.params.get("maxValue")
                if isinstance(mn, (int, float)) and value < mn:
                    errors.append(f"{where}: {value} < minValue={mn}")
                if isinstance(mx, (int, float)) and value > mx:
                    errors.append(f"{where}: {value} > maxValue={mx}")
        elif tname == "Boolean":
            if not isinstance(value, bool):
                errors.append(f"{where}: expected Boolean, got {type_name(value)}")
        elif tname == "Any":
            pass
        elif tname == "DictionaryItem":
            pass  # structural: key/value; leave to inline checks
        elif tname in types:
            if isinstance(value, InlineRecord):
                if value.type and value.type != tname:
                    errors.append(f"{where}: field declares {tname!r}, "
                                  f"value is typed {value.type!r}")
                elif value.type is None:
                    # typed values are checked by walk_typed below (no double report)
                    check_body(where, types[tname].fields, value.fields)
        else:
            if strict_unknown:
                errors.append(f"{where}: unknown type {tname!r}")

    def check_body(where: str, fdefs: List[FieldDef], values: Dict[str, Any]):
        fmap = {f.name: f for f in fdefs}
        for f in fdefs:
            req = False
            if isinstance(f.type, NamedType):
                req = bool(f.type.params.get("required", False))
            elif isinstance(f.type, AnonType):
                req = bool(f.type.params.get("required", False))
            if req and f.name not in values:
                errors.append(f"{where}.{f.name}: required field missing")
        for k, v in values.items():
            if k in fmap:
                check_field(f"{where}.{k}", fmap[k], v)

    def walk_typed(value: Any, where: str) -> None:
        """v1.1: check every typed inline record against its own type, at any depth."""
        if isinstance(value, InlineRecord):
            label = f"{where}:{value.type}" if value.type else where
            if value.type:
                if value.type in types:
                    check_body(label, types[value.type].fields, value.fields)
                elif strict_unknown:
                    errors.append(f"{where}: unknown type {value.type!r}")
            for k, v in value.fields.items():
                walk_typed(v, f"{label}.{k}")
        elif isinstance(value, list):
            for i, el in enumerate(value):
                walk_typed(el, f"{where}[{i}]")

    for r in doc.records:
        label = r.name or "<anonymous>"
        if r.type and r.type in types:
            check_body(label, types[r.type].fields, r.fields)
        elif r.type and strict_unknown:
            errors.append(f"{label}: unknown type {r.type!r}")
        for k, v in r.fields.items():
            walk_typed(v, f"{label}.{k}")
    return errors


# --------------------------------------------------------------------------- #
# JSON / YAML bridges
# --------------------------------------------------------------------------- #
def to_json(doc: Document, *, indent: int = 2, resolve_refs: bool = True,
            include_meta: bool = False) -> str:
    return json.dumps(doc.to_data(resolve_refs=resolve_refs, include_meta=include_meta),
                      indent=indent, ensure_ascii=False)


def from_json(data: Any, *, name: Optional[str] = None, type: Optional[str] = None) -> str:
    """JSON-native data (dict/list) -> MRF text."""
    return dumps(data, name=name, type=type)


def _require_yaml():
    try:
        import yaml  # noqa
        return yaml
    except ImportError:  # pragma: no cover
        raise MRFError("PyYAML is required for YAML conversion (pip install pyyaml)")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
_USAGE = """\
mrf.py — Model-Record-Format v1 tool

Usage:
  mrf.py parse     FILE.mrf            Parse and print the data as JSON
  mrf.py validate  FILE.mrf [--strict] Syntax check + schema-constraint check
  mrf.py fmt       FILE.mrf [-o OUT]   Re-emit in canonical MRF formatting
  mrf.py to-json   FILE.mrf [-o OUT] [--keep-refs] [--meta]
  mrf.py to-yaml   FILE.mrf [-o OUT] [--keep-refs] [--meta]
  mrf.py from-json FILE.json [-o OUT] [--name N] [--type T]
  mrf.py from-yaml FILE.yaml [-o OUT] [--name N] [--type T]

Reads FILE ('-' = stdin). Without -o, writes to stdout.
"""


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _write(text: str, out: Optional[str]):
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")


def _opt(args: List[str], flag: str) -> bool:
    if flag in args:
        args.remove(flag)
        return True
    return False


def _val(args: List[str], flag: str) -> Optional[str]:
    if flag in args:
        k = args.index(flag)
        v = args[k + 1]
        del args[k:k + 2]
        return v
    return None


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        sys.stdout.write(_USAGE)
        return 0
    cmd, rest = args[0], args[1:]
    out = _val(rest, "-o")
    try:
        if cmd == "parse":
            doc = loads(_read(rest[0]))
            _write(json.dumps(doc.to_data(), indent=2, ensure_ascii=False), out)
        elif cmd == "validate":
            strict = _opt(rest, "--strict")
            doc = loads(_read(rest[0]))                 # syntax
            errs = validate(doc, strict_unknown=strict)  # constraints
            if errs:
                sys.stderr.write("INVALID:\n  " + "\n  ".join(errs) + "\n")
                return 1
            sys.stdout.write("OK: syntax valid, all constraints satisfied\n")
        elif cmd == "fmt":
            doc = loads(_read(rest[0]))
            _write(dumps(doc), out)
        elif cmd == "to-json":
            keep = _opt(rest, "--keep-refs")
            meta = _opt(rest, "--meta")
            doc = loads(_read(rest[0]))
            _write(to_json(doc, resolve_refs=not keep, include_meta=meta), out)
        elif cmd == "to-yaml":
            keep = _opt(rest, "--keep-refs")
            meta = _opt(rest, "--meta")
            yaml = _require_yaml()
            doc = loads(_read(rest[0]))
            data = doc.to_data(resolve_refs=not keep, include_meta=meta)
            _write(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), out)
        elif cmd == "from-json":
            nm, tp = _val(rest, "--name"), _val(rest, "--type")
            data = json.loads(_read(rest[0]))
            _write(from_json(data, name=nm, type=tp), out)
        elif cmd == "from-yaml":
            nm, tp = _val(rest, "--name"), _val(rest, "--type")
            yaml = _require_yaml()
            data = yaml.safe_load(_read(rest[0]))
            _write(dumps(data, name=nm, type=tp), out)
        else:
            sys.stderr.write(f"unknown command {cmd!r}\n\n{_USAGE}")
            return 2
    except FileNotFoundError as e:
        sys.stderr.write(f"file not found: {e.filename}\n")
        return 2
    except MRFError as e:
        sys.stderr.write(f"{type_name(e)}: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
