import re
from io import StringIO
from enum import Enum


MathType = Enum('MathType', [(x, x) for x in [
    'LPAR', 'RPAR', 'ADD', 'SUB', 'MUL', 'DIV', 'MOD', 'MIN', 'MAX', 'NUMBER', 'OPERATOR'
]], type=str)


class MathToken(object):
    _PRECEDENCE = {MathType.RPAR: 999,
                   MathType.MUL: 1, MathType.DIV: 1, MathType.MOD: 1,
                   MathType.ADD: 2, MathType.SUB: 2,
                   MathType.MIN: 3, MathType.MAX: 3}
    _OPERATORS = {MathType.MIN, MathType.MAX,
                  MathType.MUL, MathType.DIV, MathType.MOD,
                  MathType.ADD, MathType.SUB}

    def __init__(self, at, token_type, content):
        self._at = at
        self._token_type = token_type
        self._content = content

    def at(self) -> str:
        return self._at

    def content(self):
        return self._content

    def is_a(self, wanted_type) -> bool:
        if wanted_type is MathType.OPERATOR:
            return self._token_type in self._OPERATORS
        return self._token_type is wanted_type

    def precedence(self) -> int:
        if self._token_type in MathToken._PRECEDENCE:
            return MathToken._PRECEDENCE[self._token_type]
        else:
            return None

    def token_type(self):
        return self._token_type

    def __str__(self):
        return "{%s,%s,%s}" % (self._token_type, self._at, self._content)


class MathTokenizer(object):
    _SINGLE_CHAR_TOKENS = {
        '(': MathType.LPAR,
        ')': MathType.RPAR,
        '+': MathType.ADD,
        '-': MathType.SUB,
        '*': MathType.MUL,
        '/': MathType.DIV,
        '%': MathType.MOD,
        '<': MathType.MIN,
        '>': MathType.MAX
    }

    _IS_NUMBER = re.compile('^(?:(?:[-+]?)(0[xX][0-9a-fA-F]+)|([1-9][0-9]*)|(0[0-7]*))$', re.S | re.U)

    def __init__(self, at, reader, expanding, should_resolve):
        self._at = at
        self._reader = reader
        self._expanding = expanding
        self._should_resolve = should_resolve

    def token(self):
        (c, at) = self.get()
        if c in self._SINGLE_CHAR_TOKENS:
            return MathToken(at, self._SINGLE_CHAR_TOKENS[c], c)
        if str.isalnum(c):
            content = StringIO()
            content.write(c)
            while True:
                (c, _) = self.get()
                if str.isalnum(c):
                    content.write(c)
                else:
                    self._reader.unget()
                    if self._should_resolve:
                        value = self.as_int(content.getvalue())
                        if value is None:
                            raise Exception("%s is not a number at: %s" % (content.getvalue(), at))
                    else:
                        value = None
                    return MathToken(at, MathType.NUMBER, value)
        if c is '$':
            content = self._expanding.expand(at, self._should_resolve)
            if self._should_resolve:
                neg = False
                while content and content[0] is '-':
                    neg = not neg
                    content = content[1:]
                value = self.as_int(content)
                if neg:
                    value = -value
                if value is None:
                    raise Exception("Expansion at: %s does not resolve to a number" % at)
            else:
                value = None
            return MathToken(at, MathType.NUMBER, value)
        raise Exception("Unexpected character: %s in expression at: %s" % (c, at))

    def get(self):
        while True:
            at = self._reader.at()
            c = self._reader.get()
            if c is None:
                raise Exception("Unexpected EOF in expression at: %s" % self._at)
            if str.isspace(c):
                continue
            return c, at

    def as_int(self, content):
        match = self._IS_NUMBER.match(content)
        if match is None:
            return None
        if match.group(1) is not None:
            return int(content, 16)
        if match.group(2) is not None:
            return int(content, 10)
        if match.group(3) is not None:
            return int(content, 8)


class MathTree(object):

    def get_value(self) -> int:
        raise NotImplemented()


class MathValue(MathTree):

    def __init__(self, value):
        self._value = value

    def get_value(self) -> int:
        return self._value

    def __str__(self):
        return "{%d}" % self._value


class MathExpr(MathTree):
    OPERATIONS = {
        MathType.ADD: lambda l, r: l + r,
        MathType.SUB: lambda l, r: l - r,
        MathType.MUL: lambda l, r: l * r,
        MathType.DIV: lambda l, r: int(l / r),
        MathType.MOD: lambda l, r: l % r,
        MathType.MIN: lambda l, r: min(l, r),
        MathType.MAX: lambda l, r: max(l, r)
    }

    def __init__(self, op, left, right):
        self._op = op
        self._left = left
        self._right = right

    def get_value(self):
        left = self._left.get_value()
        right = self._right.get_value()
        return self.OPERATIONS[self._op](left, right)

    def __str__(self):
        return "{%s,%s,%s}" % (self._left, self._op, self._right)