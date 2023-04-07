from __future__ import annotations

import cohdl


class AssignableType:
    def _assign_(self, source, mode: cohdl.AssignMode):
        raise AssertionError("_assign_ must be overwritten")

    @classmethod
    def _init_qualified_(cls, Qualifier, *args, **kwargs):
        return cls(
            *[Qualifier(arg) for arg in args],
            **{name: Qualifier(kwarg) for name, kwarg in kwargs.items()},
        )

    @classmethod
    def signal(cls, *args, **kwargs):
        return cls._init_qualified_(cohdl.Signal, *args, **kwargs)

    @classmethod
    def variable(cls, *args, **kwargs):
        return cls._init_qualified_(cohdl.Variable, *args, **kwargs)

    def __ilshift__(self, source):
        self._assign_(source, cohdl.AssignMode.NEXT)
        return self

    def __imatmul__(self, source):
        self._assign_(source, cohdl.AssignMode.VALUE)
        return self

    def __ixor__(self, source):
        self._assign_(source, cohdl.AssignMode.PUSH)
        return self

    @property
    def next(self):
        raise AssertionError("next only supported in store context")

    @next.setter
    def next(self, value):
        self <<= value

    @property
    def push(self):
        raise AssertionError("push only supported in store context")

    @push.setter
    def push(self, value):
        self ^= value

    @property
    def value(self):
        raise AssertionError("value only supported in store context")

    @value.setter
    def value(self, value):
        self @= value


class Class:
    def _assign_(self, source, mode: cohdl.AssignMode):
        raise AssertionError("_assign_ must be overwritten")

    @classmethod
    def _from_vector_(cls, vector: cohdl.BitVector):
        raise AssertionError("_from_vector_ must be overwritten")

    def _to_vector_(self):
        raise AssertionError("_to_vector_ must be overwritten")

    @classmethod
    def _init_qualified_(cls, Qualifier, *args, **kwargs):
        return cls(
            *[Qualifier(arg) for arg in args],
            **{name: Qualifier(kwarg) for name, kwarg in kwargs.items()},
        )

    @classmethod
    def signal(cls, *args, **kwargs):
        return cls._init_qualified_(cohdl.Signal, *args, **kwargs)

    @classmethod
    def variable(cls, *args, **kwargs):
        return cls._init_qualified_(cohdl.Variable, *args, **kwargs)

    def __ilshift__(self, source):
        self._assign_(source, cohdl.AssignMode.NEXT)
        return self

    def __imatmul__(self, source):
        self._assign_(source, cohdl.AssignMode.VALUE)
        return self

    def __ixor__(self, source):
        self._assign_(source, cohdl.AssignMode.PUSH)
        return self

    @property
    def next(self):
        raise AssertionError("next only supported in store context")

    @next.setter
    def next(self, value):
        self <<= value

    @property
    def push(self):
        raise AssertionError("push only supported in store context")

    @push.setter
    def push(self, value):
        self ^= value

    @property
    def value(self):
        raise AssertionError("value only supported in store context")

    @value.setter
    def value(self, value):
        self @= value
