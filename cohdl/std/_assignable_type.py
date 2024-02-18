from __future__ import annotations

import cohdl


class AssignableType:
    def _assign_(self, source, mode: cohdl.AssignMode):
        raise AssertionError("_assign_ must be overwritten")

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
