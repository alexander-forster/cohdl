from cohdl import std, BitVector, Unsigned, Signed, Entity, Array, Port, Signal


class Example(Entity):
    result = Port.output(Unsigned[32])

    def architecture(self):
        mem = Signal[Array[BitVector[16], 16]]()
        long = Signal[BitVector[32]]()

        @std.concurrent
        def logic():
            # self.result <<= long[15:0].unsigned
            self.result <<= mem[4].unsigned


print(std.VhdlCompiler.to_string(Example))
