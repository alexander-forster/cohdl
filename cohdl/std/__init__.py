from ._compile import VhdlCompiler
from ._assignable_type import (
    AssignableType,
    make_qualified,
    make,
    make_nonlocal,
    make_signal,
    make_variable,
)


from ._context import (
    concurrent,
    sequential,
    block,
    Clock,
    ClockEdge,
    Reset,
    Frequency,
    Period,
    Duration,
    Context,
    SequentialContext,
    concurrent_assign,
    concurrent_call,
    concurrent_eval,
    Executor,
    ExecutorMode,
)


ms = Duration.milliseconds
us = Duration.microseconds
ns = Duration.nanoseconds
ps = Duration.picoseconds

kHz = Frequency.kilohertz
MHz = Frequency.megahertz
GHz = Frequency.gigahertz

from . import axi

from . import utility
from .utility import (
    nop,
    comment,
    fail,
    tc,
    base_type,
    instance_check,
    subclass_check,
    iscouroutinefunction,
    as_awaitable,
    add_entity_port,
    zeros,
    ones,
    width,
    one_hot,
    reverse_bits,
    is_qualified,
    const_cond,
    check_type,
    select,
    choose_first,
    cond,
    check_return,
    tick,
    wait_for,
    wait_forever,
    Waiter,
    binary_fold,
    concat,
    stretch,
    apply_mask,
    as_bitvector,
    rol,
    ror,
    lshift_fill,
    rshift_fill,
    batched,
    select_batch,
    stringify,
    DelayLine,
    delayed,
    debounce,
    max_int,
    int_log_2,
    is_pow_two,
    InShiftRegister,
    OutShiftRegister,
    continuous_counter,
    ToggleSignal,
    ClockDivider,
    SyncFlag,
    Mailbox,
    Fifo,
)

from ._fixed import SFixed, UFixed, FixedOverflowStyle, FixedRoundStyle
from ._prefix import prefix, name
from . import spi
from . import bitfield
from . import _crc as crc
