from dataclasses import dataclass
import inspect


@dataclass
class SourceLocation:
    file: str | None = None
    line: int | None = None
    function: str | None = None

    def relative(self, offset: int, indent: int | None = None):
        if self.line is None:
            new_line = None
        else:
            new_line = self.line + offset - 1

        if indent is None or self.indent is None:
            return SourceLocation(self.file, new_line)
        return SourceLocation(self.file, new_line, self.indent + indent)

    @staticmethod
    def empty():
        return SourceLocation(None, 0)

    @staticmethod
    def from_function(fn):
        return SourceLocation(inspect.getfile(fn), inspect.getsourcelines(fn)[1])

    def __str__(self):
        if self.function is not None:
            return f"{self.function}:{self.file}:{self.line}"
        else:
            return f"{self.file}:{self.line}"
