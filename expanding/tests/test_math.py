from io import StringIO
from unittest import TestCase

from expanding.expand import Expansion
from expanding.math import MathTokenizer, MathType
from expanding.source import Reader, At
from expanding.variable import EnvironmentVariable


def make_tokenizer(text, should_resolve=True, **kwargs):
    reader = Reader(StringIO(text))
    variable = EnvironmentVariable(kwargs)
    expanding = Expansion(reader, variable)
    tokenizer = MathTokenizer(At("", -1, -1), reader, expanding, should_resolve)
    return tokenizer


class TestMathTokenizer(TestCase):

    def test_token(self):
        tokenizer = make_tokenizer(" ( ) 123 +\n-!")
        self.assertEqual(MathType.LPAR, tokenizer.token()._token_type)
        self.assertEqual(MathType.RPAR, tokenizer.token()._token_type)
        self.assertEqual(MathType.NUMBER, tokenizer.token()._token_type)
        self.assertEqual(MathType.ADD, tokenizer.token()._token_type)
        self.assertEqual(MathType.SUB, tokenizer.token()._token_type)
        self.assertEqual("!", tokenizer._reader.get())

    def test_token_var(self):
        tokenizer = make_tokenizer(" $ABC ", ABC="123")
        token = tokenizer.token()
        self.assertEqual(MathType.NUMBER, token._token_type)
        self.assertEqual("123", token.content())

    def test_token_var(self):
        tokenizer = make_tokenizer(" $ABCD ", should_resolve=False, ABC="123")
        token = tokenizer.token()
        self.assertEqual(MathType.NUMBER, token._token_type)
        self.assertEqual(None, token.content())


