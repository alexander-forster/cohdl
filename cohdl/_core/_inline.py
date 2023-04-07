from __future__ import annotations

from cohdl._core._intrinsic import _intrinsic


class InlineCode:
    expr_type = None

    class Node:
        ...

    class Text(Node):
        def __init__(self, text: str):
            self.text = text

    class Object(Node):
        def __init__(self, obj, read: bool):
            self.obj = obj
            self.read = read

    class SubCode(Node):
        def __init__(self, options: list[InlineCode]) -> None:
            self.options = options

    def __init__(self, content: list[InlineCode.Node]):
        self.content = content

    def copy(self):
        return type(self)(self.obj, self.read)

    def post_process(self, text):
        return text

    @_intrinsic
    def __class_getitem__(cls, _expr_type):
        class _Inline(cls):
            expr_type = _expr_type

        return _Inline


class InlineRaw(InlineCode):
    ...


class InlineVhdl(InlineCode):
    ...
