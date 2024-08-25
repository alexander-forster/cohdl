from __future__ import annotations

import enum

from cohdl._core._type_qualifier import (
    TypeQualifierBase,
    Signal,
)
from cohdl._core import (
    Bit,
    BitVector,
    Unsigned,
    true,
    false,
    Null,
    Full,
    static_assert,
    concurrent_context,
    expr_fn,
    AssignMode,
    always,
    expr,
)

from cohdl._core import Array as CohdlArray

from ._core_utility import (
    Ref,
    _Ref,
    Value,
    nop,
    Nonlocal,
    zeros,
    width,
    concat,
    to_bits,
    from_bits,
    count_bits,
    base_type,
    is_qualified,
    instance_check,
    as_pyeval,
)
from ._template import Template, TemplateArg
from ._assignable_type import AssignableType

from cohdl._core._intrinsic import _intrinsic


from ._context import Duration, SequentialContext, concurrent, at_end_of_context
from ._prefix import prefix, name, NamedQualifier
from ._exception import StdExceptionHandler, RefQualifierFail
from cohdl._core import Entity

std_name = name


# a singleton only used internally in the std module
class _None:
    pass


@_intrinsic
def add_entity_port(entity, port, name: str | None = None):
    if not isinstance(entity, type):
        entity = type(entity)

    assert issubclass(
        entity, Entity
    ), "first argument must be derived from cohdl.Entity"

    if name is None:
        name = port.name()
        assert name is not None, "cannot determine name of new port"

    assert name not in entity._cohdl_info.ports, f"port '{name}' already exists"
    entity._cohdl_info.add_port(name, port)
    setattr(entity, name, port)

    return port


class _EntityConnector:
    def __init__(self, require_inputs: bool, entity_type: type[Entity]):
        self.require_inputs = require_inputs
        self.entity_type = entity_type

    @_intrinsic
    def _gen_port_args(self, kwargs: dict):
        # make sure that the entity was instantiated
        # because new port might be added in the architecture method
        self.entity_type(_cohdl_instantiate_only=True)

        result = {}

        entity_name = self.entity_type._cohdl_info.name
        port_info = self.entity_type._cohdl_info.ports
        generic_info = self.entity_type._cohdl_info.generics

        invalid_args = kwargs.keys() - port_info.keys() - generic_info.keys()
        assert (
            len(invalid_args) == 0
        ), f"invalid arguments for '{self.entity_type}': ({invalid_args})"

        for name, port in port_info.items():
            if name in kwargs:
                result[name] = kwargs[name]
            else:
                if self.require_inputs:
                    assert (
                        port.is_output()
                    ), f"missing connection for input port '{name}'"

                port_type = base_type(port)
                result[name] = Signal[port_type](name=f"con_{entity_name}_{name}")

        return result

    @_intrinsic
    def __getitem__(self, entity_type: type[Entity]):
        assert self.entity_type is None
        assert issubclass(entity_type, Entity)
        return _EntityConnector(self.require_inputs, entity_type)

    def __call__(self, **kwargs):
        assert self.entity_type is not None
        return self.entity_type(**self._gen_port_args(kwargs))


ConnectedEntity = _EntityConnector(require_inputs=False, entity_type=None)
OpenEntity = _EntityConnector(require_inputs=True, entity_type=None)


class _SerializedTemplateArgs:
    elem_type: type

    @_intrinsic
    def __init__(self, elem_type: type):
        assert not isinstance(
            elem_type, Serialized
        ), "Serialized types should not be nested"
        self.elem_type = elem_type

    @_intrinsic
    def __hash__(self):
        return id(self.elem_type)

    @_intrinsic
    def __eq__(self, other: _SerializedTemplateArgs):
        return self.elem_type is other.elem_type


class Serialized(Template[_SerializedTemplateArgs], AssignableType):
    _elemtype_: _SerializedTemplateArgs.elem_type

    @classmethod
    def from_raw(cls, raw: BitVector):
        return cls(raw, _use_as_raw=True)

    def _assign_(self, source, mode: AssignMode) -> None:
        if isinstance(source, Serialized):
            assert (
                self._elemtype_ is source._elemtype_
            ), "elem type of source does not match elem type of target"
            self._raw._assign_(source._raw, mode)
        else:
            self._raw._assign_(to_bits(Value[self._elemtype_](source)), mode)

    def __init__(self, raw=None, _qualifier_=Value, _use_as_raw=False):
        elem_type = self._elemtype_
        bit_count = count_bits(elem_type)

        if _use_as_raw:
            assert (
                bit_count == raw.width
            ), "the number serialized bits ({}) does not match required width ({}) of type '{}'".format(
                raw.width, bit_count, elem_type
            )
            self._raw = raw.bitvector
        else:
            if isinstance(raw, Serialized):
                assert (
                    elem_type is raw._elemtype_
                ), "elem type of source does not match elem type of target"
                self._raw = _qualifier_[elem_type](raw._raw)
            elif raw is Null or raw is Full:
                self._raw = _qualifier_[BitVector[bit_count]](BitVector[bit_count](raw))
            else:
                assert (
                    base_type(raw) is elem_type
                ), "source type does not match elem type of target"
                self._raw = to_bits(raw)

    def value(self, qualifier=Value):
        return from_bits[self._elemtype_](self._raw, qualifier)

    @property
    def ref(self):
        return self.value(qualifier=Ref)

    def bits(self):
        return self._raw


#
#
#


def as_readable_vector(*parts):
    total_width = sum(width(p) for p in parts)

    result = Signal[BitVector[total_width]]()

    @concurrent
    def logic():
        result.next = concat(*parts)

    return result


def as_writeable_vector(*parts, default=None):
    offset = 0
    slice_list = []

    for part in parts:
        if instance_check(part, Bit):
            slice_list.append(part, offset)
            offset += 1
        else:
            w = width(part)
            slice_list.append((part, slice(offset + w - 1, offset)))
            offset += w

    total_width = offset

    result = Signal[BitVector[total_width]](default)

    @concurrent
    def logic():
        for part, slice in slice_list:
            part <<= result[slice]

    return result


#
#
#


class _ArrayNestingMode(enum.Enum):
    NONE = enum.auto()
    COHDL_ARRAY = enum.auto()
    STD_ARRAY = enum.auto()


class _ArrayArgs:
    def __init__(self, args: tuple):
        assert (
            isinstance(args, tuple) and len(args) == 2
        ), "std.Array should be declared like this: std.Array[TYPE, ELEM_CNT]"

        elem_type, elem_cnt = args
        self.elem_type = elem_type
        self.elem_cnt = int(elem_cnt)

        if issubclass(self.elem_type, CohdlArray):
            self.nesting = _ArrayNestingMode.COHDL_ARRAY
        elif issubclass(self.elem_type, Array):
            self.nesting = _ArrayNestingMode.STD_ARRAY
        else:
            self.nesting = _ArrayNestingMode.NONE

    def __hash__(self):
        return hash((self.elem_type, self.elem_cnt))

    def __eq__(self, other: _ArrayArgs):
        return self.elem_type is other.elem_type and self.elem_cnt == other.elem_cnt


@_intrinsic
def _check_array_defaults(defaults: list, elem_width: int):
    for nr, elem in enumerate(defaults):
        assert instance_check(
            elem, BitVector[elem_width]
        ), f"serialized type of default element {nr} ({type(elem)}) does not match type needed for array elements ({BitVector[elem_width]})"


class _ArraySlice(AssignableType):
    @staticmethod
    def _slice_to_indices(inp: slice, max_len: int):
        result = []

        start = inp.start if inp.start is not None else 0
        stop = inp.stop if inp.stop is not None else max_len
        step = inp.step if inp.step is not None else 1

        assert isinstance(start, int), "slice parameters must be integers"
        assert isinstance(stop, int), "slice parameters must be integers"
        assert isinstance(step, int), "slice parameters must be integers"

        if stop == start:
            result.append(start)
        elif stop < start:
            result.extend([*range(start, stop - 1, -1)][::step])
        else:
            result.extend([*range(start, stop + 1)][::step])

        return result

    @_intrinsic
    def __init__(self, arr: Array, s: int | slice | tuple | list, indices_ready=False):
        self._arr = arr

        if indices_ready:
            self._indices = s
        else:
            self._indices = []

            if not isinstance(s, (tuple, list)):
                s = (s,)

            for elem in s:
                if isinstance(elem, slice):
                    self._indices.extend(self._slice_to_indices(elem, len(arr) - 1))
                else:
                    self._indices.append(elem)

            for elem in self._indices:
                if isinstance(elem, int):
                    # check compile time constant indices for validity
                    assert (
                        0 <= elem < len(self._arr)
                    ), f"index {elem} out of allowed range [0-{len(self._arr)-1}]"

    def _getitem_single(self, key: int):
        assert isinstance(
            key, int
        ), "index into array slice must be compile time constant"
        return self._arr.get_elem(self._indices[key])

    @_intrinsic
    def _getitem_multiple(self, key: tuple | list | slice):
        result_keys = []

        for elem in key:
            if isinstance(elem, int):
                result_keys.append(self._indices[elem])
            else:
                assert isinstance(elem, slice)
                result_keys.extend(
                    [
                        self._indices[subindex]
                        for subindex in self._slice_to_indices(
                            elem, len(self._indices) - 1
                        )
                    ]
                )

        return _ArraySlice(self._arr, result_keys, indices_ready=True)

    def __getitem__(self, key):
        if not isinstance(key, (tuple, list, slice)):
            return self._getitem_single(key)
        else:
            return self._getitem_multiple(key)

    @_intrinsic
    def __len__(self):
        return len(self._indices)

    def _assign_(self, source, mode: AssignMode) -> None:
        if isinstance(source, _ArraySlice):
            assert len(self) == len(source), "source width does not match target width"

            for target_index, src_index in zip(self._indices, source._indices):
                self._arr.set_elem(target_index, source._arr[src_index], mode)
        elif source is Null or source is Full:
            for target_index in self._indices:
                self._arr.set_elem(target_index, source, mode)
        elif isinstance(source, dict):
            for idx, elem in source.items():
                self._arr.set_elem(self._indices[idx], elem, mode)
        else:
            assert isinstance(
                source, (Array, CohdlArray, tuple, list)
            ), "invalid source type of assignment"

            assert len(self) == len(source), "source width does not match target width"

            for index, src_elem in zip(self._indices, source):
                self._arr.set_elem(index, src_elem, mode)

    def get_elem(self, index, qualifier=Ref):
        return self._arr.get_elem(self._indices[index], qualifier)

    def set_elem(self, index, value):
        return self._arr.set_elem(self._indices[index], value)


class Array(Template[_ArrayArgs], AssignableType):
    _count_: _ArrayArgs.elem_cnt
    _elemtype_: _ArrayArgs.elem_type
    _nesting_: _ArrayArgs.nesting

    @classmethod
    @_intrinsic
    def _is_nested(cls):
        return issubclass(cls._elemtype_, (Array, CohdlArray))

    @classmethod
    @_intrinsic
    def _underlying_array_type(cls):
        match cls._nesting_:
            case _ArrayNestingMode.NONE:
                elem_type = BitVector[count_bits(cls._elemtype_)]
            case _ArrayNestingMode.COHDL_ARRAY:
                elem_type = cls._elemtype_
            case _ArrayNestingMode.STD_ARRAY:
                elem_type = cls._elemtype_._underlying_array_type()

        return CohdlArray[elem_type, cls._count_]

    def _assign_(self, source, mode: AssignMode) -> None:
        if type(self) is type(source):
            self._content._assign_(source._content, mode)
        elif instance_check(source, (Array, list, tuple, CohdlArray)):
            assert self._count_ == len(
                source
            ), "source width does not match target width"

            for index in range(self._count_):
                self.set_elem(index, source[index], mode)
        elif isinstance(source, _ArraySlice):
            assert self._count_ == len(
                source
            ), "source width does not match target width"

            for index in range(self._count_):
                self.set_elem(index, source._arr[source._indices[index]], mode)

        elif isinstance(source, dict):
            for index, val in source.items():
                self.set_elem(index, val, mode)
        else:
            assert (
                source is Null or source is Full
            ), "invalid argument type for array assignment"

            for index in range(self._count_):
                self.set_elem(index, source, mode)

    def __init__(
        self, val=None, *, name=None, _qualifier_=Signal, attributes=None, _raw_val=None
    ):
        Underlying = self._underlying_array_type()

        if _raw_val is not None:
            # used internally to create a subarray
            assert type(TypeQualifierBase.decay(_raw_val)) is Underlying
            self._content = _raw_val
        elif isinstance(_qualifier_, _Ref) and type(val) is type(self):
            self._content = val._content
        else:

            if val is None or val is Null or val is Full:
                init_val = val
            else:
                assert isinstance(
                    val, (list, tuple, CohdlArray, Array)
                ), "default argument must be a list or a tuple"
                assert (
                    len(val) <= self._count_
                ), "to many default arguments for array ({} > {})".format(
                    len(val), self._count_
                )

                if self._nesting_ is _ArrayNestingMode.COHDL_ARRAY:
                    init_val = val
                else:
                    default_as_elemtype = [
                        (
                            val_elem
                            if isinstance(val_elem, self._elemtype_)
                            else Value[self._elemtype_](val_elem)
                        )
                        for val_elem in val
                    ]

                    if self._nesting_ is _ArrayNestingMode.STD_ARRAY:
                        init_val = [elem._content for elem in default_as_elemtype]
                    else:
                        init_val = [
                            to_bits(default_elem)
                            for default_elem in default_as_elemtype
                        ]

                        _check_array_defaults(init_val, count_bits(self._elemtype_))

            self._content = _qualifier_[Underlying](
                init_val, name=std_name(name), attributes=attributes
            )

    @_intrinsic
    def __len__(self):
        return self._count_

    def get_elem(self, index, qualifier=Ref):
        error_text = [
            "attempt to create a reference to an array element failed, maybe use a value qualifier"
        ]

        with StdExceptionHandler(info=error_text, type=RefQualifierFail):
            if self._nesting_ is _ArrayNestingMode.NONE:
                return from_bits[self._elemtype_](self._content[index], qualifier)
            elif self._nesting_ is _ArrayNestingMode.COHDL_ARRAY:
                return qualifier(self._content[index])
            else:
                return self._elemtype_(_raw_val=qualifier(self._content[index]))

    def set_elem(self, index, value, mode=AssignMode.AUTO):
        if self._nesting_ is _ArrayNestingMode.COHDL_ARRAY:
            self._content[index]._assign_(value, mode)
        elif self._nesting_ is _ArrayNestingMode.STD_ARRAY:
            self._elemtype_(_raw_val=self._content[index])._assign_(value, mode)

            # self._content[index]._assign_(value, mode)
        else:
            b = to_bits(Value[self._elemtype_](value))
            self._content[index]._assign_(b, mode)

    def __getitem__(self, index):
        error_text = [
            "std.Array.__getitem__ only works for trivially serializable types",
            "to fix this, change the element type or use the",
            "methods get_elem and/or set_elem instead of the []-operator.",
            "__getitem__ is also used when iterating over arrays.",
        ]

        with StdExceptionHandler(info=error_text, type=RefQualifierFail):
            if isinstance(index, (slice, tuple, list)):
                return _ArraySlice(self, index)
            else:
                return self.get_elem(index, Ref)

    @classmethod
    @_intrinsic
    def _count_bits_(cls):
        return cls._count_ * count_bits(cls._elemtype_)

    @classmethod
    def _from_bits_(cls, bits, qualifier):
        elem_cnt = cls._count_
        elem_width = count_bits(cls._elemtype_)

        return cls(
            [
                from_bits[cls._elemtype_](
                    bits[elem_width * (nr + 1) - 1 : elem_width * nr]
                )
                for nr in range(elem_cnt)
            ],
            _qualifier_=qualifier,
        )

    def _to_bits_(self):
        return concat(
            *[to_bits(self._content[index]) for index in range(len(self._content))][
                ::-1
            ]
        )


#
#
#


@_intrinsic
def stringify(*args):
    return "".join(str(arg) for arg in args)


class DelayLine:
    def __init__(self, inp, delay: int, initial=_None, ctx: None = None):
        qualifier = NamedQualifier[Nonlocal[Signal], "delayline"][base_type(inp)]

        if initial is _None:
            self._steps = [
                inp,
                *[qualifier() for _ in range(delay)],
            ]
        else:
            self._steps = [
                inp,
                *[qualifier(initial) for _ in range(delay)],
            ]

        def delay_impl():
            for src, target in zip(self._steps, self._steps[1:]):
                target <<= src

        if ctx is not None:

            @ctx
            def process_delay():
                delay_impl()

        else:
            delay_impl()

    def __getitem__(self, delay: int):
        return self._steps[delay]

    def __len__(self):
        return len(self._steps)

    def __iter__(self):
        return iter(self._steps)

    def last(self):
        return self._steps[-1]


def delayed(inp, delay: int, initial=_None):
    return DelayLine(inp, delay, initial=initial).last()


def debounce(
    ctx: SequentialContext,
    inp: Signal[Bit],
    period: int | Duration,
    initial=False,
    allowed_delta=1e-9,
):
    if isinstance(period, Duration):
        period = period.count_periods(ctx.clk().period(), allowed_delta=allowed_delta)

    assert period >= 1, "debounce period to small"

    result = Signal[Bit](initial)
    counter = Signal[Unsigned.upto(period)](period // 2)

    @ctx
    def proc_debounce():
        if inp:
            if counter == period:
                result.next = True
            else:
                counter.next = counter + 1
        else:
            if counter == 0:
                result.next = False
            else:
                counter.next = counter - 1

    return result


#
#
#


@_intrinsic
def max_int(arg: int | Unsigned):
    if isinstance(arg, int):
        return arg
    else:
        return TypeQualifierBase.decay(arg).max_int()


@_intrinsic
def int_log_2(inp: int) -> int:
    assert isinstance(inp, int), "argument must be an integer"
    assert inp > 0, "argument must be larger than 0"
    assert inp.bit_count() == 1, "argument must be a power of 2"
    return inp.bit_length() - 1


@_intrinsic
def ceil_log_2(inp: int) -> int:
    assert isinstance(inp, int), "argument must be an integer"
    assert inp > 0, "argument must be larger than 0"

    if inp.bit_count() == 1:
        return inp.bit_length() - 1
    return inp.bit_length()


@_intrinsic
def is_pow_two(inp: int):
    return inp.bit_count() == 1


@_intrinsic
def _is_one(val):
    x = isinstance(val, int) and val == 1
    return x


async def tick() -> None:
    await true


async def wait_for(duration: int | Unsigned | Duration, *, allow_zero: bool = False):
    if isinstance(duration, Duration):
        ctx = SequentialContext.current()
        assert (
            ctx is not None
        ), "wait_for can only infer the clock in sequential contexts created with a Clock with defined frequency"
        cnt = duration.count_periods(ctx.clk().period())
    else:
        cnt = duration

    if allow_zero:
        if duration == 0:
            return
    else:
        assert (
            cnt > 0
        ), "waiting for 0 ticks only possible when allow_zero is set to True"

    if _is_one(cnt):
        await true
    else:
        counter = Signal[Unsigned.upto(max_int(cnt - 1))](cnt - 1)
        while counter:
            counter <<= counter - 1


async def wait_forever():
    await false


class Waiter:
    @_intrinsic
    def _as_ticks(self, duration: int | Duration):
        if isinstance(duration, int) or instance_check(duration, Unsigned):
            return duration
        ctx = SequentialContext.current()
        return duration.count_periods(ctx.clk().period())

    @_intrinsic
    def _init(self):
        if self._max_duration_cnt is not None:
            return

        self._max_duration_cnt = self._as_ticks(self._max_duration)
        self._duration_cnt = Signal[Unsigned.upto(self._max_duration_cnt)](Null)

    def __init__(self, max_duration: int | Duration):
        self._max_duration = max_duration
        self._max_duration_cnt: int | None = None
        self._duration_cnt: Signal[Unsigned]

    async def wait_for(
        self, duration: int | Unsigned | Duration, *, allow_zero: bool = False
    ):
        self._init()
        cnt = self._as_ticks(duration)

        assert (
            cnt <= self._max_duration_cnt
        ), "duration exceeds max_duration set in constructor"

        if allow_zero:
            if cnt == 0:
                return
        else:
            assert (
                cnt > 0
            ), "waiting for 0 ticks only possible when allow_zero is set to True"

        if _is_one(cnt):
            await true
        else:
            self._duration_cnt <<= cnt - 1
            while self._duration_cnt:
                self._duration_cnt <<= self._duration_cnt - 1


class OutShiftRegister:
    def __init__(
        self, src: BitVector, msb_first=False, unchecked=False, initial_empty=False
    ):
        self._unchecked = unchecked
        self._msb_first = msb_first

        if unchecked:
            self._data = Signal(src, name=name("out_shift_reg"))
        elif initial_empty:
            self._data = Signal[BitVector[src.width]](name="out_shift_reg")
        else:
            if msb_first:
                self._data = Signal(src @ Bit(True), name=name("out_shift_out"))
            else:
                self._data = Signal(Bit(True) @ src, name=name("out_shift_out"))

    def set_data(self, data):
        if self._unchecked:
            self._data <<= data
        else:
            assert len(data) == len(self._data) - 1
            if self._msb_first:
                self._data <<= Signal(data @ Bit(True))
            else:
                self._data <<= Signal(Bit(True) @ data)

    async def shift_all(self, target: Bit | BitVector, shift_delayed=False):
        static_assert(
            not self._unchecked,
            "the shift_all method cannot be used on unchecked shift registers",
        )
        count = target.width if instance_check(target, BitVector) else None

        if not shift_delayed:
            target <<= self.shift(count)

        while not self.empty():
            target <<= self.shift(count)

    def empty(self):
        static_assert(
            not self._unchecked,
            "the empty method cannot be used on unchecked shift registers",
        )
        if self._msb_first:
            return not self._data.lsb(rest=1)
        else:
            return not self._data.msb(rest=1)

    def shift(self, count: int | None = None):
        shift_width = count if count is not None else 1
        assert (
            isinstance(shift_width, int) and shift_width > 0
        ), "count must be a constant positive integer value"

        if self._msb_first:
            after_shift = self._data.lsb(rest=shift_width) @ zeros(shift_width)

            # check, that the marker bit is never shifted out of the extended register
            assert self._unchecked or bool(
                after_shift
            ), "invalid shift, register already empty"
            self._data <<= after_shift
            return self._data.msb(count)
        else:
            after_shift = zeros(shift_width) @ self._data.msb(rest=shift_width)
            assert self._unchecked or bool(
                after_shift
            ), "invalid shift, register already empty"
            self._data <<= after_shift
            return self._data.lsb(count)


class InShiftRegister:
    def __init__(self, len: int, msb_first=False, unchecked=False):
        self._unchecked = unchecked
        self._msb_first = msb_first
        self._len = len

        if unchecked:
            self._data = Signal[BitVector[len]](Null, name=name("in_shift_reg"))
        else:
            if msb_first:
                self._data = Signal(
                    BitVector[len](Null) @ Bit(True), name=name("in_shift_reg")
                )
            else:
                self._data = Signal(
                    Bit(True) @ BitVector[len](Null), name=name("in_shift_reg")
                )

    async def shift_all(self, src: Bit | BitVector, shift_delayed=False):
        static_assert(
            not self._unchecked,
            "the shift_all method cannot be used on unchecked shift registers",
        )

        if not shift_delayed:
            self.shift(src)

        while not self.full():
            self.shift(src)

        return self.data()

    def clear(self):
        if self._unchecked:
            self._data <<= Null
        else:
            if self._msb_first:
                self._data <<= BitVector[self._len](Null) @ Bit(True)
            else:
                self._data <<= Bit(True) @ BitVector[self._len](Null)

    def full(self):
        static_assert(
            not self._unchecked,
            "the full method cannot be used on unchecked shift registers",
        )

        if self._msb_first:
            return self._data.msb().copy()
        else:
            return self._data.lsb().copy()

    def shift(self, src: Bit | BitVector):
        shift_cnt = width(src)

        if self._msb_first:
            assert self._unchecked or not self._data.msb(
                shift_cnt
            ), "invalid shift, register already full"
            self._data <<= self._data.lsb(rest=shift_cnt) @ src
        else:
            assert self._unchecked or not self._data.lsb(
                shift_cnt
            ), "invalid shift, register already full"
            self._data <<= src @ self._data.msb(rest=shift_cnt)

    def data(self):
        if self._unchecked:
            return self._data.copy()
        else:
            if self._msb_first:
                return self._data.lsb(rest=1).copy()
            else:
                return self._data.msb(rest=1).copy()


def continuous_counter(
    ctx: SequentialContext, limit, *, on_change=nop, start_at_limit=False
):
    if max_int(limit) == 0:

        @ctx
        def proc():
            on_change(Unsigned[1](0))

        return Signal[Unsigned[1]](0)
    else:
        if not start_at_limit:
            counter = Signal[Unsigned.upto(max_int(limit))](0, name=name("counter"))

        if start_at_limit:
            assert not is_qualified(limit)
            counter = Signal[Unsigned.upto(max_int(limit))](limit, name=name("counter"))

            def reset_fn():
                counter.next = limit

            ctx = ctx(on_reset=reset_fn)

        @ctx
        def proc():
            nonlocal counter

            if not is_qualified(limit):
                next_value = 0 if counter == limit else (counter + 1)
            else:
                next_value = 0 if counter >= limit else (counter + 1)

            counter <<= next_value
            on_change(next_value)

        return counter


class ToggleSignal:
    def __init__(
        self,
        ctx: SequentialContext,
        first_duration: int | Unsigned | Duration,
        second_duration: int | Unsigned | Duration | None = None,
        *,
        default_state: bool = False,
        first_state: bool = False,
        require_enable: bool = False,
        on_rising=None,
        on_falling=None,
        _prefix="toggle",
    ):
        with prefix(_prefix):
            assert not is_qualified(
                default_state
            ), "default_state must be runtime constant"

            first = first_duration
            second = second_duration if second_duration is not None else first

            if isinstance(first, Duration):
                cnt_first = first.count_periods(ctx.clk().period())
            else:
                cnt_first = first

            if isinstance(second, Duration):
                cnt_second = second.count_periods(ctx.clk().period())
            else:
                cnt_second = second

            if is_qualified(cnt_first) or is_qualified(cnt_second):
                max_counter_end = max_int(cnt_first) + max_int(cnt_second) - 1
                CounterType = Unsigned.upto(max_counter_end)
                counter_end = Signal[CounterType](name="counter_end")

                @concurrent_context
                def logic():
                    sum = Value[CounterType](cnt_first) + Value[CounterType](cnt_second)
                    assert sum != 0, "counter end was set to 0"

                    # cast cnt_first and cnt_second to CounterType
                    # to avoid unsigned overflow
                    counter_end.next = sum - 1

            else:
                counter_end = cnt_first + cnt_second - 1
                assert counter_end >= 0, "toggle period may not be zero"

            self._reset_counter = Signal[Bit](require_enable, name=name("reset"))

            self._state = Signal[Bit](default_state, name=name("state"))
            self._rising = Signal[Bit](False, name=name("rising"))
            self._falling = Signal[Bit](False, name=name("falling"))

            def change_handler(next_cnt):
                if first_state:
                    next_state = next_cnt < cnt_first
                else:
                    next_state = not (next_cnt < cnt_first)

                self._state <<= next_state

                rising = not self._state and next_state
                falling = self._state and not next_state

                self._rising <<= rising
                self._falling <<= falling

                if on_rising is not None and rising:
                    on_rising()
                if on_falling is not None and falling:
                    on_falling()

            continuous_counter(
                ctx.or_reset(self._reset_counter), counter_end, on_change=change_handler
            )

    def get_reset_signal(self):
        return self._reset_counter

    def enable(self):
        self._reset_counter <<= False

    def disable(self):
        self._reset_counter <<= True

    def rising(self):
        return self._rising

    def falling(self):
        return self._falling

    def state(self):
        return self._state


class ClockDivider:
    def __init__(
        self,
        ctx: SequentialContext,
        duration: int | Unsigned | Duration,
        *,
        default_state: bool = False,
        tick_at_start: bool = False,
        require_enable: bool = False,
        on_rising=None,
        on_falling=None,
        _prefix="clkdiv",
    ):
        with prefix(_prefix):
            assert not is_qualified(
                default_state
            ), "default_state must be runtime constant"

            if isinstance(duration, Duration):
                cnt_duration = duration.count_periods(ctx.clk().period())
            else:
                cnt_duration = duration

            if is_qualified(cnt_duration):
                max_counter_end = max_int(cnt_duration) - 1
                CounterType = Unsigned.upto(max_counter_end)
                counter_end = Signal[CounterType](name="counter_end")

                @concurrent_context
                def logic():
                    # cast cnt_first and cnt_second to CounterType
                    # to avoid unsigned overflow
                    counter_end.next = cnt_duration - 1
                    assert cnt_duration >= 1, "clkdiv period must be greater than 1"

            else:
                counter_end = cnt_duration - 1
                assert counter_end >= 1, "clockdiv period must be greater than 1"

            self._reset_counter = Signal[Bit](require_enable, name=name("reset"))

            self._ctx = ctx
            self._state = Signal[Bit](default_state, name=name("state"))
            self._rising = Signal[Bit](False, name=name("rising"))
            self._falling = Signal[Bit](False, name=name("falling"))

            def change_handler(next_cnt):
                next_state = (not default_state) if next_cnt == 0 else default_state

                self._state <<= next_state

                rising = not self._state and next_state
                falling = self._state and not next_state

                self._rising <<= rising
                self._falling <<= falling

                if on_rising is not None and rising:
                    on_rising()
                if on_falling is not None and falling:
                    on_falling()

            continuous_counter(
                ctx.or_reset(self._reset_counter),
                counter_end,
                on_change=change_handler,
                start_at_limit=tick_at_start,
            )

    def get_reset_signal(self):
        return self._reset_counter

    def enable(self):
        self._reset_counter <<= False

    def disable(self):
        self._reset_counter <<= True

    def rising(self):
        return self._rising

    def falling(self):
        return self._falling

    def state(self):
        return self._state


_prefix_name = name


class SyncFlag:
    @_intrinsic
    def _cmp_rx(self):
        if self._rx_delay == 0:
            return self._rx

        ctx = SequentialContext.current()

        if ctx is None or ctx is self._tx_ctx:
            return self._rx

        if ctx is self._rx_ctx:
            return self._set_rx

        if ctx is self._rx_indirect_owner:
            return self._rx_indirect

        at_end_of_context(self._impl_rx_indirect)
        self._rx_indirect = Signal[Bit](name=self._rx_indirect_name)
        self._rx_indirect_owner = ctx
        return self._rx_indirect

    @_intrinsic
    def _cmp_tx(self):
        if self._tx_delay == 0:
            return self._tx

        ctx = SequentialContext.current()

        if ctx is None or ctx is self._rx_ctx:
            return self._tx

        if ctx is self._tx_ctx:
            return self._set_tx

        if ctx is self._tx_indirect_owner:
            return self._tx_indirect

        at_end_of_context(self._impl_tx_indirect)
        self._tx_indirect = Signal[Bit](name=self._tx_indirect_name)
        self._tx_indirect_owner = ctx
        return self._tx_indirect

    async def _impl_rx_indirect(self):
        ctx = SequentialContext.current()

        with always:
            if ctx is self._rx_ctx:
                self._rx_indirect <<= self._set_rx
            else:
                self._rx_indirect <<= self._rx

    async def _impl_tx_indirect(self):
        ctx = SequentialContext.current()

        with always:
            if ctx is self._tx_ctx:
                self._tx_indirect <<= self._set_tx
            else:
                self._tx_indirect <<= self._tx

    async def _impl_tx_delayline(self):
        # delay-1 because assignment to _tx adds one
        self._tx <<= delayed(self._set_tx, self._tx_delay - 1, initial=Null)

    async def _impl_rx_delayline(self):
        # delay-1 because assignment to _rx adds one
        self._rx <<= delayed(self._set_rx, self._rx_delay - 1, initial=Null)

    def _impl_rx_delay(self):
        # rx delay is implemented in tx_ctx

        tx_ctx = SequentialContext.current()

        if self._tx_ctx is None:
            as_pyeval(setattr, self, "_tx_ctx", tx_ctx)

            if self._rx_delay != 0:
                assert (
                    self._rx_ctx is not tx_ctx
                ), "std.SyncFlag with delay cannot be set and cleared in the same context"
                at_end_of_context(self._impl_rx_delayline)

            # return True first time context is detected so
            # higher level abstractions can define additional logic
            return True
        else:
            assert tx_ctx is self._tx_ctx, "std.SyncFlag set in more than one context"
            return False

    def _impl_tx_delay(
        self,
    ):
        # tx delay is implemented in rx_ctx

        rx_ctx = SequentialContext.current()

        if self._rx_ctx is None:
            as_pyeval(setattr, self, "_rx_ctx", rx_ctx)

            if self._tx_delay != 0:
                assert (
                    self._tx_ctx is not rx_ctx
                ), "std.SyncFlag with delay cannot be set and cleared in the same context"
                at_end_of_context(self._impl_tx_delayline)

            # return True first time context is detected so
            # higher level abstractions can define additional logic
            return True
        else:
            assert rx_ctx is self._rx_ctx, "std.SyncFlag set in more than one context"
            return False

    def __init__(self, *, name="sync_flag", delay=None, tx_delay=None, rx_delay=None):
        if delay is not None:
            assert (
                tx_delay is rx_delay is None
            ), "tx_delay/rx_delay cannot be set when delay is specified"
            self._tx_delay = delay
            self._rx_delay = delay
        else:
            self._tx_delay = tx_delay if tx_delay is not None else 0
            self._rx_delay = rx_delay if rx_delay is not None else 0

        with prefix(name) as p:
            self._tx = Signal[Bit](False, name=p.name("tx"))

            if self._tx_delay == 0:
                self._set_tx = self._tx
            else:
                self._set_tx = Signal[Bit](False, name=p.name("set_tx"))

            self._rx = Signal[Bit](False, name=p.name("rx"))

            if self._rx_delay == 0:
                self._set_rx = self._rx
            else:
                self._set_rx = Signal[Bit](False, name=p.name("set_rx"))

            self._tx_ctx = None
            self._rx_ctx = None

            if self._rx_delay != 0 or self._tx_delay != 0:
                self._tx_indirect_name = p.name("tx_indirect")
                self._rx_indirect_name = p.name("rx_indirect")

                self._rx_indirect_owner = None
                self._tx_indirect_owner = None
                self._rx_indirect = None
                self._tx_indirect = None

    def set(self):
        self._impl_rx_delay()
        self._set_tx <<= ~self._rx

    def clear(self):
        self._impl_tx_delay()
        self._set_rx <<= self._tx

    @expr_fn
    def is_set(self):
        return self._cmp_tx() != self._cmp_rx()

    @expr_fn
    def is_clear(self):
        return self._cmp_tx() == self._cmp_rx()

    async def receive(self):
        await self.is_set()
        self.clear()

    async def __aenter__(self):
        await self.is_set()

    async def __aexit__(self, val, type, traceback):
        self.clear()


_MailboxType = TemplateArg.Type


class Mailbox(Template[_MailboxType]):
    _datatype: _MailboxType

    def __init__(self, *, delay=None, tx_delay=None, rx_delay=None):
        with prefix("mailbox"):
            self._data = NamedQualifier[Signal, "data"][self._datatype]()
            self._flag = SyncFlag(delay=delay, tx_delay=tx_delay, rx_delay=rx_delay)

    def send(self, data):
        self._data <<= data
        self._flag.set()

    async def receive(self):
        async with self._flag:
            return self._data

    def data(self):
        return self._data

    @expr_fn
    def is_set(self):
        return self._flag.is_set()

    @expr_fn
    def is_clear(self):
        return self._flag.is_clear()

    def clear(self):
        return self._flag.clear()


#
#
#


class _FifoArgs:
    def __init__(self, arg):
        self.elemtype, self.count = arg
        assert isinstance(self.elemtype, type)
        assert isinstance(self.count, int)

    def __hash__(self) -> int:
        return hash((self.elemtype, self.count))

    def __eq__(self, other: _FifoArgs) -> bool:
        return self.elemtype is other.elemtype and self.count == other.count


class Fifo(Template[_FifoArgs]):
    _elemtype_: _FifoArgs.elemtype
    _count_: _FifoArgs.count

    async def _impl_sync_read_index(self):
        if self._sync_flag.is_clear():
            self._buf_write_index <<= self._set_write_index
            self._read_index <<= self._buf_read_index
            self._sync_flag.set()

    async def _impl_sync_write_index(self):
        if self._sync_flag.is_set():
            self._buf_read_index <<= self._set_read_index
            self._write_index <<= self._buf_write_index
            self._sync_flag.clear()

    @_intrinsic
    def _cmp_full(self):
        if not self._sync_contexts:
            return self._full

        ctx = SequentialContext.current()

        if ctx is None:
            return self._full

        if ctx is self._sync_flag._tx_ctx:
            return self._full_in_sender

        if ctx is self._sync_flag._rx_ctx:
            return self._full_in_receiver

        if ctx is self._full_indirect_owner:
            return self._full_indirect

        at_end_of_context(self._impl_full_indirect)
        self._full_indirect = Signal[Bit](name=self._full_indirect_name)
        return self._full_indirect

    @_intrinsic
    def _cmp_empty(self):
        if not self._sync_contexts:
            return self._empty

        ctx = SequentialContext.current()

        if ctx is None:
            return self._empty

        if ctx is self._sync_flag._tx_ctx:
            return self._empty_in_sender

        if ctx is self._sync_flag._rx_ctx:
            return self._empty_in_receiver

        if ctx is self._empty_indirect_owner:
            return self._empty_indirect

        at_end_of_context(self._impl_empty_indirect)
        self._empty_indirect = Signal[Bit](name=self._empty_indirect_name)
        return self._empty_indirect

    async def _impl_full_indirect(self):
        with always:
            ctx = SequentialContext.current()

            if ctx is self._sync_flag._tx_ctx:
                self._full_indirect <<= self._full_in_sender
            elif ctx is self._sync_flag._rx_ctx:
                self._full_indirect <<= self._full_in_receiver
            else:
                self._full_indirect <<= self._full

    async def _impl_empty_indirect(self):
        with always:
            ctx = SequentialContext.current()

            if ctx is self._sync_flag._tx_ctx:
                self._empty_indirect <<= self._empty_in_sender
            elif ctx is self._sync_flag._rx_ctx:
                self._empty_indirect <<= self._empty_in_receiver
            else:
                self._empty_indirect <<= self._empty

    #
    #
    #

    def _next_index(self, index):
        if is_pow_two(self._max_index + 1):
            return index + 1
        else:
            return index + 1 if index != self._max_index else 0

    @_intrinsic
    def __len__(self):
        return self._count_

    def __init__(self, *, name="fifo", delay=None, rx_delay=None, tx_delay=None):
        count = self._count_
        self._max_index = count - 1
        CounterType = Unsigned.upto(self._max_index)

        if delay is not None:
            assert (
                tx_delay is rx_delay is None
            ), "tx_delay/rx_delay cannot be set when delay is specified"
            self._tx_delay = delay
            self._rx_delay = delay
        else:
            self._tx_delay = tx_delay if tx_delay is not None else 0
            self._rx_delay = rx_delay if rx_delay is not None else 0

        self._sync_contexts = self._rx_delay != 0 or self._tx_delay != 0

        with prefix(name) as p:
            self._mem = Array[self._elemtype_, count](
                name=p.name("mem"), _qualifier_=Signal
            )

            self._write_index = Signal[CounterType](0, name=p.name("wr_index"))
            self._read_index = Signal[CounterType](0, name=p.name("rd_index"))

            self._empty = Signal[Bit](name=p.name("empty"))
            self._full = Signal[Bit](name=p.name("full"))

            if self._sync_contexts:
                self._sync_flag = SyncFlag(
                    name="sync", rx_delay=self._rx_delay, tx_delay=self._tx_delay
                )

                self._set_write_index = Signal[CounterType](
                    0, name=p.name("set_wr_index")
                )

                self._set_read_index = Signal[CounterType](
                    0, name=p.name("set_rd_index")
                )

                self._buf_write_index = Signal[CounterType](
                    0, name=p.name("buf_wr_index")
                )

                self._buf_read_index = Signal[CounterType](
                    0, name=p.name("buf_rd_index")
                )

                self._full_in_sender = Signal[Bit](name=p.name("full_in_sender"))
                self._empty_in_sender = Signal[Bit](name=p.name("empty_in_sender"))
                self._full_in_receiver = Signal[Bit](name=p.name("full_in_receiver"))
                self._empty_in_receiver = Signal[Bit](name=p.name("empty_in_receiver"))

                self._full_indirect_name = p.name("full_indirect")
                self._empty_indirect_name = p.name("empty_indirect")

                self._full_indirect_owner = None
                self._empty_indirect_owner = None

                @concurrent
                def logic():
                    self._full_in_sender <<= (
                        self._next_index(self._set_write_index) == self._read_index
                    )

                    self._empty_in_sender <<= self._set_write_index == self._read_index

                    self._full_in_receiver <<= (
                        self._next_index(self._write_index) == self._set_read_index
                    )

                    self._empty_in_receiver <<= (
                        self._write_index == self._set_read_index
                    )

            else:
                self._set_write_index = self._write_index
                self._set_read_index = self._read_index

        @concurrent
        def logic():
            self._empty <<= self._write_index == self._read_index
            self._full <<= self._next_index(self._write_index) == self._read_index

    def push(self, data):
        if self._sync_contexts:
            if self._sync_flag._impl_rx_delay():
                at_end_of_context(self._impl_sync_read_index)

        assert not self._full, "writing to full fifo"
        self._mem.set_elem(self._set_write_index, data)
        self._set_write_index <<= self._next_index(self._set_write_index)

    def pop(self, *, qualifier=Value):
        if self._sync_contexts:
            if self._sync_flag._impl_tx_delay():
                at_end_of_context(self._impl_sync_write_index)

        assert not self._empty, "reading from empty fifo"
        self._set_read_index <<= self._next_index(self._set_read_index)
        return self._mem.get_elem(self._set_read_index, qualifier)

    def front(self, *, qualifier=Value):
        return self._mem.get_elem(self._set_read_index, qualifier=qualifier)

    def empty(self):
        return self._cmp_empty()

    def full(self):
        return self._cmp_full()

    async def receive(self, *, qualifier=Value):
        await expr(not self.empty())
        return self.pop(qualifier=qualifier)


#
#
#
#
#


class StackMode(enum.Enum):
    NO_OVERFLOW = enum.auto()
    DROP_OLD = enum.auto()


class Stack(Template[_FifoArgs]):
    _elemtype_: _FifoArgs.elemtype
    _count_: _FifoArgs.count

    def _prev_index(self):
        if self._mode is StackMode.NO_OVERFLOW:
            return self._index - 1
        else:
            return (self._count_ - 1) if self._index == 0 else (self._index - 1)

    def _next_index(self):
        if self._mode is StackMode.NO_OVERFLOW:
            return self._index + 1
        else:
            return (self._index + 1) if self._index != self._count_ - 1 else 0

    #
    #
    #

    @_intrinsic
    def __len__(self):
        return self._count_

    def __init__(self, *, name="stack", mode=StackMode.NO_OVERFLOW):
        count = self._count_
        CounterType = Unsigned.upto(count)

        self._mode = mode

        with prefix(name) as p:
            self._mem = Array[self._elemtype_, self._count_](
                name=p.name("mem"), _qualifier_=Signal
            )
            self._index = Signal[CounterType](0, name=p.name("index"))

            if mode is StackMode.DROP_OLD:
                self._cnt = Signal[CounterType](0, name=p.name("cnt"))
            else:
                self._cnt = self._index

    def push(self, data):
        self._mem.set_elem(self._index, data)

        if self._mode is StackMode.DROP_OLD:
            self._cnt <<= self._count_ if self._cnt == self._count_ else (self._cnt + 1)
        else:
            assert self._index < self._count_, "push to full stack"

        self._index <<= self._next_index()

    def pop(self, *, qualifier=Value):
        assert self._cnt != 0, "pop from empty stack"

        if self._mode is StackMode.DROP_OLD:
            self._cnt <<= self._cnt - 1

        prev_index = self._prev_index()
        self._index <<= prev_index
        return self._mem.get_elem(prev_index, qualifier=qualifier)

    def front(self, *, qualifier=Value):
        return self._mem.get_elem(self._prev_index(), qualifier=qualifier)

    def empty(self):
        return self._cnt == 0

    def full(self):
        return self._cnt == self._count_

    def reset(self):
        self._index <<= 0

        if self._mode is StackMode.DROP_OLD:
            self._cnt <<= 0

    def size(self):
        return Value(self._cnt)
