import unittest

import cohdl
from cohdl import BitVector, Port
from cohdl import std


from cohdl_testutil import cocotb_util


class test_concurrent_wrappers_01(cohdl.Entity):
    port_a = Port.input(BitVector[4])
    port_b = Port.input(BitVector[4])

    port_out_assign = Port.output(BitVector[4])

    port_out_eval_or = Port.output(BitVector[4])
    port_out_call_or = Port.output(BitVector[4])

    port_out_eval_and = Port.output(BitVector[4])
    port_out_call_and = Port.output(BitVector[4])

    port_out_eval_xor = Port.output(BitVector[4])
    port_out_call_xor = Port.output(BitVector[4])

    def architecture(self):
        def or_inputs(a, b):
            return a | b

        def and_inputs(a, b):
            return a & b

        def xor_inputs(a, b):
            return a ^ b

        def assign(target, fn, *args, **kwargs):
            target <<= fn(*args, **kwargs)

        std.concurrent_assign(self.port_out_assign, self.port_a)

        std.concurrent_eval(self.port_out_eval_or, or_inputs, self.port_a, self.port_b)
        std.concurrent_eval(
            self.port_out_eval_and, and_inputs, self.port_a, b=self.port_b
        )
        std.concurrent_eval(
            self.port_out_eval_xor, xor_inputs, a=self.port_a, b=self.port_b
        )

        std.concurrent_call(
            assign, self.port_out_call_or, or_inputs, self.port_a, self.port_b
        )
        std.concurrent_call(
            assign, self.port_out_call_and, and_inputs, self.port_a, b=self.port_b
        )
        std.concurrent_call(
            assign, self.port_out_call_xor, xor_inputs, a=self.port_a, b=self.port_b
        )


@cocotb_util.test()
async def testbench_simple(dut: test_concurrent_wrappers_01):
    for a in range(16):
        for b in range(16):
            or_val = a | b
            and_val = a & b
            xor_val = a ^ b
            dut.port_a.value = a
            dut.port_b.value = b
            await cocotb_util.step()

            assert dut.port_out_assign == a
            assert dut.port_out_eval_or == or_val
            assert dut.port_out_call_or == or_val
            assert dut.port_out_eval_and == and_val
            assert dut.port_out_call_and == and_val
            assert dut.port_out_eval_xor == xor_val
            assert dut.port_out_call_xor == xor_val


class Unittest(unittest.TestCase):
    def test_concurrent(self):
        cocotb_util.run_cocotb_tests(
            test_concurrent_wrappers_01, __file__, self.__module__
        )
