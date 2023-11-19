from cohdl._core import Bit, BitVector, Signal

from ._context import SequentialContext

import enum

class Baud(enum.IntEnum):
    """
    Enumeration of common uart baud rates
    """

    BAUD_110 = 110
    BAUD_300 = 300
    BAUD_600 = 600
    BAUD_1200 = 1200
    BAUD_2400 = 2400
    BAUD_4800 = 4800
    BAUD_9600 = 9600
    BAUD_14400 = 14400
    BAUD_19200 = 19200
    BAUD_38400 = 38400
    BAUD_57600 = 57600
    BAUD_115200 = 115200
    BAUD_128000 = 128000

class Parity(enum.Enum):
    NONE = enum.auto()
    EVEN = enum.auto()
    ODD = enum.auto()

class UartSender:
    def __init__(
        self,
        ctx: SequentialContext,
        tx: Signal[Bit],
        baud: int | Baud,
        bits: int = 8,
        stop_bits: int = 1,
        parity: Parity = Parity.NONE,
    ):
        """
        Check std.Uart for a documentation of the parameters.
        """
    async def send(self, data: BitVector):
        """
        Wait until uart transmitter is ready and send
        one word of data
        """

class UartReceiver:
    def __init__(
        self,
        ctx: SequentialContext,
        rx: Signal[Bit],
        baud: int | Baud,
        bits: int = 8,
        stop_bits=1,
        debounce: float | None = None,
        parity: Parity = Parity.NONE,
    ):
        """
        Check std.Uart for a documentation of the parameters.
        """
    def data_valid(self) -> bool:
        """
        Returns true when the UartReceiver received new data
        since the last call to clear_data or receive.
        """
    def clear_data(self):
        """ """
    def data(self) -> BitVector:
        """
        Return the last received data word.
        Only allowed when `data_valid()` returns true.
        """
    async def receive(self) -> BitVector:
        """
        Wait until new data is received and return it.
        """

class Uart:
    def __init__(
        self,
        ctx: SequentialContext,
        rx: Signal[Bit],
        tx: Signal[Bit],
        baud: int | Baud,
        bits: int = 8,
        stop_bits=1,
        debounce: float | None = None,
        parity: Parity = Parity.NONE,
    ):
        """
        Initialized a sender and a receiver with the same properties.

        :ctx:       Source of clocks and reset of the Uart logic.
                      The clock must have a defined frequency.
        :rx:        Signal with outgoing uart data
        :tx:        Signal with incoming uart data
        :baud:      baud rate
        :bits:      number of bits per word
        :stop_bits: number of stop bits
        :debounce:  When set the rx signal is debounced with a low pass filter.
                      The value defines the duration for a state change of the output
                      relative to a singe bit. Should be less than 0.5.
        :parity:    parity mode
        """

        self.sender: UartSender
        self.receiver: UartReceiver
