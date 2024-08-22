from __future__ import annotations

from typing import TypeVar

T = TypeVar(T)

class _Always:
    def __call__(self, expr: T, /) -> T: ...
    def __enter__(self) -> None: ...
    def __exit__(self, type, value, traceback): ...

always = _Always()
"""
`cohdl.always` creates concurrent logic within an sequential context.

When called, the argument expression is hoisted out of the generated VHDL process
into the concurrent scope. The return value can be used from within the sequential
context.

>>> @std.sequential(clk)
>>> async def example():
>>>     sig <<= cohdl.Signal[Unsigned[4]](0)
>>>     incremented_sig = cohdl.always(sig + 1)
>>>     await std.tick()
>>>     # incremented_sig always follows changes in sig
>>>     assert incremented_sig == 1
>>>     sig <<= 2
>>>     await std.tick()
>>>     # incremented_sig always follows changes in sig
>>>     assert incremented_sig == 2

To implement more than one concurrent statement, `cohdl.always` is passed
to a Python context manager (with statement).

>>> inp_a = Signal[BitVector[8]]()
>>> inp_b = Signal[BitVector[8]]()
>>>
>>> @std.sequential(clk)
>>> async def example()
>>>     with cohdl.always:
>>>         result_and = inp_a & inp_b
>>>         result_or = inp_a | inp_b
>>>
>>>     assert result_and == inp_a & inp_b, "this assertion always holds"
>>>     await some_operation()
>>>     assert result_or == inp_a | inp_b, "so does this one"
"""

def expr(expr, /):
    """
    `expr` is used to hand an entire expression to the `await` operator.
    This is only possible in synthesizable contexts.

    ---
    Example:
    wait until one of two Signals becomes true

    a, b = Signal[Bit](), Signal[Bit]()

    ---
    `await a | b`
    this does not work because the await operator has higher precedence than the bitor operator
    i.e. Python evaluates it as `(await a) | b`

    ---
    `await (a | b)`
    is not allowed because await acts on the result of a|b
    and not the expression itself

    ---
    `await expr(a | b)`
    this works, the execution continues once a|b evaluates to true
    """

def expr_fn(fn, /):
    """
    When a function is decorated with `expr_fn` each call acts as if it
    were wrapped in a call to `expr`. This has no effect except when
    the result is used as the argument of an await expression.
    """

def evaluated() -> bool:
    """
    This function returns True when evaluated in a synthesizable context.
    When called in normal python code False is returned.
    """

def static_assert(cond: bool, msg: str | None = None) -> None: ...
