import re
import urllib
from typing import TypeVar
from xml.sax import saxutils
from io import StringIO

from expanding.math import MathTokenizer, MathType, MathValue, MathExpr, MathTree
from expanding.source import Reader, At
from expanding.variable import EnvironmentVariable

_str = TypeVar('_str', str, None)


class Expansion(object):
    """
Dollar-expansion

Supports following expansions:
 * $VARIABLE
 * ${VARIABLE[:quote[,quote...][|default value]}
 * $( integer expression )
"""
    DEFAULT_QUOTES = {
        'ms': lambda s, at: Expansion.to_milliseconds(s, at),
        's': lambda s, at: Expansion.to_seconds(s, at),
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
        """
        Constructor with sane defaults

        :param reader: input source
        :param variable: Object that can read variable names from a reader, and resolve variables
        :param quotes: map of quotes @see add_quote()
        """
        self._reader = reader
        self._variable = variable
        self.quotes = quotes

    def add_quote(self, name, func) -> TypeVar('Expansion'):
        """
        Add a new type of quotation

        :param name: name of quotation
        :param func: function that takes string and At object returning the quoted text
        :return: self for chaining
        """
        self.quotes[name] = func
        return self

    def expand(self, at, should_resolve=True) -> str:
        """
        Expand a $-expression

        reader should be positioned after $

        :param at: location if $ for error reporting
        :param should_resolve: if it is required to resolve
        :return: expanded text
        """
        c = self._reader.get()
        if c is '{':
            return self._expand_variable(at, should_resolve)
        if c is '(':
            return self._expand_math(at, should_resolve)
        self._reader.unget()
        (name, value) = self._process_variable()
        if should_resolve:
            self._fail_variable(at, name, value)
        return value

    def _process_variable(self) -> (_str, _str):
        """
        Read a variable form source

        :return:tuple of variable name and value
        """
        name = self._variable.get_name(self._reader)
        value = None
        if name is not None:
            value = self._variable.lookup_variable(name)
        return name, value

    @staticmethod
    def _fail_variable(at, name, value) -> None:
        """
        Fail if variable cannot be resolved

        :param at: location
        :param name: tuple from _process_variable
        :param value: tuple from _process_variable
        """
        if name is None:
            raise Exception("Cannot find variable name at: %s" % at)
        if value is None:
            raise Exception("Cannot resolve variable: %s at: %s" % (name, at))

    @staticmethod
    def to_milliseconds(string, at) -> str:
        """
        Convert a string to a number of milliseconds as string

        :param string: text containing a number and optional a duration
                       this duration is d/h/m/s/ms
        :param at : Input object with the location of the source
        """
        match = Expansion.TO_MILLISECONDS.match(string)
        if match is None:
            raise Exception("%s is not a duration at: %s" % (string, at))
        ms_pr_unit = Expansion.TO_MILLISECONDS_SCALE[match.group(2)]
        return str(int(match.group(1)) * ms_pr_unit)

    @staticmethod
    def to_seconds(string, at) -> str:
        """
        Convert a string to a number of seconds as string

        :param string: text containing a number and optional a duration
                       this duration is d/h/m/s
        :param at: Input object with the location of the source
        """
        match = Expansion.TO_SECONDS.match(string)
        if match is None:
            raise Exception("%s is not a duration at: %s" % (string, at))
        ms_pr_unit = Expansion.TO_SECONDS_SCALE[match.group(2)]
        return str(int(match.group(1)) * ms_pr_unit)

    def _expand_variable(self, at: At, should_resolve: bool) -> str:
        """
        expand ${} construction

        :param at: location of $
        :param should_resolve: if a result is required
        :return: expanded text
        """
        (name, value) = self._process_variable()
        at_after = self._reader.at()
        c = self._reader.get()
        quotes = []
        if c is ':':
            c = ','
            while c is ',':
                at_quote = self._reader.at()
                quote = StringIO()
                c = self._reader.get()
                while str.isalnum(c):
                    quote.write(c)
                    c = self._reader.get()
                quote = quote.getvalue()
                if quote not in self.quotes:
                    raise Exception("Unknown quote: '%s' at: %s" % (quote, at_quote))
                quotes.append(quote)

        if c is '|':
            default_value = self._process_until_closing_bracket(should_resolve and value is None)
        else:
            if c is None:
                raise Exception("Unexpected EOF in variable: %s at: %s" % (name, at))
            if c is not '}':
                raise Exception("Expected '}' in variable: %s at: %s got %s" % (name, at_after, c))
            if should_resolve:
                self._fail_variable(at, name, value)
        if should_resolve:
            if value is not None:
                for quote in quotes:
                    value = self.quotes[quote](value, at)
                return value
            else:
                return default_value
        else:
            return ""

    def _process_until_closing_bracket(self, should_resolve) -> str:
        """
        Expand text (default value) up until closing bracket

        :param should_resolve: if nested expansions should resolve
        :return: expanded content
        """
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

    def _expand_math(self, at: At, should_resolve: bool) -> str:
        """
        expand $() construction

        :param at: location of $
        :param should_resolve: if a result is required
        :return: expanded text
       """
        self._tokenizer = MathTokenizer(at, self._reader, self, should_resolve)
        tree = self._process_to_closing_parenthesis()
        if should_resolve:
            return str(tree.get_value())
        else:
            return ""

    def _process_to_closing_parenthesis(self) -> MathTree:
        """
        Build a math tree up until the matching closing parenthesis
        :return: Math Tree
        """
        operators = []
        values = []
        while True:
            neg = False
            token = self._tokenizer.token()
            while token.is_a(MathType.SUB):
                neg = not neg
                token = self._tokenizer.token()
            if token.is_a(MathType.LPAR):
                tree = self._process_to_closing_parenthesis()
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
