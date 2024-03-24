from dataclasses import dataclass
import inspect


@dataclass
class SourceLocation:
    file: str | None
    line: int | None = None
    function: str | None = None

    def relative(self, offset: int):
        if self.line is None:
            new_line = None
        else:
            new_line = self.line + offset - 1

        return SourceLocation(self.file, new_line, self.function)

    @staticmethod
    def from_function(fn):
        return SourceLocation(
            inspect.getfile(fn), inspect.getsourcelines(fn)[1], fn.__name__
        )

    def __str__(self):
        if self.function is not None:
            return f"{self.function}:{self.file}:{self.line}"
        else:
            return f"{self.file}:{self.line}"
