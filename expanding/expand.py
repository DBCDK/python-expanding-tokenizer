import re
import urllib
from typing import TypeVar
from xml.sax import saxutils
from io import StringIO

from expanding.math import MathTokenizer, MathType, MathValue, MathExpr, MathTree
from expanding.source import Reader, At
from expanding.variable import EnvironmentVariable

_str = TypeVar('_str', str, None)


class Expanding(object):
    DEFAULT_QUOTES = {
        'ms': lambda s, at: Expanding.to_milliseconds(s, at),
        's': lambda s, at: Expanding.to_seconds(s, at),
        'xml': lambda s, at: saxutils.escape(s),
        'attr': lambda s, at: saxutils.escape(s, {'"': '&quot;'}),
        'uri': lambda s, at: urllib.parse.quote_plus(s.encode('utf-8')),
        'sql': lambda s, at: s.replace("'", "''")
    }
    TO_MILLISECONDS = re.compile('^([1-9][0-9]*)(|h|ms?|s)$', re.S)
    TO_MILLISECONDS_SCALE = {'': 1, 'ms': 1, 's': 1000, 'm': 60000, 'h': 3600000, 'd': 86400000}
    TO_SECONDS = re.compile('^([1-9][0-9]*)(|h|m|s)$', re.S)
    TO_SECONDS_SCALE = {'': 1, 's': 1, 'm': 60, 'h': 3600, 'd': 86400}

    def __init__(self, reader, variable=EnvironmentVariable(), quotes=DEFAULT_QUOTES):
        self._reader = reader
        self._variable = variable
        self.quotes = quotes

    def add_quote(self, name, func) -> TypeVar('Expanding'):
        self.quotes[name] = func
        return self

    def expand(self, at, should_resolve=True) -> str:
        c = self._reader.get()
        if c is '{':
            return _ExpandVariable(at, self._reader, self, should_resolve).content()
        if c is '(':
            return _ExpandMath(at, self._reader, self, should_resolve).content()
        self._reader.unget()
        (name, value) = self.process_variable()
        if should_resolve:
            self.fail_variable(at, name, value)
        return value

    def process_variable(self) -> (_str, _str):
        name = self._variable.get_name(self._reader)
        value = None
        if name is not None:
            value = self._variable.lookup_variable(name)
        return name, value

    @staticmethod
    def fail_variable(at, name, value):
        if name is None:
            raise Exception("Cannot find variable name at: %s" % at)
        if value is None:
            raise Exception("Cannot resolve variable: %s at: %s" % (name, at))

    def process_until_closing_bracket(self, should_resolve) -> str:
        at = self._reader.at()
        content = StringIO()
        while True:
            pos = self._reader.at()
            c = self._reader.get()
            if c is '}':
                return content.getvalue()
            if c is None:
                raise Exception("Unexpected EOF in default value at %s" % at)
            if c is '$':
                c = self.expand(pos, should_resolve)
            elif c is '\\':
                c = self._reader.get_quoted()
            if c is not None:
                content.write(c)

    @staticmethod
    def to_milliseconds(string, location) -> str:
        """Convert a string to a number of milliseconds as string

        Parameters
        ----------
        string : text containing a number and optionalt a duration
                 this duration is d/h/m/s/ms
        location : Input object with the location of the source
        """
        match = Expanding.TO_MILLISECONDS.match(string)
        if match is None:
            raise Exception("%s is not a duration at: %s" % (string, location))
        ms_pr_unit = Expanding.TO_MILLISECONDS_SCALE[match.group(2)]
        return str(int(match.group(1)) * ms_pr_unit)

    @staticmethod
    def to_seconds(string, location) -> str:
        """Convert a string to a number of seconds as string

        Parameters
        ----------
        string : text containing a number and optionalt a duration
                 this duration is d/h/m/s
        location : Input object with the location of the source
        """
        match = Expanding.TO_SECONDS.match(string)
        if match is None:
            raise Exception("%s is not a duration at: %s" % (string, location))
        ms_pr_unit = Expanding.TO_SECONDS_SCALE[match.group(2)]
        return str(int(match.group(1)) * ms_pr_unit)


class _Expand(object):

    def content(self) -> str:
        raise NotImplemented()


class _ExpandVariable(_Expand):
    def __init__(self, at: At, reader: Reader, expanding: Expanding, should_resolve: bool) -> object:
        (name, value) = expanding.process_variable()
        at_after = reader.at()
        c = reader.get()
        quotes = []
        if c is ':':
            c = ','
            while c is ',':
                at_quote = reader.at()
                quote = StringIO()
                c = reader.get()
                while str.isalnum(c):
                    quote.write(c)
                    c = reader.get()
                quote = quote.getvalue()
                if not quote in expanding.quotes:
                    raise Exception("Unknown quote: '%s' at: %s" % (quote, at_quote))
                quotes.append(quote)

        if c is '|':
            default_value = expanding.process_until_closing_bracket(should_resolve and value is None)
        else:
            if c is None:
                raise Exception("Unexpected EOF in variable: %s at: %s" % (name, at))
            if c is not '}':
                raise Exception("Expected '}' in variable: %s at: %s got %s" % (name, at_after, c))
            if should_resolve:
                expanding.fail_variable(at, name, value)
        if should_resolve:
            if value is not None:
                for quote in quotes:
                    value = expanding.quotes[quote](value, at)
                self._content = value
            else:
                self._content = default_value
        else:
            self._content = ""

    def content(self) -> str:
        return self._content


class _ExpandMath(_Expand):

    def __init__(self, at: At, reader: Reader, expanding: Expanding, should_resolve: bool) -> object:
        self._tokenizer = MathTokenizer(at, reader, expanding, should_resolve)
        tree = self._process_to_closing()
        if should_resolve:
            self._content = str(tree.get_value())
        else:
            self._content = ""

    def content(self) -> str:
        return self._content

    def _process_to_closing(self) -> MathTree:
        operators = []
        values = []
        while True:
            neg = False
            token = self._tokenizer.token()
            while token.is_a(MathType.SUB):
                neg = not neg
                token = self._tokenizer.token()
            if token.is_a(MathType.LPAR):
                tree = self._process_to_closing()
            elif token.is_a(MathType.NUMBER):
                tree = MathValue(token.content())
            else:
                raise Exception("Unexpected token: %s at: %s" % (str(token.content()), token.at()))
            if neg:
                tree = MathExpr(MathType.SUB, MathValue(0), tree)
            values.append(tree)
            token = self._tokenizer.token()
            precedence = token.precedence()
            if precedence is None:
                raise Exception(
                    "Unexpected token: %s at: %s expected ')' or [operator]" % (str(token.content()), token.at()))
            while operators and operators[-1].precedence() <= precedence:
                right = values.pop()
                left = values.pop()
                operator = operators.pop()
                values.append(MathExpr(operator.token_type(), left, right))
            if token.is_a(MathType.RPAR):
                return values.pop()
            operators.append(token)
