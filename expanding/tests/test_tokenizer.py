from io import StringIO
from unittest import TestCase

from expanding.source import At, Reader
from expanding.tokenizer import *
from expanding.variable import EnvironmentVariable

at = At("Unknown", 1, 2)


def make_tokenizer(text, whitespace=TokenWhitespace.NEWLINE, **kwargs):
    return Tokenizer(Reader(StringIO(text)), EnvironmentVariable(kwargs), whitespace=whitespace)


class TestToken(TestCase):

    def test_is_a(self):
        token = Token(at, TokenType.TEXT, "123")
        self.assertEqual(True, token.is_a(TokenType.NUMBER))
        self.assertEqual(True, token.is_a(TokenType.WORD))
        token = Token(at, TokenType.TEXT, "1A3")
        self.assertEqual(False, token.is_a(TokenType.NUMBER))
        self.assertEqual(True, token.is_a(TokenType.WORD))
        token = Token(at, TokenType.TEXT, "1 23")
        self.assertEqual(False, token.is_a(TokenType.NUMBER))
        self.assertEqual(False, token.is_a(TokenType.WORD))


class TestTokenizer(TestCase):

    def test_tokens_are_word(self):
        self.assertTrue(make_tokenizer("abc \n").tokens_are(TokenType.TEXT))
        self.assertTrue(make_tokenizer("abc \n").tokens_are(TokenType.WORD))

    def test_tokens_are_single_quote(self):
        self.assertTrue(make_tokenizer("'abc' \n").tokens_are(TokenType.TEXT))
        self.assertTrue(make_tokenizer("'abc' \n").tokens_are(TokenType.WORD))

    def test_tokens_are_expanded(self):
        output = []
        self.assertTrue(make_tokenizer(" $FOO ", FOO="a b").tokens_are(TokenType.TEXT, output=output))
        self.assertEqual(1, len(output))
        self.assertEqual("a b", output[0].content())

    def test_tokens_are_double_quote(self):
        self.assertTrue(make_tokenizer('"abc"').tokens_are(TokenType.TEXT))
        self.assertTrue(make_tokenizer('"abc"').tokens_are(TokenType.WORD))

    def test_tokens_are_double_quote_expanded(self):
        output = []
        self.assertTrue(make_tokenizer('foo = "abc $($ID) def"\n', ID="123")
                        .tokens_are(TokenType.WORD, TokenType.EQ, TokenType.TEXT, TokenType.NEWLINE, output=output))
        self.assertEqual("abc 123 def", output[2].content())
        tokenizer = make_tokenizer('')
        self.assertTrue(tokenizer.tokens_are(TokenType.EOF))
        self.assertTrue(tokenizer.tokens_are(TokenType.EOF))

    def test_tokens_are_section_and_comment(self):
        output = []
        self.assertTrue(make_tokenizer('; bah \n[fool] #abc\n  \n', ID="123")
                        .tokens_are(TokenType.SECTION, TokenType.NEWLINE, TokenType.EOF, output=output))
        self.assertEqual("fool", output[0].content())

    def test_token_eof(self):
        self.assertRaises(Exception, make_tokenizer('[fool').tokens_are, TokenType.SECTION)
        self.assertRaises(Exception, make_tokenizer('\'fool').tokens_are, TokenType.TEXT)
        self.assertRaises(Exception, make_tokenizer('"fool').tokens_are, TokenType.TEXT)

    def test_whitespace_none(self):
        tzr = make_tokenizer("  \n   foo bar", whitespace=TokenWhitespace.NONE)
        output = []

        self.assertTrue(tzr.tokens_are(TokenType.TEXT, output=output))
        self.assertEqual(1, len(output))
        self.assertEqual("foo", output[0].content())
        self.assertTrue(tzr.tokens_are(TokenType.TEXT, TokenType.EOF))

    def test_whitespace_newline(self):
        tzr = make_tokenizer("  \n   foo bar", whitespace=TokenWhitespace.NEWLINE)
        output = []
        self.assertTrue(tzr.tokens_are(TokenType.NEWLINE, TokenType.TEXT, output=output))
        self.assertEqual(2, len(output))
        self.assertEqual("foo", output[1].content())
        self.assertTrue(tzr.tokens_are(TokenType.TEXT, TokenType.EOF))

    def test_whitespace_newline_match_optional_whitespace(self):
        tzr = make_tokenizer("  \n   foo bar", whitespace=TokenWhitespace.NEWLINE)
        output = []
        self.assertTrue(tzr.tokens_are(TokenType.OPTIONAL, TokenType.ANY_WHITESPACE, TokenType.TEXT, output=output))
        self.assertEqual(1, len(output))
        self.assertEqual("foo", output[0].content())
        self.assertTrue(tzr.tokens_are(TokenType.TEXT, TokenType.EOF))

    def test_whitespace_whitespace(self):
        tzr = make_tokenizer("  \n   foo bar", whitespace=TokenWhitespace.WHITESPACE)
        output = []
        self.assertFalse(tzr.tokens_are(TokenType.NEWLINE, TokenType.TEXT, output=output))
        self.assertTrue(tzr.tokens_are(TokenType.WHITESPACE, TokenType.TEXT, output=output))
        self.assertEqual(2, len(output))
        self.assertEqual("foo", output[1].content())
        self.assertTrue(tzr.tokens_are(TokenType.OPTIONAL, TokenType.WHITESPACE, TokenType.TEXT, TokenType.EOF))

    def test_whitespace_both(self):
        tzr = make_tokenizer("  \n   foo bar", whitespace=TokenWhitespace.BOTH)
        output = []
        self.assertFalse(tzr.tokens_are(TokenType.NEWLINE, TokenType.TEXT, output=output))
        self.assertTrue(tzr.tokens_are(TokenType.WHITESPACE, TokenType.NEWLINE, TokenType.WHITESPACE, TokenType.TEXT, output=output))
        self.assertEqual(4, len(output))
        self.assertEqual("foo", output[3].content())
        self.assertTrue(tzr.tokens_are(TokenType.OPTIONAL,TokenType.ANY_WHITESPACE, TokenType.TEXT, TokenType.EOF))

    def test_whitespace_both_optional(self):
        tzr = make_tokenizer("  \n   foo'bar'", whitespace=TokenWhitespace.BOTH)
        output = []
        self.assertTrue(tzr.tokens_are(TokenType.OPTIONAL, TokenType.ANY_WHITESPACE, TokenType.TEXT, output=output))
        self.assertEqual(1, len(output))
        self.assertEqual("foo", output[0].content())
        self.assertTrue(tzr.tokens_are(TokenType.OPTIONAL, TokenType.ANY_WHITESPACE, TokenType.TEXT, TokenType.EOF))


