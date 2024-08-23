from __future__ import annotations

import unittest
import itertools

import cohdl
from cohdl import Bit, BitVector, Port, Unsigned, Signed, select_with, Null, Full

from cohdl import std

from cohdl_testutil import cocotb_util

ctx_type = None

# compile feedback used to test that
# entity instances are not cached between builds
compile_feedback = None


@cohdl.pyeval
def is_numeric(val):
    return issubclass(std.base_type(val), (Signed, Unsigned))


@cohdl.pyeval
def vec_type(val):
    t = std.base_type(val)

    if issubclass(t, Unsigned):
        return Unsigned
    if issubclass(t, Signed):
        return Signed
    if issubclass(t, BitVector):
        return BitVector
    raise AssertionError("not a vec type")


@cohdl.pyeval
def dict_insert(d, op_name, lhs_name, rhs_name, val):
    d[f"{op_name}_{lhs_name}_{rhs_name}"] = val


def compare_all(a_v, a_u, a_s, b_v, b_u, b_s, c_v, c_u, c_s):
    vals = {
        "av": a_v,
        "au": a_u,
        "as": a_s,
        "bv": b_v,
        "bu": b_u,
        "bs": b_s,
        "cv": c_v,
        "cu": c_u,
        "cs": c_s,
    }

    result = {}

    for (lhs_name, lhs), (rhs_name, rhs) in std.as_pyeval(
        itertools.product, vals.items(), repeat=2
    ):
        if vec_type(lhs) is vec_type(rhs):
            compare_equality = (lhs.width == rhs.width) or (is_numeric(lhs))

            if compare_equality:
                dict_insert(result, "eq", lhs_name, rhs_name, lhs == rhs)
                dict_insert(result, "ne", lhs_name, rhs_name, lhs != rhs)

            if is_numeric(lhs):
                dict_insert(result, "lt", lhs_name, rhs_name, lhs < rhs)
                dict_insert(result, "le", lhs_name, rhs_name, lhs <= rhs)
                dict_insert(result, "gt", lhs_name, rhs_name, lhs > rhs)
                dict_insert(result, "ge", lhs_name, rhs_name, lhs >= rhs)

    return result


class test_compare_01(cohdl.Entity):
    a_v = Port.input(BitVector[2])
    a_u = Port.input(Unsigned[2])
    a_s = Port.input(Signed[2])

    b_v = Port.input(BitVector[4])
    b_u = Port.input(Unsigned[4])
    b_s = Port.input(Signed[4])

    c_v = Port.input(BitVector[6])
    c_u = Port.input(Unsigned[6])
    c_s = Port.input(Signed[6])

    def architecture(self):

        @ctx_type
        def logic_compare_01():

            result = compare_all(
                a_v=self.a_v,
                a_u=self.a_u,
                a_s=self.a_s,
                b_v=self.b_v,
                b_u=self.b_u,
                b_s=self.b_s,
                c_v=self.c_v,
                c_u=self.c_u,
                c_s=self.c_s,
            )

            for name, val in result.items():
                p = std.as_pyeval(Port.output, Bit, name=name)
                std.add_entity_port(type(self), p)
                p <<= val


#
# test code
#


def check_result(a_v, a_u, a_s, b_v, b_u, b_s, c_v, c_u, c_s, result: dict[str, int]):
    a_signed = a_s if a_s < 2 else a_s - 4
    b_signed = b_s if b_s < 8 else b_s - 16
    c_signed = c_s if c_s < 32 else c_s - 64

    def check(name, expected):
        assert result[name] == expected, f"failed for check {name}"
        del result[name]

    if True:
        check("eq_av_av", a_v == a_v)
        check("eq_au_au", a_u == a_u)
        check("eq_as_as", a_s == a_s)

        check("eq_bv_bv", b_v == b_v)
        check("eq_bu_bu", b_u == b_u)
        check("eq_bs_bs", b_s == b_s)

        check("eq_cv_cv", c_v == c_v)
        check("eq_cu_cu", c_u == c_u)
        check("eq_cs_cs", c_s == c_s)

        check("eq_au_bu", a_u == b_u)
        check("eq_au_cu", a_u == c_u)
        check("eq_bu_au", b_u == a_u)
        check("eq_bu_cu", b_u == c_u)
        check("eq_cu_au", c_u == a_u)
        check("eq_cu_bu", c_u == b_u)

        check("eq_as_bs", a_signed == b_signed)
        check("eq_as_cs", a_signed == c_signed)
        check("eq_bs_as", b_signed == a_signed)
        check("eq_bs_cs", b_signed == c_signed)
        check("eq_cs_as", c_signed == a_signed)
        check("eq_cs_bs", c_signed == b_signed)

    if True:
        check("ne_av_av", a_v != a_v)
        check("ne_au_au", a_u != a_u)
        check("ne_as_as", a_s != a_s)

        check("ne_bv_bv", b_v != b_v)
        check("ne_bu_bu", b_u != b_u)
        check("ne_bs_bs", b_s != b_s)

        check("ne_cv_cv", c_v != c_v)
        check("ne_cu_cu", c_u != c_u)
        check("ne_cs_cs", c_s != c_s)

        check("ne_au_bu", a_u != b_u)
        check("ne_au_cu", a_u != c_u)
        check("ne_bu_au", b_u != a_u)
        check("ne_bu_cu", b_u != c_u)
        check("ne_cu_au", c_u != a_u)
        check("ne_cu_bu", c_u != b_u)

        check("ne_as_bs", a_signed != b_signed)
        check("ne_as_cs", a_signed != c_signed)
        check("ne_bs_as", b_signed != a_signed)
        check("ne_bs_cs", b_signed != c_signed)
        check("ne_cs_as", c_signed != a_signed)
        check("ne_cs_bs", c_signed != b_signed)

    if True:
        check("lt_au_au", a_u < a_u)
        check("lt_au_bu", a_u < b_u)
        check("lt_au_cu", a_u < c_u)

        check("lt_bu_au", b_u < a_u)
        check("lt_bu_bu", b_u < b_u)
        check("lt_bu_cu", b_u < c_u)

        check("lt_cu_au", c_u < a_u)
        check("lt_cu_bu", c_u < b_u)
        check("lt_cu_cu", c_u < c_u)

        check("lt_as_as", a_signed < a_signed)
        check("lt_as_bs", a_signed < b_signed)
        check("lt_as_cs", a_signed < c_signed)

        check("lt_bs_as", b_signed < a_signed)
        check("lt_bs_bs", b_signed < b_signed)
        check("lt_bs_cs", b_signed < c_signed)

        check("lt_cs_as", c_signed < a_signed)
        check("lt_cs_bs", c_signed < b_signed)
        check("lt_cs_cs", c_signed < c_signed)

    if True:
        check("le_au_au", a_u <= a_u)
        check("le_au_bu", a_u <= b_u)
        check("le_au_cu", a_u <= c_u)

        check("le_bu_au", b_u <= a_u)
        check("le_bu_bu", b_u <= b_u)
        check("le_bu_cu", b_u <= c_u)

        check("le_cu_au", c_u <= a_u)
        check("le_cu_bu", c_u <= b_u)
        check("le_cu_cu", c_u <= c_u)

        check("le_as_as", a_signed <= a_signed)
        check("le_as_bs", a_signed <= b_signed)
        check("le_as_cs", a_signed <= c_signed)

        check("le_bs_as", b_signed <= a_signed)
        check("le_bs_bs", b_signed <= b_signed)
        check("le_bs_cs", b_signed <= c_signed)

        check("le_cs_as", c_signed <= a_signed)
        check("le_cs_bs", c_signed <= b_signed)
        check("le_cs_cs", c_signed <= c_signed)

    #

    if True:
        check("gt_au_au", a_u > a_u)
        check("gt_au_bu", a_u > b_u)
        check("gt_au_cu", a_u > c_u)

        check("gt_bu_au", b_u > a_u)
        check("gt_bu_bu", b_u > b_u)
        check("gt_bu_cu", b_u > c_u)

        check("gt_cu_au", c_u > a_u)
        check("gt_cu_bu", c_u > b_u)
        check("gt_cu_cu", c_u > c_u)

        check("gt_as_as", a_signed > a_signed)
        check("gt_as_bs", a_signed > b_signed)
        check("gt_as_cs", a_signed > c_signed)

        check("gt_bs_as", b_signed > a_signed)
        check("gt_bs_bs", b_signed > b_signed)
        check("gt_bs_cs", b_signed > c_signed)

        check("gt_cs_as", c_signed > a_signed)
        check("gt_cs_bs", c_signed > b_signed)
        check("gt_cs_cs", c_signed > c_signed)

    if True:
        check("ge_au_au", a_u >= a_u)
        check("ge_au_bu", a_u >= b_u)
        check("ge_au_cu", a_u >= c_u)

        check("ge_bu_au", b_u >= a_u)
        check("ge_bu_bu", b_u >= b_u)
        check("ge_bu_cu", b_u >= c_u)

        check("ge_cu_au", c_u >= a_u)
        check("ge_cu_bu", c_u >= b_u)
        check("ge_cu_cu", c_u >= c_u)

        check("ge_as_as", a_signed >= a_signed)
        check("ge_as_bs", a_signed >= b_signed)
        check("ge_as_cs", a_signed >= c_signed)

        check("ge_bs_as", b_signed >= a_signed)
        check("ge_bs_bs", b_signed >= b_signed)
        check("ge_bs_cs", b_signed >= c_signed)

        check("ge_cs_as", c_signed >= a_signed)
        check("ge_cs_bs", c_signed >= b_signed)
        check("ge_cs_cs", c_signed >= c_signed)

    if len(result) != 0:
        for name in result:
            print(" not checked ", name)
        assert "not all results have been checked"


@cocotb_util.test()
async def testbench_compare_01(dut: test_compare_01):
    gen2 = cocotb_util.ConstrainedGenerator(2)
    gen4 = cocotb_util.ConstrainedGenerator(4)
    gen6 = cocotb_util.ConstrainedGenerator(6)

    for _ in range(128):
        a = gen2.random(3)
        b = gen4.random(3)
        c = gen6.random(3)

        a_v, a_u, a_s = a[0].as_int(), a[1].as_int(), a[2].as_int()
        b_v, b_u, b_s = b[0].as_int(), b[1].as_int(), b[2].as_int()
        c_v, c_u, c_s = c[0].as_int(), c[1].as_int(), c[2].as_int()

        dut.a_v.value = a_v
        dut.a_u.value = a_u
        dut.a_s.value = a_s
        dut.b_v.value = b_v
        dut.b_u.value = b_u
        dut.b_s.value = b_s
        dut.c_v.value = c_v
        dut.c_u.value = c_u
        dut.c_s.value = c_s

        await cocotb_util.step()

        static_result = compare_all(
            a_v=BitVector[2](a[0].as_str()),
            a_u=Unsigned[2](a[1].as_str()),
            a_s=Signed[2](a[2].as_str()),
            b_v=BitVector[4](b[0].as_str()),
            b_u=Unsigned[4](b[1].as_str()),
            b_s=Signed[4](b[2].as_str()),
            c_v=BitVector[6](c[0].as_str()),
            c_u=Unsigned[6](c[1].as_str()),
            c_s=Signed[6](c[2].as_str()),
        )

        sim_result = {}

        for name in static_result:
            sim_result[name] = bool(getattr(dut, name).value)

        for result in (static_result, sim_result):
            check_result(
                a_v=a_v,
                a_u=a_u,
                a_s=a_s,
                b_v=b_v,
                b_u=b_u,
                b_s=b_s,
                c_v=c_v,
                c_u=c_u,
                c_s=c_s,
                result=result,
            )


class Unittest(unittest.TestCase):
    def test_compare_01(self):
        global ctx_type, sw_type

        for ctx in (std.concurrent, std.sequential):
            ctx_type = ctx
            cocotb_util.run_cocotb_tests(test_compare_01, __file__, self.__module__)
