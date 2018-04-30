import re
from enum import Enum
from io import StringIO
from typing import TypeVar, List

from expanding.expand import Expanding
from expanding.source import Reader, At
from expanding.variable import EnvironmentVariable, Variable


class TokenType(Enum):
    # Could be produced synthetically, zbut then completion is missing
    TEXT = 'TEXT'
    EQ = 'EQ'
    DOT = 'DOT'
    COMMA = 'COMMA'
    COLON = 'COLON'
    LPARENT = 'LPARENT'
    RPARENT = 'RPARENT'
    LBRACE = 'LBRACE'
    RBRACE = 'RBRACE'
    LBRACKET = 'LBRACK'  # Enabling this inhibits production of SECTION
    RBRACKET = 'RBRACK'
    SEMICOLON = 'SEMICOLON'
    SECTION = 'SECTION'
    NEWLINE = 'NEWLINE'
    ADD = 'ADD'
    SUB = 'SUB'
    MUL = 'MUL'
    DIV = 'DIV'
    MOD = 'MOD'
    POW = 'POW'
    AMP = 'AMP'
    LT = 'LT'
    GT = 'GT'
    QUESTION = 'QUESTION'
    EXCLAMATION = 'EXCLAMATION'
    EOF = 'EOF'
    WORD = 'WORD'  # Synthetic: TEXT without whitespace
    NUMBER = 'NUMBER'  # Synthetic: TEXT containing hex,octal or decimal number, optionally negative
    EOL = 'EOL'  # Synthetic: EOF or NEWLINE


class Token(object):
    _IS_NUMBER = re.compile('^(?:(?:[-+]?)(?:0[xX][0-9a-fA-F]+)|(?:[1-9][0-9]*)|(?:0[0-7]*))$', re.S | re.U)
    _IS_WORD = re.compile('^\\S+$', re.S | re.U)

    def __init__(self, at: At, token_type: TokenType, content: str) -> TypeVar('Token'):
        self._at = at
        self._token_type = token_type
        self._content = content

    def at(self) -> At:
        return self._at

    def content(self) -> str:
        return self._content

    def is_a(self, wanted_type: TokenType) -> bool:
        if wanted_type is TokenType.EOL:
            return self._token_type is TokenType.NEWLINE or self._token_type is TokenType.EOF
        if wanted_type is TokenType.NUMBER:
            return self._IS_NUMBER.match(self._content) is not None
        if wanted_type is TokenType.WORD:
            return self._IS_WORD.match(self._content) is not None
        return wanted_type is self._token_type

    def __str__(self):
        return "{%s,%s,%s}" % (self._token_type, self._at, self._content)


class Tokenizer(object):
    _SINGLE_CHARACTER_TOKENS = {
        '=': TokenType.EQ,
        '.': TokenType.DOT,
        ',': TokenType.COMMA,
        ':': TokenType.COLON,
        ';': TokenType.SEMICOLON,
        '(': TokenType.LPARENT,
        ')': TokenType.RPARENT,
        '{': TokenType.LBRACE,
        '}': TokenType.RBRACE,
        '[': TokenType.LBRACKET,
        ']': TokenType.RBRACKET,
        '+': TokenType.ADD,
        '-': TokenType.SUB,
        '*': TokenType.MUL,
        '/': TokenType.DIV,
        '%': TokenType.MOD,
        '^': TokenType.POW,
        '&': TokenType.AMP,
        '<': TokenType.LT,
        '>': TokenType.GT,
        '?': TokenType.QUESTION,
        '!': TokenType.EXCLAMATION,
    }

    @staticmethod
    def ini_from_file(filename: str) -> TypeVar('Tokenizer'):
        with open(filename, 'r') as f:
            content = f.read()
            reader = Reader(source=StringIO(content), source_name=filename)
            return Tokenizer(reader=reader, variable=EnvironmentVariable(), newline=True, single_tokens="=")

    @staticmethod
    def full_from_file(filename: str) -> TypeVar('Tokenizer'):
        with open(filename, 'r') as f:
            content = f.read()
            reader = Reader(source=StringIO(content), source_name=filename)
            return Tokenizer(reader=reader, variable=EnvironmentVariable(), newline=True,
                             single_tokens="".join(Tokenizer._SINGLE_CHARACTER_TOKENS.keys()))

    def __init__(self, reader: Reader, variable: Variable = EnvironmentVariable(), newline: bool = True,
                 single_tokens: str = "=") -> TypeVar('Tokenizer'):
        self._variable = variable
        self._reader = reader
        self._newline = newline
        self.expander = Expanding(reader, variable)
        self._tokens = []
        self._single_tokens = dict(
            [(x, self._SINGLE_CHARACTER_TOKENS[x]) for x in self._SINGLE_CHARACTER_TOKENS.keys() if x in single_tokens])
        self._break_chars = ''.join(self._single_tokens.keys()) + "[]$;#'" + '"'

    def peek_token(self) -> Token:
        if not self._tokens:
            self._next_token()
        return self._tokens[0]

    def tokens_are(self, *args: TokenType, output: List[Token] = []) -> List[Token]:
        for i in range(0, len(args)):
            if len(self._tokens) <= i:
                self._next_token()
            if not self._tokens[i].is_a(args[i]):
                return None
        for token in self._tokens[0:len(args)]:
            output.append(token)
        self._tokens = self._tokens[len(args):]
        return output

    def _next_token(self) -> None:
        while True:
            at = self._reader.at()
            c = self._reader.get()
            if c is None:
                self._tokens.append(Token(at, TokenType.EOF, ''))
                return
            if self._newline and c is "\n":
                self._tokens.append(Token(at, TokenType.NEWLINE, c))
                return
            if str.isspace(c):
                continue
            if c is '#' or c is ';':
                while True:
                    c = self._reader.get()
                    if c is None or c is "\n":
                        break
                continue
            if c is "$":
                content = self.expander.expand(at)
                self._tokens.append(Token(at, TokenType.TEXT, content))
                return
            if c in self._single_tokens:
                self._tokens.append(Token(at, self._single_tokens[c], c))
                return
            if c is '[':
                self._read_section(at)
                return
            if c is '"':
                self._read_double_quote(at)
                return
            if c is "'":
                self._read_single_quote(at)
                return

            content = StringIO()
            content.write(c)
            while True:
                c = self._reader.get()
                if c is None:
                    break
                if str.isspace(c) or c in self._break_chars:
                    self._reader.unget()
                    break
                content.write(c)
            self._tokens.append(Token(at, TokenType.TEXT, content.getvalue()))

    def _read_single_quote(self, at) -> None:
        content = StringIO()
        while True:
            c = self._reader.get()
            if c is None:
                raise Exception("Unexpected EOF in single quote starting at: %s" % at)
            if c is "'":
                c = self._reader.get()
                if c is not "'":
                    if c is not None:
                        self._reader.unget()
                    self._tokens.append(Token(at, TokenType.TEXT, content.getvalue()))
                    return
            content.write(c)

    def _read_double_quote(self, at) -> None:
        content = StringIO()
        while True:
            a = self._reader.at()
            c = self._reader.get()
            if c is None:
                raise Exception("Unexpected EOF in double quote starting at: %s" % at)
            if c is '"':
                self._tokens.append(Token(at, TokenType.TEXT, content.getvalue()))
                return
            if c is '$':
                content.write(self.expander.expand(a))
                continue
            if c is '\\':
                c = self._reader.get_quoted()
            content.write(c)

    def _read_section(self, at) -> None:
        content = StringIO()
        while True:
            c = self._reader.get()
            if c is None:
                raise Exception("Unexpected EOF in section starting at: %s" % at)
            if c is ']':
                self._tokens.append(Token(at, TokenType.SECTION, content.getvalue()))
                return
            if str.isspace(c):
                raise Exception("Whitespace is not allowed in section at: %s" % at)
            content.write(c)
