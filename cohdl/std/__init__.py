from ._compile import VhdlCompiler
from ._assignable_type import AssignableType

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

from ._core_utility import (
    nop,
    comment,
    as_pyeval,
    fail,
    identity,
    assign,
    regenerate_defaults,
    Ref,
    Value,
    Signal,
    Variable,
    Temporary,
    Nonlocal,
    NoresetSignal,
    NoresetVariable,
    base_type,
    instance_check,
    subclass_check,
    iscouroutinefunction,
    as_awaitable,
    zeros,
    ones,
    width,
    one_hot,
    is_one_hot,
    reverse_bits,
    is_qualified,
    const_cond,
    check_type,
    select,
    choose_first,
    cond,
    to_bits,
    from_bits,
    count_bits,
    check_return,
    binary_fold,
    batched_fold,
    concat,
    repeat,
    stretch,
    leftpad,
    rightpad,
    pad,
    apply_mask,
    Mask,
    as_bitvector,
    rol,
    ror,
    lshift_fill,
    rshift_fill,
    batched,
    select_batch,
    minimum,
    maximum,
    min_element,
    max_element,
    min_index,
    max_index,
    count,
    count_set_bits,
    count_clear_bits,
    clamp,
)

from . import utility
from .utility import (
    add_entity_port,
    OpenEntity,
    ConnectedEntity,
    Serialized,
    as_readable_vector,
    as_writeable_vector,
    Array,
    tick,
    wait_for,
    wait_forever,
    Waiter,
    stringify,
    DelayLine,
    delayed,
    debounce,
    max_int,
    int_log_2,
    ceil_log_2,
    is_pow_two,
    InShiftRegister,
    OutShiftRegister,
    continuous_counter,
    ToggleSignal,
    ClockDivider,
    SyncFlag,
    Mailbox,
    Fifo,
    StackMode,
    Stack,
)

from ._fixed import SFixed, UFixed, FixedOverflowStyle, FixedRoundStyle
from ._prefix import prefix, name, NamedQualifier
from . import spi
from . import bitfield
from . import _crc as crc
from . import uart

from ._template import Template, TemplateArg
from ._record import Record
from .enum import Enum, FlagEnum

from . import _exception as exception
