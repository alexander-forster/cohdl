import unittest

from cohdl import (
    Unsigned,
    Signed,
    Bit,
    BitVector,
    Port,
    Signal,
    Variable,
    Temporary,
)


INP = Port.Direction.INPUT
OUT = Port.Direction.OUTPUT
INOUT = Port.Direction.INOUT


class TestInheritance(unittest.TestCase):
    def test_ports(self):
        for Wrapped in (
            Bit,
            BitVector[1],
            BitVector[2],
            Unsigned[3],
            Unsigned[4],
            Signed[7],
        ):
            self.assertTrue(isinstance(Port.input(Wrapped), Signal[Wrapped]))
            self.assertTrue(isinstance(Port.output(Wrapped), Signal[Wrapped]))
            self.assertTrue(isinstance(Port.inout(Wrapped), Signal[Wrapped]))
            self.assertFalse(isinstance(Port.input(Wrapped), Variable[Wrapped]))
            self.assertFalse(isinstance(Port.output(Wrapped), Variable[Wrapped]))
            self.assertFalse(isinstance(Port.inout(Wrapped), Variable[Wrapped]))
            self.assertFalse(isinstance(Port.input(Wrapped), Temporary[Wrapped]))
            self.assertFalse(isinstance(Port.output(Wrapped), Temporary[Wrapped]))
            self.assertFalse(isinstance(Port.inout(Wrapped), Temporary[Wrapped]))

            self.assertTrue(issubclass(Port[Wrapped, INP], Signal[Wrapped]))
            self.assertTrue(issubclass(Port[Wrapped, OUT], Signal[Wrapped]))
            self.assertTrue(issubclass(Port[Wrapped, INOUT], Signal[Wrapped]))
            self.assertFalse(issubclass(Port[Wrapped, INP], Variable[Wrapped]))
            self.assertFalse(issubclass(Port[Wrapped, OUT], Variable[Wrapped]))
            self.assertFalse(issubclass(Port[Wrapped, INOUT], Variable[Wrapped]))
            self.assertFalse(issubclass(Port[Wrapped, INP], Temporary[Wrapped]))
            self.assertFalse(issubclass(Port[Wrapped, OUT], Temporary[Wrapped]))
            self.assertFalse(issubclass(Port[Wrapped, INOUT], Temporary[Wrapped]))

            self.assertFalse(issubclass(Signal[Wrapped], Port[Wrapped, INP]))
            self.assertFalse(issubclass(Signal[Wrapped], Port[Wrapped, OUT]))
            self.assertFalse(issubclass(Signal[Wrapped], Port[Wrapped, INOUT]))
            self.assertFalse(issubclass(Variable[Wrapped], Port[Wrapped, INP]))
            self.assertFalse(issubclass(Variable[Wrapped], Port[Wrapped, OUT]))
            self.assertFalse(issubclass(Variable[Wrapped], Port[Wrapped, INOUT]))
            self.assertFalse(issubclass(Temporary[Wrapped], Port[Wrapped, INP]))
            self.assertFalse(issubclass(Temporary[Wrapped], Port[Wrapped, OUT]))
            self.assertFalse(issubclass(Temporary[Wrapped], Port[Wrapped, INOUT]))

    def test_vectors(self):
        for w in range(1, 8):
            self.assertTrue(isinstance(Port.input(BitVector[w]), Port[BitVector, INP]))
            self.assertFalse(
                isinstance(Port.input(BitVector[w]), Port[BitVector[w + 1], INP])
            )
            self.assertFalse(isinstance(Port.input(BitVector[w]), Port[BitVector, OUT]))
            self.assertFalse(
                isinstance(Port.input(BitVector[w]), Port[BitVector, INOUT])
            )

            self.assertTrue(isinstance(Port.output(BitVector[w]), Port[BitVector, OUT]))
            self.assertFalse(
                isinstance(Port.output(BitVector[w]), Port[BitVector[w + 1], OUT])
            )
            self.assertFalse(
                isinstance(Port.output(BitVector[w]), Port[BitVector, INP])
            )
            self.assertFalse(
                isinstance(Port.output(BitVector[w]), Port[BitVector, INOUT])
            )

            self.assertTrue(
                isinstance(Port.inout(BitVector[w]), Port[BitVector, INOUT])
            )
            self.assertFalse(
                isinstance(Port.inout(BitVector[w]), Port[BitVector[w + 1], INOUT])
            )
            self.assertFalse(isinstance(Port.inout(BitVector[w]), Port[BitVector, INP]))
            self.assertFalse(isinstance(Port.inout(BitVector[w]), Port[BitVector, OUT]))

    def test_signed_unsigned(self):
        for TQ in (Signal, Variable, Temporary):
            self.assertTrue(issubclass(TQ[Bit], TQ[Bit]))

            self.assertTrue(issubclass(TQ[BitVector], TQ[BitVector]))
            self.assertTrue(issubclass(TQ[Unsigned], TQ[BitVector]))
            self.assertTrue(issubclass(TQ[Signed], TQ[BitVector]))

            self.assertTrue(issubclass(TQ[BitVector[4]], TQ[BitVector[4]]))
            self.assertTrue(issubclass(TQ[Unsigned[4]], TQ[BitVector[4]]))
            self.assertTrue(issubclass(TQ[Signed[4]], TQ[BitVector[4]]))
            self.assertTrue(issubclass(TQ[BitVector[4]], TQ[BitVector]))
            self.assertTrue(issubclass(TQ[Unsigned[4]], TQ[BitVector]))
            self.assertTrue(issubclass(TQ[Signed[4]], TQ[BitVector]))

            self.assertFalse(issubclass(TQ[BitVector[4]], TQ[BitVector[3]]))
            self.assertFalse(issubclass(TQ[Unsigned[4]], TQ[BitVector[3]]))
            self.assertFalse(issubclass(TQ[Signed[4]], TQ[BitVector[3]]))

            self.assertFalse(issubclass(TQ[BitVector[4]], TQ[Unsigned[4]]))
            self.assertFalse(issubclass(TQ[BitVector[4]], TQ[Signed[4]]))
            self.assertFalse(issubclass(TQ[Signed[4]], TQ[Unsigned[4]]))
            self.assertFalse(issubclass(TQ[Unsigned[4]], TQ[Signed[4]]))
