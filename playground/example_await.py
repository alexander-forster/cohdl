from cohdl import Bit, BitVector, Entity, Signal, Port, Variable, expr
from cohdl import std


def foo(a, b, o):
    o <<= a | b
    return expr(a | b)


class MyEntity(Entity):
    clk = Port.input(Bit)

    a = Port.input(Bit)
    b = Port.input(Bit)

    result1 = Port.output(Bit)
    result2 = Port.output(Bit)

    def architecture(self):
        clk = std.Clock(self.clk)

        @std.sequential(clk)
        async def proc():
            x = await expr(self.a | self.b)
            self.result1 <<= x

        @std.sequential(clk)
        async def proc_b():
            x = await expr(foo(self.a, self.b, self.result2))
            self.result2 <<= x


print(std.VhdlCompiler.to_string(MyEntity))
