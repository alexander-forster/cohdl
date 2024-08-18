from __future__ import annotations

import enum

from cohdl._core._intrinsic import (
    _intrinsic,
    _intrinsic_replacement,
    _intrinsic_property,
)
from cohdl._core import _intrinsic_operations as intr_op
from cohdl._core._intrinsic_operations import AssignMode

from cohdl._core._primitive_type import is_primitive, is_primitive_type
from cohdl._core._integer import Integer
from cohdl._core._boolean import _Boolean, Null, Full
from cohdl._core._bit_vector import BitVector
from cohdl._core._signed import Signed
from cohdl._core._unsigned import Unsigned
from cohdl._core._array import Array

#
#
#


class RefSpec:
    def is_constant(self) -> bool:
        pass

    def simplify(self):
        # combine all constant values
        pass


class Offset(RefSpec):
    def __init__(self, offset, base_offset: list | None):
        self.offset = offset
        self.base_offset = base_offset if base_offset is not None else []
        self.obj = None

    def copy(self):
        new = Offset(self.offset, self.base_offset)
        new.obj = self.obj
        return new

    def simplify(self):
        base_offset = []
        const_sum = 0

        for off in self.base_offset:
            if not isinstance(off, TypeQualifier):
                assert isinstance(off, int)
                const_sum += off
            else:
                base_offset.append(off)

        if not isinstance(self.offset, TypeQualifier):
            assert isinstance(self.offset, int)
            self.offset += const_sum
            self.base_offset = base_offset
        else:
            if const_sum != 0:
                self.base_offset = [const_sum, *base_offset]
            else:
                self.base_offset = base_offset

    def is_constant(self) -> bool:
        return not isinstance(self.offset, TypeQualifier) and not any(
            isinstance(base, TypeQualifier) for base in self.base_offset
        )


class Slice(RefSpec):
    def __init__(self, start, stop, base_offset: list | None) -> None:
        self.start = start
        self.stop = stop
        self.base_offset = base_offset if base_offset is not None else []
        self.obj = None

    def copy(self):
        new = Slice(self.start, self.stop, self.base_offset)
        new.obj = self.obj
        return new

    def simplify(self):
        base_offset = []
        const_sum = 0

        for off in self.base_offset:
            if not isinstance(off, TypeQualifier):
                assert isinstance(off, int)
                const_sum += off
            else:
                base_offset.append(off)

        assert isinstance(self.start, int)
        assert isinstance(self.stop, int)

        self.start += const_sum
        self.stop += const_sum
        self.base_offset = base_offset

    def is_constant(self) -> bool:
        return (
            not isinstance(self.start, TypeQualifier)
            and not isinstance(self.stop, TypeQualifier)
            and not any(isinstance(base, TypeQualifier) for base in self.base_offset)
        )


#
#
#


class Attribute:
    name: str
    attr_type: type

    def __init__(self, value):
        assert isinstance(value, self.attr_type)
        self.value = value

    def __init_subclass__(cls, **kwargs) -> None:
        cls.name = kwargs.get("name", cls.__name__)
        cls.attr_type = kwargs["type"]


#
#
#


def _decay(val):
    if isinstance(val, TypeQualifier):
        return val._value
    return val


class _TypeQualifier(type):
    _Wrapped: type
    _SubTypes: dict[type, type]
    _Qualifier: _TypeQualifier

    @_intrinsic
    def __getitem__(cls, Wrapped: type | tuple):
        # direction only used for ports

        if isinstance(Wrapped, tuple):
            WrappedType, direction = Wrapped
        else:
            WrappedType = Wrapped
            direction = None

        if WrappedType is bool:
            WrappedType = _Boolean
        elif WrappedType is int:
            WrappedType = Integer

        type_spec = (WrappedType, direction)

        if type_spec in cls._SubTypes:
            return cls._SubTypes[type_spec]

        # issubclass(Signal[BitVector[32]], Signal[BitVector]) should return True
        if issubclass(WrappedType, BitVector):
            if hasattr(WrappedType, "_width"):
                if issubclass(WrappedType, Unsigned):
                    if direction is None:
                        parent_cls = type(
                            cls.__name__,
                            (
                                cls[Unsigned],
                                cls[BitVector[WrappedType._width]],
                            ),
                            {},
                        )
                    else:
                        parent_cls = type(
                            cls.__name__,
                            (
                                cls[Unsigned, direction],
                                cls[BitVector[WrappedType._width], direction],
                            ),
                            {},
                        )
                elif issubclass(WrappedType, Signed):
                    if direction is None:
                        parent_cls = type(
                            cls.__name__,
                            (
                                cls[Signed],
                                cls[BitVector[WrappedType._width]],
                            ),
                            {},
                        )
                    else:
                        parent_cls = type(
                            cls.__name__,
                            (
                                cls[Signed, direction],
                                cls[BitVector[WrappedType._width], direction],
                            ),
                            {},
                        )
                else:
                    parent_cls = (
                        cls[BitVector]
                        if direction is None
                        else cls[BitVector, direction]
                    )
            else:
                if WrappedType is BitVector:
                    parent_cls = cls
                elif WrappedType is Unsigned or WrappedType is Signed:
                    if direction is None:
                        parent_cls = cls[BitVector]
                    else:
                        parent_cls = cls[BitVector, direction]
                else:
                    raise AssertionError(f"invalid generic argument to type qualifier")
        else:
            parent_cls = cls

        if issubclass(parent_cls, Port):
            assert isinstance(direction, Port.Direction), f"direction = {direction}"

            new_type = type(
                cls.__name__,
                (parent_cls, Signal[WrappedType]),
                {"_Wrapped": WrappedType, "_direction": direction},
            )
        else:
            assert direction is None, "direction can only be set on ports"
            new_type = type(cls.__name__, (parent_cls,), {"_Wrapped": WrappedType})

        cls._SubTypes[type_spec] = new_type
        return new_type

    @_intrinsic
    def __str__(cls):
        if not hasattr(cls, "_Wrapped"):
            return f"{cls.__name__}"

        if not hasattr(cls, "_direction"):
            return f"{cls.__name__}[{cls._Wrapped}]"
        return f"{cls.__name__}[{cls._Wrapped}, {cls._direction}]"

    @_intrinsic
    def __repr__(cls):
        return cls.__str__()

    @property
    @_intrinsic
    def type(cls):
        return cls._Wrapped

    @property
    @_intrinsic
    def qualifier(cls):
        return cls._Qualifier

    #
    #
    #


class TypeQualifierBase:
    @_intrinsic
    def decay(val):
        if isinstance(val, TypeQualifier):
            return val._value
        elif isinstance(val, TypeQualifierBase):
            return val.decay()
        return val


class TypeQualifier(TypeQualifierBase, metaclass=_TypeQualifier):
    @property
    def type(cls):
        return cls._Wrapped

    @property
    def qualifier(self):
        return self._Qualifier

    @property
    def width(self):
        return self._Wrapped.width

    _intrinsic(width.fget)

    #
    #
    #

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_Wrapped"):
            value = args[0]
            decayed = _decay(value)
            wrapped_class = cls[type(decayed)]
        else:
            wrapped_class = cls

        if not is_primitive_type(wrapped_class._Wrapped):
            if issubclass(wrapped_class._Wrapped, (tuple, list)):
                assert len(args) == 1
                assert (
                    len(kwargs) == 0
                ), "TypeQualifier called with tuple/list argument does not expect any keyword arguments"
                return wrapped_class._Wrapped([cls(elem) for elem in args[0]])
            else:
                return wrapped_class._Wrapped(
                    *args, **kwargs, _qualifier_=cls._Qualifier
                )
        else:
            return object.__new__(wrapped_class)

    @_intrinsic
    def __init__(
        self,
        value=None,
        *,
        name: str | None = None,
        attributes: dict | None = None,
        noreset: bool = False,
        maybe_uninitialized: bool = False,
        _root: TypeQualifier | None = None,
        _ref_spec: list[RefSpec] | None = None,
    ):
        if _root is not None:
            root_qualifier = _root.qualifier
            self_qualifier = self.qualifier

            if isinstance(root_qualifier, _PortQualifier):
                assert isinstance(
                    self_qualifier, _PortQualifier
                ), f"internal error: expected port qualifier"
                assert (
                    root_qualifier._direction is self_qualifier._direction
                ), f"internal error: port direction mismatch"
            else:
                assert (
                    _root.qualifier is self.qualifier
                ), f"internal error: _root.qualifier != self.qualifier {_root.qualifier} {self.qualifier}"
            assert type(value) is self.type, "internal error: type(value) != self.type"
            self._value = value
        else:
            value = TypeQualifier.decay(value)
            self._value = type(self)._Wrapped(value)

        self._name = name
        self._default = (
            None
            if (value is None) or (isinstance(self, Temporary))
            else type(self)._Wrapped(value)
        )
        self._attributes = [] if attributes is None else attributes
        self._noreset = noreset
        self._maybe_uninitialized = maybe_uninitialized

        self._root = self if _root is None else _root

        if _ref_spec is None:
            self._ref_spec = []
        else:
            self._ref_spec = list(_ref_spec)

            if len(self._ref_spec) != 0:
                self._ref_spec[-1] = _ref_spec[-1].copy()
                self._ref_spec[-1].obj = self

    @_intrinsic
    def name(self):
        return self._name

    @_intrinsic
    def set_name(self, name: str):
        self._name = name

    @_intrinsic
    def has_default(self):
        return self._default is not None

    @_intrinsic
    def default(self):
        return self._default

    @_intrinsic
    def __hash__(self):
        # Generate a unique hash for each TypeQualifier
        # so qualified types can be used as dictionary keys.
        return id(self)

    @_intrinsic
    def __str__(self):
        return f"{type(self)}({self._value!s})"

    @_intrinsic
    def __repr__(self):
        return f"{type(self)}({self._value!s})"

    @_intrinsic
    def __len__(self):
        return self._value.__len__()

    @_intrinsic
    def __iter__(self):
        if len(self._ref_spec) != 0 and isinstance(self._ref_spec[-1], Slice):
            offset = self._ref_spec[-1].stop
            prev = self._ref_spec[:-1]
        else:
            offset = 0
            prev = self._ref_spec

        for nr, elem in enumerate(self._value):
            yield self.qualifier[type(elem)](
                elem, _ref_spec=[*prev, Offset(offset + nr, [])], _root=self._root
            )

    @_intrinsic
    def get(self):
        return self._value

    @_intrinsic
    def __getitem__(self, arg):
        if isinstance(arg, (tuple, list)):
            first, *rest = arg

            if len(rest) == 0:
                if isinstance(first, slice):
                    return self.__getitem__(first)
                else:
                    return self.__getitem__(slice(first, first))
            else:
                return self.__getitem__(first) @ self.__getitem__(rest)

        ref_spec = self._ref_spec

        if len(ref_spec) != 0 and isinstance(ref_spec[-1], Slice):
            last_ref = ref_spec[-1]
            prev = ref_spec[:-1]
            base_offset = [*last_ref.base_offset, last_ref.stop]
        else:
            prev = ref_spec
            base_offset = []

        if isinstance(arg, tuple):
            raise NotImplementedError()
        elif isinstance(arg, slice):
            assert arg.step is None, "step parameter in slice is not allowed"

            if isinstance(arg.start, int):
                assert isinstance(arg.stop, int)

                result = self._value[arg.start : arg.stop]

                return self.qualifier[type(result)](
                    result,
                    _root=self._root,
                    _ref_spec=[*prev, Slice(arg.start, arg.stop, base_offset)],
                )
            else:
                raise NotImplemented()
        else:
            if isinstance(arg, int):
                result = self._value[arg]
                return self.qualifier[type(result)](
                    result,
                    _root=self._root,
                    _ref_spec=[*prev, Offset(arg, base_offset)],
                )
            elif isinstance(arg, TypeQualifier):
                result = self._value[0]

                return self.qualifier[type(result)](
                    result,
                    _root=self._root,
                    _ref_spec=[*prev, Offset(arg, base_offset)],
                )
            else:
                raise NotImplemented()

    def lsb(self, count=None, rest=None):
        val_width = self._value.width
        if count is not None:
            if rest is not None:
                assert (
                    count + rest == val_width
                ), "the sum of count and reset does not match the value width"
            return self[count - 1 : 0]
        elif rest is not None:
            vec_count = val_width - rest
            return self[vec_count - 1 : 0]
        else:
            return self[0]

    def msb(self, count=None, rest=None):
        val_width = self._value.width
        if count is not None:
            if rest is not None:
                assert (
                    count + rest == val_width
                ), "the sum of count and reset does not match the value width"
            return self[val_width - 1 : val_width - count]
        elif rest is not None:
            vec_count = val_width - rest
            return self[val_width - 1 : val_width - vec_count]
        else:
            return self[val_width - 1]

    def right(self, count=None, rest=None):
        val_width = self._value.width
        if count is not None:
            if rest is not None:
                assert (
                    count + rest == val_width
                ), "the sum of count and reset does not match the value width"
            return self[count - 1 : 0]
        elif rest is not None:
            vec_count = val_width - rest
            return self[vec_count - 1 : 0]
        else:
            return self[0]

    def left(self, count=None, rest=None):
        val_width = self._value.width
        if count is not None:
            if rest is not None:
                assert (
                    count + rest == val_width
                ), "the sum of count and reset does not match the value width"
            return self[val_width - 1 : val_width - count]
        elif rest is not None:
            vec_count = val_width - rest
            return self[val_width - 1 : val_width - vec_count]
        else:
            return self[val_width - 1]

    def resize(self, target_width: int | None = None, *, zeros: int = 0):
        type = self.type
        padded_width = self.width + zeros

        if target_width is None:
            result_width = padded_width
        else:
            result_width = target_width

        assert (
            padded_width <= result_width
        ), "width zero extended value exceeds target width"

        if zeros == 0:
            padded = self
        else:
            padded = self @ BitVector[zeros](Null)

        if issubclass(type, Signed):
            return Temporary[Signed[result_width]](padded.signed)
        elif issubclass(type, Unsigned):
            return Temporary[Unsigned[result_width]](padded.unsigned)
        else:
            raise AssertionError(
                "resize is only defined for Signed and Unsigned arguments"
            )

    def copy(self):
        return Temporary(self)

    @_intrinsic
    def _assign_(self, value, assign_mode: AssignMode):
        if assign_mode is AssignMode.NEXT:
            assert isinstance(
                self, Signal
            ), "only Signal objects can use next assignment"
            self <<= value
        elif assign_mode is AssignMode.PUSH:
            assert isinstance(
                self, Signal
            ), "only Signal objects can use push assignment"
            self ^= value
        elif assign_mode is AssignMode.VALUE:
            assert isinstance(
                self, Variable
            ), "only Variable objects can use value assignment"
            self @= value
        else:
            raise AssertionError(f"invalid assign_mode {assign_mode}")

    @_intrinsic
    def _needs_array_elem_assignment(self, src):
        # check if array elements must be assigned individually
        return issubclass(self._Wrapped, Array) and not isinstance(_decay(src), Array)

    @_intrinsic
    def _perform_array_elem_assignment(self, src, assignment_fn):
        if src is Null or src is Full:

            def assign_null_full_elements():
                for index in range(len(self)):
                    assignment_fn(self[index], src)
                return self

            return intr_op._IntrinsicSynthesizableFunctionCall(
                assign_null_full_elements, [], {}
            )

        # special case for assignment of lists/tuples to arrays, assigned elements individually
        assert isinstance(
            src, (tuple, list)
        ), f"only tuples/lists and array can be assigned to arrays (got {src})"

        assert len(self) == len(
            src
        ), f"source width does not match target width ({len(self)} != {len(src)})"

        def assign_array_elements(value):
            for index in range(len(self)):
                assignment_fn(self[index], value[index])
            return self

        return intr_op._IntrinsicSynthesizableFunctionCall(
            assign_array_elements, [src], {}
        )

    #
    #
    #

    @_intrinsic
    def __bool__(self):
        return bool(self._value)

    @_intrinsic
    def __and__(self, other):
        result = self._value & _decay(other)
        return Temporary[type(result)](result)

    @_intrinsic
    def __rand__(self, other):
        result = _decay(other).__and__(self._value)
        return Temporary[type(result)](result)

    @_intrinsic
    def __or__(self, other):
        result = self._value.__or__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __ror__(self, other):
        result = _decay(other).__or__(self._value)
        return Temporary[type(result)](result)

    @_intrinsic
    def __xor__(self, other):
        result = self._value.__xor__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __rxor__(self, other):
        result = _decay(other).__xor__(self._value)
        return Temporary[type(result)](result)

    @_intrinsic
    def __matmul__(self, other):
        result = self._value.__matmul__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __rmatmul__(self, other):
        result = _decay(other).__matmul__(self._value)
        return Temporary[type(result)](result)

    #
    # numeric operators
    #

    @_intrinsic
    def __add__(self, other):
        result = self._value.__add__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __radd__(self, other):
        result = self._value.__radd__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __sub__(self, other):
        result = self._value.__sub__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __rsub__(self, other):
        result = self._value.__rsub__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __mul__(self, other):
        result = self._value.__mul__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __rmul__(self, other):
        result = self._value.__rmul__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __floordiv__(self, other):
        result = self._value.__floordiv__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __rfloordiv__(self, other):
        result = self._value.__rfloordiv__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __mod__(self, other):
        result = self._value.__mod__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __rmod__(self, other):
        result = self._value.__rmod__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __lshift__(self, rhs):
        result = self._value.__lshift__(_decay(rhs))
        return Temporary[type(result)](result)

    @_intrinsic
    def __rshift__(self, rhs):
        result = self._value.__rshift__(_decay(rhs))
        return Temporary[type(result)](result)

    @_intrinsic
    def __rlshift__(self, lhs):
        result = _decay(lhs).__lshift__(self._value)
        return Temporary[type(result)](result)

    @_intrinsic
    def __rrshift__(self, lhs):
        result = _decay(lhs).__rshift__(self._value)
        return Temporary[type(result)](result)

    #
    # compare
    #

    @_intrinsic
    def __eq__(self, other):
        result = self._value.__eq__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __ne__(self, other):
        result = self._value.__ne__(_decay(other))
        return Temporary[type(result)](result)

    @_intrinsic
    def __lt__(self, other):
        result = self._value.__lt__(_decay(other))
        return result if result is NotImplemented else Temporary[type(result)](result)

    @_intrinsic
    def __gt__(self, other):
        result = self._value.__gt__(_decay(other))
        return result if result is NotImplemented else Temporary[type(result)](result)

    @_intrinsic
    def __le__(self, other):
        result = self._value.__le__(_decay(other))
        return result if result is NotImplemented else Temporary[type(result)](result)

    @_intrinsic
    def __ge__(self, other):
        result = self._value.__ge__(_decay(other))
        return result if result is NotImplemented else Temporary[type(result)](result)

    #
    # unary operators
    #

    @_intrinsic
    def __abs__(self):
        result = self._value.__abs__()
        return Temporary[type(result)](result)

    @_intrinsic
    def __inv__(self):
        result = self._value.__inv__()
        return Temporary[type(result)](result)

    @_intrinsic
    def __neg__(self):
        result = self._value.__neg__()
        return Temporary[type(result)](result)

    @_intrinsic
    def __pos__(self):
        result = self._value.__pos__()
        return Temporary[type(result)](result)

    #
    #
    # replacements
    #
    #

    @_intrinsic_replacement(__init__)
    def _init_replacement(
        self,
        value=None,
        *,
        name: str | None = None,
        attributes: dict | None = None,
        maybe_uninitialized: bool = False,
        _root: TypeQualifier | None = None,
        _ref_spec: list[RefSpec] | None = None,
    ):
        assert _root is None, "internal error: _root is None"
        assert _ref_spec is None, "internal error: _ref_spec is None"
        # set default to None, because locally defined
        # Signals/Variables cannot be used before they are constructed
        # and thus initialized
        self.__init__(
            None,
            name=name,
            attributes=attributes,
            maybe_uninitialized=maybe_uninitialized,
        )

        if value is None or is_primitive(value) and value._is_uninitialized():
            return intr_op._IntrinsicDeclaration(self, None)
        return intr_op._IntrinsicDeclaration(self, value)

    @_intrinsic_replacement(__bool__)
    def _bool_replacement(self):
        return intr_op._IntrinsicUnaryOp(
            intr_op.UnaryOperator.BOOL, Temporary[bool](self.__bool__()), self
        )

    @_intrinsic_replacement(__or__)
    def _or_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.BIT_OR, self.__or__(other), self, other
        )

    @_intrinsic_replacement(__ror__)
    def _ror_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.BIT_OR, self.__ror__(other), other, self
        )

    @_intrinsic_replacement(__and__)
    def _and_replacement_(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.BIT_AND, self.__and__(other), self, other
        )

    @_intrinsic_replacement(__rand__)
    def _rand_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.BIT_AND, self.__rand__(other), other, self
        )

    @_intrinsic_replacement(__xor__)
    def _and_replacement_(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.BIT_XOR, self.__xor__(other), self, other
        )

    @_intrinsic_replacement(__rxor__)
    def _rand_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.BIT_XOR, self.__rxor__(other), other, self
        )

    @_intrinsic_replacement(__matmul__)
    def _matmul_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.CONCAT, self.__matmul__(other), self, other
        )

    @_intrinsic_replacement(__rmatmul__)
    def _rmatmul_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.CONCAT, self.__rmatmul__(other), other, self
        )

    @_intrinsic_replacement(__getitem__)
    def __getitem_replacement(self, arg):
        if isinstance(arg, (tuple, list)):

            def synthesizable_impl(s, arg):
                first, *rest = arg

                if len(rest) == 0:
                    if isinstance(first, slice):
                        return self.__getitem__(first)
                    else:
                        return self.__getitem__(slice(first, first))
                else:
                    return self.__getitem__(first) @ synthesizable_impl(s, rest)

            return intr_op._IntrinsicSynthesizableFunctionCall(
                synthesizable_impl, [self, arg], {}
            )
        elif isinstance(arg, slice):
            assert arg.step is None, "step argument not allowed in slice"

            if isinstance(arg.start, int):
                assert isinstance(arg.stop, int)
                return intr_op._IntrinsicConstElemAccess(self.__getitem__(arg))
            else:
                raise NotImplemented()
        else:
            if isinstance(arg, int):
                return intr_op._IntrinsicConstElemAccess(self.__getitem__(arg))
            elif isinstance(arg, TypeQualifier):
                index = arg
                index_temp = Temporary[index.type]()
                result = self.__getitem__(index_temp)
                return intr_op._IntrinsicElemAccess(result, index, index_temp)
            else:
                raise NotImplemented()

    @_intrinsic_replacement(_assign_, assignment_spec=(0, 1))
    def _assign_replacement(self, value, assign_mode: AssignMode):
        if assign_mode is AssignMode.AUTO:
            if isinstance(self, Signal):
                assign_mode = AssignMode.NEXT
            else:
                assert isinstance(
                    self, Variable
                ), "AssignMode.AUTO only valid for signals and variables"
                assign_mode = AssignMode.VALUE

        if assign_mode is AssignMode.NEXT:
            assert isinstance(
                self, Signal
            ), "only Signal objects can use next assignment"
            return self._next_setter_replacement(value)
        elif assign_mode is AssignMode.PUSH:
            assert isinstance(
                self, Signal
            ), "only Signal objects can use push assignment"
            return self._push_setter_replacement(value)
        elif assign_mode is AssignMode.VALUE:
            assert isinstance(
                self, Variable
            ), "only Variable objects can use value assignment"
            return self._value_setter_replacement(value)

        raise AssertionError(f"invalid assign_mode {assign_mode}")

    #
    # numeric
    #

    @_intrinsic_replacement(__add__)
    def _add_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.ADD, self.__add__(other), self, other
        )

    @_intrinsic_replacement(__radd__)
    def _radd_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.ADD, self.__radd__(other), other, self
        )

    @_intrinsic_replacement(__sub__)
    def _sub_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.SUB, self.__sub__(other), self, other
        )

    @_intrinsic_replacement(__rsub__)
    def _rsub_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.SUB, self.__rsub__(other), other, self
        )

    @_intrinsic_replacement(__mul__)
    def _mul_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.MUL, self.__mul__(other), self, other
        )

    @_intrinsic_replacement(__rmul__)
    def _rmul_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.MUL, self.__rmul__(other), other, self
        )

    @_intrinsic_replacement(__floordiv__)
    def _floordiv_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.FLOOR_DIV, self.__floordiv__(other), self, other
        )

    @_intrinsic_replacement(__rfloordiv__)
    def _rfloordiv_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.FLOOR_DIV, self.__rfloordiv__(other), other, self
        )

    @_intrinsic_replacement(__mod__)
    def _mod_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.MOD, self.__mod__(other), self, other
        )

    @_intrinsic_replacement(__rmod__)
    def _rmod_replacement(self, other):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.MOD, self.__rmod__(other), other, self
        )

    @_intrinsic_replacement(__lshift__)
    def _lshift_replacement(self, rhs):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.LSHIFT, self.__lshift__(rhs), self, rhs
        )

    @_intrinsic_replacement(__rshift__)
    def _rshift_replacement(self, rhs):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.RSHIFT, self.__rshift__(rhs), self, rhs
        )

    @_intrinsic_replacement(__rlshift__)
    def _lshift_replacement(self, lhs):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.LSHIFT, self.__rlshift__(lhs), lhs, self
        )

    @_intrinsic_replacement(__rrshift__)
    def _rshift_replacement(self, lhs):
        return intr_op._IntrinsicBinOp(
            intr_op.BinaryOperator.RSHIFT, self.__rrshift__(lhs), lhs, self
        )

    #
    # compare
    #

    @_intrinsic_replacement(__eq__)
    def _eq_replacement(self, other):
        result = self.__eq__(other)

        if other is Null or other is Full:
            other = self.type(other)

        return (
            result
            if result is NotImplemented
            else intr_op._IntrinsicComparison(
                intr_op.ComparisonOperator.EQ, result, self, other
            )
        )

    @_intrinsic_replacement(__ne__)
    def _ne_replacement(self, other):
        result = self.__ne__(other)

        if other is Null or other is Full:
            other = self.type(other)

        return (
            result
            if result is NotImplemented
            else intr_op._IntrinsicComparison(
                intr_op.ComparisonOperator.NE, result, self, other
            )
        )

    @_intrinsic_replacement(__lt__)
    def _lt_replacement(self, other):
        result = self.__lt__(other)

        if other is Null or other is Full:
            other = self.type(other)

        return (
            result
            if result is NotImplemented
            else intr_op._IntrinsicComparison(
                intr_op.ComparisonOperator.LT, result, self, other
            )
        )

    @_intrinsic_replacement(__gt__)
    def _gt_replacement(self, other):
        result = self.__gt__(other)

        if other is Null or other is Full:
            other = self.type(other)

        return (
            result
            if result is NotImplemented
            else intr_op._IntrinsicComparison(
                intr_op.ComparisonOperator.GT, result, self, other
            )
        )

    @_intrinsic_replacement(__le__)
    def _le_replacement(self, other):
        result = self.__le__(other)

        if other is Null or other is Full:
            other = self.type(other)

        return (
            result
            if result is NotImplemented
            else intr_op._IntrinsicComparison(
                intr_op.ComparisonOperator.LE, result, self, other
            )
        )

    @_intrinsic_replacement(__ge__)
    def _ge_replacement(self, other):
        result = self.__ge__(other)

        if other is Null or other is Full:
            other = self.type(other)

        return (
            result
            if result is NotImplemented
            else intr_op._IntrinsicComparison(
                intr_op.ComparisonOperator.GE, result, self, other
            )
        )

    #
    # unary operators
    #

    @_intrinsic_replacement(__abs__)
    def _abs_replacement(self):
        result = self.__abs__()
        return intr_op._IntrinsicUnaryOp(intr_op.UnaryOperator.ABS, result, self)

    @_intrinsic_replacement(__inv__)
    def _inv_replacement(self):
        result = self.__inv__()
        return intr_op._IntrinsicUnaryOp(intr_op.UnaryOperator.INV, result, self)

    @_intrinsic_replacement(__neg__)
    def _neg_replacement(self):
        result = self.__neg__()
        return intr_op._IntrinsicUnaryOp(intr_op.UnaryOperator.NEG, result, self)

    @_intrinsic_replacement(__pos__)
    def _pos_replacement(self):
        result = self.__pos__()
        return intr_op._IntrinsicUnaryOp(intr_op.UnaryOperator.POS, result, self)

    #
    # casts
    #

    @property
    def unsigned(self):
        if issubclass(self._Wrapped, Unsigned):
            return self
        else:
            cast = self._value.unsigned
            return self.qualifier[type(cast)](
                cast, _ref_spec=self._ref_spec, _root=self._root
            )

    @unsigned.setter
    def unsigned(self, value):
        self._value.unsigned = _decay(value)

    _intrinsic(unsigned.fget)
    _intrinsic(unsigned.fset)

    @property
    def signed(self):
        if issubclass(self._Wrapped, Signed):
            return self
        else:
            cast = self._value.signed
            return self.qualifier[type(cast)](
                cast, _ref_spec=self._ref_spec, _root=self._root
            )

    @signed.setter
    def signed(self, value):
        self._value.signed = _decay(value)

    _intrinsic(signed.fget)
    _intrinsic(signed.fset)

    @property
    def bitvector(self):
        if not issubclass(self._Wrapped, (Signed, Unsigned)):
            return self
        else:
            cast = self._value.bitvector
            return self.qualifier[type(cast)](
                cast, _ref_spec=self._ref_spec, _root=self._root
            )

    @bitvector.setter
    def bitvector(self, value):
        self._value.bitvector = _decay(value)

    _intrinsic(bitvector.fget)
    _intrinsic(bitvector.fset)


class Signal(TypeQualifier):
    _SubTypes = {}

    @_intrinsic
    def __init__(
        self,
        value=None,
        *,
        name: str | None = None,
        attributes: dict | None = None,
        delayed_init: bool = None,
        noreset: bool = False,
        maybe_uninitialized: bool = False,
        _root: TypeQualifier | None = None,
        _ref_spec: list[RefSpec] | None = None,
    ):
        assert (
            delayed_init is None
        ), "delayed_init can only be used in synthesizable contexts"

        super().__init__(
            value,
            name=name,
            attributes=attributes,
            noreset=noreset,
            maybe_uninitialized=maybe_uninitialized,
            _root=_root,
            _ref_spec=_ref_spec,
        )

    @_intrinsic_replacement(__init__)
    def _init_replacement(
        self,
        value=None,
        *,
        name: str | None = None,
        attributes: dict | None = None,
        delayed_init: bool = False,
        noreset=None,
        maybe_uninitialized: bool = False,
        _root: TypeQualifier | None = None,
        _ref_spec: list[RefSpec] | None = None,
    ):
        assert noreset is None, "noreset is not valid in synthesizable contexts"

        # copy of TypeQualifier._init_replacement
        # with added support for delayed_init

        assert _root is None, "internal error: _root is None"
        assert _ref_spec is None, "internal error: _ref_spec is None"
        # set default to None, because locally defined
        # Signals/Variables cannot be used before they are constructed
        # and thus initialized
        self.__init__(
            None,
            name=name,
            attributes=attributes,
            maybe_uninitialized=maybe_uninitialized,
        )

        if value is None or is_primitive(value) and value._is_uninitialized():
            return intr_op._IntrinsicDeclaration(self, None, delayed_init)
        return intr_op._IntrinsicDeclaration(self, value, delayed_init)

    #
    # next assignment
    #

    @property
    def next(self):
        raise AssertionError("Signal.next can only be written")

    @next.setter
    def next(self, value):
        self._value._assign(_decay(value))

    _intrinsic(next.fget)
    _intrinsic(next.fset)

    @_intrinsic_replacement(next.fset, assignment_spec=(0, 1))
    def _next_setter_replacement(self, value):
        if self._needs_array_elem_assignment(value):

            def assign_next(a, b):
                a <<= b

            return self._perform_array_elem_assignment(value, assign_next)

        # assign value to check whether operation is allowed
        inp_value = _decay(value)
        self._value._assign(inp_value)
        if is_primitive(inp_value):
            return intr_op._IntrinsicAssignment(self, value, AssignMode.NEXT)
        return intr_op._IntrinsicAssignment(self, self._value.copy(), AssignMode.NEXT)

    @_intrinsic
    def __ilshift__(self, value):
        self.next = value
        return self

    _intrinsic_replacement(__ilshift__, assignment_spec=(0, 1))(
        _next_setter_replacement
    )

    #
    # push assignment
    #

    @property
    def push(self):
        raise AssertionError("Signal.push can only be written")

    @push.setter
    def push(self, value):
        assert self._default is not None, "pushed signal requires default value"
        self._value._assign(_decay(value))

    _intrinsic(push.fget)
    _intrinsic(push.fset)

    @_intrinsic_replacement(push.fset, assignment_spec=(0, 1))
    def _push_setter_replacement(self, value):
        # assign value to check wheather operation is allowed
        assert (
            self._default is not None
        ), f"pushed signal requires default value (name hint='{self._name}')"
        inp_value = _decay(value)
        self._value._assign(inp_value)
        if is_primitive(inp_value):
            return intr_op._IntrinsicAssignment(self, value, AssignMode.PUSH)
        return intr_op._IntrinsicAssignment(self, self._value.copy(), AssignMode.PUSH)

    @_intrinsic
    def __ixor__(self, value):
        self.push = value
        return self

    _intrinsic_replacement(__ixor__, assignment_spec=(0, 1))(_push_setter_replacement)


class _PortQualifier:
    @_intrinsic
    def __init__(self, direction, type):
        self._direction = direction
        self._type = type

    @_intrinsic
    def __getitem__(self, type):
        return Port[type, self._direction]


class Port(Signal):
    _SubTypes = {}
    _direction: Direction

    @property
    @_intrinsic
    def qualifier(self):
        return _PortQualifier(self._direction, None)

    class Direction(enum.Enum):
        INPUT = enum.auto()
        OUTPUT = enum.auto()
        INOUT = enum.auto()

        @_intrinsic
        def __str__(self):
            match self:
                case Port.Direction.INPUT:
                    return "INPUT"
                case Port.Direction.OUTPUT:
                    return "OUTPUT"
                case Port.Direction.INOUT:
                    return "INOUT"

        @_intrinsic
        def is_input(self):
            return self is Port.Direction.INPUT

        @_intrinsic
        def is_output(self):
            return self is Port.Direction.OUTPUT

        @_intrinsic
        def is_inout(self):
            return self is Port.Direction.INOUT

    @classmethod
    @_intrinsic
    def is_input(cls):
        return cls._direction is Port.Direction.INPUT

    @classmethod
    @_intrinsic
    def is_output(cls):
        return cls._direction is Port.Direction.OUTPUT

    @classmethod
    @_intrinsic
    def is_inout(cls):
        return cls._direction is Port.Direction.INOUT

    @staticmethod
    def input(Wrapped, *, name: str | None = None) -> Port:
        return Port[Wrapped, Port.Direction.INPUT](name=name)

    @staticmethod
    def output(
        Wrapped, *, default=None, name: str | None = None, noreset=False
    ) -> Port:
        return Port[Wrapped, Port.Direction.OUTPUT](default, name=name, noreset=noreset)

    @staticmethod
    def inout(Wrapped, *, default=None, name: str | None = None, noreset=False) -> Port:
        return Port[Wrapped, Port.Direction.INOUT](default, name=name, noreset=noreset)

    @classmethod
    @_intrinsic
    def direction(cls):
        return cls._direction


class Variable(TypeQualifier):
    _SubTypes = {}

    #
    # value assignment
    #

    @property
    def value(self):
        raise AssertionError("Variable.value can only be written")

    @value.setter
    def value(self, value):
        self._value._assign(_decay(value))

    _intrinsic_property(value)

    @_intrinsic_replacement(value.fset, assignment_spec=(0, 1))
    def _value_setter_replacement(self, value):
        # assign value to check wheather operation is allowed
        inp_value = _decay(value)
        self._value._assign(inp_value)
        if is_primitive(inp_value):
            return intr_op._IntrinsicAssignment(self, value, AssignMode.VALUE)
        return intr_op._IntrinsicAssignment(self, self._value.copy(), AssignMode.VALUE)

    @_intrinsic
    def __imatmul__(self, value):
        self.next = value
        return self

    _intrinsic_replacement(__imatmul__, assignment_spec=(0, 1))(
        _value_setter_replacement
    )


class Temporary(TypeQualifier):
    _SubTypes = {}


class Generic: ...


Signal._Qualifier = Signal
Variable._Qualifier = Variable
Temporary._Qualifier = Temporary
