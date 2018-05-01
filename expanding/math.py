import re
from io import StringIO
from enum import Enum
from typing import TypeVar

from expanding.source import Reader


class MathType(Enum):
    LPAR = 'LPAR'
    RPAR = 'RPAR'
    ADD = 'ADD'
    SUB = 'SUB'
    MUL = 'MUL'
    DIV = 'DIV'
    MOD = 'MOD'
    MIN = 'MIN'
    MAX = 'MAX'
    NUMBER = 'NUMBER'
    OPERATOR = 'OPERATOR'


class MathToken(object):
    """
    Math Token

    Representation of a value or operator
    """
    _PRECEDENCE = {MathType.RPAR: 999,
                   MathType.MUL: 1, MathType.DIV: 1, MathType.MOD: 1,
                   MathType.ADD: 2, MathType.SUB: 2,
                   MathType.MIN: 3, MathType.MAX: 3}
    _OPERATORS = {MathType.MIN, MathType.MAX,
                  MathType.MUL, MathType.DIV, MathType.MOD,
                  MathType.ADD, MathType.SUB}

    def __init__(self, at, token_type, content):
        """
        Build a token

        :param at: location of token start
        :param token_type: type (operator or value)
        :param content: content (only needed for value type)
        """
        self._at = at
        self._token_type = token_type
        self._content = content

    def at(self) -> str:
        return self._at

    def content(self):
        return self._content

    def is_a(self, wanted_type) -> bool:
        """
        Type matching

        Is the toke of the given type. Also knows the synthetic type OPERATOR

        :param wanted_type: the type to test against
        :return: if token if of wanted type
        """
        if wanted_type is MathType.OPERATOR:
            return self._token_type in self._OPERATORS
        return self._token_type is wanted_type

    def precedence(self) -> TypeVar('_int', int, None):
        """
        Get the precedence of the operators or closing parenthesis
        :return: precedence as a number, None if unknown precedence
        """
        if self._token_type in MathToken._PRECEDENCE:
            return MathToken._PRECEDENCE[self._token_type]
        else:
            return None

    def token_type(self) -> TypeVar('MathToken'):
        return self._token_type

    def __str__(self):
        return "{%s,%s,%s}" % (self._token_type, self._at, self._content)


class MathTokenizer(object):
    """
    Math tokenizer

    tokenizes input into know math tokens expanding variables when needed
    """
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

    def __init__(self, at, reader: Reader, expansion: TypeVar('Expansion'), should_resolve: bool):
        """
        Construct a tokenizer for input source consuming

        :param at: where the math expression starts
        :param reader: source of input
        :param expansion: variable expansion class
        :param should_resolve: are variables required to resolve
        """
        self._at = at
        self._reader = reader
        self._expansion = expansion
        self._should_resolve = should_resolve

    def token(self):
        (c, at) = self._get()
        if c in self._SINGLE_CHAR_TOKENS:
            return MathToken(at, self._SINGLE_CHAR_TOKENS[c], c)
        if str.isalnum(c):
            content = StringIO()
            content.write(c)
            while True:
                (c, _) = self._get()
                if str.isalnum(c):
                    content.write(c)
                else:
                    self._reader.unget()
                    if self._should_resolve:
                        value = self._as_int(content.getvalue())
                        if value is None:
                            raise Exception("%s is not a number at: %s" % (content.getvalue(), at))
                    else:
                        value = None
                    return MathToken(at, MathType.NUMBER, value)
        if c is '$':
            content = self._expansion.expand(at, self._should_resolve)
            if self._should_resolve:
                neg = False
                while content and content[0] is '-':
                    neg = not neg
                    content = content[1:]
                value = self._as_int(content)
                if neg:
                    value = -value
                if value is None:
                    raise Exception("Expansion at: %s does not resolve to a number" % at)
            else:
                value = None
            return MathToken(at, MathType.NUMBER, value)
        raise Exception("Unexpected character: %s in expression at: %s" % (c, at))

    def _get(self) -> str:
        """
        Read a character from source (skipping whitespace)

        :return: character
        :raises: Exception of EOF is encountered
        """
        while True:
            at = self._reader.at()
            c = self._reader.get()
            if c is None:
                raise Exception("Unexpected EOF in expression at: %s" % self._at)
            if str.isspace(c):
                continue
            return c, at

    def _as_int(self, content) -> int:
        """
        converts value int integer

        knows about negative numbers, octal, decimal or hexadecimal numbers

        :param content: text containing number
        :return: the integer value
        """
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
    """
    Interface type for mathematical expressions
    """

    def get_value(self) -> int:
        """
        The value this tree node represents

        :return: integer value
        """
        raise NotImplemented()


class MathValue(MathTree):
    """
    MathTree object, that resolves a value
    """

    def __init__(self, value):
        self._value = value

    def get_value(self) -> int:
        return self._value

    def __str__(self):
        return "{%d}" % self._value


class MathExpr(MathTree):
    """
    MathTree object, that computes a value (binary operator)
    """

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
        """
        Construct a binary operator

        :param op: operator
        :param left: left node
        :param right: right node
        """
        self._op = op
        self._left = left
        self._right = right

    def get_value(self):
        """
        Compute value

        :return: computed value
        """
        left = self._left.get_value()
        right = self._right.get_value()
        return self.OPERATIONS[self._op](left, right)

    def __str__(self):
        return "{%s,%s,%s}" % (self._left, self._op, self._right)
