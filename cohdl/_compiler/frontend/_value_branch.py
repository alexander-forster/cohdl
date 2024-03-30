from __future__ import annotations

from typing import Tuple


from cohdl._core._type_qualifier import TypeQualifier, Signal, Variable, Temporary
from cohdl._core._primitive_type import is_primitive

from cohdl._core._intrinsic import _BitSignalEvent, _BitSignalEventGroup
from cohdl._core._bit import Bit
from cohdl._core._boolean import _Boolean, _BooleanLiteral, _NullFullType
from cohdl._core._bit_vector import BitVector
from cohdl._core._signed import Signed
from cohdl._core._unsigned import Unsigned


class _Redirect:
    def __init__(self, target, source):
        self.target = target

        if isinstance(source, TypeQualifier):
            self.source = source
        else:
            self.source = target.type(source)

    def print(self):
        print(f"{self.target} <<= {self.source}")


class _ValueBranchHook:
    def __init__(self, redirects: list[_Redirect] | None = None, *, name=None):
        self.redirects = [] if redirects is None else redirects
        self.name = name

    def add_redirect(self, redirect: _Redirect):
        self.redirects.append(redirect)

    def has_redirect(self):
        return len(self.redirects) != 0

    def print(self):
        for red in self.redirects:
            red.print()


class _ValueBranch:
    def __init__(self, hook: _ValueBranchHook, obj):
        self.obj = obj
        self.hook = hook

    def _type(self):
        return _ValueBranch(self.hook, type(self.obj))

    def _id(self):
        return _ValueBranch(self.hook, id(self.obj))

    def __getitem__(self, args):
        return _ValueBranch(self.hook, self.obj.__getitem__(args))

    def _getattr(self, name):
        return _ValueBranch(self.hook, ObjTraits.getattr(self.obj, name))

    def _redirect(self, target):
        assert isinstance(target, TypeQualifier)

        if isinstance(self.obj, _MergedBranch):
            source_obj = Temporary[target.type]()
            self.obj._redirect_values(source_obj)
        else:
            source_obj = self.obj

        self.hook.add_redirect(_Redirect(target, source_obj))


def _try_join(options):
    result_type = None

    # find most constrained primitive type compatible with all options
    for option in options:
        option = TypeQualifier.decay(option)
        option_type = type(option)

        if result_type is None:
            if is_primitive(option):
                result_type = type(option)
            elif isinstance(option, bool):
                result_type = _Boolean
        else:
            if issubclass(result_type, Bit):
                if option_type not in (
                    Bit,
                    bool,
                    _Boolean,
                    _BooleanLiteral,
                    _NullFullType,
                ):
                    # incompatible branches, return early
                    return None
            elif issubclass(result_type, _Boolean):
                if option_type is Bit:
                    result_type = Bit
                elif option_type not in (
                    bool,
                    _Boolean,
                    _BooleanLiteral,
                    _NullFullType,
                ):
                    # incompatible branches, return early
                    return None
            elif issubclass(result_type, BitVector) and issubclass(
                option_type, BitVector
            ):
                if issubclass(result_type, Signed) and issubclass(option_type, Signed):
                    result_type = (
                        result_type
                        if result_type.width >= option_type.width
                        else option_type
                    )
                elif issubclass(result_type, Unsigned) and issubclass(
                    option_type, Unsigned
                ):
                    result_type = (
                        result_type
                        if result_type.width >= option_type.width
                        else option_type
                    )
                else:
                    if result_type.width != option_type.width:
                        # incompatible branches, return early
                        return None

                    result_type = BitVector[result_type.width]

    if result_type is None:
        return None

    for option in options:
        option = TypeQualifier.decay(option)
        try:
            result_type(option)
        except Exception:
            return None

    return result_type


class _MergedBranch:
    def __new__(cls, branches: list[_ValueBranch]):
        if len(branches) == 0:
            return None

        if len(branches) == 1:
            return branches[0].obj

        first, *rest = branches
        first_obj = first.obj

        if all(first.obj is branch.obj for branch in rest):
            return first_obj

        result_type = _try_join([branch.obj for branch in branches])

        if result_type is not None:
            result = Temporary[result_type]()

            for branch in branches:
                branch._redirect(result)

            return result

        return object.__new__(cls)

    def __init__(self, branches: list[_ValueBranch]):
        # avoid double initialization if __new__ returns an existing
        # _MergedBranch object (possible when branches contains a single _MergedBranch object)
        if not hasattr(self, "_cohdl_init_complete"):
            for branch in branches:
                assert isinstance(
                    branch, _ValueBranch
                ), "internal error: argument of MergedBranch is not a _ValueBranch"
                assert branch.obj is not self, "internal error: recursive merged branch"

            self.branches = branches
            self._cohdl_init_complete = True

    def isinstance(self, types):
        branch_results = [isinstance(branch.obj, types) for branch in self.branches]

        all_results = all(branch_results)
        any_result = any(branch_results)

        assert (
            all_results or not any_result
        ), "the result of isinstance must be the same for all possible input objects"
        return all_results

    def issubclass(self, types):
        branch_results = [issubclass(branch.obj, types) for branch in self.branches]

        all_results = all(branch_results)
        any_result = any(branch_results)

        assert (
            all_results or not any_result
        ), "the result of issubclass must be the same for all possible input objects"
        return all_results

    def type(self):
        return _MergedBranch([branch._type() for branch in self.branches])

    def id(self):
        return _MergedBranch([branch._id() for branch in self.branches])

    def _getitem(self, *args):
        return _MergedBranch([branch.__getitem__(*args) for branch in self.branches])

    def _hasattr(self, name):
        return all(ObjTraits.hasattr(branch.obj, name) for branch in self.branches)

    def _getattr(self, name):
        return _MergedBranch([branch._getattr(name) for branch in self.branches])

    def _redirect_values(self, target):
        for branch in self.branches:
            branch._redirect(target)


class ObjTraits:
    @staticmethod
    def init_active(obj) -> bool:
        if isinstance(obj, _MergedBranch):
            return False
        return hasattr(obj, "_cohdl_init_active")

    @staticmethod
    def hasattr(obj, name: str):
        if isinstance(obj, _MergedBranch):
            return obj._hasattr(name)

        # don't use hasattr directly to avoid problems
        # with descriptors

        if isinstance(obj, int):
            return hasattr(obj, name)

        return (
            (hasattr(obj, "__dict__") and name in vars(obj))
            or hasattr(type(obj), name)
            or hasattr(obj, name)
        )

    @staticmethod
    def gettype(obj):
        if isinstance(obj, _MergedBranch):
            return obj.type()
        return type(obj)

    @staticmethod
    def getattr(obj, name: str):
        if isinstance(obj, _MergedBranch):
            return obj._getattr(name)
        return getattr(obj, name)

    @staticmethod
    def isinstance(obj, class_or_tuple: type | Tuple) -> bool:
        assert not isinstance(obj, _MergedBranch)
        if isinstance(obj, _MergedBranch):
            return obj.is_instance(class_or_tuple)
        return isinstance(obj, class_or_tuple)

    @staticmethod
    def get(obj):
        assert not isinstance(obj, _MergedBranch)
        if isinstance(obj, _MergedBranch):
            return obj.get()
        return obj

    @staticmethod
    def runtime_variable(obj) -> bool:
        assert not isinstance(obj, _MergedBranch)
        return (ObjTraits.isinstance(obj, (Signal, Variable, Temporary))) or isinstance(
            obj, (_BitSignalEvent, _BitSignalEventGroup)
        )
