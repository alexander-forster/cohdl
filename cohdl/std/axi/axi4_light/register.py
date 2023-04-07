from __future__ import annotations

from .base import Axi4Light

import cohdl
from cohdl.std._context import sequential


class Register:
    def __init__(
        self,
        addr,
        *,
        name=None,
        value=None,
        on_read=None,
        on_write=None,
        read_only=False,
        write_only=False,
    ):
        if not read_only:
            assert value is not None or on_write is not None
        if not write_only:
            assert value is not None or on_read is not None

        self.addr = addr
        self.name = name
        self.value = value
        self.on_read = on_read
        self.on_write = on_write
        self.read_only = read_only
        self.write_only = write_only


@cohdl.consteval
def _readable_reg(registers: list[Register]):
    return [reg for reg in registers if not reg.write_only]


@cohdl.consteval
def _writeable_reg(registers: list[Register]):
    return [reg for reg in registers if not reg.read_only]


def register_bank(axi: Axi4Light, registers: list[Register]):
    def read_handler(addr, prot):
        result = cohdl.Variable(cohdl.BitVector[32])

        for reg in _readable_reg(registers):
            if addr.unsigned == reg.addr:
                if reg.on_read is None:
                    result.value = reg.value
                else:
                    result.value = reg.on_read(prot)
                break
        else:
            result.value = cohdl.Null

        return result, cohdl.Null

    @sequential(axi.clk, axi.reset)
    async def proc_read():
        await axi.handle_reads(read_handler)

    def write_handler(addr, prot, data, strb):
        resp = cohdl.Variable(cohdl.BitVector[2])

        for reg in _writeable_reg(registers):
            if addr.unsigned == reg.addr:
                if reg.on_write is None:
                    reg.value <<= Axi4Light.mask_wstrb(reg.value, data, strb)
                    resp @= cohdl.Null
                else:
                    resp @= reg.on_write(prot, data, strb)

        return resp

    @sequential(axi.clk, axi.reset)
    async def proc_write():
        await axi.handle_writes(write_handler)
