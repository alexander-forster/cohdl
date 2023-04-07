import cohdl
from cohdl import Bit, BitVector, Port, Clock, always, Signal


class Simple(cohdl.Entity):
    clk = Port.input(Bit)
    sw = Port.input(BitVector[16])
    led = Port.output(BitVector[16])

    def architecture(self):
        clock = Clock(self.clk)
        pushed = Signal(Bit, False, name="pushed")

        @cohdl.sequential(clock)
        async def logic():
            nonlocal pushed

            self.led[0] <<= self.sw[15]
            await self.sw[0]
            self.led[1] <<= self.sw[14]

            pushed ^= Bit(1)

            await self.sw[1]
            self.led[2] <<= self.sw[13]


#
# compile to vhdl
#

if __name__ == "__main__":
    compiler = cohdl.ToVhdl()
    result = compiler.apply(Simple)
    result.write_dir("tests/reference_builds/bin")
