import cohdl
from cohdl import std
from cohdl import Port, Bit, Signal, BitVector
import unittest
import enum


class SelectBool(enum.Enum):
    CONST_FALSE = enum.auto()
    CONST_TRUE = enum.auto()
    CONST_NONE = enum.auto()
    CONST_0 = enum.auto()
    CONST_1 = enum.auto()
    CONST_HIGH = enum.auto()
    CONST_LOW = enum.auto()
    CONST_NULL = enum.auto()
    CONST_FULL = enum.auto()
    SIG_BOOL = enum.auto()
    SIG_BIT = enum.auto()
    SIG_VEC = enum.auto()


S = SelectBool

VALID_LIST = [S.CONST_FALSE, S.CONST_TRUE, S.SIG_BOOL]


class CheckBoolean:
    def __init__(self, val):
        self.val = val

    def __bool__(self):
        return self.val


def genEntity(
    selected_bool: SelectBool,
    cast=False,
    logic_not=False,
    logic_and=False,
    logic_or=False,
    logic_any=False,
    logic_all=False,
    if_expr=False,
):
    class ProcessBoolean(cohdl.Entity):
        sig_bit = Port.input(Bit)
        sig_bool = Port.input(bool)
        sig_vec = Port.input(BitVector[4])

        sig_out = Port.output(bool)

        def architecture(self):
            @cohdl.pyeval
            def choose_inp():
                match selected_bool:
                    case S.CONST_FALSE:
                        return False
                    case S.CONST_TRUE:
                        return True
                    case S.CONST_NONE:
                        return None
                    case S.CONST_0:
                        return 0
                    case S.CONST_1:
                        return 1
                    case S.CONST_HIGH:
                        return Bit(1)
                    case S.CONST_LOW:
                        return Bit(0)
                    case S.CONST_NULL:
                        return cohdl.Null
                    case S.CONST_FULL:
                        return cohdl.Full
                    case S.SIG_BOOL:
                        return self.sig_bool
                    case S.SIG_BIT:
                        return self.sig_bit
                    case S.SIG_VEC:
                        return self.sig_vec

                raise IndexError("invalid selector value")

            @std.concurrent
            def logic():
                if cast:
                    boolean = CheckBoolean(bool(choose_inp()))
                elif logic_not:
                    boolean = CheckBoolean(not choose_inp())
                elif logic_and:
                    boolean = CheckBoolean(choose_inp() and choose_inp())
                elif logic_or:
                    boolean = CheckBoolean(choose_inp() or choose_inp())
                elif logic_any:
                    boolean = CheckBoolean(any([choose_inp()]))
                elif logic_all:
                    boolean = CheckBoolean(all([choose_inp(), choose_inp()]))
                elif if_expr:
                    boolean = CheckBoolean(True if choose_inp() else False)
                else:
                    boolean = CheckBoolean(choose_inp())

                self.sig_out <<= True if boolean else False

    return ProcessBoolean


class SynthesizableTester(unittest.TestCase):
    def test_dunder_bool_must_return_boolean(self):
        # The compiler must enforce that __bool__ returns
        # a possibly type qualified boolean and nothing else.
        # Other return types like Bit can case issues even if
        # then are convertible to bool (example when passed
        # to formal verification functions or inline HDL).

        for inp_select in VALID_LIST:
            # check that input can be converted to boolean
            std.VhdlCompiler.to_string(genEntity(inp_select))

        for inp_select in SelectBool:
            if inp_select in VALID_LIST:
                continue

            # check that compiler rejects input
            self.assertRaises(
                AssertionError,
                std.VhdlCompiler.to_string,
                genEntity(inp_select),
            )

        for inp_select in SelectBool:
            # check that all inputs are accepted when implicitly/explicitly cast to boolean
            std.VhdlCompiler.to_string(genEntity(inp_select, cast=True))
            std.VhdlCompiler.to_string(genEntity(inp_select, logic_not=True))
            std.VhdlCompiler.to_string(genEntity(inp_select, logic_and=True))
            std.VhdlCompiler.to_string(genEntity(inp_select, logic_or=True))
            std.VhdlCompiler.to_string(genEntity(inp_select, logic_any=True))
            std.VhdlCompiler.to_string(genEntity(inp_select, logic_all=True))
            std.VhdlCompiler.to_string(genEntity(inp_select, if_expr=True))
