
class At(object):
    """
    Location object
    """
    def __init__(self, source, line=None, pos=None):
        """
        Construct a location object

        :param source: the filename
        :param line: line number
        :param pos: character on line
        """
        self.source = source
        self.line = line
        self.pos = pos

    def __str__(self) -> str:
        if self.line is None:
            return self.source
        else:
            return "%s:%d:%d" % (self.source, self.line, self.pos)


class Reader(object):
    """
    (Line) buffered reader with location
    """

    _QUOTED = {
        "n": "\n",
        "r": "\r",
        "t": "\t"
    }

    def __init__(self, source, name="<UNKNOWN>"):
        """
        Construct a reader

        :param source: input file handle
        :param name: name of source
        """
        self._source = source
        self._source_name = name
        self._buffer = []
        self._line = 0
        self._real_line = 0
        self._pos = -1
        self._eof = False
        self._read_line()

    def _read_line(self) -> None:
        """
        Add a line to the buffer

        Remove old lines, that are no longer needed
        """
        if not self.eof():
            line = self._source.readline()
            if line is "":
                self._eof = True
            else:
                while len(self._buffer) > 2:
                    self._buffer = self._buffer[1:]
                self._line = len(self._buffer)
                self._real_line = self._real_line + 1
                self._buffer.append([self._real_line] + [c for c in line])
                self._pos = 1

    def get(self) -> str:
        """
        Get a character from the input

        :return: character (str) or None of at end of file
        """
        if self.eof():
            return None
        c = self._buffer[self._line][self._pos]
        self._pos = self._pos + 1
        if self._pos == len(self._buffer[self._line]):
            if self._line + 1 == len(self._buffer):
                self._read_line()
            else:
                self._pos = 1
                self._line = self._line + 1
        return c

    def get_quoted(self) -> str:
        """
        Read a backquoted value from  input

        typical \\ r t n {octal} u{hex} or $
        :return: character
        :raises: Exception if EOF is encountered
        """
        c = self.get()
        if c is None:
            raise Exception("Unexpected EOF - dangling quote")
        if c in self._QUOTED:
            return self._QUOTED[c]
        if c is 'u':
            hexa = str(self.get()) + str(self.get()) + str(self.get()) + str(self.get())
            if len(hexa) is not 4:
                raise Exception("Unexpected EOF - dangling quote")
            return chr(int(hexa, 16))
        if str.isnumeric(c) and int(c) <= 3:
            octal = c + str(self.get()) + str(self.get())
            if len(octal) is not 3:
                raise Exception("Unexpected EOF - dangling quote")
            return chr(int(octal, 8))
        return c

    def unget(self) -> None:
        """
        Roll a character back, in the input
        """
        self._pos = self._pos - 1
        if self._pos <= 0:
            if self._line == 0:
                raise BufferError("Unget beyond buffering")
            self._line = self._line - 1
            self._pos = len(self._buffer[self._line]) - 1

    def eof(self) -> bool:
        """
        Is the input consumed

        :return: at end of file
        """
        return self._eof and (
                self._line >= len(self._buffer) or  # Special for empty input
                (self._line + 1 == len(self._buffer) and
                 self._pos == len(self._buffer[self._line])))

    def at(self) -> str:
        """
        The current location in the input

        :return: At (location) object
        """
        if self.eof():
            return At(self._source_name + ":EOF")
        return At(self._source_name, self._buffer[self._line][0], self._pos)
