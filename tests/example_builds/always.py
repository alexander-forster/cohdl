import cohdl
from cohdl import (
    Bit,
    BitVector,
    Unsigned,
    Port,
    select_with,
    Signal,
    Constant,
    Integer,
    Variable,
    always,
)


class Always(cohdl.Entity):
    clk = Port.input(Bit())

    sw = Port.input(BitVector(16))
    led = Port.output(BitVector(16))

    sseg_ca = Port.output(BitVector(7))
    sseg_an = Port.output(BitVector(8))

    def architecture(self):
        @cohdl.sequential(cohdl.Clock(self.clk))
        async def process(x=Variable(Bit(0))):
            inv = always(self.sw.as_unsigned() + 1)
            self.led.next = inv


#
# compile to vhdl
#

if __name__ == "__main__":
    compiler = cohdl.ToVhdl()
    result = compiler.apply(Always)
    result.write_dir("tests/reference_builds/bin")
