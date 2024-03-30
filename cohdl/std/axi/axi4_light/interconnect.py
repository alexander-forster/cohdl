import cohdl
from cohdl.std._context import concurrent, sequential


from .base import Axi4Light

#
#
# interconnect
#
#


def background_range(clk, reset, addr_width):
    axi = Axi4Light.signal(
        clk,
        reset,
        addr_width=addr_width,
        data_width=32,
    )

    @concurrent
    def background_axi():
        axi.rdaddr.ready <<= True

        axi.rddata.valid <<= True
        axi.rddata.rdata <<= cohdl.Null
        axi.rddata.rresp <<= Axi4Light.RespConstants.DECERR

        axi.wraddr.ready <<= True
        axi.wrdata.ready <<= True
        axi.wrresp.valid <<= True
        axi.wrresp.bresp <<= Axi4Light.RespConstants.DECERR

    return axi


class Interconnect:
    class SlaveWrapper:
        def __init__(self, offset: int, size: int, axi: Axi4Light):
            assert size.bit_count() == 1, "size must be a power of 2"
            assert offset % size == 0, "offset must be a multiple of the interface size"

            self.range_start = offset
            self.range_end = offset + size - 1
            self.axi = axi
            self.rd_active = cohdl.Signal[cohdl.Bit](False)
            self.wr_active = cohdl.Signal[cohdl.Bit](False)

        def when_active(self, value):
            return value if self.active else cohdl.Null

        def contains_addr(self, addr):
            return self.range_start <= addr.unsigned <= self.range_end

        def overlapps(self, offset, size):
            return (
                (self.range_start <= offset <= self.range_end)
                or (self.range_start <= offset + size <= self.range_end)
                or (offset <= self.range_start < offset + size)
                or (offset <= self.range_end < offset + size)
            )

    def _all_slaves(self):
        return [*self._slaves, self._background]

    def __init__(self, master: Axi4Light):
        addr_width = master.addr_width()

        self._clk = master.clk
        self._reset = master.reset
        self._background = Interconnect.SlaveWrapper(
            0, 2**addr_width, background_range(self._clk, self._reset, addr_width)
        )
        self._slaves: list[Interconnect.SlaveWrapper] = []

        @sequential
        def proc_connect():
            for slv in self._all_slaves():
                slv_addr_width = slv.axi.addr_width()

                if slv.rd_active:
                    master.rdaddr.ready ^= slv.axi.rdaddr.ready
                    slv.axi.rdaddr.valid ^= master.rdaddr.valid
                    slv.axi.rdaddr.araddr ^= master.rdaddr.araddr.lsb(slv_addr_width)
                    slv.axi.rdaddr.arprot ^= master.rdaddr.arprot

                    slv.axi.rddata.ready ^= master.rddata.ready
                    master.rddata.valid ^= slv.axi.rddata.valid
                    master.rddata.rdata ^= slv.axi.rddata.rdata
                    master.rddata.rresp ^= slv.axi.rddata.rresp

                if slv.wr_active:
                    master.wraddr.ready ^= slv.axi.wraddr.ready
                    slv.axi.wraddr.valid ^= master.wraddr.valid
                    slv.axi.wraddr.awaddr ^= master.wraddr.awaddr.lsb(slv_addr_width)
                    slv.axi.wraddr.awprot ^= master.wraddr.awprot

                    master.wrdata.ready ^= slv.axi.wraddr.ready
                    slv.axi.wrdata.valid ^= master.wrdata.valid
                    slv.axi.wrdata.wdata ^= master.wrdata.wdata
                    slv.axi.wrdata.wstrb ^= master.wrdata.wstrb

                    slv.axi.wrresp.ready ^= master.wrresp.ready
                    master.wrresp.valid ^= slv.axi.wrresp.valid
                    master.wrresp.bresp ^= slv.axi.wrresp.bresp

        @sequential(self._clk, self._reset)
        async def proc_read():
            await master.rdaddr.valid

            for slv in self._all_slaves():
                if slv.contains_addr(master.rdaddr.araddr):
                    slv.rd_active <<= True

            await master.rddata.valid & master.rddata.ready

            for slv in self._all_slaves():
                slv.rd_active <<= False

        @sequential(self._clk, self._reset)
        async def proc_write():
            await master.wraddr.valid

            for slv in self._all_slaves():
                if slv.contains_addr(master.wraddr.awaddr):
                    slv.wr_active <<= True

            await master.wrresp.valid & master.wrresp.ready

            for slv in self._all_slaves():
                slv.wr_active <<= False

    def reserve(self, offset: int, size: int, prefix="") -> Axi4Light:
        assert size.bit_count() == 1, "size must be a power of 2"
        addr_width = size.bit_length() - 1

        axi = Axi4Light.signal(self._clk, self._reset, addr_width, prefix=prefix)

        self.connect(axi, offset, size)

        return axi

    def connect(self, axi: Axi4Light, offset: int, size: int | None = None):
        requested_size = size
        actual_size = 2 ** axi.addr_width()

        assert requested_size is None or (requested_size == actual_size)

        for slv in self._slaves:
            assert not slv.overlapps(offset, actual_size)

        self._slaves.append(Interconnect.SlaveWrapper(offset, actual_size, axi))
