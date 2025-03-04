import cohdl
from cohdl import std
from cohdl import Port, Bit, BitVector
import unittest


class ValHolder:
    def __init__(self, val):
        self.val = val


class Entity(cohdl.Entity):
    enable = Port.input(Bit)

    inp1 = Port.input(BitVector[4])
    inp2 = Port.input(BitVector[4])

    output1 = Port.output(BitVector[4])
    output2 = Port.output(BitVector[4])
    output3 = Port.output(Bit)


def make_derived(member_function):

    class Derived(Entity):

        def architecture(self):
            @std.concurrent
            def proc():
                member_function(self)

    return Derived


class TestInvalidValueBranch(unittest.TestCase):
    def test_value_branches(self):

        def valid_fn(entity: Entity):
            v = ValHolder(entity.inp1) if entity.enable else ValHolder(entity.inp2)

            assert hasattr(v, "val")
            assert not hasattr(v, "asdf")

            entity.output1 <<= v.val
            entity.output2 <<= getattr(v, "val")
            entity.output3 <<= getattr(
                ValHolder(v.val[2]) if entity.inp1[0] else ValHolder(entity.inp2[3]),
                "val",
            )

        std.VhdlCompiler.to_string(make_derived(valid_fn))

        val_with_other = ValHolder(None)
        val_with_other.other = 1

        def valid_hasattr_same_result(entity: Entity):
            v = ValHolder(entity.inp1) if entity.enable else val_with_other

            assert hasattr(v, "val")

        std.VhdlCompiler.to_string(make_derived(valid_hasattr_same_result))

        def invalid_hasattr_result_differs(entity: Entity):
            v = ValHolder(entity.inp1) if entity.enable else val_with_other

            assert hasattr(v, "other")

        self.assertRaises(
            AssertionError,
            std.VhdlCompiler.to_string,
            make_derived(invalid_hasattr_result_differs),
        )

        def valid_getattr_both_exist(entity: Entity):
            v = ValHolder(entity.inp1) if entity.enable else val_with_other
            getattr(v, "val")

        std.VhdlCompiler.to_string(make_derived(valid_getattr_both_exist))

        def invalid_getattr_one_exists(entity: Entity):
            v = ValHolder(entity.inp1) if entity.enable else val_with_other
            getattr(v, "other")

        self.assertRaises(
            AttributeError,
            std.VhdlCompiler.to_string,
            make_derived(invalid_getattr_one_exists),
        )

        def invalid_getter_one_exists(entity: Entity):
            v = ValHolder(entity.inp1) if entity.enable else val_with_other
            v.other

        self.assertRaises(
            AssertionError,
            std.VhdlCompiler.to_string,
            make_derived(invalid_getter_one_exists),
        )

        def invalid_getattr_none_exist(entity: Entity):
            v = ValHolder(entity.inp1) if entity.enable else val_with_other
            getattr(v, "asdf")

        self.assertRaises(
            AttributeError,
            std.VhdlCompiler.to_string,
            make_derived(invalid_getattr_none_exist),
        )

        def invalid_getter_none_exist(entity: Entity):
            v = ValHolder(entity.inp1) if entity.enable else val_with_other
            v.asdf

        self.assertRaises(
            AssertionError,
            std.VhdlCompiler.to_string,
            make_derived(invalid_getter_none_exist),
        )
