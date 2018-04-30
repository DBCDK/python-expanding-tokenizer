import os
from typing import TypeVar

_str = TypeVar('_str', str, None)

class Variable(object):

    def get_name(self, reader) -> _str:
        raise NotImplemented

    def lookup_variable(self, var_name) -> _str:
        raise NotImplemented


class EnvironmentVariable(Variable):

    def __init__(self, env: object = os.environ) -> object:
        self._env = env

    def get_name(self, reader) -> _str:
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

    def lookup_variable(self, var_name) -> _str:
        if var_name in self._env:
            return self._env[var_name]
        return None
