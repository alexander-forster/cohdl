from __future__ import annotations


class TextBlock:
    def __init__(
        self,
        content: str | TextBlock | list[str | TextBlock],
        *,
        title=None,
        indent=False,
        trailer=None,
    ):
        self._title = title
        self._indent = indent if title is None else True
        self._trailer = trailer

        self._content = []
        self.add(content)

    def add(self, elem: str | TextBlock | list[str | TextBlock]):
        if isinstance(elem, list):
            for i in elem:
                self.add(i)
        else:
            assert isinstance(elem, (str, TextBlock))
            self._content.append(elem)

    def _dump_impl(self, indent, step=2):
        result = []

        initial_indent = indent

        if self._title is not None:
            result.append(indent + self._title)

        if self._indent:
            indent = indent + " " * step

        for elem in self._content:
            if isinstance(elem, str):
                result.append(indent + elem)
            else:
                result.extend(elem._dump_impl(indent, step))

        if self._trailer is not None:
            result.append(initial_indent + self._trailer)

        return result

    def dump(self, indent="", step=2):
        return "\n".join(self._dump_impl(indent, step))

    def __str__(self):
        return self.dump()

    def __repr__(self) -> str:
        return self.dump()


class IndentBlock(TextBlock):
    def __init__(self, content: str | TextBlock | list[str | TextBlock], *, title=None):
        super().__init__(content, title=title, indent=True)
