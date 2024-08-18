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
            try:
                # try to construct target type from source to check,
                # that they are compatible
                target.type(TypeQualifier.decay(source))
            except Exception as err:
                err.add_note(
                    f"at least one possible source of this expression is not compatible with the target (source={source})"
                )
                raise

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

    def __iter__(self):
        return iter(_ValueBranch(self.hook, elem) for elem in self.obj)

    def __len__(self):
        return len(self.obj)

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
        if isinstance(option, _NullFullType):
            # do not join Null/Full assignments like the following
            # would lead to errors
            #
            # Signal[Unsigned[8]]() <<= Signal[Unsigned[4]]() if a else Full
            return None

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
                r_signed = isinstance(result_type, Signed)
                r_unsigned = isinstance(result_type, Unsigned)

                o_signed = isinstance(option_type, Signed)
                o_unsigned = isinstance(option_type, Unsigned)

                if (r_signed and o_signed) or (r_unsigned and o_unsigned):
                    result_type = (
                        result_type
                        if result_type.width >= option_type.width
                        else option_type
                    )
                elif not (r_unsigned or r_signed or o_unsigned or o_signed):
                    if result_type.width != option_type.width:
                        # incompatible branches, return early
                        return None

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

    def _is(self, other):
        if not isinstance(other, _MergedBranch):
            return False

        if len(self.branches) != len(other.branches):
            return False

        return all(a.obj is b.obj for a, b in zip(self.branches, other.branches))

    def _getitem(self, *args):
        return _MergedBranch([branch.__getitem__(*args) for branch in self.branches])

    def _hasattr(self, name):
        return all(ObjTraits.hasattr(branch.obj, name) for branch in self.branches)

    def _getattr(self, name):
        return _MergedBranch([branch._getattr(name) for branch in self.branches])

    def _redirect_values(self, target):
        for branch in self.branches:
            branch._redirect(target)

    def __getitem__(self, *args):
        return self._getitem(*args)

    def __len__(self):
        result = None

        for elem in self.branches:
            l = len(elem)

            if result is None:
                result = l
            else:
                assert (
                    result == l
                ), f"length of possible sources is not consistent {result} != {l}"

        return result

    def __iter__(self):
        result = []

        for elems in zip(*self.branches, strict=True):
            result.append(_MergedBranch(elems))

        return iter(result)


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
