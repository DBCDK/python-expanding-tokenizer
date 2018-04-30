from unittest import TestCase
from expanding.source import Reader
from io import StringIO

from expanding.variable import EnvironmentVariable


class TestEnvVarReader(TestCase):

    def test_get_name(self):
        var_reader = EnvironmentVariable(env = {"_ABC123": "abc", "DEF": "fed"})
        reader = Reader(StringIO("_ABC123"))
        self.assertEqual("_ABC123", var_reader.get_name(reader), "At eof")
        self.assertEqual(None, reader.get())
        reader = Reader(StringIO("_ABC123 "))
        self.assertEqual("_ABC123", var_reader.get_name(reader), "At eof")
        self.assertEqual(" ", reader.get())
        reader = Reader(StringIO("_ABC123\n"))
        self.assertEqual("_ABC123", var_reader.get_name(reader), "At eof")
        self.assertEqual("\n", reader.get())

    def test_lookup_variable(self):
        var_reader = EnvironmentVariable(env = {"_ABC123": "abc", "DEF": "fed"})
        self.assertEqual(None, var_reader.lookup_variable("FOO"))
        self.assertEqual("abc", var_reader.lookup_variable("_ABC123"))
