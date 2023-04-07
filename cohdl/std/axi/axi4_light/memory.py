from __future__ import annotations

import cohdl
from cohdl.std._context import sequential

from .base import Axi4Light


def memory(axi: Axi4Light, size: int, use_wstrb=True):
    addr_width = (size - 1).bit_length() - 2
    data_width = axi.data_width()

    memory = cohdl.Signal[cohdl.Array[cohdl.BitVector[data_width], size]](name="memory")

    def index(addr):
        # remove two lsb since only aligned access allowed
        addr_word = addr.msb(rest=2)
        return addr_word.lsb(addr_width).unsigned

    @sequential(axi.clk, axi.reset)
    async def process_read():
        while True:
            req = await axi.await_read_request()
            await axi.send_read_resp(memory[index(req.addr)], axi.RespConstants.OKAY)
            continue

    @sequential(axi.clk, axi.reset)
    async def process_write():
        while True:
            req = await axi.await_write_request()

            if use_wstrb:
                memory[index(req.addr)] <<= axi.mask_wstrb(
                    memory[index(req.addr)], req.data, req.strb
                )
            else:
                memory[index(req.addr)] <<= req.data

            await axi.send_write_response(axi.RespConstants.OKAY)
            continue
