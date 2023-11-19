from __future__ import annotations

import inspect
import typing

from cohdl._core._type_qualifier import (
    TypeQualifierBase,
    TypeQualifier,
    Temporary,
    Signal,
)
from cohdl._core import (
    Bit,
    BitVector,
    Unsigned,
    Array,
    select_with,
    evaluated,
    true,
    false,
    Null,
    Full,
    static_assert,
    concurrent_context,
    expr_fn,
)

from ._assignable_type import make_nonlocal, make_signal

from cohdl._core._intrinsic import _intrinsic

from cohdl._core._intrinsic import comment as cohdl_comment

from ._context import Duration, SequentialContext, concurrent
from ._prefix import prefix, name


# a singleton only used internally in the std module
class _None:
    pass


def nop(*args, **kwargs):
    pass


def comment(*lines):
    cohdl_comment(*lines)


@_intrinsic
def fail(message: str = "", *args, **kwargs):
    raise AssertionError("Compilation failed: " + message.format(*args, **kwargs))


class _TC:
    def __init__(self, T=None) -> None:
        self._T = T

    def __call__(self, arg):
        if self._T is None:
            if isinstance(arg, TypeQualifier):
                assert evaluated(), "expression only allowed in synthesizable contexts"
                return Temporary(arg)
            elif isinstance(arg, TypeQualifierBase):
                return TypeQualifierBase.decay(arg)
            else:
                return arg
        else:
            if isinstance(arg, TypeQualifier):
                assert evaluated(), "expression only allowed in synthesizable contexts"
                return Temporary[self._T](arg)
            elif isinstance(arg, TypeQualifierBase):
                return TypeQualifierBase.decay(arg)
            else:
                return self._T(arg)

    @_intrinsic
    def __getitem__(self, T):
        assert self._T is None, "redefining expression type not allowed"
        return _TC(T)


tc = _TC()

#
#
#


@_intrinsic
def iscouroutinefunction(fn):
    return inspect.iscoroutinefunction(fn)


def base_type(x):
    if isinstance(x, type):
        if issubclass(x, TypeQualifierBase):
            return x.type
        else:
            return x
    else:
        if isinstance(x, TypeQualifierBase):
            return x.type
        else:
            return type(x)


def instance_check(val, type):
    return isinstance(TypeQualifierBase.decay(val), type)


def subclass_check(val, type):
    return issubclass(TypeQualifierBase.decay(val), type)


async def as_awaitable(fn, /, *args, **kwargs):
    if iscouroutinefunction(fn):
        return await fn(*args, **kwargs)
    else:
        return fn(*args, **kwargs)


@_intrinsic
def add_entity_port(entity, port, name: str | None = None):
    if name is None:
        name = port.name()
        assert name is not None, "cannot determine name of new port"

    assert name not in entity._info.ports, f"port '{name}' already exists"

    entity._info.add_port(name, port)
    return port


#
#
#


@_intrinsic
def zeros(len: int):
    return BitVector[len](Null)


@_intrinsic
def ones(len: int):
    return BitVector[len](Full)


@_intrinsic
def width(inp: Bit | BitVector) -> int:
    if instance_check(inp, Bit):
        return 1
    else:
        return inp.width


def one_hot(width: int, bit_pos: int | Unsigned) -> BitVector:
    assert 0 <= bit_pos < width, "bit_pos out of range"
    return (Unsigned[width](1) << bit_pos).bitvector


def reverse_bits(inp: BitVector) -> BitVector:
    return concat(*inp)


#
#
#


def is_qualified(arg):
    return isinstance(arg, TypeQualifierBase)


def const_cond(arg):
    result = bool(arg)
    static_assert(isinstance(result, bool), "condition is not a constant")
    return result


class _UncheckedType:
    pass


def _check_type(result, expected):
    if expected is _UncheckedType:
        return True
    elif expected is None:
        return result is None
    else:
        return instance_check(result, expected)


@_intrinsic
def _format_type_check_error(expected_type, actual_type):
    return f"invalid type in checked expression: expected '{expected_type}' but got '{actual_type}'"


class _TypeCheckedExpression:
    def __init__(self, expected_type: type | tuple = _UncheckedType):
        self._expected = expected_type

    def _checked(self, arg):
        assert _check_type(arg, self._expected), _format_type_check_error(
            self._expected, arg
        )
        return arg

    def __getitem__(self, expected_type):
        return type(self)(expected_type)


class _CheckType(_TypeCheckedExpression):
    def __call__(self, arg):
        assert (
            self._expected is not _UncheckedType
        ), "no type specified in std.check_type"
        return self._checked(arg)


class _Select(_TypeCheckedExpression):
    def __call__(self, arg, branches: dict, default=None):
        return self._checked(
            select_with(
                arg,
                branches,
                default=default,
            )
        )


def _first_impl(*args, default):
    if len(args) == 0:
        return default
    else:
        first, *rest = args
        return first[1] if first[0] else _first_impl(*rest, default=default)


class _ChooseFirst(_TypeCheckedExpression):
    def __call__(self, *args, default):
        return self._checked(_first_impl(*args, default=default))


class _Cond(_TypeCheckedExpression):
    def __call__(self, cond: bool, on_true, on_false):
        return self._checked(on_true if cond else on_false)


check_type = _CheckType()
select = _Select()
choose_first = _ChooseFirst()
cond = _Cond()


@_intrinsic
def _get_return_type_hint(fn):
    return typing.get_type_hints(fn).get("return", _UncheckedType)


def check_return(fn):
    if iscouroutinefunction(fn):

        async def wrapper(*args, **kwargs):
            result = await fn(*args, **kwargs)
            assert _check_type(
                result, _get_return_type_hint(fn)
            ), "invalid return value in function call"
            return result

    else:

        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            assert _check_type(
                result, _get_return_type_hint(fn)
            ), "invalid return value in function call"
            return result

    wrapper.__name__ = fn.__name__
    return wrapper


#
#
#


def binary_fold(fn, args, right_fold=False):
    if len(args) == 1:
        return tc(args[0])
    else:
        if const_cond(right_fold):
            first, *rest = args
            return fn(first, binary_fold(fn, rest, right_fold=True))
        else:
            first, snd, *rest = args
            return binary_fold(fn, [fn(first, snd), *rest])


@_intrinsic
def _batch_args(args: list, batch_size: int):
    batches = []

    for nr in range(0, len(args), batch_size):
        batches.append(args[nr : nr + batch_size])

    print(batches)
    return batches


def batched_fold(fn, args, batch_size=2):
    if const_cond(len(args) <= batch_size):
        return binary_fold(fn, *args)
    else:
        return batched_fold(
            fn,
            *[
                batched_fold(fn, batch, batch_size=batch_size)
                for batch in _batch_args(args, batch_size)
            ],
        )


def _concat_impl(args):
    return binary_fold(lambda a, b: a @ b, args, right_fold=True)


def concat(first, *args):
    if len(args) == 0:
        if instance_check(first, Bit):
            return as_bitvector(first)
        else:
            assert instance_check(first, BitVector)
            return tc[BitVector[len(first)]](first)
    else:
        return _concat_impl([first, *args])


def stretch(val: Bit | BitVector, factor: int):
    if instance_check(val, Bit):
        if const_cond(factor == 1):
            return as_bitvector(val)
        else:
            return concat(*[val for _ in range(factor)])
    elif instance_check(val, BitVector):
        if const_cond(factor == 1):
            return val.bitvector.copy()
        else:
            # reverse stretched list so bit 0 is the leftmost
            # concatenated value
            return concat(*[stretch(b, factor) for b in val][::-1])
    else:
        raise AssertionError("invalid argument")


def apply_mask(old: BitVector, new: BitVector, mask: BitVector):
    assert old.width == new.width
    return (old & ~mask) | (new & mask)


def as_bitvector(inp: BitVector | Bit | str):
    if isinstance(inp, str):
        return BitVector[len(inp)](inp)
    elif instance_check(inp, BitVector):
        return inp.bitvector.copy()
    else:
        assert instance_check(inp, Bit)
        return (inp @ inp)[0:0]


def rol(inp: BitVector, n: int = 1) -> BitVector:
    static_assert(0 <= n <= inp.width)
    if const_cond(n == 0 or n == inp.width):
        return inp.bitvector.copy()
    else:
        return inp.lsb(rest=n) @ inp.msb(n)


def ror(inp: BitVector, n: int = 1) -> BitVector:
    static_assert(0 <= n <= inp.width)
    if const_cond(n == 0 or n == inp.width):
        return inp.bitvector.copy()
    else:
        return inp.lsb(n) @ inp.msb(rest=n)


def lshift_fill(val: BitVector, fill: Bit | BitVector) -> BitVector:
    width_val = width(val)
    width_fill = width(fill)

    if width_fill == width_val:
        return as_bitvector(fill)
    elif width_fill > width_val:
        fail("fill width ({}) exceeds width of value ({})", width_fill, width_val)
    else:
        return val.lsb(width_val - width_fill) @ fill


def rshift_fill(val: BitVector, fill: Bit | BitVector) -> BitVector:
    width_val = width(val)
    width_fill = width(fill)

    if width_fill == width_val:
        return as_bitvector(fill)
    elif width_fill > width_val:
        fail("fill width ({}) exceeds width of value ({})", width_fill, width_val)
    else:
        return fill @ val.msb(width_val - width_fill)


def batched(input: BitVector, n: int) -> list[BitVector]:
    static_assert(len(input) % n == 0)

    return [input[off + n - 1 : off] for off in range(0, len(input), n)]


def select_batch(
    input: BitVector, onehot_selector: BitVector, batch_size: int
) -> BitVector:
    static_assert(len(input) == len(onehot_selector) * batch_size)
    masked = input.bitvector & stretch(onehot_selector, batch_size)

    return binary_fold(lambda a, b: a | b, batched(masked, batch_size))


def parity(vec: BitVector) -> Bit:
    return binary_fold(lambda a, b: a ^ b, vec)


@_intrinsic
def stringify(*args):
    return "".join(str(arg) for arg in args)


class DelayLine:
    def __init__(self, inp, delay: int, initial=_None, ctx: None = None):
        with prefix("delayline"):
            if initial is _None:
                self._steps = [
                    inp,
                    *[
                        make_nonlocal[Signal](
                            base_type(inp), name=name(stringify(n + 1))
                        )
                        for n in range(delay)
                    ],
                ]
            else:
                self._steps = [
                    inp,
                    *[
                        make_nonlocal[Signal](
                            base_type(inp), initial, name=name(stringify(n + 1))
                        )
                        for n in range(delay)
                    ],
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
    assert isinstance(inp, int)
    assert inp > 0
    assert inp.bit_count() == 1
    return inp.bit_length() - 1


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
                    sum = tc[CounterType](cnt_first) + tc[CounterType](cnt_second)
                    assert sum != 0

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
    def __init__(self, *, name="sync_flag"):
        with prefix(name):
            self._tx = Signal[Bit](False, name=_prefix_name("tx"))
            self._rx = Signal[Bit](False, name=_prefix_name("rx"))

    def set(self):
        self._tx <<= ~self._rx

    def clear(self):
        self._rx <<= self._tx

    @expr_fn
    def is_set(self):
        return self._tx != self._rx

    @expr_fn
    def is_clear(self):
        return self._tx == self._rx

    async def receive(self):
        await self.is_set()
        self._rx <<= self._tx
        return self._tx != self._rx

    async def __aenter__(self):
        await self.is_set()

    async def __aexit__(self, val, type, traceback):
        self.clear()


class Mailbox:
    def __init__(self, type, *args, **kwargs):
        self._data = make_signal(type, *args, **kwargs)
        self._flag = SyncFlag()

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


class Fifo:
    def _next_index(self, index):
        if is_pow_two(self._max_index + 1):
            return index + 1
        else:
            return index + 1 if index != self._max_index else 0

    def __init__(self, elem_width: int, depth: int, name="fifo"):
        with prefix(name):
            self._mem = Signal[Array[BitVector[elem_width], depth]](
                name=_prefix_name("mem")
            )
            self._max_index = depth - 1

            self._write_index = Signal[Unsigned.upto(self._max_index)](
                0, name=_prefix_name("wr_index")
            )
            self._read_index = Signal[Unsigned.upto(self._max_index)](
                0, name=_prefix_name("rd_index")
            )

            self._empty = Signal[Bit](name=_prefix_name("empty"))
            self._full = Signal[Bit](name=_prefix_name("full"))

        @concurrent
        def logic():
            self._empty <<= self._write_index == self._read_index
            self._full <<= self._next_index(self._write_index) == self._read_index

    def push(self, data: BitVector):
        assert not self._full, "writing to full fifo"
        self._mem[self._write_index] <<= data
        self._write_index <<= self._next_index(self._write_index)

    def pop(self) -> BitVector:
        assert not self._empty, "reading from empty fifo"
        self._read_index <<= self._next_index(self._read_index)
        return self._mem[self._read_index]

    def front(self):
        return self._mem[self._read_index]

    def empty(self):
        return self._empty

    def full(self):
        return self._full
