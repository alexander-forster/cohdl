from __future__ import annotations

import enum


class UnaryOperator(enum.Enum):
    BOOL = enum.auto()
    NEG = enum.auto()
    POS = enum.auto()
    INV = enum.auto()
    NOT = enum.auto()
    ABS = enum.auto()


class BinaryOperator(enum.Enum):
    AND = enum.auto()
    OR = enum.auto()

    BIT_AND = enum.auto()
    BIT_OR = enum.auto()
    BIT_XOR = enum.auto()

    ADD = enum.auto()
    SUB = enum.auto()

    MUL = enum.auto()
    DIV = enum.auto()
    MOD = enum.auto()
    FLOOR_DIV = enum.auto()

    CONCAT = enum.auto()

    LSHIFT = enum.auto()
    RSHIFT = enum.auto()


class ComparisonOperator(enum.Enum):
    EQ = enum.auto()
    NE = enum.auto()
    GT = enum.auto()
    LT = enum.auto()
    GE = enum.auto()
    LE = enum.auto()


class _IntrinsicOp:
    def __init__(self, result):
        self.result = result


class _IntrinsicUnaryOp(_IntrinsicOp):
    def __init__(self, op: UnaryOperator, result, arg):
        super().__init__(result)
        self.op = op
        self.arg = arg


class _IntrinsicBinOp(_IntrinsicOp):
    def __init__(self, op: BinaryOperator, result, lhs, rhs):
        super().__init__(result)
        self.op = op
        self.lhs = lhs
        self.rhs = rhs


class _IntrinsicComparison(_IntrinsicOp):
    def __init__(self, op: ComparisonOperator, result, lhs, rhs):
        super().__init__(result)
        self.op = op
        self.lhs = lhs
        self.rhs = rhs


class _IntrinsicConstElemAccess:
    def __init__(self, obj):
        # dummy wrapper type
        # only used to indicate to the parser, that
        # an item access was performed with constant arguments

        self.obj = obj


class _IntrinsicElemAccess:
    def __init__(self, obj, index, index_temp):
        # when __getitem__ is called with a non-constant argument
        # store the current state of the index in a temporary
        # and use the value when assignments to the value are performed

        self.obj = obj
        self.index = index
        self.index_temp = index_temp


class AssignMode(enum.Enum):
    VALUE = enum.auto()
    NEXT = enum.auto()
    PUSH = enum.auto()
    AUTO = enum.auto()
    _TEMP = enum.auto()


class _IntrinsicAssignment:
    def __init__(self, target, source, mode):
        self.target = target
        self.source = source
        self.mode = mode


class _IntrinsicDeclaration:
    def __init__(self, new_obj, assigned_value, delayed_init=False):
        self.new_obj = new_obj
        self.assigned_value = assigned_value
        self.delayed_init = delayed_init


class _IntrinsicSynthesizableFunctionCall:
    """
    when returned from an intrinsic function the callable
    is evaluated using the given args/kwargs at the location
    the intrinsic function was called.
    """

    def __init__(self, callable, args, kwargs):
        assert isinstance(args, list)
        assert isinstance(kwargs, dict)

        self.callable = callable
        self.args = args
        self.kwargs = kwargs
