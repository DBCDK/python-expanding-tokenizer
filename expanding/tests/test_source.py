from unittest import TestCase
from io import StringIO
import expanding.source as source


class TestReader(TestCase):

    def test_get_unget_two_lines(self):
        reader = source.Reader(StringIO("One\nTwo\n"))
        self.assertEqual("<UNKNOWN>:1:1", str(reader.at()))
        self.assertEqual('O', reader.get())
        self.assertEqual('n', reader.get())
        self.assertEqual('e', reader.get())
        reader.unget()
        self.assertEqual('e', reader.get())
        self.assertEqual("<UNKNOWN>:1:4", str(reader.at()))
        self.assertEqual("\n", reader.get())
        self.assertEqual("<UNKNOWN>:2:1", str(reader.at()))
        reader.unget()  # Across lines
        self.assertEqual("<UNKNOWN>:1:4", str(reader.at()))
        self.assertEqual("\n", reader.get())
        self.assertEqual('T', reader.get())
        self.assertEqual('w', reader.get())
        self.assertEqual('o', reader.get())
        self.assertEqual("<UNKNOWN>:2:4", str(reader.at()))
        self.assertEqual("\n", reader.get())
        self.assertEqual("<UNKNOWN>:EOF", str(reader.at()))

    def test_too_many_ungets(self):
        reader = source.Reader(StringIO("\n\n\n123"))
        self.assertEqual("\n", reader.get())
        self.assertEqual("\n", reader.get())
        self.assertEqual("\n", reader.get())
        self.assertEqual("1", reader.get())
        reader.unget()  # 1
        reader.unget()  # \n
        reader.unget()  # \n
        self.assertRaises(BufferError, reader.unget)  # fail

    def test_get_quoted(self):
        reader = source.Reader(StringIO("\\n\\r\\t\\u0040\\040\\$"))
        self.assertEqual("\\", reader.get())
        self.assertEqual("\n", reader.get_quoted())
        self.assertEqual("\\", reader.get())
        self.assertEqual("\r", reader.get_quoted())
        self.assertEqual("\\", reader.get())
        self.assertEqual("\t", reader.get_quoted())
        self.assertEqual("\\", reader.get())
        self.assertEqual("@", reader.get_quoted())
        self.assertEqual("\\", reader.get())
        self.assertEqual(" ", reader.get_quoted())
        self.assertEqual("\\", reader.get())
        self.assertEqual("$", reader.get_quoted())
