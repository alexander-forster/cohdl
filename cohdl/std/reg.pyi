from __future__ import annotations

from typing import TypeVar, Generic, NoReturn

from cohdl import Null, Signal, BitVector, Unsigned, Signed
from cohdl import std
from cohdl._core import AssignMode

from cohdl.std._context import SequentialContext

from .utility import SyncFlag

W = TypeVar("W")

class GenericArg:
    offset: int
    end: int
    array_step: int

class RegisterTools(Generic[W]):
    _word_width_: int
    """
    Number of bits in a register word.
    All reads and writes are performed using data vectors of this width.
    All reads and writes are word aligned.
    """

    _addr_unit_width_: int = 8
    """
    `_word_width_` must be an integer multiple of this value.
    """

    _word_stride_: int
    """
    Number of addressable units per word.
    Calculated from `_word_width_` and `_addr_unit_width_`.
    """

    Field = std.bitfield.Field

    class RegisterObject(std.Template[GenericArg]):
        _register_tools_: type[RegisterTools]
        _generic_arg_: GenericArg
        _global_offset_: int
        _parent_offset_: GenericArg.offset
        _global_word_offset_: int
        _word_count_: int

        _readable_: bool = True
        _writable_: bool = True

        def _implement_synthesizable_contexts_(self, ctx: SequentialContext):
            """
            This method is used by the address bus implementation to
            instantiate the register object.

            It should never be called from user code.
            """

        def __init__(self, parent: RegisterTools.RegisterDevice, name: str): ...
        def _flatten_(self) -> list[RegisterTools.RegisterObject]: ...
        def _print_(self, *args, **kwargs): ...
        def _word_width_(self) -> int: ...
        def _basic_read_(self, addr: Unsigned, meta) -> BitVector: ...
        def _basic_write_(
            self, addr: Unsigned, data: BitVector, mask: BitVector, meta
        ): ...
        def _info_(self): ...
        def __init_subclass__(cls, readonly=False, writeonly=False): ...
        def _config_(self, *args, **kwargs):
            """
            Classes derived from `RegisterObject` can override this method to configure
            objects after they have been initialized. If a `RegisterObject` overrides this method
            but does not call it during `RootDevice._config_` it will be called without
            any arguments to provide a default configuration.
            """

    class RegisterDevice(RegisterObject):
        _member_types_: dict[str, type[RegisterTools[W].RegisterObject]]
        def _impl_(self, ctx: std.SequentialContext) -> None: ...
        def _impl_sequential_(self) -> None: ...
        def _impl_concurrent_(self) -> None: ...
        def __init_subclass__(
            cls, *, word_count, readonly=False, writeonly=False
        ) -> None: ...

    class RootDevice(RegisterDevice[0]):
        def __init__(self, *args, **kwargs): ...

    class GenericRegister(RegisterObject):
        _word_count_ = 1

        def _on_read_(self) -> BitVector: ...
        def _on_write_(self, data, mask):
            pass

    #
    #
    #

    class Field:
        @classmethod
        def _count_bits_(cls) -> int: ...
        @classmethod
        def _from_bits_(cls, val, qualifier): ...
        def _to_bits_(self) -> BitVector: ...
        def __ilshift__(self, other):
            return self

        def __ixor__(self, other):
            return self

        def __init__(self, value: BitVector, _qualifier_=Signal): ...
        def value(self) -> BitVector: ...

    class UField(Field):
        def __init__(self, value: Unsigned, _qualifier_=Signal): ...
        def value(self) -> Unsigned: ...

    class SField(Field):
        def __init__(self, value: Signed, _qualifier_=Signal): ...
        def value(self) -> Signed: ...

    class MemField(Field):
        pass

    class MemUField(UField):
        pass

    class MemSField(SField):
        pass

    class FlagField:
        @classmethod
        def _count_bits_(cls) -> int: ...
        @classmethod
        def _from_bits_(
            cls, val: BitVector[1], qualifier=std.Value
        ) -> RegisterTools.FlagField: ...
        def _to_bits_(self) -> BitVector[1]: ...
        def flag(self) -> SyncFlag: ...
        def set(self) -> None: ...
        def clear(self) -> None: ...
        def is_set(self) -> bool: ...
        def is_clear(self) -> bool: ...

    class Register(GenericRegister):
        _field_types_: dict[str, std.bitfield.FieldBit | std.bitfield.FieldBitVector]

        def __ilshift__(self, source):
            return self

        @property
        def next(self) -> NoReturn: ...
        @next.setter
        def next(self, value): ...
        def _config_(self, default=Null): ...
        def _raw_(self) -> Signal[BitVector]: ...
        def __init_subclass__(cls, readonly=None, writeonly=None): ...

    RW = Register
    """
    a readable and writable register
    alias for `Register`
    """

    class R(Register, readonly=True):
        """
        a read only register
        """

    class W(Register, writeonly=True):
        """
        a write only register
        """

    class Input(GenericRegister, readonly=True):
        def _on_read_(self) -> BitVector: ...
        def _config_(self, signal: Signal[BitVector]) -> None: ...

    class Output(GenericRegister, writeonly=True):
        def _on_write_(self, data: BitVector, mask: BitVector) -> BitVector: ...
        def _config_(self, signal: Signal[BitVector]) -> None: ...

    class Array(RegisterObject):
        def __init__(self, parent: RegisterTools.RegisterDevice): ...
        def __len__(self) -> int: ...
        def __getitem__(self, index: int) -> RegisterTools.RegisterObject: ...

    class AddrRange(RegisterObject):
        async def _on_read_(self, addr: Unsigned): ...
        async def _on_write_(
            self, addr: Unsigned, data: BitVector, mask: BitVector
        ): ...
        async def _on_read_relative_(self, addr: Unsigned): ...
        async def _on_write_relative_(
            self, addr: Unsigned, data: BitVector, mask: BitVector
        ): ...

def register_tools(word_width: int = 32) -> type[RegisterTools]:
    return RegisterTools
