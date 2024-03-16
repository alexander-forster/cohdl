from __future__ import annotations

from typing import Any, TypeVar, Generic, NoReturn, Self
import enum

from cohdl import Null, Signal, BitVector, Unsigned, Signed
from cohdl import std

from cohdl.std._context import SequentialContext

from ..utility import SyncFlag

W = TypeVar("W")

# offset
OFF = TypeVar("OFF")
# type
T = TypeVar("T")
# default
D = TypeVar("D")

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

    class Access(enum.Enum):
        na = enum.auto()
        r = enum.auto()
        w = enum.auto()
        w1 = enum.auto()
        rw = enum.auto()
        rw1 = enum.auto()

    class HwAccess(enum.Enum):
        na = enum.auto()
        r = enum.auto()
        w = enum.auto()
        rw = enum.auto()

    class RegisterObject(std.Template[GenericArg]):
        """

        Customization points:

        _config_
            Used to initialize the RegisterObject.
            Needed because __init__ is reserved for internal use
            by the register implementation.

        _impl_
        _impl_sequential_
        _impl_concurrent_
            Used to implement the behavior of the RegisterObject.

        _basic_read_
        _basic_write_
            These methods connect the register implementation defined
            above to the generic register interface.
        """

        _register_tools_: type[RegisterTools]
        _global_offset_: int
        _word_count_: int

        _readable_: bool = True
        _writable_: bool = True

        def _global_word_offset_(self) -> int: ...
        def _implement_synthesizable_contexts_(self, ctx: SequentialContext):
            """
            This method is used by the address bus implementation to
            instantiate the register object.

            It should never be called from user code.
            """

        def _config_(self, *args, **kwargs):
            """
            Classes derived from `RegisterObject` can override this method to configure
            objects after they have been initialized. If a `RegisterObject` overrides this method
            but does not call it during `AddrMap._config_` it will be called without
            any arguments to provide a default configuration.
            """

        def _impl_(self, ctx: std.SequentialContext) -> None:
            """
            Called by the bus master to implement register object behavior.
            `ctx` is the context of the bus clock.
            """

        def _impl_sequential_(self) -> None:
            """
            Called by the bus master to implement register object behavior.
            """

        def _impl_concurrent_(self) -> None:
            """
            Called by the bus master to implement register object behavior.
            """

        def __init__(self, parent: RegisterTools.RegFile, name: str): ...
        def _flatten_(self) -> list[RegisterTools.RegisterObject]:
            """
            Returns all register objects contained in a register device.
            """

        def _print_(self, *args, **kwargs): ...
        def _word_width_(self) -> int:
            """
            Returns the number of bits in a register word.
            """

        def _basic_read_(self, addr: Unsigned, meta) -> BitVector:
            """
            This method is called by the bus master for every read access
            to an address in the range covered by this object.

            Can be overwritten with a function or coroutine.

            `addr` is the address used by the hardware read request.

            `meta` exists to pass bus specific meta data.
            Currently always set to None.

            The returned BitVector is used for the read response.
            """

        def _basic_write_(
            self, addr: Unsigned, data: BitVector, mask: std.Mask, meta
        ) -> None:
            """
            This method is called by the bus master for every write access
            to an address in the range covered by this object.

            Can be overwritten with a function or coroutine.

            `addr` is the address used by the hardware write request.

            `data` one word of data received as part of the write request.

            `mask` can be applied to `data` for writes that affect
            only part of a word.

            `meta` exists to pass bus specific meta data.
            Currently always set to None.
            """

        def _info_(self): ...
        def __init_subclass__(cls, readonly=False, writeonly=False): ...

    class RegFile(RegisterObject):
        _member_types_: dict[str, type[RegisterTools[W].RegisterObject]]

        def __init_subclass__(
            cls, *, word_count, readonly=False, writeonly=False
        ) -> None: ...

    class AddrMap(RegFile[0]):
        def __init__(self, *args, **kwargs): ...

    class GenericRegister(RegisterObject):
        """
        Represents a single register word.
        Users can derive from this class an customize the
        read and write behavior by overriding
        the methods `_on_read_` or `_on_write_`.
        """

        _word_count_ = 1

        def _on_read_(self) -> BitVector:
            """
            Customization point for the read behavior of the register.
            By default `cohdl.Null` is returned.

            This method can be overridden with a function or an async-coroutine.
            """

        def _on_write_(self, data: BitVector, mask: std.Mask):
            """
            Customization point for the write behavior of the register.
            By default the received value is discarded.

            This method can be overridden with a function or an async-coroutine.
            """

    #
    #
    #

    class Register(GenericRegister):
        """
        High level abstraction of a single device register word.

        Derive from this class and use the field types described
        below to conveniently access bit fields within the register.

        >>>
        >>> # Defines a register that performs a bitwise or operation
        >>> # of its two low bytes and returns the result via the high byte.
        >>> class OrField(reg32.Register):
        >>>     inp_a: reg32.MemField[7:0]      # MemFields store written values
        >>>     inp_b: reg32.MemField[15:8]     #
        >>>     out:   reg32.Field[31:24]       # Fields to not automatically hold values
        >>>                                     # but can be assigned like signals
        >>>
        >>>     def _config_(self):
        >>>         # optional _config_ method used to
        >>>         # set default value of inp_b to '11111111'
        >>>         self.inp_b._config_(cohdl.Full)
        >>>
        >>>     def _impl_concurrent_(self):
        >>>         self.out <<= self.inp_a.value() | self.inp_b.value()
        >>>
        >>> # Example for FlagField
        >>> # Performs a long running task every time bit 16 is set to '1'.
        >>> # the bit will stay high until the task is done.
        >>> # The api is modeled after std.SyncFlag.
        >>> class FlagExample(reg32.Register):
        >>>     inp:  reg32.MemField[15:0]
        >>>     flag: reg32.FlagField[16]
        >>>
        >>>     async def _impl_sequential_(self):
        >>>         # wait until the flag is set
        >>>         # and clear it once the task is done
        >>>         async with self.flag:
        >>>             await some_long_running_task(self.inp.value())
        >>>
        >>> class CustomReadWrite(reg32.Register):
        >>>     inc_on_read:  reg32.MemUField[7:0]
        >>>     inc_on_write: reg32.MemUField[15:8]
        >>>     normal_mem:   reg32.MemField[31:16]
        >>>
        >>>     def _read_(self):
        >>>         # increments read counter and returns old value
        >>>         self.inc_on_read <<= self.inc_on_read.value() + 1
        >>>         return self
        >>>
        >>>     def _write_(self, value: CustomReadWrite):
        >>>         # only change `inc_on_write`
        >>>         # `inc_on_read` will keep its old value
        >>>         return self(
        >>>             inc_on_write=self.inc_on_write.value() + 1,
        >>>             normal_mem=value.normal_mem
        >>>         )
        >>>
        >>>     # Alternative implementation of _write_ with the same effect
        >>>     # the call operator returns a copy of self with
        >>>     # individual members replaced by objects constructed from the
        >>>     # provided values.
        >>>     def _write_(self, value: CustomReadWrite):
        >>>         # only change `inc_on_write`
        >>>         # `inc_on_read` will keep its old value
        >>>         return value(
        >>>             inc_on_read=self.inc_on_read,
        >>>             inc_on_write=self.inc_on_write.value() + 1
        >>>         )
        >>>
        """

        def __ilshift__(self: Self, source: Self):
            """
            `RegisterObjects` support direct signal assignments.
            """
            return self

        @property
        def next(self) -> NoReturn:
            """
            `next` is a write only property.
            """

        @next.setter
        def next(self: Self, value: Self):
            """
            alternative to the `<<=` operator.
            """

        def _config_(self, default=Null):
            """
            Used provide default values for `MemFields`.
            """

        def __init_subclass__(cls, readonly=None, writeonly=None): ...
        def _on_read_(self: Self) -> Self:
            """
            The return value is serialized into a BitVector and
            sent as part of the read response.
            """

        def _on_write_(self: Self, data: Self) -> Self | None:
            """
            The return value is used to update all `MemFields` and `FlagFields`
            in the register. If no such field exists the return value
            is ignored and may be set to None.
            """

        def __call__(self: Self, **kwargs: Any) -> Self:
            """
            Returns a copy of `self`, the optional keyword arguments
            are used to replace members of the result with `FieldObjects`
            constructed from the provided value.
            """

    class Field(Generic[OFF, T, D]):
        """
        Represents a range of one or more bits in a `Register`.

        Declaring a `Field` has no side effect. It only serves as
        a convenient reference to register bits.
        """

        @classmethod
        def _count_bits_(cls) -> int:
            """
            Part of the standard serialization api.
            See `std.count_bits`.
            """

        @classmethod
        def _from_bits_(cls: type[Self], val: BitVector, qualifier) -> Self:
            """
            Part of the standard serialization api.
            See `std.from_bits`.
            """

        def _to_bits_(self) -> BitVector:
            """
            Part of the standard serialization api.
            See `std.to_bits`.
            """

        def __ilshift__(self, other):
            return self

        def __ixor__(self, other):
            return self

        def __init__(self, value: T, _qualifier_=Signal): ...
        def value(self) -> T:
            """
            returns the current value of the `Field`
            """

    class UField(Field):
        """
        A specialization of `Field` that represents an unsigned
        value instead of a BitVector.
        """

        def __init__(self, value: Unsigned, _qualifier_=Signal): ...
        def value(self) -> Unsigned: ...

    class SField(Field):
        """
        A specialization of `Field` that represents a signed
        value instead of a BitVector.
        """

        def __init__(self, value: Signed, _qualifier_=Signal): ...
        def value(self) -> Signed: ...

    class MemField(Field):
        """
        `MemField` is functionally equivalent to the normal `Field` type.
        The only difference is, that values written to this field are stored.
        """

    class MemUField(UField):
        """
        A specialization of `MemField` that represents an unsigned
        value instead of a BitVector.
        """

    class MemSField(SField):
        """
        A specialization of `MemField` that represents a signed
        value instead of a BitVector.
        """

    class FlagField:
        """
        A single bit field that can be set by the bus master
        and cleared by the cohdl implementation.
        """

        @classmethod
        def _count_bits_(cls) -> int:
            """
            Part of the standard serialization api.
            See `std.count_bits`.
            """

        @classmethod
        def _from_bits_(
            cls, val: BitVector[1], qualifier=std.Value
        ) -> RegisterTools.FlagField:
            """
            Part of the standard serialization api.
            See `std.from_bits`.
            """

        def _to_bits_(self) -> BitVector[1]:
            """
            Part of the standard serialization api.
            See `std.to_bits`.
            """

        def flag(self) -> SyncFlag:
            """
            returns the interal `std.SyncFlag` object
            """

        def set(self) -> None:
            """
            Set the flag to True, usually not called from user
            code. Instead this method is called then a '1' bit is written
            to the corresponding register bit.
            """

        def clear(self) -> None:
            """
            Set the flag to False.
            """

        def is_set(self) -> bool:
            """
            Returns True when the flag is set.
            """

        def is_clear(self) -> bool:
            """
            Returns False when the flag is set.
            """

        async def __aenter__(self): ...
        async def __aexit__(self, val, type, traceback): ...

    class Input(GenericRegister, readonly=True):
        """
        A single read-only register that connects a Signal to the address bus.

        >>>
        >>> # A register device, that provides access to hardware buttons
        >>> # and LEDs.
        >>> class ExampleInOut(reg32.RegFile, word_count=2):
        >>>     reg_btn: reg32.Input[0x0]   # input register at offset 0x00
        >>>     reg_led: reg32.Output[0x4]  # output register at offset 0x04
        >>>
        >>>     def _config_(self, signal_button, signal_led):
        >>>         # connect signal_button to the register
        >>>         self.reg_btn._config_(signal_button)
        >>>         # connect signal_led to the register
        >>>         self.reg_led._config_(signal_led)
        """

        def _config_(
            self,
            signal: Signal[BitVector],
            /,
            offset: int | None = None,
            padding: int | None = None,
            lsbs: bool | None = False,
            msbs: bool | None = False,
        ):
            """
            When the width of the
            """

    class Output(GenericRegister, writeonly=True):
        """
        A single write-only register, that connects a Signal to the address bus.

        See example of `Input`.
        """

        def _config_(self, signal: Signal[BitVector]) -> None: ...

    class Array(RegisterObject):
        """
        A range of register objects of the same type located at equidistant address locations.
        """

        def __len__(self) -> int: ...
        def __getitem__(self, index: int) -> RegisterTools.RegisterObject: ...

    class AddrRange(RegisterObject):
        def _on_read_(self, addr: Unsigned) -> BitVector:
            """
            called on read accesses to the address range

            addr is the global address within the bus address space
            """

        def _on_write_(self, addr: Unsigned, data: BitVector, mask: std.Mask):
            """
            called on write accesses to the address range

            addr is the global address within the bus address space
            """

        def _on_read_relative_(self, addr: Unsigned):
            """
            Equivalent to _on_read_ but the given address is
            relative to the base address of this object.

            Only one of `_on_read_` and `_on_read_relative_` can be specified.
            """

        def _on_write_relative_(self, addr: Unsigned, data: BitVector, mask: std.Mask):
            """
            Equivalent to _on_write_relative_ but the given address is
            relative to the base address of this object.

            Only one of `_on_write_`and `_on_write_relative_` can be specified.
            """

reg32 = RegisterTools[32, 8]
"""
Provides register tools pre-configured with a
word size of 32 bits and 8 bits per byte.
"""

Access = RegisterTools.Access
HwAccess = RegisterTools.HwAccess
