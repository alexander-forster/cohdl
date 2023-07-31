import cohdl
from cohdl import std
from cohdl import Port, Bit, BitVector, Signal, Temporary
import unittest


class Entity_If_Ok(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)
    c = Port.output(Bit)

    def architecture(self):
        @std.sequential
        def proc():
            if self.a:
                t = self.a | self.b


class Entity_If_Ok2(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)

    x = Port.output(Bit)
    y = Port.output(Bit)
    z = Port.output(Bit)

    def architecture(self):
        # Functions with multiple return paths are implemented
        # using temporaries that are defined in each branch.
        # Check that the temporary validation does not affect this.

        def choose_inp_x():
            if self.a:
                return self.a
            else:
                return self.b

        def choose_inp_y():
            if self.a:
                return self.a

            return self.b

        def choose_inp_z():
            if self.a:
                pass
            else:
                return self.a

            return self.b

        @std.sequential
        def proc():
            self.x <<= choose_inp_x()
            self.y <<= choose_inp_y()
            self.z <<= choose_inp_z()


class Entity_For_Ok(cohdl.Entity):
    a = Port.input(BitVector[2])
    b = Port.input(Bit)
    c = Port.output(Bit)

    x = Port.output(Bit)

    def architecture(self):
        def choose_x():
            # check, that for loop with multiple return paths is not affected
            # by temporary validation logic

            for cmp in ("00", "01", "10"):
                if cmp == self.a:
                    return self.b
            else:
                return self.c

        @std.sequential
        def proc():
            self.x <<= choose_x()


class Entity_Select_Ok(cohdl.Entity):
    a = Port.input(BitVector[2])
    b = Port.input(Bit)
    c = Port.output(Bit)

    x = Port.output(Bit)

    def architecture(self):
        def choose_x():
            # check, that select function is not affected
            # by temporary validation logic

            return std.select(
                self.a,
                {
                    "00": self.c,
                    "01": self.b,
                    "10": self.c,
                },
                default=self.c,
            )

        @std.sequential
        def proc():
            self.x <<= choose_x()


class Entity_If_Err(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)
    c = Port.output(Bit)

    def architecture(self):
        @std.sequential
        def proc():
            if self.a:
                t = self.a | self.b

            # error temporary might not be defined
            # in this line
            self.c <<= t


class Entity_If_Err2(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)
    c = Port.output(Bit)

    def architecture(self):
        @std.sequential
        def proc():
            if self.a:
                pass
            else:
                t = self.a | self.b

            # error temporary t might not be defined
            # in this line
            self.c <<= t


class Entity_Match_Err(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)
    c = Port.output(Bit)

    def architecture(self):
        @std.sequential
        def proc():
            match self.a:
                case "0":
                    x = Temporary(self.a)
                case _:
                    y = self.a | self.b

            # error temporary x might not be defined
            # in this line
            self.c <<= x


class Entity_Match_Err2(cohdl.Entity):
    a = Port.input(Bit)
    b = Port.input(Bit)
    c = Port.output(Bit)

    def architecture(self):
        @std.sequential
        def proc():
            match self.a:
                case "0":
                    x = Temporary(self.a)
                case _:
                    y = self.a | self.b

            # error temporary y might not be defined
            # in this line
            self.c <<= y


class SynthesizableTester(unittest.TestCase):
    def test_incompatible_entity_port(self):
        std.VhdlCompiler.to_string(Entity_If_Ok)
        std.VhdlCompiler.to_string(Entity_If_Ok2)
        std.VhdlCompiler.to_string(Entity_For_Ok)
        std.VhdlCompiler.to_string(Entity_Select_Ok)
        self.assertRaises(AssertionError, std.VhdlCompiler.to_string, Entity_If_Err)
        self.assertRaises(AssertionError, std.VhdlCompiler.to_string, Entity_If_Err2)
        self.assertRaises(AssertionError, std.VhdlCompiler.to_string, Entity_Match_Err)
        self.assertRaises(AssertionError, std.VhdlCompiler.to_string, Entity_Match_Err2)
