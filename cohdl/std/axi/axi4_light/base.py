from __future__ import annotations

from cohdl.std._context import SequentialContext
from cohdl.std.axi._axi4_channel import Channel
from cohdl.std._core_utility import Mask, stretch

import cohdl


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

    async def handle_reads(self, read_handler, is_async=False):
        while True:
            self.rdaddr.ready <<= True
            await self.rdaddr.valid
            self.rdaddr.ready <<= False

            if is_async:
                data, resp = await read_handler(self.rdaddr.araddr, self.rdaddr.arprot)
            else:
                data, resp = read_handler(self.rdaddr.araddr, self.rdaddr.arprot)

            self.rddata.rdata <<= data
            self.rddata.rresp <<= resp
            self.rddata.valid <<= True

            await self.rddata.ready
            self.rddata.valid <<= False

            continue

    async def handle_writes(self, write_handler, is_async=False):
        while True:
            self.wraddr.ready <<= False
            self.wrdata.ready <<= False
            self.wrresp.valid <<= False

            if self.wraddr.valid & self.wrdata.valid:
                if is_async:
                    resp = await write_handler(
                        self.wraddr.awaddr,
                        self.wraddr.awprot,
                        self.wrdata.wdata,
                        self.wrdata.wstrb,
                    )
                else:
                    resp = write_handler(
                        self.wraddr.awaddr,
                        self.wraddr.awprot,
                        self.wrdata.wdata,
                        self.wrdata.wstrb,
                    )

                self.wraddr.ready <<= True
                self.wrdata.ready <<= True

                self.wrresp.bresp <<= resp
                self.wrresp.valid <<= True

                while ~self.wrresp.ready:
                    self.wraddr.ready <<= False
                    self.wrdata.ready <<= False

                self.wraddr.ready <<= False
                self.wrdata.ready <<= False
                self.wrresp.valid <<= False

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

    @staticmethod
    def mask_wstrb(old_data, new_data, wstrb):
        byte_0 = new_data[7:0] if wstrb[0] else old_data[7:0]
        byte_1 = new_data[15:8] if wstrb[1] else old_data[15:8]
        byte_2 = new_data[23:16] if wstrb[2] else old_data[23:16]
        byte_3 = new_data[31:24] if wstrb[3] else old_data[31:24]

        return byte_3 @ byte_2 @ byte_1 @ byte_0

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
