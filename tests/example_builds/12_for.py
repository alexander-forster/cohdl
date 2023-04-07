import cohdl
from cohdl import Bit, BitVector, Port, Clock, Unsigned, Signal, Null, Full


def first(branches, default):
    if len(branches) == 0:
        return default
    else:
        cond, val = branches[0]
        return val if cond else first(branches[1:], default)


class ForLoop(cohdl.Entity):
    clk = Port.input(Bit)
    sw = Port.input(BitVector[3])
    led = Port.output(BitVector[16])

    def architecture(self):
        clock = Clock(self.clk)

        first_set = Signal(Unsigned[6], 0)

        """@cohdl.sequential(clock)
        def process():
            for id, bit in enumerate(self.sw):
                if bit:
                    first_set.next = id
                    break
            else:
                first_set.next = 32"""

        @cohdl.concurrent
        def logic():
            first_set[0].next = (
                Bit(0) if self.sw[0] else Bit(1) if self.sw[1] else Bit(0)
            )


#
# compile to vhdl
#

if __name__ == "__main__":
    compiler = cohdl.ToVhdl()
    result = compiler.apply(ForLoop)
    result.write_dir("tests/reference_builds/bin")
