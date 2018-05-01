from io import StringIO
from unittest import TestCase

from expanding.expand import Expansion
from expanding.source import Reader, At
from expanding.variable import EnvironmentVariable


def make_expanding(text, **kwargs):
    reader = Reader(StringIO(text))
    variable = EnvironmentVariable(kwargs)
    expanding = Expansion(reader, variable)
    return expanding


class TestExpansion(TestCase):

    def test_expand_simple(self):
        expanding = make_expanding("FOO!", FOO="BAR")
        self.assertEqual("BAR", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())
        self.assertRaises(Exception, expanding.expand, At("", -1, -1))

    def test_expand_simple_missing_value(self):
        expanding = make_expanding("ABC!", FOO="BAR")
        self.assertRaises(Exception, expanding.expand, At("", -1, -1))

    def test_expand_with_nothing_special(self):
        expanding = make_expanding("{FOO}!", FOO="BAR")
        self.assertEqual("BAR", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

    def test_expand_with_default_unresolvable(self):
        expanding = make_expanding("{ABC|123}!", FOO="BAR")
        self.assertEqual("123", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

    def test_expand_with_default_quoted(self):
        expanding = make_expanding("{ABC|12\\}3}!", FOO="BAR")
        self.assertEqual("12}3", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

    def test_expand_with_default_resolvable(self):
        expanding = make_expanding("{FOO|12\\}3}!", FOO="BAR")
        self.assertEqual("BAR", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

    def test_expand_with_nested(self):
        expanding = make_expanding("{ABC|12${FOO}3}!", FOO="BAR")
        self.assertEqual("12BAR3", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

    def test_expand_with_nested_resolved(self):
        expanding = make_expanding("{FOO|12${ABC}3}!", FOO="BAR")
        self.assertEqual("BAR", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

    def test_expand_math(self):
        expanding = make_expanding("(123)!")
        self.assertEqual("123", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

    def test_expand_math_nested_paren(self):
        expanding = make_expanding("( ( $A ) )!", A="321")
        self.assertEqual("321", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

    def test_expand_math_simple_op(self):
        expanding = make_expanding("($A+12)!", A="321")
        self.assertEqual("333", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

    def test_expand_math_precedence_op(self):
        expanding = make_expanding("($A+3*4)!", A="321")
        self.assertEqual("333", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

    def test_expand_math_precedence_op(self):
        expanding = make_expanding("(4/3*0)!")
        self.assertEqual("0", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

    def test_expand_math_neg_number_1(self):
        expanding = make_expanding("(- 4)!")
        self.assertEqual("-4", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

    def test_expand_math_neg_number_2(self):
        expanding = make_expanding("(4 * ---4)!")
        self.assertEqual("-16", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

    def test_expand_math_neg_number_2(self):
        expanding = make_expanding("($A * ---4)!", A="-4")
        self.assertEqual("16", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

    def test_expand_with_quotes(self):
        expanding = make_expanding("{A:sql,attr}!", A="ab'\"cd")
        self.assertEqual("ab''&quot;cd", expanding.expand(At("", -1, -1)))
        self.assertEqual("!", expanding._reader.get())

