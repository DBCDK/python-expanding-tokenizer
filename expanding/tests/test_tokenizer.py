from io import StringIO
from unittest import TestCase

from expanding.source import At, Reader
from expanding.tokenizer import Token, TokenType, Tokenizer
from expanding.variable import EnvironmentVariable

at = At("Unknown", 1, 2)


def make_tokenizer(text, **kwargs):
    return Tokenizer(Reader(StringIO(text)), EnvironmentVariable(kwargs))


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

    def test_tokens_are(self):
        self.assertTrue(make_tokenizer("abc \n").tokens_are(TokenType.TEXT))
        self.assertTrue(make_tokenizer("abc \n").tokens_are(TokenType.WORD))

        self.assertTrue(make_tokenizer("'abc' \n").tokens_are(TokenType.TEXT))
        self.assertTrue(make_tokenizer("'abc' \n").tokens_are(TokenType.WORD))

        output = []
        self.assertTrue(make_tokenizer(" $FOO ", FOO="a b").tokens_are(TokenType.TEXT, output=output))
        self.assertEqual(1, len(output))
        self.assertEqual("a b", output[0].content())

        self.assertTrue(make_tokenizer('"abc"').tokens_are(TokenType.TEXT))
        self.assertTrue(make_tokenizer('"abc"').tokens_are(TokenType.WORD))

        output = []
        self.assertTrue(make_tokenizer('foo = "abc $($ID) def"\n', ID="123")
                        .tokens_are(TokenType.WORD, TokenType.EQ, TokenType.TEXT, TokenType.NEWLINE, output=output))
        self.assertEqual("abc 123 def", output[2].content())
        tokenizer = make_tokenizer('')
        self.assertTrue(tokenizer.tokens_are(TokenType.EOF))
        self.assertTrue(tokenizer.tokens_are(TokenType.EOF))

        output = []
        self.assertTrue(make_tokenizer('; bah \n[fool] #abc\n  \n', ID="123")
                        .tokens_are(TokenType.SECTION, TokenType.NEWLINE, TokenType.EOF, output=output))
        self.assertEqual("fool", output[0].content())

    def test_token_eof(self):
        self.assertRaises(Exception, make_tokenizer('[fool').tokens_are, TokenType.SECTION)
        self.assertRaises(Exception, make_tokenizer('\'fool').tokens_are, TokenType.TEXT)
        self.assertRaises(Exception, make_tokenizer('"fool').tokens_are, TokenType.TEXT)
