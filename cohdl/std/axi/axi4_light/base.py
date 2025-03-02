from __future__ import annotations

from cohdl.std._context import SequentialContext
from cohdl.std.axi._axi4_channel import Channel
from cohdl.std._core_utility import Mask, stretch, as_awaitable
from cohdl.std._context import Clock, Reset, ClockEdge, Frequency

from cohdl.std.reg import RegisterObject, reg32

import cohdl
from cohdl import Port, Bit, Unsigned, Null, BitVector, pyeval

from typing import get_type_hints


class Axi4Light:
    class RespConstants:
        OKAY = "00"
        EXOKAY = "01"
        SLVERR = "10"
        DECERR = "11"

    class WrAddr(Channel):
        def __init__(self, valid, ready, awaddr, awprot, **kwargs):
            super().__init__(valid, ready, awaddr=awaddr, awprot=awprot, **kwargs)

            self.awaddr = awaddr
            self.awprot = awprot

    class WrData(Channel):
        def __init__(self, valid, ready, wdata, wstrb, **kwargs):
            super().__init__(valid, ready, wdata=wdata, wstrb=wstrb, **kwargs)

            self.wdata = wdata
            self.wstrb = wstrb

    class WrResp(Channel):
        def __init__(self, valid, ready, bresp, **kwargs):
            super().__init__(valid, ready, bresp=bresp, **kwargs)

            self.bresp = bresp

    class RdAddr(Channel):
        def __init__(self, valid, ready, araddr, arprot, **kwargs):
            super().__init__(valid, ready, araddr=araddr, arprot=arprot, **kwargs)

            self.araddr = araddr
            self.arprot = arprot

    class RdData(Channel):
        def __init__(self, valid, ready, rdata, rresp, **kwargs):
            super().__init__(valid, ready, rdata=rdata, rresp=rresp, **kwargs)

            self.rdata = rdata
            self.rresp = rresp

    @staticmethod
    def signal(
        clk,
        reset,
        addr_width,
        data_width=32,
        strb_width=4,
        prot_width=3,
        resp_width=2,
        prefix="",
    ):
        S = cohdl.Signal
        Bit = cohdl.Bit
        BitVector = cohdl.BitVector
        Null = cohdl.Null

        awaddr = Axi4Light.WrAddr(
            S[Bit](Null, name=f"{prefix}awvalid"),
            S[Bit](Null, name=f"{prefix}awready"),
            S[BitVector[addr_width]](Null, name=f"{prefix}awaddr"),
            (
                S[BitVector[prot_width]](Null, name=f"{prefix}awprot")
                if prot_width is not None
                else None
            ),
        )

        wrdata = Axi4Light.WrData(
            S[Bit](Null, name=f"{prefix}wvalid"),
            S[Bit](Null, name=f"{prefix}wready"),
            S[BitVector[data_width]](Null, name=f"{prefix}wdata"),
            S[BitVector[strb_width]](Null, name=f"{prefix}wstrb"),
        )

        bresp = Axi4Light.WrResp(
            S[Bit](Null, name=f"{prefix}bvalid"),
            S[Bit](Null, name=f"{prefix}bready"),
            S[BitVector[resp_width]](Null, name=f"{prefix}bresp"),
        )

        rdaddr = Axi4Light.RdAddr(
            S[Bit](Null, name=f"{prefix}arvalid"),
            S[Bit](Null, name=f"{prefix}arready"),
            S[BitVector[addr_width]](Null, name=f"{prefix}araddr"),
            (
                S[BitVector[prot_width]](Null, name=f"{prefix}arprot")
                if prot_width is not None
                else None
            ),
        )

        rddata = Axi4Light.RdData(
            S[Bit](Null, name=f"{prefix}rvalid"),
            S[Bit](Null, name=f"{prefix}rready"),
            S[BitVector[data_width]](Null, name=f"{prefix}rdata"),
            S[BitVector[resp_width]](Null, name=f"{prefix}rresp"),
        )

        return Axi4Light(clk, reset, awaddr, wrdata, bresp, rdaddr, rddata)

    def __init__(
        self,
        clk,
        reset,
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

        self._addr_width = rdaddr.araddr.width
        self._data_width = rddata.rdata.width

    def addr_width(self):
        return self._addr_width

    def data_width(self):
        return self._data_width

    async def read_word(self, addr, prot=cohdl.Null):
        if self.rdaddr.arprot is None:
            assert (
                prot is cohdl.Null
            ), "arprot not provided, interface does not support `prot` argument"
        else:
            self.rdaddr.arprot <<= prot

        self.rdaddr.araddr.unsigned <<= addr

        self.rdaddr.valid <<= True

        await self.rdaddr.ready
        self.rdaddr.valid <<= False

        self.rddata.ready <<= True
        await self.rddata.valid
        self.rddata.ready <<= False

        return self.rddata.rdata, self.rddata.rresp

    async def write_word(self, addr, data, strb=cohdl.Full, prot=cohdl.Null):
        if self.wraddr.awprot is None:
            assert (
                prot is cohdl.Null
            ), "awprot not provided, interface does not support `prot` argument"
        else:
            self.wraddr.awprot <<= prot

        self.wraddr.awaddr.unsigned <<= addr
        self.wraddr.valid <<= True

        self.wrdata.wdata <<= data
        self.wrdata.wstrb <<= strb
        self.wrdata.valid <<= True

        ack_addr = cohdl.Variable(self.wraddr.ready)
        ack_data = cohdl.Variable(self.wrdata.ready)

        while True:
            ack_addr @= self.wraddr.ready | ack_addr
            ack_data @= self.wrdata.ready | ack_data

            self.wraddr.valid <<= ~ack_addr
            self.wrdata.valid <<= ~ack_data

            if ack_addr & ack_data:
                break

        self.wrresp.ready <<= True
        await self.wrresp.valid
        self.wrresp.ready <<= False

        return self.wrresp.bresp

    class _ReadRequest:
        def __init__(self, addr, prot):
            self.addr = addr
            self.prot = prot

    async def await_read_request(self):
        self.rdaddr.ready <<= True
        await self.rdaddr.valid
        self.rdaddr.ready <<= False
        return Axi4Light._ReadRequest(self.rdaddr.araddr, self.rdaddr.arprot)

    async def send_read_resp(self, data, resp=cohdl.Null):
        self.rddata.rdata <<= data
        self.rddata.rresp <<= resp
        self.rddata.valid <<= True
        await self.rddata.ready
        self.rddata.valid <<= False

    class _WriteRequest:
        def __init__(self, addr, prot, data, strb):
            self.addr = addr
            self.prot = prot
            self.data = data
            self.strb = strb

    async def await_write_request(self):
        awready = self.wraddr.ready
        awvalid = self.wraddr.valid

        wready = self.wrdata.ready
        wvalid = self.wrdata.valid

        addr_latched = cohdl.Variable[cohdl.Bit](False)
        data_latched = cohdl.Variable[cohdl.Bit](False)

        awready <<= True
        wready <<= True

        while True:
            if ~addr_latched:
                addr_buffer = cohdl.Signal(self.wraddr.awaddr, maybe_uninitialized=True)
                prot_buffer = cohdl.Signal(self.wraddr.awprot, maybe_uninitialized=True)
            if ~data_latched:
                data_buffer = cohdl.Signal(self.wrdata.wdata, maybe_uninitialized=True)
                strb_buffer = cohdl.Signal(self.wrdata.wstrb, maybe_uninitialized=True)

            addr_latched @= addr_latched | awvalid
            data_latched @= data_latched | wvalid

            awready <<= ~addr_latched
            wready <<= ~data_latched

            if addr_latched & data_latched:
                break

        return Axi4Light._WriteRequest(
            addr_buffer, prot_buffer, data_buffer, strb_buffer
        )

    async def send_write_response(self, resp=cohdl.Null):
        self.wrresp.bresp <<= resp
        self.wrresp.valid <<= True
        await self.wrresp.ready
        self.wrresp.valid <<= False

    def connect_addr_map(self, addr_map):
        from cohdl.std.reg import RegisterTools
        from cohdl.std._core_utility import as_awaitable

        assert isinstance(addr_map, RegisterTools.AddrMap), "addr_map is not a AddrMap"
        assert addr_map._word_width_() == 32, "word width of addr_map object must be 32"
        assert (
            addr_map._register_tools_._addr_unit_width_ == 8
        ), "unit width of addr_map object must be 8"

        ctx = SequentialContext(self.clk, self.reset)
        addr_map._implement_synthesizable_contexts_(ctx)

        regs = addr_map._flatten_()

        readable_regs = [reg for reg in regs if reg._readable_]
        writable_regs = [reg for reg in regs if reg._writable_]

        @ctx
        async def proc_read():
            while True:
                request = await self.await_read_request()
                assert isinstance(request.addr, cohdl.Signal)

                result = cohdl.Variable[cohdl.BitVector[32]](cohdl.Null)

                for reg in readable_regs:
                    if reg._contains_addr_(request.addr.unsigned):
                        result @= await as_awaitable(
                            reg._basic_read_, request.addr.unsigned, None
                        )
                        break

                await self.send_read_resp(result)
                continue

        @ctx
        async def proc_write():
            while True:
                request = await self.await_write_request()
                assert isinstance(request.addr, cohdl.Signal)
                mask = cohdl.Variable(stretch(request.strb, 8))

                for reg in writable_regs:
                    if reg._contains_addr_(request.addr.unsigned):
                        await as_awaitable(
                            reg._basic_write_,
                            request.addr.unsigned,
                            request.data,
                            Mask(mask),
                            None,
                        )
                        break

                await self.send_write_response()
                continue


#
#
#


def base_entity(
    *,
    addr_width=32,
    data_width=32,
    clk_edge=ClockEdge.RISING,
    clk_freq: Frequency | int | None = None,
    no_reset=False,
    active_high_reset=False,
):
    class AxiBaseEntity(cohdl.Entity):
        axi_clk = Port.input(Bit)

        if no_reset:
            axi_reset = None
        else:
            axi_reset = Port.input(Bit)

        axi_awaddr = Port.input(Unsigned[addr_width])
        axi_awprot = Port.input(Unsigned[3])
        axi_awvalid = Port.input(Bit)
        axi_awready = Port.output(Bit, default=Null)

        axi_wdata = Port.input(BitVector[data_width])
        axi_wstrb = Port.input(BitVector[4])
        axi_wvalid = Port.input(Bit)
        axi_wready = Port.output(Bit, default=Null)

        axi_bresp = Port.output(BitVector[2], default=Null)
        axi_bvalid = Port.output(Bit, default=Null)
        axi_bready = Port.input(Bit)

        axi_araddr = Port.input(Unsigned[addr_width])
        axi_arprot = Port.input(Unsigned[3])
        axi_arvalid = Port.input(Bit)
        axi_arready = Port.output(Bit, default=Null)

        axi_rdata = Port.output(BitVector[data_width], default=Null)
        axi_rresp = Port.output(BitVector[2], default=Null)
        axi_rvalid = Port.output(Bit, default=Null)
        axi_rready = Port.input(Bit)

        @pyeval
        def interface_context(self) -> SequentialContext:
            if not hasattr(self, "_cohdlstd_axi_context"):
                if no_reset:
                    reset = None
                elif active_high_reset:
                    reset = Reset(self.axi_reset)
                else:
                    reset = Reset(self.axi_reset, active_low=True)

                self._cohdlstd_axi_context = SequentialContext(
                    Clock(self.axi_clk, active_edge=clk_edge, frequency=clk_freq),
                    reset,
                )

            return self._cohdlstd_axi_context

        @pyeval
        def interface_connection(self):

            return Axi4Light(
                clk=self.interface_context().clk(),
                reset=self.interface_context().reset(),
                wraddr=Axi4Light.WrAddr(
                    valid=self.axi_awvalid,
                    ready=self.axi_awready,
                    awaddr=self.axi_awaddr,
                    awprot=self.axi_awprot,
                ),
                wrdata=Axi4Light.WrData(
                    valid=self.axi_wvalid,
                    ready=self.axi_wready,
                    wdata=self.axi_wdata,
                    wstrb=self.axi_wstrb,
                ),
                wrresp=Axi4Light.WrResp(
                    valid=self.axi_bvalid,
                    ready=self.axi_bready,
                    bresp=self.axi_bresp,
                ),
                rdaddr=Axi4Light.RdAddr(
                    valid=self.axi_arvalid,
                    ready=self.axi_arready,
                    araddr=self.axi_araddr,
                    arprot=self.axi_arprot,
                ),
                rddata=Axi4Light.RdData(
                    valid=self.axi_rvalid,
                    ready=self.axi_rready,
                    rdata=self.axi_rdata,
                    rresp=self.axi_rresp,
                ),
            )

    return AxiBaseEntity


def addr_map_entity(
    *,
    addr_width=32,
    clk_edge=ClockEdge.RISING,
    clk_freq: Frequency | int | None = None,
    no_reset=False,
    active_high_reset=False,
    addr_map=None,
    entity_name=None,
):
    Base = base_entity(
        addr_width=addr_width,
        clk_edge=clk_edge,
        clk_freq=clk_freq,
        no_reset=no_reset,
        active_high_reset=active_high_reset,
    )

    class AxiAddrMapEntity(Base):
        def architecture(self):
            AddrMap = self._gen_addr_map_()

            # connect the AXI signals to the address map
            # defined in the exampled derived below
            self.interface_connection().connect_addr_map(AddrMap())

        @classmethod
        @pyeval
        def _gen_addr_map_(cls):
            cache_name = "_cohdlstd_AddrMap"

            if hasattr(cls, cache_name):
                return getattr(cls, cache_name)

            if addr_map is not None:
                if isinstance(addr_map, str):
                    assert hasattr(
                        cls, addr_map
                    ), f"class member '{addr_map}' does not exist"
                    AddrMap = getattr(cls, addr_map)
                else:
                    AddrMap = addr_map
            else:

                annotations = {}
                members = {}

                for name, member_type in get_type_hints(
                    cls, include_extras=True
                ).items():

                    if not issubclass(member_type, RegisterObject):
                        continue

                    assert (
                        member_type._register_tools_ is reg32
                    ), "incompatible register refinition"

                    annotations[name] = member_type

                assert (
                    len(annotations) != 0
                ), "missing register definition in class derived from addr_map_entity"

                for mro_elem in cls.mro():
                    if mro_elem is AxiAddrMapEntity:
                        break

                    for name, val in mro_elem.__dict__.items():
                        if name in members:
                            continue

                        members[name] = val

                del members["__annotations__"]

                AddrMap = type(
                    cls.__name__ if entity_name is None else entity_name,
                    (reg32.AddrMap,),
                    {**members, "__annotations__": annotations},
                )

                assert issubclass(AddrMap, reg32.AddrMap)

            setattr(cls, cache_name, AddrMap)
            return AddrMap

    return AxiAddrMapEntity
