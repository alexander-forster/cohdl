from ._compile import VhdlCompiler
from ._assignable_type import AssignableType

from ._prescaler import Prescaler, moving_average, duty_cycle, ClockDivider
from ._uart import UartReceiver, UartTransmitter

from ._context import (
    concurrent,
    sequential,
    block,
    Clock,
    ClockEdge,
    Reset,
    Frequency,
    Period,
)

Duration = Period

ms = Period.milliseconds
us = Period.microseconds
ns = Period.nanoseconds
ps = Period.picoseconds

kHz = Frequency.kilohertz
MHz = Frequency.megahertz
GHz = Frequency.gigahertz

from . import axi
from .sequential_context import SeqContext

from . import utility
from .utility import tc, instance_check, subclass_check, iscouroutinefunction
from .utility import check_type, select, choose_first, cond, check_return

from ._fixed import SFixed, UFixed, FixedOverflowStyle, FixedRoundStyle
