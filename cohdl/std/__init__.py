from ._compile import VhdlCompiler
from ._assignable_type import (
    AssignableType,
    make_qualified,
    make,
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
    concurrent_assign,
    concurrent_call,
    concurrent_eval,
    Executor,
    ExecutorMode,
)


ms = Period.milliseconds
us = Period.microseconds
ns = Period.nanoseconds
ps = Period.picoseconds

kHz = Frequency.kilohertz
MHz = Frequency.megahertz
GHz = Frequency.gigahertz

from . import axi

from . import utility
from .utility import (
    nop,
    comment,
    tc,
    instance_check,
    subclass_check,
    iscouroutinefunction,
    as_awaitable,
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
    wait_for,
    binary_fold,
    concat,
    stretch,
    apply_mask,
    as_bitvector,
    max_int,
    int_log_2,
    InShiftRegister,
    OutShiftRegister,
    continuous_counter,
    ToggleSignal,
)

from ._fixed import SFixed, UFixed, FixedOverflowStyle, FixedRoundStyle
from ._prefix import prefix, name
from . import spi
from . import bitfield
