from __future__ import annotations

import inspect
import typing

from typing import Any

from cohdl._core._type_qualifier import (
    TypeQualifierBase,
    TypeQualifier,
    Temporary,
    Signal,
    Variable,
)

from cohdl._core import (
    Bit,
    BitVector,
    Signed,
    Unsigned,
    select_with,
    evaluated,
    Null,
    Full,
    static_assert,
    is_primitive_type,
    AssignMode,
    Array as CohdlArray,
    Integer as CohdlInteger,
    Boolean as CohdlBool,
)

from cohdl._core._intrinsic import _intrinsic

from cohdl._core._intrinsic import comment as cohdl_comment

from ._exception import RefQualifierFail, SerializationFail


class _PrivateNone: ...


def nop(*args, **kwargs):
    pass


def comment(*lines):
    cohdl_comment(*lines)


def assign(target, source, mode: AssignMode = AssignMode.AUTO):
    target._assign_(source, mode)


@_intrinsic
def as_pyeval(fn, /, *args, **kwargs):
    return fn(*args, **kwargs)


@_intrinsic
def fail(message: str = "", *args, **kwargs):
    raise AssertionError("Compilation failed: " + message.format(*args, **kwargs))


@_intrinsic
def identity(inp, /):
    return inp


@_intrinsic
def _bind_partial(signature, args, kwargs) -> inspect.Signature:
    return signature.bind_partial(*args, **kwargs)


def _determine_defaults(signature: inspect.Signature, args, kwargs, scope):
    bound = _bind_partial(signature, args, kwargs)

    for name, param in as_pyeval(signature.parameters.items):
        if name not in bound.arguments:
            param_str = str(param)

            if not as_pyeval(param_str.startswith, "*"):
                _, default_str = as_pyeval(param_str.split, "=", maxsplit=1)

                default = as_pyeval(eval, default_str, scope)
                as_pyeval(bound.arguments.__setitem__, name, default)

    return bound


def regenerate_defaults(fn, /):
    assert (
        not evaluated()
    ), "regenerate_defaults should not be called in synthesizable contexts"

    is_function = inspect.isfunction(fn)
    is_async = inspect.iscoroutinefunction(fn)

    assert (
        is_function or is_async
    ), "the object wrapped by regnerate_defaults must be a function or async function"

    scope = fn.__globals__
    callable = fn
    signature = inspect.signature(callable)

    if not is_async:

        def helper(*args, **kwargs):
            bound = _determine_defaults(signature, args, kwargs, scope)
            return fn(*bound.args, **bound.kwargs)

    else:

        async def helper(*args, **kwargs):
            bound = _determine_defaults(signature, args, kwargs, scope)
            return fn(*bound.args, **bound.kwargs)

    return helper


@_intrinsic
def _check_type_qualifier_params(kwargs):
    return ("name" in kwargs) + ("attributes" in kwargs) == len(kwargs)


class _Value:
    @_intrinsic
    def _any_instance(self, iter, base):
        return any(isinstance(elem, base) for elem in iter)

    @_intrinsic
    def __init__(self, T=None):
        self._T = T

    def _make_const_or_temp(self, T, arg):
        if isinstance(arg, TypeQualifier):
            return Temporary[T](arg)
        elif isinstance(arg, TypeQualifierBase):
            return TypeQualifierBase.decay(arg)
        else:
            return T(arg)

    def __call__(self, *args, **kwargs):
        if self._T is None:
            assert len(args) == 1 and len(kwargs) == 0
            T = type(TypeQualifierBase.decay(args[0]))
        else:
            T = self._T

        if is_primitive_type(T) or T is bool or T is int:
            if len(args) == 0 and _check_type_qualifier_params(kwargs):
                return T()
            else:
                assert len(args) == 1 and _check_type_qualifier_params(kwargs)
                arg = args[0]

                if issubclass(T, CohdlArray) and isinstance(arg, (list, tuple)):
                    if self._any_instance(arg, TypeQualifier):
                        return Temporary[T](arg, **kwargs)
                    elif self._any_instance(arg, TypeQualifierBase):
                        return T([TypeQualifierBase.decay(elem) for elem in arg])
                    else:
                        return T(arg)
                else:
                    if isinstance(arg, TypeQualifier):
                        if isinstance(arg, Temporary[T]):
                            return arg
                        else:
                            return Temporary[T](arg, **kwargs)
                    elif isinstance(arg, TypeQualifierBase):
                        return TypeQualifierBase.decay(arg)
                    else:
                        return T(arg)
        elif issubclass(T, (tuple, list)):
            assert len(args) == 1
            assert (
                len(kwargs) == 0
            ), "std.Value called with tuple/list argument does not expect any keyword arguments"
            return T([Value(elem) for elem in args[0]])
        else:
            return T(*args, **kwargs, _qualifier_=Value)

    @_intrinsic
    def __getitem__(self, arg):
        assert isinstance(
            arg, type
        ), f"type argument of Value[T] is not a type (T={arg})"

        return _Value(arg)


class _Ref:
    @_intrinsic
    def __init__(self, T=None):
        self._T = T

    @_intrinsic
    def __call__(self, *args, **kwargs):
        if self._T is None:
            assert (
                len(args) == 1 and len(kwargs) == 0
            ), "std.Ref() without explicit target type expects a single argument"
            T = type(TypeQualifierBase.decay(args[0]))
        else:
            T = self._T

        if is_primitive_type(T) or T is bool or T is CohdlBool:
            assert len(args) == 1 and _check_type_qualifier_params(kwargs)
            arg = args[0]

            if subclass_check(T, BitVector):
                if subclass_check(T, Signed):
                    return arg.signed
                elif subclass_check(T, Unsigned):
                    return arg.unsigned
                else:
                    return arg.bitvector
            if T is bool or T is CohdlBool:
                RefQualifierFail.raise_if(
                    not instance_check(arg, (bool, CohdlBool)),
                    f"cannot create reference of type '{T}' from argument '{arg}'",
                )

                return arg
            else:
                RefQualifierFail.raise_if(
                    not instance_check(arg, T),
                    f"cannot create reference of type '{T}' from argument '{arg}'",
                )

                return arg
        elif issubclass(T, (tuple, list)):
            assert len(args) == 1
            assert (
                len(kwargs) == 0
            ), "std.Ref called with tuple/list argument does not expect any keyword arguments"
            return T([Ref(elem) for elem in args[0]])
        else:
            return T(*args, **kwargs, _qualifier_=Ref)

    @_intrinsic
    def __getitem__(self, arg):
        return _Ref(arg)


#
#
#


class _Nonlocal:
    @_intrinsic
    def __init__(self, qualified_type):
        self._qualified_type = qualified_type

    @_intrinsic
    def __call__(self, *args, **kwargs):
        assert (
            self._qualified_type is not None
        ), "type of Nonlocal must be set using Nonlocal[TARGET_TYPE]"
        return self._qualified_type(*args, **kwargs)

    @_intrinsic
    def __getitem__(self, arg):
        if self._qualified_type is None:
            assert issubclass(
                arg, (Signal, Variable)
            ), "std.Nonlocal should only be used to create Signals or Variables"
            return _Nonlocal(arg)
        else:
            return _Nonlocal(self._qualified_type[arg])


class _Noreset:
    _Qualifier: Signal

    @_intrinsic
    def __init__(self, T=None):
        self._T = T

    @_intrinsic
    def __call__(self, *args, **kwargs):
        if self._T is None:
            assert len(args) == 1 and len(kwargs) == 0
            T = type(TypeQualifierBase.decay(args[0]))
        else:
            T = self._T

        if is_primitive_type(T) or T is bool or T is int:
            return self._Qualifier[T](*args, **kwargs, noreset=True)
        else:
            return T(*args, **kwargs, _qualifier_=type(self)())

    @_intrinsic
    def __getitem__(self, arg):
        return type(self)(arg)


class _NoresetSignal(_Noreset):
    _Qualifier = Signal


class _NoresetVariable(_Noreset):
    _Qualifier = Variable


Ref = _Ref()
Value = _Value()
Nonlocal = _Nonlocal(None)
NoresetSignal = _NoresetSignal()
NoresetVariable = _NoresetVariable()

#
#
#


@_intrinsic
def iscouroutinefunction(fn):
    return inspect.iscoroutinefunction(fn)


def base_type(x):
    if isinstance(x, type):
        if issubclass(x, TypeQualifierBase):
            return x.type
        else:
            return x
    else:
        if isinstance(x, TypeQualifierBase):
            return x.type
        else:
            return type(x)


def instance_check(val, type):
    return isinstance(TypeQualifierBase.decay(val), type)


def subclass_check(val, type):
    return issubclass(TypeQualifierBase.decay(val), type)


async def as_awaitable(fn, /, *args, **kwargs):
    if iscouroutinefunction(fn):
        return await fn(*args, **kwargs)
    else:
        return fn(*args, **kwargs)


#
#
#


@_intrinsic
def zeros(len: int):
    return BitVector[len](Null)


@_intrinsic
def ones(len: int):
    return BitVector[len](Full)


@_intrinsic
def width(inp: Bit | BitVector) -> int:
    if instance_check(inp, Bit):
        return 1
    else:
        return inp.width


def one_hot(width: int, bit_pos: int | Unsigned) -> BitVector:
    assert 0 <= bit_pos < width, "bit_pos out of range"
    return (Unsigned[width](1) << bit_pos).bitvector


@_intrinsic
def _one_hot_map(l):
    return {one_hot(l, bit): True for bit in range(l)}


def is_one_hot(inp):
    return select(inp.bitvector, _one_hot_map(len(inp)), False)


def reverse_bits(inp: BitVector) -> BitVector:
    return concat(*inp)


def is_qualified(arg):
    return isinstance(arg, TypeQualifierBase)


def const_cond(arg):
    result = bool(arg)
    static_assert(isinstance(result, bool), "condition is not a constant")
    return result


class _UncheckedType:
    pass


def _check_type(result, expected):
    if expected is _UncheckedType:
        return True
    elif expected is None:
        return result is None
    else:
        return instance_check(result, expected)


@_intrinsic
def _format_type_check_error(expected_type, actual_type):
    return f"invalid type in checked expression: expected '{expected_type}' but got '{actual_type}'"


class _TypeCheckedExpression:
    def __init__(self, expected_type: type | tuple = _UncheckedType):
        self._expected = expected_type

    def _checked(self, arg):
        assert _check_type(arg, self._expected), _format_type_check_error(
            self._expected, arg
        )
        return arg

    def __getitem__(self, expected_type):
        return type(self)(expected_type)


class _CheckType(_TypeCheckedExpression):
    def __call__(self, arg):
        assert (
            self._expected is not _UncheckedType
        ), "no type specified in std.check_type"
        return self._checked(arg)


class _Select(_TypeCheckedExpression):
    def __call__(self, arg, branches: dict, default=None):
        return self._checked(
            select_with(
                arg,
                branches,
                default=default,
            )
        )


def _first_impl(*args, default):
    if len(args) == 0:
        return default
    else:
        first, *rest = args
        return first[1] if first[0] else _first_impl(*rest, default=default)


class _ChooseFirst(_TypeCheckedExpression):
    def __call__(self, *args, default):
        return self._checked(_first_impl(*args, default=default))


class _Cond(_TypeCheckedExpression):
    def __call__(self, cond: bool, on_true, on_false):
        return self._checked(on_true if cond else on_false)


check_type = _CheckType()
select = _Select()
choose_first = _ChooseFirst()
cond = _Cond()

#
#
#


@_intrinsic
def count_bits(inp):
    if not isinstance(inp, type):
        inp = type(inp)

    if subclass_check(inp, Bit):
        return 1
    elif subclass_check(inp, BitVector):
        return inp.width
    elif subclass_check(inp, CohdlArray):
        inp = TypeQualifierBase.decay(inp)
        return inp._count_ * count_bits(inp._elemtype_)
    elif subclass_check(inp, (bool, CohdlBool)):
        return 1
    elif subclass_check(inp, (int, CohdlInteger)):
        raise SerializationFail("integer type cannot be serialized")
    else:
        return inp._count_bits_()


def to_bits(inp, /):
    if instance_check(inp, (Bit, BitVector)):
        return as_bitvector(inp)
    elif instance_check(inp, CohdlArray):
        return concat(*[to_bits(elem) for elem in inp][::-1])
    elif instance_check(inp, (bool, CohdlBool)):
        return BitVector[1]("1") if inp else BitVector[1]("0")
    else:
        return inp._to_bits_()


class _FromBits:
    @_intrinsic
    def __init__(self, target_type: type):
        self._target_type = target_type

        if target_type is not None:
            assert isinstance(target_type, type), "target_type is not a type"
            assert issubclass(
                target_type, (Bit, BitVector, CohdlArray, bool, CohdlBool)
            ) or hasattr(
                target_type, "_from_bits_"
            ), "target_type does not implement from_bits"

    @_intrinsic
    def __getitem__(self, target_type):
        return _FromBits(target_type)

    def __call__(self, bits: BitVector, qualifier=Value):
        assert (
            self._target_type is not None
        ), "missing target type, expected usage: std.from_bits[TARGET_TYPE](inp)"
        assert instance_check(
            bits, BitVector
        ), "std.from_bits expects a BitVector as its first argument"
        bv = bits.bitvector

        if issubclass(self._target_type, Bit):
            assert bv.width == 1, "cannot deserialize BitVector to Bit, width is not 1"
            return qualifier[Bit](bv[0])
        elif issubclass(self._target_type, BitVector):
            assert (
                bv.width == self._target_type.width
            ), "cannot deserialize BitVector to BitVector, width does not match"
            return qualifier[self._target_type](bv)
        elif issubclass(self._target_type, CohdlArray):
            elem_width = count_bits(self._target_type._elemtype_)
            assert bv.width == count_bits(
                self._target_type
            ), "cannot deserialize BitVector to Array, width does not match"
            return qualifier[self._target_type](
                [
                    from_bits[self._target_type._elemtype_](
                        bv[elem_width * idx + elem_width - 1 : elem_width * idx]
                    )
                    for idx in range(self._target_type._count_)
                ]
            )
        elif self._target_type is bool or self._target_type is CohdlBool:
            return qualifier[CohdlBool](bv[0])
        else:
            assert (
                self._target_type._count_bits_() == bits.width
            ), "width of serialized BitVector does not match width expected by the target type"
            return self._target_type._from_bits_(bits, qualifier)


from_bits = _FromBits(None)

#
#
#


@_intrinsic
def _get_return_type_hint(fn):
    return typing.get_type_hints(fn).get("return", _UncheckedType)


def check_return(fn):
    if iscouroutinefunction(fn):

        async def wrapper(*args, **kwargs):
            result = await fn(*args, **kwargs)
            assert _check_type(
                result, _get_return_type_hint(fn)
            ), "invalid return value in function call"
            return result

    else:

        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            assert _check_type(
                result, _get_return_type_hint(fn)
            ), "invalid return value in function call"
            return result

    wrapper.__name__ = fn.__name__
    return wrapper


#
#
#


def binary_fold(fn, args, *, right_fold=False):
    if len(args) == 1:
        return Value(args[0])
    else:
        if const_cond(right_fold):
            first, *rest = args
            return fn(first, binary_fold(fn, rest, right_fold=True))
        else:
            first, snd, *rest = args
            return binary_fold(fn, [fn(first, snd), *rest])


@_intrinsic
def _batch_args(args: list, batch_size: int):
    batches = []

    for nr in range(0, len(args), batch_size):
        batches.append(args[nr : nr + batch_size])

    return batches


def batched_fold(fn, args, *, batch_size=2):
    if const_cond(len(args) <= batch_size):
        return binary_fold(fn, args)
    else:
        return batched_fold(
            fn,
            [
                batched_fold(fn, batch, batch_size=batch_size)
                for batch in _batch_args(args, batch_size)
            ],
        )


def _concat_impl(a, b):
    return a @ b


def concat(first, *args):
    if len(args) == 0:
        if instance_check(first, Bit):
            return as_bitvector(first)
        else:
            assert instance_check(
                first, BitVector
            ), "first is {} and not a BitVector".format(first)
            return Value[BitVector[len(first)]](first)
    else:
        return batched_fold(_concat_impl, [first, *args])


def _repeat_filter_by_factor(stretch_list, factor: int):
    return [s for nr, s in enumerate(stretch_list) if (factor & (1 << nr))]


def repeat(val, times: int):
    pow2_list = [val]

    for _ in range(1, times.bit_length()):
        as_pyeval(pow2_list.append, pow2_list[-1] @ pow2_list[-1])

    return concat(
        *[elem for elem in as_pyeval(_repeat_filter_by_factor, pow2_list, times)]
    )


def stretch(val: Bit | BitVector, factor: int):
    assert factor > 0

    if instance_check(val, Bit):
        return repeat(val, factor)
    elif instance_check(val, BitVector):
        if const_cond(factor == 1):
            return val.bitvector.copy()
        else:
            # reverse stretched list so bit 0 is the leftmost
            # concatenated value
            return concat(*[stretch(b, factor) for b in val][::-1])
    else:
        raise AssertionError("invalid argument")


def resize(inp: BitVector, result_width: int):
    inp_width = inp.width

    assert (
        inp_width <= result_width
    ), f"the result width of resize must be larger than the input width"

    if inp_width == result_width:
        return Value[BitVector[result_width]](inp)
    else:
        return zeros(inp_width) @ inp


def leftpad(inp: BitVector, result_width: int, fill=None):
    inp_width = inp.width

    assert (
        inp_width <= result_width
    ), f"the result width of resize must be larger than the input width"

    if inp_width == result_width:
        return Value[BitVector[result_width]](inp)
    else:
        if fill is None:
            fill_bit = Bit(False)
        elif fill is Null or fill is Full:
            fill_bit = Bit(fill)
        else:
            assert instance_check(
                fill, Bit
            ), f"parameter 'fill' should be Null, Full or a Bit type"
            fill_bit = fill

        return stretch(fill_bit, result_width - inp_width) @ inp


def rightpad(inp: BitVector, result_width: int, fill=None):
    inp_width = inp.width

    assert (
        inp_width <= result_width
    ), f"the result width of resize must be larger than the input width"

    if inp_width == result_width:
        return Value[BitVector[result_width]](inp)
    else:
        if fill is None:
            fill_bit = Bit(False)
        elif fill is Null or fill is Full:
            fill_bit = Bit(fill)
        else:
            assert instance_check(
                fill, Bit
            ), f"parameter 'fill' should be Null, Full or a Bit type"
            fill_bit = fill

        return inp @ stretch(fill_bit, result_width - inp_width)


def pad(
    inp: BitVector, left: int = 0, right: int = 0, fill: Bit | Null | Full = Null
) -> BitVector:
    if fill is None:
        fill_bit = Bit(False)
    elif fill is Null or fill is Full:
        fill_bit = Bit(fill)
    else:
        assert instance_check(
            fill, Bit
        ), f"parameter 'fill' should be Null, Full or a Bit type"
        fill_bit = fill

    assert isinstance(left, int) and left >= 0
    assert isinstance(right, int) and right >= 0

    if left == 0 and right == 0:
        return as_bitvector(inp)

    if left != 0:
        left_padded = stretch(fill_bit, left) @ inp
    else:
        left_padded = inp

    if right != 0:
        return left_padded @ stretch(fill_bit, right)
    else:
        return left_padded


def apply_mask(old: BitVector, new: BitVector, mask: BitVector):
    assert old.width == new.width, "old.width does not match new.width"
    return (old.bitvector & ~mask) | (new.bitvector & mask)


class Mask:
    def __init__(self, val):
        self._val = val

    def apply(self, old, new):
        if self._val is Null:
            return Temporary(old)
        elif self._val is Full:
            return Temporary(new.copy())
        else:
            return apply_mask(old, new, self._val)

    def as_vector(self, width: int):
        return self.apply(zeros(width), ones(width))


def as_bitvector(inp: BitVector | Bit | str):
    if isinstance(inp, str):
        return BitVector[len(inp)](inp)
    elif instance_check(inp, BitVector):
        return inp.bitvector.copy()
    else:
        assert instance_check(inp, Bit)
        return (inp @ inp)[0:0]


def rol(inp: BitVector, n: int = 1) -> BitVector:
    static_assert(0 <= n <= inp.width)
    if const_cond(n == 0 or n == inp.width):
        return inp.bitvector.copy()
    else:
        return inp.lsb(rest=n) @ inp.msb(n)


def ror(inp: BitVector, n: int = 1) -> BitVector:
    static_assert(0 <= n <= inp.width)
    if const_cond(n == 0 or n == inp.width):
        return inp.bitvector.copy()
    else:
        return inp.lsb(n) @ inp.msb(rest=n)


def lshift_fill(val: BitVector, fill: Bit | BitVector) -> BitVector:
    width_val = width(val)
    width_fill = width(fill)

    if width_fill == width_val:
        return as_bitvector(fill)
    elif width_fill > width_val:
        fail("fill width ({}) exceeds width of value ({})", width_fill, width_val)
    else:
        return val.lsb(width_val - width_fill) @ fill


def rshift_fill(val: BitVector, fill: Bit | BitVector) -> BitVector:
    width_val = width(val)
    width_fill = width(fill)

    if width_fill == width_val:
        return as_bitvector(fill)
    elif width_fill > width_val:
        fail("fill width ({}) exceeds width of value ({})", width_fill, width_val)
    else:
        return fill @ val.msb(width_val - width_fill)


@_intrinsic
def _batched_indices(l, n):
    last = l - 1
    return [(min(off + n - 1, last), off) for off in range(0, l, n)]


def batched(input: BitVector, n: int, allow_partial=False) -> list[BitVector]:
    is_multiple = len(input) % n == 0

    static_assert(is_multiple or const_cond(allow_partial))

    return [input[upper:lower] for upper, lower in _batched_indices(len(input), n)]


def select_batch(
    input: BitVector, onehot_selector: BitVector, batch_size: int
) -> BitVector:
    static_assert(len(input) == len(onehot_selector) * batch_size)
    masked = input.bitvector & stretch(onehot_selector, batch_size)

    return batched_fold(lambda a, b: a | b, batched(masked, batch_size))


def parity(vec: BitVector) -> Bit:
    return batched_fold(lambda a, b: a ^ b, vec)


_lt = lambda a, b: a < b
_gt = lambda a, b: a > b


def minimum(first, /, *args, key=identity, cmp=_lt):
    if len(args) != 0:
        return minimum([first, *args], key=key, cmp=cmp)
    else:
        assert len(first) != 0, "first argument is empty"
        # reverse order of elements before fold so the first found
        # minimum is returned
        return batched_fold(lambda a, b: a if cmp(key(a), key(b)) else b, first[::-1])


def maximum(first, /, *args, key=identity, cmp=_gt):
    return minimum(first, *args, key=key, cmp=cmp)


def min_element(container, /, *, key=identity, cmp=_lt):
    Index = Unsigned.upto(len(container))
    indexed_container = [(Index(nr), elem) for nr, elem in enumerate(container)]
    return minimum(indexed_container, key=lambda x: key(x[1]), cmp=cmp)


def max_element(container, /, *, key=identity, cmp=_gt):
    return min_element(container, key=key, cmp=cmp)


def min_index(container, /, *, key=identity, cmp=lambda a, b: a < b):
    keys = [key(elem) for elem in container]
    return min_element(keys, cmp=cmp)[0]


def max_index(container, /, *, key=identity, cmp=lambda a, b: a > b):
    keys = [key(elem) for elem in container]
    return max_element(keys, cmp=cmp)[0]


@_intrinsic
def _safe_add_unsigned_target(a: Unsigned, b: Unsigned):
    return Value[Unsigned[max(a.width, b.width) + 1]]


def _safe_add_unsigned(a: Unsigned, b: Unsigned):
    # add two unsigned numbers and extend the result
    # size so no overflow is possible

    T = _safe_add_unsigned_target(a, b)
    return T(a) + b


def _count_impl(container, cmp):
    T_bit = Value[Bit]
    inital_cnt = [as_bitvector(T_bit(bool(cmp(elem)))).unsigned for elem in container]

    result_width = len(inital_cnt).bit_length()

    result = batched_fold(_safe_add_unsigned, inital_cnt)

    # TODO check if need, might always work because of batched_fold
    if result.width != result_width:
        return result.lsb(result_width).unsigned
    else:
        return result


def count(container, /, value=_PrivateNone, *, check=_PrivateNone):
    if len(container) == 0:
        return Unsigned[1](0)
    else:
        if value is _PrivateNone:
            assert check is not _PrivateNone, "one of value or check must be specified"
            _check = check
        else:
            assert check is _PrivateNone, "only one of value and check can be specified"
            _check = lambda x: x == value

        return _count_impl(container, _check)


@_intrinsic
def _set_bit_map(w: int):
    T = Unsigned.upto(w)
    return {nr: T(nr.bit_count()) for nr in range(2**w)}


def _count_set_bits_impl(vector: BitVector):
    return select(vector.unsigned, _set_bit_map(vector.width), default=0)


def count_set_bits(vector: BitVector, /, *, batch_size: int = 6):
    set_cnt = [
        _count_set_bits_impl(vec)
        for vec in batched(vector, batch_size, allow_partial=True)
    ]

    result = batched_fold(_safe_add_unsigned, set_cnt)
    result_width = vector.width.bit_length()

    if result.width != result_width:
        return result.lsb(result_width).unsigned
    else:
        return result


@_intrinsic
def _clear_bit_map(w: int):
    T = Unsigned.upto(w)
    return {nr: T(w - nr.bit_count()) for nr in range(2**w)}


def _count_clear_bits_impl(vector: BitVector):
    return select(vector.unsigned, _clear_bit_map(vector.width), default=0)


def count_clear_bits(vector: BitVector, /, *, batch_size: int = 6):
    set_cnt = [
        _count_clear_bits_impl(vec)
        for vec in batched(vector, batch_size, allow_partial=True)
    ]

    result = batched_fold(_safe_add_unsigned, set_cnt)
    result_width = vector.width.bit_length()

    if result.width != result_width:
        return result.lsb(result_width).unsigned
    else:
        return result


def clamp(val, low, high, cmp=_lt):
    T = base_type(val)
    val_low = Value[T](low)
    val_high = Value[T](high)

    return (
        val_low
        if cmp(val, val_low)
        else (val_high if cmp(val_high, val) else Value[T](val))
    )
