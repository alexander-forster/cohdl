from __future__ import annotations

from typing import Tuple, Any

import os
import pathlib
import random
import shutil
from cocotb_test import simulator
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from cohdl import std


test = cocotb.test


class ConstrainedGenerator:
    def __init__(self, width):
        self.width = width
        self.min_value = 0
        self.max_value = 2**width - 1

    def random(self, cnt: int | None = None, *, required=[]):
        if cnt is None:
            return ConstraindValue(
                self.width, random.randint(self.min_value, self.max_value)
            )

        return [
            *[ConstraindValue(self.width, val) for val in required],
            *[
                ConstraindValue(
                    self.width, random.randint(self.min_value, self.max_value)
                )
                for _ in range(cnt)
            ],
        ]

    def all(self):
        return [
            ConstraindValue(self.width, val)
            for val in range(self.min_value, self.max_value + 1)
        ]

    def null(self):
        return ConstraindValue(self.width, 0)

    def full(self):
        return ~self.null()


class ConstraindValue:
    def __init__(self, width: int, value: int = 0, *, default=None, resize=False):
        self.width = width
        self.value = 0
        self.default = default

        if resize:
            value = ((1 << width) - 1) & value

        self.assign(value)

    def copy(self):
        return ConstraindValue(self.width, self.value, default=self.default)

    def reset(self):
        if self.default is not None:
            self.assign(self.default)

    def randomize(self):
        self.assign(random.randint(0, 2**self.width - 1))

    def __str__(self):
        return self.as_str()

    def __repr__(self):
        return self.as_str()

    def __bool__(self):
        return bool(self.value)

    def get_bit(self, index):
        if index < 0:
            index = self.width + index
        assert 0 <= index < self.width, f"{index=}, {self.width=}"

        return ConstraindValue(1, (self.value >> index) & 1)

    def get_slice(self, start, stop):
        stop = stop + 1
        assert 0 <= start < stop, f"{start=}, {stop=}"
        width = stop - start
        value = self.value >> start
        value &= (1 << width) - 1
        return ConstraindValue(width, value)

    def __getitem__(self, index):
        if isinstance(index, slice):
            assert index.step is None
            return self.get_slice(index.start, index.stop)

        return self.get_bit(index)

    def assign(self, value):
        if isinstance(value, ConstraindValue):
            value = value.value
        if isinstance(value, str):
            int_value = 0
            for bit in value[::-1]:
                int_value *= 2
                if bit == "1":
                    int_value += 1
            value = int_value

        assert isinstance(value, int)
        assert value.bit_length() <= self.width
        self.value = value

    def set_bit(self, index):
        self.value |= 1 << index

    def as_str(self):
        bits = bin(self.value)[2:]

        assert len(bits) <= self.width

        return ("0" * (self.width - len(bits))) + bits

    def as_int(self):
        return self.value

    def inverse(self):
        new_val = (self.value) | (1 << self.width)
        new_val = ~new_val
        new_val = new_val + 2 ** (self.width + 1)
        return ConstraindValue(self.width, new_val)

    def __iter__(self):
        for i in range(self.width):
            yield self.get_bit(i)

    def __len__(self):
        return self.width

    def __invert__(self):
        return self.inverse()

    def __and__(self, other):
        assert self.width == other.width
        return ConstraindValue(self.width, self.value & other.value)

    def __or__(self, other):
        assert self.width == other.width
        return ConstraindValue(self.width, self.value | other.value)

    def __xor__(self, other):
        assert self.width == other.width
        return ConstraindValue(self.width, self.value ^ other.value)

    def __lshift__(self, shift):
        return ConstraindValue(
            self.width, (self.value << shift) & ((1 << self.width) - 1)
        )

    def __rshift__(self, shift):
        return ConstraindValue(self.width, self.value >> shift)

    def signed_rshift(self, shift):
        val = (self.signed() >> shift) & ((1 << self.width) - 1)
        return ConstraindValue(self.width, val)

    def resize(self, width):
        resized_value = ((1 << width) - 1) & self.value
        return ConstraindValue(width, resized_value)

    def signed(self):
        if self.value >= 2 ** (self.width - 1):
            return self.value - (2**self.width)
        return self.value

    def __eq__(self, other):
        if isinstance(other, int):
            return self.value == other
        if isinstance(other, str):
            return ConstraindValue(self.width, other) == self

        assert isinstance(other, ConstraindValue)
        return self.value == other.value

    def __lt__(self, other):
        if isinstance(other, ConstraindValue):
            return self.value < other.value
        return self.value < other

    def __add__(self, other):
        if isinstance(other, ConstraindValue):
            width = max(self.width, other.width)
            value = self.value + other.value
        else:
            width = self.width
            value = self.value + other

        return ConstraindValue(width, value, resize=True)

    def __sub__(self, other):
        if isinstance(other, ConstraindValue):
            width = max(self.width, other.width)
            maxval = 2**width
            value = (self.value - other.value + maxval) % maxval
        else:
            width = self.width
            value = self.value - other
        return ConstraindValue(width, value)

    def __radd__(self, other):
        if isinstance(other, ConstraindValue):
            width = max(self.width, other.width)
            value = other.value + self.value
        else:
            width = self.width
            value = other + self.value

        return ConstraindValue(width, value, resize=True)

    def __rsub__(self, other):
        if isinstance(other, ConstraindValue):
            width = max(self.width, other.width)
            maxval = 2**width
            value = (other.value - self.value + maxval) % maxval
        else:
            width = self.width
            maxval = 2**width
            value = (other - self.value + maxval) % maxval
        return ConstraindValue(width, value)

    def __mul__(self, other):
        if isinstance(other, ConstraindValue):
            width = self.width + other.width
            value = self.value * other.value
        else:
            width = self.width + other.bit_length()
            value = self.value * other
        return ConstraindValue(width, value)

    def __matmul__(self, other):
        assert isinstance(other, ConstraindValue)
        val = (self.value << other.width) | other.value
        return ConstraindValue(self.width + other.width, val)


class TestValue:
    @staticmethod
    def random_values(width: int, cnt: int):
        ...

    def __init__(self, value):
        self.val = value


def run_cocotb_tests(
    entity,
    file,
    module,
    *,
    no_build=False,
    build_files=[],
    extra_env=None,
    relatilve_vhdl_sources=None,
    vhdl_sources=None,
    sim_args=None,
    **kwargs,
):
    entity_name = entity.__name__
    local_dir = os.path.dirname(os.path.realpath(file))
    build_dir = f"{local_dir}/test_build"
    vhdl_path = f"{build_dir}/{entity_name}.vhd"
    sim_dir = f"{local_dir}/test_sim"

    if sim_args is None:
        sim_args = []

    if vhdl_sources is None:
        vhdl_sources = []

    if relatilve_vhdl_sources is not None:
        for path in relatilve_vhdl_sources:
            vhdl_sources.append(f"{local_dir}/{path}")

    if not no_build:
        if pathlib.Path(build_dir).exists():
            shutil.rmtree(build_dir)
        if pathlib.Path(sim_dir).exists():
            shutil.rmtree(sim_dir)

        pathlib.Path(build_dir).mkdir()
        pathlib.Path(sim_dir).mkdir()
        std.VhdlCompiler.to_dir(entity, build_dir)

    simulator.run(
        simulator="ghdl",
        sim_args=["--vcd=waveform.vcd", *sim_args],
        sim_build=sim_dir,
        vhdl_sources=[
            vhdl_path,
            *[f"{build_dir}/{filename}" for filename in build_files],
            *vhdl_sources,
        ],
        toplevel=entity_name,
        module=str(module),
        extra_env=extra_env,
        **kwargs,
    )


async def step():
    await cocotb.triggers.Timer(1)


def assign(target, value):
    target.value = cast_value(value)


def compare(dut_value, expected):
    expected = cast_value(expected)
    return dut_value.value == expected


def cast_value(val):
    if isinstance(val, ConstraindValue):
        return val.value
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        return int(val, 2)
    return int(val.value)


def _do_checks(
    checks: list[Tuple[Any, Any] | Tuple[Any, Any, Any] | None], check_msg=None
):
    for check in checks:
        if check is None:
            continue

        if len(check) == 2:
            signal, expected = check
            msg = signal.get_definition_name()
        else:
            signal, expected, msg = check
        expected = cast_value(expected)

        if check_msg is not None:
            msg = f"{check_msg=}, {msg=}"

        if expected < 0:
            signed_value = signal.value.get_value_signed()
            assert signed_value == expected, f"{msg} ({signed_value=}, {expected=})"
        else:
            assert signal.value == expected, f"{msg} ({signal.value=}, {expected=})"


async def check_concurrent(
    stim: list[Tuple[Any, Any]],
    checks: list[Tuple[Any, Any] | Tuple[Any, Any, Any] | None],
    check_msg=None,
):
    for signal, value in stim:
        signal.value = cast_value(value)

    await cocotb.triggers.Timer(1)

    _do_checks(checks, check_msg)


async def check_sequential(
    event,
    stim: list[Tuple[Any, Any]],
    checks: list[Tuple[Any, Any] | Tuple[Any, Any, Any] | None],
    check_msg=None,
):
    for signal, value in stim:
        signal.value = cast_value(value)

    await event
    await event
    await cocotb.triggers.Timer(1)

    _do_checks(checks, check_msg)


class SequentialTest:
    def __init__(self, clk):
        cocotb.start_soon(Clock(clk, 1, units="ns").start())
        self.clk = clk

    async def delta(self):
        await step()

    async def tick(self, cnt=1):
        for _ in range(cnt):
            await RisingEdge(self.clk)
        await step()

    async def check_next_tick(
        self,
        stim: list[Tuple[Any, Any]],
        checks: list[Tuple[Any, Any] | Tuple[Any, Any, Any] | None],
        check_msg=None,
    ):
        return await check_sequential(RisingEdge(self.clk), stim, checks, check_msg)
