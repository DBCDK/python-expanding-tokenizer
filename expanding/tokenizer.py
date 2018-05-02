import re
from enum import Enum
from io import StringIO
from typing import TypeVar, List

from expanding.expand import Expansion
from expanding.source import Reader, At
from expanding.variable import EnvironmentVariable, Variable


class TokenType(Enum):
    """
Type of token

Some are synthetic (groups) ie. matches multiple base tokens
Some are synthetic (content) ie. matches TEXT with certain properties (single word / number)
Some are matchers (OPTIONAL) ie. matches a list of next type
    """
    # Could be produced synthetically, but then completion is missing
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
    WHITESPACE = 'WHITESPACE'
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
    NUMBER = 'NUMBER'  # Synthetic: TEXT containing hex, octal or decimal number, optionally negative
    EOL = 'EOL'  # Synthetic: EOF or NEWLINE
    ANY_WHITESPACE = 'ANY_WHITESPACE'  # Synthetic: whitespace or newline
    ANY = 'ANY'  # Synthetic: wildcard
    OPTIONAL = 'OPTIONAL'  # Matches 0-n of next type, not outputed


class TokenWhitespace(Enum):
    """How are whitespaces processed by Tokenizer"""
    # Could be produced synthetically, but then completion is missing
    NONE = 'NONE' """Skip all whitespace"""
    NEWLINE = 'NEWLINE' """Produce only newline tokens"""
    WHITESPACE = 'WHITESPACE' """Produces whitespace tokens (can contain newlines)"""
    BOTH = 'BOTH' """Produces both newline and whitespace tokens (whitespace will not contain newlines)"""


class Token(object):
    """
Container for a token

Implements location, type and content
Also has matchers for token types
    """
    _IS_NUMBER = re.compile('^(?:(?:[-+]?)(?:0[xX][0-9a-fA-F]+)|(?:[1-9][0-9]*)|(?:0[0-7]*))$', re.S | re.U)
    _IS_WORD = re.compile('^\\S+$', re.S | re.U)

    def __init__(self, at: At, token_type: TokenType, content: str) -> TypeVar('Token'):
        """
        Token class contructor

        :param at: Location of token
        :param token_type: type
        :param content: content string
        :returns: new object
        """
        self._at = at
        self._token_type = token_type
        self._content = content

    def at(self) -> At:
        """
        Get location of token

        :returns: At object where this token starts
        """
        return self._at

    def content(self) -> str:
        """
        Get string with token content, most useful whendealing with TEXT type tokens

        :returns: content string
        """
        return self._content

    def is_a(self, wanted_type: TokenType) -> bool:
        """
        Is the token of a given type

        Handles synthetic types such as, WORD, NUMBER, EOL

        :param wanted_type: type
        :returns: true if type is matched
        """
        if wanted_type is TokenType.ANY:
            return True
        if wanted_type is TokenType.ANY_WHITESPACE:
            return self._token_type is TokenType.NEWLINE or self._token_type is TokenType.WHITESPACE
        if wanted_type is TokenType.EOL:
            return self._token_type is TokenType.NEWLINE or self._token_type is TokenType.EOF
        if wanted_type is TokenType.NUMBER:
            return self._token_type is TokenType.TEXT and self._IS_NUMBER.match(self._content) is not None
        if wanted_type is TokenType.WORD:
            return self._token_type is TokenType.TEXT and self._IS_WORD.match(self._content) is not None
        return wanted_type is self._token_type

    def __str__(self):
        return "{%s,%s,%s}" % (self._token_type, self._at, self._content)


class Tokenizer(object):
    """
Tokenizer

Primary purpose of this package is
 * expanding variables / expressions and
 * patten-matching content from  a input source
"""
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
        """
        Create a Tokenizer from a file, for parsing ini files

        The file is read into memory - inefficient when dealing with large files.

        :param filename: path of file
        :returns: new object
        """
        with open(filename, 'r') as f:
            content = f.read()
            reader = Reader(source=StringIO(content), name=filename)
            return Tokenizer(reader=reader, variable=EnvironmentVariable(), whitespace=TokenWhitespace.NEWLINE, single_tokens="=")

    @staticmethod
    def full_from_file(filename: str) -> TypeVar('Tokenizer'):
        """
        Create a Tokenizer from a file, for parsing any files

        The file is read into memory - inefficient when dealing with large files.

        :param filename: path of file
        :returns: new object
        """
        with open(filename, 'r') as f:
            content = f.read()
            reader = Reader(source=StringIO(content), name=filename)
            return Tokenizer(reader=reader, variable=EnvironmentVariable(), whitespace=TokenWhitespace.BOTH,
                             single_tokens="".join(Tokenizer._SINGLE_CHARACTER_TOKENS.keys()))

    def __init__(self, reader: Reader, variable: Variable = EnvironmentVariable(),
                 whitespace: TokenWhitespace = TokenWhitespace.NEWLINE,
                 single_tokens: str = "=") -> TypeVar('Tokenizer'):
        """
        Tokenizer constructor

        :param reader: the file source
        :param variable: the variable expander (defaults to Environment)
        :param whitespace: should newlines be tokens
        :param single_tokens: String of chars thet should be their own tokens
                              see _SINGLE_CHARACTER_TOKENS for known tokens
        :returns: new object
        """
        self._variable = variable
        self._reader = reader
        if whitespace is TokenWhitespace.BOTH:
            self._handle_whitespace = self._handle_whitespace_both
        elif whitespace is TokenWhitespace.NEWLINE:
            self._handle_whitespace = self._handle_whitespace_newline
        elif whitespace is TokenWhitespace.WHITESPACE:
            self._handle_whitespace = self._handle_whitespace_whitespace
        else:
            self._handle_whitespace = self._handle_whitespace_none
        self.expander = Expansion(reader, variable)
        self._tokens = []
        self._single_tokens = dict(
            [(x, self._SINGLE_CHARACTER_TOKENS[x]) for x in self._SINGLE_CHARACTER_TOKENS.keys() if x in single_tokens])
        self._break_chars = ''.join(self._single_tokens.keys()) + "[]$;#'" + '"'

    def peek_token(self) -> Token:
        """
        Look at the next token, mostly for error reporting, when unable to match a token sequence

        :returns: next token
        """
        if not self._tokens:
            self._next_token()
        return self._tokens[0]

    def tokens_are(self, *args: TypeVar('_TokenType', TokenType, List[TokenType]), output: List[Token] = []) -> List[Token]:
        """
        Match the inut for a list of tokens.

        :param args: list of token types elements to match
                     element is optionally a list of token types where at least one should match
        :param output: where to put the matched token
                       (only put is entire token list matches)
        :returns: sane as output or None if no match is made
        """
        taken = []
        i = 0
        last_was = None
        for arg in args:
            self._ensure_n_tokens(i)

            if last_was is TokenType.OPTIONAL:
                while self._tokens[i].is_a(arg):
                    i = i + 1
                    self._ensure_n_tokens(i)
            elif arg is TokenType.OPTIONAL:
                pass
            elif hasattr(arg, '__iter__'):
                if True in [self._tokens[i].is_a(t) for t in arg]:
                    taken.append(self._tokens[i])
                    i = i + 1
                else:
                    return None
            elif self._tokens[i].is_a(arg):
                taken.append(self._tokens[i])
                i = i + 1
            else:
                return None
            last_was = arg
        if last_was is TokenType.OPTIONAL:
            raise Exception("Dangling OPTIONAL in tokens_are()")
        for token in taken:
            output.append(token)
        self._tokens = self._tokens[i:]
        return output

    def _ensure_n_tokens(self, n: int) -> None:
        while len(self._tokens) <= n:
            self._next_token()

    def _next_token(self) -> None:
        """
        Construct a new token, and puts it in the token list

        :raises Exception: if input is invalid
        """
        while True:
            at = self._reader.at()
            c = self._reader.get()
            if c is None:
                self._tokens.append(Token(at, TokenType.EOF, ''))
                return
            if str.isspace(c):
                if self._handle_whitespace(at, c):
                    return
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

    def _handle_whitespace_none(self, at, c) -> False:
        """
        Eat all whitespace in source

        :param at: required by interface
        :param c: required by interface
        :return False: Doesn't produce a token
        """
        while True:
            if c is None:
                return False
            if not str.isspace(c):
                self._reader.unget()
                return False
            c = self._reader.get()

    def _handle_whitespace_newline(self, at, c) -> bool:
        """
        Constructs a newline token if a newline is encountered in whitespace block

        :param at: Needed for new token
        :param c: first whitespace character
        :return bool: if a newline is encountered
        """
        while True:
            if c is None:
                return False
            if c is "\n":
                self._tokens.append(Token(at, TokenType.NEWLINE, c))
                return True
            if not str.isspace(c):
                self._reader.unget()
                return False
            c = self._reader.get()

    def _handle_whitespace_whitespace(self, at, c) -> True:
        """
        Constructs a whitespace token with optional newlines in it

        :param at: Needed for new token
        :param c: first whitespace character
        :return True: will always produce a token
        """
        content = StringIO()
        while True:
            if c is None:
                self._tokens.append(Token(at, TokenType.WHITESPACE, content.getvalue()))
                return True
            if not str.isspace(c):
                self._reader.unget()
                self._tokens.append(Token(at, TokenType.WHITESPACE, content.getvalue()))
                return True
            content.write(c)
            c = self._reader.get()

    def _handle_whitespace_both(self, at, c) -> True:
        """
        Constructs a newline token or a whitespace token

        :param at: Needed for new token
        :param c: first whitespace character
        :return True: will always produce a token
        """
        if c is "\n":
            self._tokens.append(Token(at, TokenType.NEWLINE, c))
            return True
        content = StringIO()
        while True:
            if c is None:
                self._tokens.append(Token(at, TokenType.WHITESPACE, content.getvalue()))
                return True
            if not str.isspace(c) or c is "\n":
                self._reader.unget()
                self._tokens.append(Token(at, TokenType.WHITESPACE, content.getvalue()))
                return True
            content.write(c)
            c = self._reader.get()

    def _read_single_quote(self, at) -> None:
        """
        Constructs a token from a single quote text, and puts it into the token list.

        Input should be positioned after 1st quote

        :raises Exception: On unexpected eof
        """
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
        """
        Constructs a token from a double quote text, and puts it into the token list.

        Input should be positioned after 1st quote.
        \\ escapes are expanded and variables are expanded

        :raises Exception: On unexpected eof, invalid quote or variable
        """
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
        """
        Constructs a token from a section, and puts it into the token list.

        Input should be positioned after [.

        :raises Exception: On unexpected eof or whitespace
        """
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

