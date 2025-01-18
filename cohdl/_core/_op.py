"""
Defines functions that invoke operators that are usable
in synthesizable contexts.

The Python builtin module `operator` cannot be used
for this purpose because the CoHDL compiler cannot trace
the implementation of builtin functions.

This module also provides the `rem` (remainder) function
that exists in VHDL but has no corresponding Python operator
and `truncdiv` which is a VHDL compatible replacement
for `floordiv`.
"""


def lt(a, b, /):
    return a < b


def le(a, b, /):
    return a <= b


def eq(a, b, /):
    return a == b


def ne(a, b, /):
    return a != b


def ge(a, b, /):
    return a >= b


def gt(a, b, /):
    return a > b


# Logical Operations **********************************************************#


def not_(a, /):
    return not a


def is_(a, b, /):
    return a is b


def is_not(a, b, /):
    return a is not b


# Mathematical/Bitwise Operations *********************************************#


def add(a, b, /):
    return a + b


def and_(a, b, /):
    return a & b


def inv(a, /):
    return ~a


def lshift(a, b, /):
    return a << b


def mod(a, b, /):
    return a % b


def rem(a, b, /):
    """
    Does not exist as an operator in Python
    but is available in VHDL so we special case it here.
    """

    if isinstance(a, int) and isinstance(b, int):
        return a - b * int(a / b)
    else:
        if hasattr(a, "_cohdl_rem_"):
            rem_result = a._cohdl_rem_(b)

            if rem_result is NotImplemented:
                return b._cohdl_rrem_(a)
            else:
                return rem_result
        else:
            return b._cohdl_rrem_(a)


def truediv(a, b, /):
    return a / b


def floordiv(a, b, /):
    return a // b


def truncdiv(a, b, /):
    """
    Represents the division operator '/' in VHDL.
    It is distinct from floordiv (Pythons '//') because the rounding behavior
    for negative results differs.
    """

    if isinstance(a, int) and isinstance(b, int):
        # explicitly handle integer division
        return int(a / b)
    else:
        if hasattr(a, "_cohdl_truncdiv_"):
            rem_result = a._cohdl_truncdiv_(b)

            if rem_result is NotImplemented:
                return b._cohdl_rtruncdiv_(a)
            else:
                return rem_result
        else:
            return b._cohdl_rtruncdiv_(a)


def mul(a, b, /):
    return a * b


def matmul(a, b, /):
    return a @ b


def neg(a, /):
    return -a


def or_(a, b, /):
    return a | b


def pos(a, /):
    return +a


def pow(a, b, /):
    return a**b


def rshift(a, b, /):
    return a >> b


def sub(a, b, /):
    return a - b


def xor(a, b, /):
    return a ^ b
