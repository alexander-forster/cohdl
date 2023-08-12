def always(expr, /):
    return expr

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
