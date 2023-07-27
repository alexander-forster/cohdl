from __future__ import annotations

from typing import TypeVar, Coroutine

def _intrinsic(fn):
    return fn

def comment(*lines: str) -> None:
    """
    Inserts a comment into the generated VHDL representation.

    std.comment("Hello, world!", "A", "B") is translated into

    `-- Hello, world!`

    `-- A`

    `-- B`
    """

Option = TypeVar("Option")
Result = TypeVar("Result")

def select_with(
    arg, branches: dict[Option, Result], default: Result | None = None
) -> Result:
    if arg in branches:
        return branches[arg]

    return default

#
#
#

def coroutine_step(coro: Coroutine) -> None:
    """
    This function is the core of cohdls coroutine support

    The cohdl compiler translates the given coroutine into
    a HDL statemachine and inserts it at the location of
    the call to `coroutine_step`.

    This has the effect, that the statemachine advances
    each time `coroutine_step` is "called" at runtime.
    """

class sensitivity:
    @staticmethod
    def list(*args) -> None:
        """
        this function is used in sequential contexts
        the compiler adds the arguments (which have to be
        signals) to the sensitivity list of the generated hdl process
        """
    @staticmethod
    def all() -> None:
        """
        this function is used in sequential contexts
        when the compiler encounters this function it
        adds all signals, that are read in the context
        to the sensitivity list of the generated hdl process
        """

#
#
#

def reset_context() -> None:
    """
    This function can only be used in sequential contexts.

    When the cohdl compiler encounters a call to `reset_context`
    it inserts default assignments for all Signals, Variables and Ports that
    have a defined default value and are driven somewhere in the enclosing context
    """

def reset_pushed() -> None:
    """
    `reset_pushed` is similar to `reset_context`. The only difference is,
    that only Ports/Signals using the push assignment mode (`^=` operator) are considered.

    Within a sequential context, that does not call `reset_pushed`
    push assignments are functionally equivalent to signal assignment.
    """

#
#
#

def rising_edge(_) -> bool: ...
def falling_edge(_) -> bool: ...
def high_level(_) -> bool: ...
def low_level(_) -> bool: ...
