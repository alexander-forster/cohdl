from __future__ import annotations
from dataclasses import dataclass
from typing import Any

import enum

from cohdl.utility import IdMap

#
#
# intrinsic decorators
#
#


class _IntrinsicReplacement:
    class _Assignment:
        def __init__(self, nr_target, nr_source):
            self.nr_target = nr_target
            self.nr_source = nr_source

    def __init__(self, fn, is_special_case, *, assignment_spec=None, evaluate=False):
        self.fn = fn

        if evaluate:
            assert (
                is_special_case
            ), "internal error: cannot evaluate _IntrinsicReplacement unless it is special cased"

        self.is_special_case = is_special_case
        self.assignment_spec = assignment_spec
        self.evaluate = evaluate


_intrinsic_functions = []
_intrinsic_replacements = IdMap[Any, _IntrinsicReplacement]()


def _intrinsic(fn):
    _intrinsic_functions.append(fn)
    return fn


def _intrinsic_replacement(
    default_implementation,
    *,
    special_case=True,
    assignment_spec: tuple[int, int] | None = None,
    evaluate=False,
):
    assert (
        default_implementation in _intrinsic_functions
    ), "internal error: default implementation of intrinsic_replacement is not intrinsic"

    if assignment_spec is not None:
        assignment_spec = _IntrinsicReplacement._Assignment(*assignment_spec)

    def helper(fn):
        assert (
            default_implementation not in _intrinsic_replacements
        ), "internal error: redefinition of intrinsic_replacement"
        _intrinsic_replacements[default_implementation] = _IntrinsicReplacement(
            fn, special_case, assignment_spec=assignment_spec, evaluate=evaluate
        )
        return fn

    return helper


def _intrinsic_property(p):
    _intrinsic(p.fset)
    _intrinsic(p.fget)
    return p


def _is_intrinsic(fn):
    return fn in _intrinsic_functions


def _has_intrinsic_replacement(fn):
    return fn in _intrinsic_replacements


#
# comment
#


class _IntrinsicComment:
    def __init__(self, lines: list[str]):
        self.lines = lines


@_intrinsic
def comment(*lines: str):
    assert all(
        isinstance(line, str) for line in lines
    ), "all arguments of comment must be of type str"
    pass


@_intrinsic_replacement(comment)
def _comment_replacement(*lines: str):
    assert all(
        isinstance(line, str) for line in lines
    ), "all arguments of comment must be of type str"
    return _IntrinsicComment(lines)


#
# inline entity
#


class _IntrinsicInlineEntity:
    def __init__(self, entity):
        self.entity = entity


#
#
# select
#
#


@_intrinsic
def select_with(arg, branches: dict, default=None):
    if arg in branches:
        return branches[arg]

    return default


@dataclass
class _SelectWith:
    arg: Any
    branches: dict
    default: Any


@_intrinsic_replacement(select_with)
def _intrinsic_select_with(arg, branches: dict, default=None):
    return _SelectWith(arg, branches, default)


#
#
#


class _CoroutineStep:
    def __init__(self, coro):
        self.coro = coro


@_intrinsic
def coroutine_step(coro) -> None:
    """
    should never be called, always is handled by parser
    """

    raise AssertionError("coroutine_step called outside synthesizable context")


@_intrinsic_replacement(coroutine_step)
def coroutine_step_replacement(coro):
    return _CoroutineStep(coro)


class _SensitivitySpec: ...


class _SensitivityList(_SensitivitySpec):
    def __init__(self, signals):
        self.signals: list = signals


class _SensitivityAll(_SensitivitySpec):
    def __init__(self): ...


class _Sensitivity:
    @staticmethod
    def list(*args):
        raise AssertionError("_Sensitivity.list called outside synthesizable context")

    @staticmethod
    def all():
        raise AssertionError("_Sensitivity.all called outside synthesizable context")


_intrinsic(_Sensitivity.all)
_intrinsic(_Sensitivity.list)


@_intrinsic_replacement(_Sensitivity.list)
def sensitifity_list_replacement(*args):
    return _SensitivityList([*args])


@_intrinsic_replacement(_Sensitivity.all)
def sensitifity_all_replacement(*args):
    return _SensitivityAll()


sensitivity = _Sensitivity

#
#
#


class _ResetContext: ...


@_intrinsic
def reset_context():
    raise AssertionError("reset_context called outside synthesizable context")


@_intrinsic_replacement(reset_context)
def reset_context_replacement():
    return _ResetContext()


class _ResetPushed: ...


@_intrinsic
def reset_pushed():
    raise AssertionError("reset_pushed called outside synthesizable context")


@_intrinsic_replacement(reset_pushed)
def reset_pushed_replacement():
    return _ResetPushed()


#
#
#


class _IsInstance:
    def __init__(self, obj, type):
        self.obj = obj
        self.type = type


class _IsSubclass:
    def __init__(self, cls, type):
        self.cls = cls
        self.type = type


class _Type:
    def __init__(self, obj):
        self.obj = obj


class _Id:
    def __init__(self, obj):
        self.obj = obj


_intrinsic(isinstance)
_intrinsic(issubclass)
_intrinsic(type)
_intrinsic(id)


@_intrinsic_replacement(isinstance)
def isinstance_replacement(obj, type):
    return _IsInstance(obj, type)


@_intrinsic_replacement(issubclass)
def issubclass_replacement(obj, type):
    return _IsSubclass(obj, type)


@_intrinsic_replacement(type)
def type_replacement(obj):
    return _Type(obj)


@_intrinsic_replacement(id)
def id_replacement(obj):
    return _Id(obj)


#
#
#


class _BitSignalEvent:
    class Type(enum.Enum):
        RISING = enum.auto()
        FALLING = enum.auto()
        BOTH_EDGES = enum.auto()
        HIGH = enum.auto()
        LOW = enum.auto()

    def __init__(self, sig, event_type: _BitSignalEvent.Type):
        self.sig = sig
        self.event_type = event_type

    def __and__(self, other):
        return _BitSignalEventGroup(_BitSignalEventGroup.Operation.AND, [self, other])

    def __or__(self, other):
        return _BitSignalEventGroup(_BitSignalEventGroup.Operation.OR, [self, other])


class _BitSignalEventGroup:
    class Operation(enum.Enum):
        AND = enum.auto()
        OR = enum.auto()

    def __init__(self, operation, events: list[_BitSignalEvent | _BitSignalEventGroup]):
        self.operation = operation
        self.events = events

    def __and__(self, other):
        if self.operation is _BitSignalEventGroup.Operation.AND:
            return _BitSignalEventGroup(
                _BitSignalEventGroup.Operation.AND, [*self.events, other]
            )
        else:
            return _BitSignalEventGroup(
                _BitSignalEventGroup.Operation.AND, [self, other]
            )

    def __or__(self, other):
        if self.operation is _BitSignalEventGroup.Operation.OR:
            return _BitSignalEventGroup(
                _BitSignalEventGroup.Operation.OR, [*self.events, other]
            )
        else:
            return _BitSignalEventGroup(
                _BitSignalEventGroup.Operation.OR, [self, other]
            )


@_intrinsic
def rising_edge(_):
    raise AssertionError("rising called outside synthesizable context")


@_intrinsic
def falling_edge(_):
    raise AssertionError("falling called outside synthesizable context")


@_intrinsic
def high_level(_):
    raise AssertionError("high_level called outside synthesizable context")


@_intrinsic
def low_level(_):
    raise AssertionError("low_level called outside synthesizable context")


@_intrinsic_replacement(rising_edge, special_case=False)
def rising_edge_replacement(sig):
    return _BitSignalEvent(sig, _BitSignalEvent.Type.RISING)


@_intrinsic_replacement(falling_edge, special_case=False)
def falling_edge_replacement(sig):
    return _BitSignalEvent(sig, _BitSignalEvent.Type.FALLING)


@_intrinsic_replacement(high_level, special_case=False)
def high_level_replacement(sig):
    return _BitSignalEvent(sig, _BitSignalEvent.Type.HIGH)


@_intrinsic_replacement(low_level, special_case=False)
def low_level_replacement(sig):
    return _BitSignalEvent(sig, _BitSignalEvent.Type.LOW)
