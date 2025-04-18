from __future__ import annotations

from ._bit_vector import BitVector
from ._integer import Integer
from ._unsigned import Unsigned

class Signed(BitVector):
    def __init__(
        self,
        val: None | BitVector | str | int = None,
    ): ...
    @classmethod
    def min(self) -> int: ...
    @classmethod
    def max(self) -> int: ...
    def to_int(self) -> int: ...
    def __add__(self, rhs: Signed | int | Integer) -> Signed: ...
    def __radd__(self, lhs: int | Integer) -> Signed: ...
    def __sub__(self, rhs: Signed | int | Integer) -> Signed: ...
    def __rsub__(self, lhs: int | Integer) -> Signed: ...
    def __mul__(self, rhs: Signed | int | Integer) -> Signed: ...
    def __rmul__(self, lhs: Signed | int | Integer) -> Signed: ...
    def _cohdl_truncdiv_(self, rhs: Signed | int | Integer) -> Signed: ...
    def _cohdl_rtruncdiv_(self, lhs: Signed | int | Integer) -> Signed: ...
    def __mod__(self, rhs: Signed | int | Integer) -> Signed: ...
    def __rmod__(self, lhs: Signed | int | Integer) -> Signed: ...
    def _cohdl_rem_(self, rhs: Signed | int | Integer) -> Signed: ...
    def _cohdl_rrem_(self, lhs: Signed | int | Integer) -> Signed: ...
    def __neg__(self) -> Signed: ...
    def __and__(self, other: Signed) -> Signed: ...
    def __or__(self, other: Signed) -> Signed: ...
    def __xor__(self, other: Signed) -> Signed: ...
    def __eq__(self, other: BitVector | int | Integer) -> bool: ...
    def __ne__(self, other: BitVector | int | Integer) -> bool: ...
    def __lt__(self, rhs: Signed | int | Integer) -> bool: ...
    def __gt__(self, rhs: Signed | int | Integer) -> bool: ...
    def __le__(self, rhs: Signed | int | Integer) -> bool: ...
    def __ge__(self, rhs: Signed | int | Integer) -> bool: ...
    def __lshift__(self, rhs: Unsigned | int | Integer) -> Signed: ...
    def __rshift__(self, rhs: Unsigned | int | Integer) -> Signed: ...
    def resize(self, target_width: int | None = None, *, zeros: int = 0) -> Signed: ...
