def always(expr, /):
    return expr

def evaluated() -> bool:
    """
    This function returns True when evaluated in a synthesizable context.
    When called in normal python code False is returned.
    """

def static_assert(cond: bool, msg: str | None = None) -> None: ...
