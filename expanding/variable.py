import os
from typing import TypeVar

from expanding.source import Reader

_str = TypeVar('_str', str, None)


class Variable(object):
    """
    Variable resolver interface
    """

    def get_name(self, reader: Reader) -> _str:
        """
        Read a name from an input source
        :param reader: the input source
        :return: name of variable, or None if no name could be matched
        """
        raise NotImplemented

    def lookup_variable(self, name: str) -> _str:
        """
        Resolve a givan variable
        :param name: variable name
        :return: resolved variable or None if variable is unknown
        """
        raise NotImplemented


class EnvironmentVariable(Variable):

    def __init__(self, env: dict = os.environ) -> object:
        """
        dictionary resolver

        :param env: dictionary, defaults to ENV
        """
        self._env = env

    def get_name(self, reader: Reader) -> _str:
        """
        Resolve name consisting of a-z A-Z 0-9 _
        :param reader: the input source
        :return: variable name read from input
        """
        name = None
        while True:
            c = reader.get()
            if c is None:
                break
            if name is None and (str.isalnum(c) or c is '_'):
                name = c
            elif str.isalnum(c) or c is '_':
                name = name + c
            else:
                reader.unget()
                break
        return name

    def lookup_variable(self, name: str) -> _str:
        """
        Resolve variable name from dictionary
        :param name: name to look up
        :return: value or None if the variable is unknown
        """
        if name in self._env:
            return self._env[name]
        return None
