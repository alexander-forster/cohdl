from __future__ import annotations

from typing import TypeVar

def _intrinsic(fn):
    return fn

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

def coroutine_step(coro) -> None: ...

class sensitivity:
    @staticmethod
    def list(*args) -> None: ...
    @staticmethod
    def all() -> None: ...

#
#
#

def reset_context() -> None: ...
def reset_pushed() -> None: ...

#
#
#

def rising_edge(_) -> bool: ...
def falling_edge(_) -> bool: ...
def high_level(_) -> bool: ...
def low_level(_) -> bool: ...
