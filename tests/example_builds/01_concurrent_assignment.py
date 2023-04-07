import cohdl
from cohdl import (
    Bit,
    BitVector,
    Port,
)


class Simple(cohdl.Entity):
    sw = Port.input(BitVector[16])
    led = Port.output(BitVector[16])

    def architecture(self):
        @cohdl.concurrent
        def logic():
            self.led <<= self.sw | self.sw


#
# compile to vhdl
#

if __name__ == "__main__":
    compiler = cohdl.ToVhdl()
    result = compiler.apply(Simple)
    result.write_dir("tests/reference_builds/bin")
