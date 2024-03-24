from __future__ import annotations

from types import TracebackType

from .source_location import SourceLocation


class VirtualFrame:
    def __init__(
        self, location: SourceLocation, scope: dict, parent: VirtualFrame | None = None
    ):
        self._location = location
        self._scope = scope
        self._parent = parent

    def location(self):
        # define location as a function so it can be overwritten
        return self._location

    def ignore(self, prev: VirtualFrame) -> bool:
        return prev.location() == self.location()

    def _add_single(
        self,
        prev: VirtualFrame | None = None,
        prev_tb: TracebackType | None = None,
    ):
        # helper function to insert stack frames from traced python code
        # to the exception traceback

        if prev is not None:
            if self.ignore(prev):
                return prev_tb

        loc = self.location()

        function_name = loc.function if loc.function is not None else "UNKNOWN_FUNCTION"

        # It is not possible to construct the python builtin FrameType from
        # user code. As a workaround we create a fake by constructing a string of python code
        # that contains a function with the same name. The fake function raises an assertion
        # so we can extract the frame object after a call to `exec`.
        code_str = f"def {function_name}():\n\traise AssertionError('dummy')\n{function_name}()\n"

        compiled_fn = compile(code_str, filename=loc.file, mode="exec")

        try:
            # Use the fake function of create a frame object with the correct
            # function name, line number, filename and local/global variables
            exec(compiled_fn, self._scope)
        except BaseException as dummy_err:
            new_frame = dummy_err.__traceback__.tb_next.tb_next.tb_frame

            for name, val in self._scope.items():
                new_frame.f_locals[name] = val

            return TracebackType(prev_tb, new_frame, 1, loc.line)

    def apply_to_exception(self, exception: Exception, extend=False):
        """
        Replaces the existing traceback of the given `exception` with one
        constructed from this virtual frame.
        When `extend` is set to true the existing traceback is not discarded.
        Instead the virtual traceback is added to it.
        """

        current_frame = self
        prev_frame = None

        if extend:
            custom_tb = exception.__traceback__
        else:
            custom_tb = None

        while current_frame is not None:
            custom_tb = current_frame._add_single(prev_frame, custom_tb)
            prev_frame = current_frame
            current_frame = current_frame._parent

        exception.__traceback__ = custom_tb

    def relative(self, offset: int, parent=None):
        return VirtualFrame(
            self.location().relative(offset),
            self._scope,
            self if parent is None else parent,
        )
