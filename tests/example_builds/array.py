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
    Clock,
    Array,
)


class TestArray(cohdl.Entity):
    clk = Port.input(Bit())

    index = Port.input(Unsigned(4, 0))

    def architecture(self):
        arr = Signal(Array(16, BitVector(8)))
        arr_2 = Signal(Array(32, Bit()))

        @cohdl.sequential(cohdl.Clock(self.clk))
        def process():
            arr[self.index].next = BitVector(8, "00000000")
            arr_2[self.index].next = Bit(0)


#
# compile to vhdl
#

if __name__ == "__main__":
    compiler = cohdl.ToVhdl()
    result = compiler.apply(TestArray)
    result.write_dir("tests/reference_builds/bin")
