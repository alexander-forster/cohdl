import unittest

import cohdl
from cohdl import BitVector, Port, Signal, Signed, vhdl
from cohdl import std

from abc import abstractmethod, ABCMeta


from cohdl_testutil import cocotb_util


class TestWriter(metaclass=ABCMeta):
    def extern(self):
        return type(self.name(), (cohdl.Entity,), self.ports(), extern=True)

    def result(self, arg, width, name):
        self.assign(self.make_output(BitVector[width], name), self.to_slv(arg))

    @abstractmethod
    def write(self):
        ...

    @abstractmethod
    def name(self):
        ...

    @abstractmethod
    def ports(self):
        ...

    @abstractmethod
    def make_signal(self, type, name):
        ...

    @abstractmethod
    def make_input(self, type, name):
        ...

    @abstractmethod
    def make_output(self, type, name):
        ...

    @abstractmethod
    def start_section(self, name: str):
        ...

    @abstractmethod
    def to_slv(self, obj):
        ...

    @abstractmethod
    def to_sfixed(self, obj, left, right):
        ...

    @abstractmethod
    def assign(self, out: Port, arg):
        ...

    @abstractmethod
    def add(self, a, b):
        ...

    @abstractmethod
    def resize(
        self,
        arg,
        left,
        right,
        round_style: std.FixedRoundStyle,
        overflow_style: std.FixedOverflowStyle,
    ):
        ...


class PseudoSignal:
    def __init__(self, obj, name):
        self.obj = obj
        self._name = name

    def name(self):
        return self._name


class VhdlTestWriter(TestWriter):
    def __init__(self, test_fn, entity_name: str):
        self._entity_name = entity_name
        self._inputs: list[Port] = []
        self._outputs: list[Port] = []
        self._used_signals: list[Signal] = []

        self._body: list[str] = []

        test_fn(self)

    def _val(self, arg):
        if isinstance(arg, PseudoSignal):
            arg = arg.name()

        if isinstance(arg, Signal):
            return arg.name()
        return str(arg)

    def _add_line(self, line: str):
        self._body.append(f"    {line}")

    #
    #
    #

    def ports(self):
        return {
            **{port.name(): port for port in self._inputs},
            **{port.name(): port for port in self._outputs},
        }

    def name(self):
        return self._entity_name

    def write(self, file=None):
        def vhdl_type(obj):
            if isinstance(obj, PseudoSignal):
                obj = obj.obj

            if std.instance_check(obj, Signed):
                return f"signed({len(obj)-1} downto {0})"
            elif std.instance_check(obj, BitVector):
                return f"std_logic_vector({len(obj)-1} downto {0})"
            elif std.instance_check(obj, std.SFixed):
                return f"sfixed({obj.left()} downto {obj.right()})"
            raise

        def write(*args):
            print(*args, file=file)

        name = self._entity_name

        # write header
        write("library IEEE;")
        write("use IEEE.STD_LOGIC_1164.ALL;")
        write("use IEEE.fixed_pkg.all;")
        write("use IEEE.NUMERIC_STD.ALL;")
        write("use ieee.fixed_float_types.all;")

        write()

        write(f"entity {name} is")
        write(f"port(")

        for inp in self._inputs:
            write(f"    {inp.name()}  : in {vhdl_type(inp)};")

        for out in self._outputs[:-1]:
            write(f"    {out.name()}  : out {vhdl_type(out)};")
        out = self._outputs[-1]
        write(f"    {out.name()}  : out {vhdl_type(out)}")

        write(");")
        write(f"end {name};")

        write()

        write(f"architecture arch of {name} is")

        for sig in self._used_signals:
            write(f"    signal {sig.name()}  :  {vhdl_type(sig)};")

        write("begin")
        write()

        for line in self._body:
            write(line)

        write()
        write("end arch;")

    def make_signal(self, type, name):
        if issubclass(type, std.SFixed):
            sig = PseudoSignal(type.signal(), name)
        else:
            sig = Signal[type](name=name)
        self._used_signals.append(sig)
        return sig

    def make_input(self, type, name):
        port = Port[type, Port.Direction.INPUT](name=name)
        self._inputs.append(port)
        return port

    def make_output(self, type, name):
        port = Port[type, Port.Direction.OUTPUT](name=name)
        self._outputs.append(port)
        return port

    def start_section(self, name: str):
        self._add_line("")
        self._add_line(f"-- {name}")

    def to_slv(self, obj):
        return f"to_slv({self._val(obj)})"

    def to_sfixed(self, obj, left, right):
        return f"to_sfixed({self._val(obj)}, {self._val(left)}, {self._val(right)})"

    def assign(self, out: Port, arg):
        self._add_line(f"{self._val(out)} <= {self._val(arg)};")

    def add(self, a, b):
        return f"{self._val(a)} + {self._val(b)}"

    def resize(
        self,
        arg,
        left,
        right,
        round_style: std.FixedRoundStyle,
        overflow_style: std.FixedOverflowStyle,
    ):
        overflow_style = {
            std.FixedOverflowStyle.WRAP: "fixed_wrap",
            std.FixedOverflowStyle.SATURATE: "fixed_saturate",
        }[overflow_style]

        round_style = {
            std.FixedRoundStyle.ROUND: "fixed_round",
            std.FixedRoundStyle.TRUNCATE: "fixed_truncate",
        }[round_style]

        return f"resize(arg => {self._val(arg)}, left_index => {left}, right_index => {right}, round_style => {round_style}, overflow_style => {overflow_style})"


class CoHDL_TestWriter(TestWriter):
    def __init__(self, test_fn, entity_name: str):
        class CoHDLTest(cohdl.Entity, name=entity_name):
            def architecture(entity):
                @cohdl.concurrent_context
                def logic():
                    test_fn(self)

        self._entity_name = entity_name
        self._Entity = CoHDLTest

    def name(self):
        return self._entity_name

    def ports(self):
        return self._Entity._info.ports

    def write(self, file=None):
        print(std.VhdlCompiler.to_string(self._Entity), file=file)

    def make_signal(self, type, name):
        if issubclass(type, std.SFixed):
            return type.signal()
        else:
            return Signal[type](name=name)

    @cohdl.consteval
    def make_input(self, type, name):
        port = Port[type, Port.Direction.INPUT](name=name)
        self._Entity._info.add_port(name, port)
        return port

    @cohdl.consteval
    def make_output(self, type, name):
        port = Port[type, Port.Direction.OUTPUT](name=name)
        self._Entity._info.add_port(name, port)
        return port

    def start_section(self, name: str):
        f"{vhdl:-- {name}}"
        return

    def to_slv(self, obj):
        return obj._val

    def to_sfixed(self, obj, left, right):
        return std.SFixed[left:right](raw=obj.signed)

    def assign(self, out: Port, arg):
        out <<= arg

    def add(self, a, b):
        return a + b

    def resize(
        self,
        arg,
        left,
        right,
        round_style: std.FixedRoundStyle,
        overflow_style: std.FixedOverflowStyle,
    ):
        return arg.resize[left:right](round_style, overflow_style)


def make_combined(test_fn, name):
    import os

    local_dir = os.path.dirname(os.path.realpath(__file__))
    build_dir = f"{local_dir}/test_build"
    vhdl_path = f"{build_dir}/{name}.vhd"
    sim_dir = f"{local_dir}/test_sim"

    with open(vhdl_path, "w") as file:
        vhdl_writer = VhdlTestWriter(test_fn, f"vhdl_{name}")
        cohdl_writer = CoHDL_TestWriter(test_fn, f"cohdl_{name}")

        print(file=file)
        print("-- vhdl reference entity", file=file)
        print(file=file)
        vhdl_writer.write(file)
        print(file=file)
        print("-- cohdl generated entity", file=file)
        print(file=file)
        cohdl_writer.write(file)

        vhdl_ports = vhdl_writer.ports()
        cohdl_ports = cohdl_writer.ports()

        vhdl_prefix = "vhdl"
        cohdl_prefix = "cohdl"

        vhdl_entity = vhdl_writer.extern()
        cohdl_entity = cohdl_writer.extern()

        assert len(vhdl_ports) == len(cohdl_ports)

        class CombinedTest(cohdl.Entity, name=name):
            def architecture(self):
                for port_name, port in vhdl_ports.items():
                    port_name = f"{vhdl_prefix}_{port_name}"
                    port._name = port_name
                    CombinedTest._info.add_port(port_name, port)

                for port_name, port in cohdl_ports.items():
                    port_name = f"{cohdl_prefix}_{port_name}"
                    port._name = port_name
                    CombinedTest._info.add_port(port_name, port)

                vhdl_entity(
                    **{port_name: port for port_name, port in vhdl_ports.items()}
                )

                cohdl_entity(
                    **{port_name: port for port_name, port in cohdl_ports.items()}
                )

        print(file=file)
        print("-- test wrapper entity", file=file)
        print(file=file)
        print(std.VhdlCompiler.to_string(CombinedTest), file=file)


#
#
#
#
#
#
#
#
#
#


@cohdl.consteval
def fmt_string(str: str, *args):
    return str.format(*args).replace("-", "neg")


@cohdl.consteval
def add_width(la, ra, lb, rb):
    w = max(la, lb) + 2 - min(ra, rb)
    name = f"out_add_{la}_{ra}_{lb}_{rb}".replace("-", "neg")
    return w, name


@cohdl.consteval
def round_str(la, ra, lb, rb, overflow: std.FixedOverflowStyle, round):
    return f"out_resize_{la}_{ra}_{lb}_{rb}_{overflow.name}_{round.name}".replace(
        "-", "neg"
    )


def test_fixed_math(t: TestWriter):
    inp_a = t.make_input(BitVector[8], "inp_a")
    inp_b = t.make_input(BitVector[8], "inp_b")

    a_signals = {
        (offset + 7, offset): t.make_signal(
            std.SFixed[offset + 7 : offset],
            name=fmt_string("sig_a_{}", offset),
        )
        for offset in (0, 1, -1)
    }
    b_signals = {
        (offset + 7, offset): t.make_signal(
            std.SFixed[offset + 7 : offset],
            name=fmt_string("sig_b_{}", offset),
        )
        for offset in (0, 1, -1)
    }

    t.start_section("init signals")

    for (l, r), sig in a_signals.items():
        t.assign(sig, t.to_sfixed(inp_a, l, r))

    for (l, r), sig in b_signals.items():
        t.assign(sig, t.to_sfixed(inp_b, l, r))

    t.start_section("test addition")

    for (la, ra), sig_a in a_signals.items():
        for (lb, rb), sig_b in b_signals.items():
            w, name = add_width(la, ra, lb, rb)
            t.result(t.add(sig_a, sig_b), w, name=name)

    t.start_section("test resize")

    for (la, ra), sig in a_signals.items():
        for width in (10, 8, 5, 2):
            for offset in (0, 1, -1):
                lb = width + offset - 1
                rb = offset

                for round in (std.FixedRoundStyle.ROUND, std.FixedRoundStyle.TRUNCATE):
                    for overflow in (
                        std.FixedOverflowStyle.WRAP,
                        std.FixedOverflowStyle.SATURATE,
                    ):
                        print(la, ra, " : ", lb, rb, width, offset)

                        t.result(
                            t.resize(sig, lb, rb, round, overflow),
                            width,
                            name=round_str(la, ra, lb, rb, round, overflow),
                        )


test_fn = test_fixed_math


@cocotb_util.test()
async def testbench_simple(dut):
    ports = VhdlTestWriter(test_fn, "").ports()

    name_pairs = [(f"vhdl_{name}", f"cohdl_{name}") for name in ports.keys()]

    cnt = 0
    a = 0
    b = 0

    def set_random():
        nonlocal a, b
        a = 12 + cnt
        b = 23 + cnt
        dut.vhdl_inp_a.value = a
        dut.cohdl_inp_a.value = a
        dut.vhdl_inp_b.value = b
        dut.cohdl_inp_b.value = b

    for i in range(20):
        set_random()
        cnt += 1
        await cocotb_util.step()

        for v, c in name_pairs:
            val_vhdl = getattr(dut, v).value
            val_cohdl = getattr(dut, c).value

            if val_cohdl != val_vhdl:
                print(
                    f"ERR: {dut.vhdl_inp_a.value=} {b=}   | {val_vhdl=}  , {val_cohdl=}  | ({v})"
                )
                assert val_cohdl == val_vhdl


class Unittest(unittest.TestCase):
    def test_concurrent(self):
        make_combined(test_fn, test_fn.__name__)

        class DummyEntity(cohdl.Entity, name=test_fn.__name__):
            ...

        DummyEntity.__name__ = test_fn.__name__

        cocotb_util.run_cocotb_tests(
            DummyEntity,
            __file__,
            self.__module__,
            no_build=True,
            compile_args=["--std=08"],
        )
