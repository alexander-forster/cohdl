from __future__ import annotations

from cohdl.std._context import SequentialContext
from cohdl.std.axi._axi4_channel import Channel
from cohdl.std._context import ClockEdge, Frequency

from cohdl.std.reg import reg32

import cohdl
from cohdl import Port, Bit, Unsigned, Null, BitVector

from typing import overload
import std

class Axi4Light:
    class RespConstants:
        OKAY = "00"
        EXOKAY = "01"
        SLVERR = "10"
        DECERR = "11"

    class WrAddr(Channel):
        def __init__(
            self, valid: Bit, ready: Bit, awaddr: BitVector, awprot: BitVector, **kwargs
        ):
            super().__init__(valid, ready, awaddr=awaddr, awprot=awprot, **kwargs)

            self.awaddr = awaddr
            self.awprot = awprot

    class WrData(Channel):
        def __init__(
            self, valid: Bit, ready: Bit, wdata: BitVector, wstrb: BitVector, **kwargs
        ):
            super().__init__(valid, ready, wdata=wdata, wstrb=wstrb, **kwargs)

            self.wdata = wdata
            self.wstrb = wstrb

    class WrResp(Channel):
        def __init__(self, valid: Bit, ready: Bit, bresp: BitVector[2], **kwargs):
            super().__init__(valid, ready, bresp=bresp, **kwargs)

            self.bresp = bresp

    class RdAddr(Channel):
        def __init__(
            self, valid: Bit, ready: Bit, araddr: BitVector, arprot: BitVector, **kwargs
        ):
            super().__init__(valid, ready, araddr=araddr, arprot=arprot, **kwargs)

            self.araddr = araddr
            self.arprot = arprot

    class RdData(Channel):
        def __init__(
            self, valid: Bit, ready: Bit, rdata: BitVector, rresp: BitVector, **kwargs
        ):
            super().__init__(valid, ready, rdata=rdata, rresp=rresp, **kwargs)

            self.rdata = rdata
            self.rresp = rresp

    @staticmethod
    def signal(
        clk: std.Clock,
        reset: std.Clock,
        addr_width,
        data_width=32,
        strb_width=4,
        prot_width=3,
        resp_width=2,
        prefix="",
    ) -> Axi4Light: ...
    def __init__(
        self,
        clk: std.Clock,
        reset: std.Clock,
        wraddr: Axi4Light.WrAddr,
        wrdata: Axi4Light.WrData,
        wrresp: Axi4Light.WrResp,
        rdaddr: Axi4Light.RdAddr,
        rddata: Axi4Light.RdData,
    ):
        self.clk = clk
        self.reset = reset
        self.wraddr = wraddr
        self.wrdata = wrdata
        self.wrresp = wrresp
        self.rdaddr = rdaddr
        self.rddata = rddata

    def addr_width(self) -> int: ...
    def data_width(self) -> int: ...
    async def read_word(
        self, addr: BitVector, prot=cohdl.Null
    ) -> tuple[BitVector, BitVector]:
        """
        Perform a read from the given address.
        Returns a tuple of the received rdata and rresp values.
        """

    async def write_word(
        self, addr: BitVector, data: BitVector, strb=cohdl.Full, prot=cohdl.Null
    ) -> BitVector:
        """
        Perform a write to the given address.
        Return the received bresp value.
        """

    class _ReadRequest:
        def __init__(self, addr: BitVector, prot: BitVector):
            self.addr = addr
            self.prot = prot

    async def await_read_request(self) -> _ReadRequest:
        """
        Wait for a read request and return its payload.
        """

    async def send_read_resp(self, data: BitVector, resp=cohdl.Null):
        """
        Generate a read response with the provided payload.
        """

    class _WriteRequest:
        def __init__(
            self, addr: BitVector, prot: BitVector, data: BitVector, strb: BitVector
        ):
            self.addr = addr
            self.prot = prot
            self.data = data
            self.strb = strb

    async def await_write_request(self) -> _WriteRequest:
        """
        Wait for a write request and return its payload.
        """

    async def send_write_response(self, resp=cohdl.Null):
        """
        Send `resp` to the AXI master using the bresp channel.
        """

    def connect_addr_map(self, addr_map: reg32.AddrMap):
        """
        Connect an abstract register definition to the AXI interface.
        """

class _CommonBase(cohdl.Entity):
    axi_clk = Port.input(Bit)
    axi_reset = Port.input(Bit)

    axi_awaddr = Port.input(Unsigned)
    axi_awprot = Port.input(Unsigned[3])
    axi_awvalid = Port.input(Bit)
    axi_awready = Port.output(Bit, default=Null)

    axi_wdata = Port.input(BitVector)
    axi_wstrb = Port.input(BitVector[4])
    axi_wvalid = Port.input(Bit)
    axi_wready = Port.output(Bit, default=Null)

    axi_bresp = Port.output(BitVector[2], default=Null)
    axi_bvalid = Port.output(Bit, default=Null)
    axi_bready = Port.input(Bit)

    axi_araddr = Port.input(Unsigned)
    axi_arprot = Port.input(Unsigned[3])
    axi_arvalid = Port.input(Bit)
    axi_arready = Port.output(Bit, default=Null)

    axi_rdata = Port.output(BitVector, default=Null)
    axi_rresp = Port.output(BitVector[2], default=Null)
    axi_rvalid = Port.output(Bit, default=Null)
    axi_rready = Port.input(Bit)

    def interface_context(self) -> SequentialContext:
        """
        Returns the sequential context defined by the AXI clock
        and reset signals.
        """

    def interface_connection(self) -> Axi4Light:
        """
        Returns all AXI signals of the entity wrapped
        in a class.
        """

@overload
def base_entity(
    *,
    addr_width=32,
    data_width=32,
    clk_edge=ClockEdge.RISING,
    clk_freq: Frequency | int | None = None,
    no_reset=False,
    active_high_reset=False,
) -> type[_CommonBase]:
    """
    Creates a cohdl.Entity class with predefiend ports
    for all AXI4 Lite signals. The parameters of the function
    configure the properties of these ports.

    User code should subclass the type returned by this
    function and implement AXI slave logic in the
    architecture method.

    The following example implements an AXI entity that acts
    as a FIFO. It receives data on the write channels, ignores
    the address and places the data onto a FIFO of depth 16.

    Every read returns the top element of the FIFO.

    >>> class ExampleFifo(base_entity()):
    >>>
    >>>     def architecture(self):
    >>>         axi_con = self.interface_connection()
    >>>         axi_ctx = self.interface_context()
    >>>
    >>>         fifo = std.Fifo[BitVector[32], 16]()
    >>>
    >>>         @axi_ctx
    >>>         async def proc_write():
    >>>             request = await axi_con.await_write_request()
    >>>
    >>>             if not fifo.full():
    >>>                 fifo.push(request.data)
    >>>
    >>>             await axi_con.send_write_response()
    >>>
    >>>         @axi_ctx
    >>>         async def proc_read():
    >>>             await axi_con.await_read_request()
    >>>
    >>>             result = Null if fifo.empty() else fifo.pop()
    >>>
    >>>             await axi_con.send_read_resp(result)
    """

class _CommonAddrMap(_CommonBase):
    def architecture(self):
        """
        The architecture of this class connects
        the generic register map returned by _gen_addr_map_
        to the AXI interface exposed by the entity.
        """

    @classmethod
    def _gen_addr_map_(cls) -> type[reg32.AddrMap]:
        """
        Returns the abstract register definition used to
        implement this AXI slave entity.

        When the parameter `addr_map_name` of `addr_map_entity` is
        specified, a class member of that name must exist in the
        class and is returned by this function.

        Otherwise the address map is created based on the type
        annotations of the derived entity itself.

        Subclasses can override _gen_addr_map_ to return
        a custom address map definition.
        """

def addr_map_entity(
    *,
    addr_width=32,
    clk_edge=ClockEdge.RISING,
    clk_freq: Frequency | int | None = None,
    no_reset=False,
    active_high_reset=False,
    addr_map: str | type[reg32.AddrMap] | None = None,
    entity_name: str | None = None,
) -> type[_CommonAddrMap]:
    """
    Define a AXI slave entity based on a generic address map.
    Users should subclass the returned type to define the
    registers of the entity.

    When `entity_name` is set, it is used as the name of the
    generated HDL entity. Defaults to the name of the Python class.

    There are three ways to define the register interface
    implemented by the entity:

    1. When `addr_map` is not defined, the interface is defined
        by type annotations on the derived class.

    >>> # Defines an AXI slave with 3 registers
    >>> # checkout the documentation of the register abstraction
    >>> # library (std.reg) for more features.
    >>> class ExampleAxi(addr_map_entity()):
    >>>     word_0: reg32.MemWord[0x00]
    >>>     word_1: reg32.MemWord[0x04]
    >>>     word_2: reg32.MemWord[0x08]
    >>>

    2. When `addr_map` is defined, it is used to lookup
        the register definition as a class member.

    >>> class ExampleAddrMap(reg32.AddrMap):
    >>>     word_0: reg32.MemWord[0x00]
    >>>     word_1: reg32.MemWord[0x04]
    >>>     word_2: reg32.MemWord[0x08]
    >>>
    >>> class ExampleAxi(addr_map_entity(addr_map="_ExampleAddrMap_")):
    >>>     _ExampleAddrMap_ = ExampleAddrMap

    3. When the subclass overrides `_gen_addr_map_` its return value is used.

    >>> class ExampleAddrMap(reg32.AddrMap):
    >>>     word_0: reg32.MemWord[0x00]
    >>>     word_1: reg32.MemWord[0x04]
    >>>     word_2: reg32.MemWord[0x08]
    >>>
    >>> class ExampleAxi(addr_map_entity(addr_map="_ExampleAddrMap_")):
    >>>     @classmethod
    >>>     def _gen_addr_map_(cls):
    >>>         return ExampleAddrMap
    """
