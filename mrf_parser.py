#!/usr/bin/env python3
"""
Reference parser for the reconciled Model-Record-Format (MRF) v1 grammar.
Purpose: validate that the corrected EBNF accepts every example in the spec,
including the ones that broke the original grammar (anonymous types, arrays,
record references, the attribute-in-first-parens form).

Not production code: no semantic/type checking, only structural (syntactic)
acceptance. If .parse_program() returns without raising, the input conforms
to the grammar.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

TOKEN_SPEC = [
    ("WS",       r"[ \t\r\n]+"),
    ("COMMENT_L", r"//[^\n]*"),
    ("COMMENT_B", r"/\*.*?\*/"),
    ("COMMA",    r","),                      # optional separator -> ignored
    ("STRING",   r'"(?:\\.|[^"\\])*"'),
    ("NUMBER",   r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"),
    ("LBRACK",   r"\["),
    ("RBRACK",   r"\]"),
    ("LPAREN",   r"\("),
    ("RPAREN",   r"\)"),
    ("COLON",    r":"),
    ("EQ",       r"="),
    ("IDENT",    r"[A-Za-z][A-Za-z0-9_]*"),
]

KEYWORDS = {"using", "type", "record"}
BOOLS = {"true", "false"}

MASTER = re.compile("|".join(f"(?P<{n}>{p})" for n, p in TOKEN_SPEC), re.DOTALL)


@dataclass
class Tok:
    kind: str
    val: str
    pos: int


def lex(src: str):
    toks, i = [], 0
    while i < len(src):
        m = MASTER.match(src, i)
        if not m:
            raise SyntaxError(f"Unexpected char {src[i]!r} at {i}")
        i = m.end()
        kind = m.lastgroup
        val = m.group()
        if kind in ("WS", "COMMENT_L", "COMMENT_B", "COMMA"):
            continue
        if kind == "IDENT":
            if val in KEYWORDS:
                kind = val.upper()          # USING / TYPE / RECORD
            elif val in BOOLS:
                kind = "BOOL"
        toks.append(Tok(kind, val, m.start()))
    toks.append(Tok("EOF", "", len(src)))
    return toks


# ---------------------------------------------------------------------------
# Parser  (recursive descent, matches the reconciled EBNF)
# ---------------------------------------------------------------------------

class Parser:
    def __init__(self, src: str):
        self.toks = lex(src)
        self.i = 0

    # -- helpers ------------------------------------------------------------
    @property
    def cur(self) -> Tok:
        return self.toks[self.i]

    def at(self, *kinds) -> bool:
        return self.cur.kind in kinds

    def eat(self, kind) -> Tok:
        if self.cur.kind != kind:
            raise SyntaxError(
                f"Expected {kind}, got {self.cur.kind} {self.cur.val!r} at {self.cur.pos}"
            )
        t = self.cur
        self.i += 1
        return t

    # -- Program ::= { Using | TypeDef | RecordDef } -----------------------
    def parse_program(self):
        out = []
        while not self.at("EOF"):
            if self.at("USING"):
                out.append(self.using())
            elif self.at("TYPE"):
                out.append(self.typedef())
            elif self.at("RECORD"):
                out.append(self.recorddef())
            else:
                raise SyntaxError(
                    f"Expected using/type/record, got {self.cur.kind} "
                    f"{self.cur.val!r} at {self.cur.pos}"
                )
        return out

    # -- Using ::= "using" String ------------------------------------------
    def using(self):
        self.eat("USING")
        s = self.eat("STRING").val
        return ("using", s)

    # -- TypeDef ::= "type" TypeId "(" { FieldDef } ")" --------------------
    def typedef(self):
        self.eat("TYPE")
        name = self.eat("IDENT").val
        self.eat("LPAREN")
        fields = []
        while not self.at("RPAREN"):
            fields.append(self.fielddef())
        self.eat("RPAREN")
        return ("type", name, fields)

    # -- FieldDef ::= Id ArrayMarker? ":" TypeExpr -------------------------
    def fielddef(self):
        name = self.eat("IDENT").val
        arr = self.array_marker()
        self.eat("COLON")
        te = self.type_expr()
        return ("field", name, arr, te)

    def array_marker(self) -> bool:
        if self.at("LBRACK"):
            self.eat("LBRACK")
            self.eat("RBRACK")
            return True
        return False

    # -- TypeExpr ::= NamedType | AnonType ---------------------------------
    #    NamedType ::= TypeId "(" { Param } ")"
    #    AnonType  ::= "(" { FieldDef } ")" [ "(" { Param } ")" ]
    def type_expr(self):
        if self.at("LPAREN"):                       # anonymous type
            self.eat("LPAREN")
            fields = []
            while not self.at("RPAREN"):
                fields.append(self.fielddef())
            self.eat("RPAREN")
            attrs = []
            if self.at("LPAREN"):                   # optional attribute parens
                self.eat("LPAREN")
                while not self.at("RPAREN"):
                    attrs.append(self.param())
                self.eat("RPAREN")
            return ("anon_type", fields, attrs)
        else:                                       # named type
            tname = self.eat("IDENT").val
            self.eat("LPAREN")
            params = []
            while not self.at("RPAREN"):
                params.append(self.param())
            self.eat("RPAREN")
            return ("named_type", tname, params)

    # -- Param ::= Id "=" Scalar -------------------------------------------
    def param(self):
        key = self.eat("IDENT").val
        self.eat("EQ")
        val = self.scalar()
        return ("param", key, val)

    def scalar(self):
        if self.at("STRING"):
            return ("string", self.eat("STRING").val)
        if self.at("NUMBER"):
            return ("number", self.eat("NUMBER").val)
        if self.at("BOOL"):
            return ("bool", self.eat("BOOL").val)
        raise SyntaxError(
            f"Expected scalar, got {self.cur.kind} {self.cur.val!r} at {self.cur.pos}"
        )

    # -- RecordDef ::= "record" Id? (":" TypeId)? "(" { FieldAssign } ")" --
    def recorddef(self):
        self.eat("RECORD")
        name = None
        if self.at("IDENT"):
            name = self.eat("IDENT").val
        typ = None
        if self.at("COLON"):
            self.eat("COLON")
            typ = self.eat("IDENT").val
        self.eat("LPAREN")
        assigns = []
        while not self.at("RPAREN"):
            assigns.append(self.fieldassign())
        self.eat("RPAREN")
        return ("record", name, typ, assigns)

    # -- FieldAssign ::= Id ArrayMarker? (":" TypeId)? "=" Value -----------
    def fieldassign(self):
        name = self.eat("IDENT").val
        arr = self.array_marker()       # optional; documents list type, not needed for parsing
        typ = None
        if self.at("COLON"):
            self.eat("COLON")
            typ = self.eat("IDENT").val
        self.eat("EQ")
        val = self.value()
        return ("assign", name, arr, typ, val)

    # -- Value  (array literals are bracket-delimited -> self-disambiguating) --
    #    ArrayValue ::= "[" { Element } "]"
    #    SingleValue::= Element
    def value(self):
        if self.at("LBRACK"):                       # array literal [ ... ]
            self.eat("LBRACK")
            elems = []
            while not self.at("RBRACK"):
                elems.append(self.element())
            self.eat("RBRACK")
            return ("array", elems)
        return self.element()

    def element(self):
        if self.at("LPAREN"):                       # inline record ( ... )
            self.eat("LPAREN")
            assigns = []
            while not self.at("RPAREN"):
                assigns.append(self.fieldassign())
            self.eat("RPAREN")
            return ("inline_record", assigns)
        if self.at("STRING", "NUMBER", "BOOL"):
            return self.scalar()
        if self.at("IDENT"):                        # bareword -> record ref
            return ("record_ref", self.eat("IDENT").val)
        raise SyntaxError(
            f"Expected value, got {self.cur.kind} {self.cur.val!r} at {self.cur.pos}"
        )


def parse(src: str):
    return Parser(src).parse_program()
