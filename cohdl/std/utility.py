from cohdl._core._type_qualifier import TypeQualifier, Temporary
from cohdl._core import Bit, BitVector


def instance_check(val, type):
    return isinstance(TypeQualifier.decay(val), type)


def subclass_check(val, type):
    return issubclass(TypeQualifier.decay(val), type)


def binary_fold(fn, first, *args):
    if len(args) == 0:
        return Temporary(first)
    else:
        return fn(first, binary_fold(fn, *args))


def concat(first, *args):
    return binary_fold(lambda a, b: a @ b, first, *args)


def stretch(val: Bit | BitVector, factor: int):
    if instance_check(val, Bit):
        return concat(*[val for _ in range(factor)])
    elif instance_check(val, BitVector):
        return concat(*[stretch(b, factor) for b in val])
    else:
        raise AssertionError("invalid argument")


def apply_mask(old: BitVector, new: BitVector, mask: BitVector):
    assert old.width == new.width
    return (old & ~mask) | (new & mask)
