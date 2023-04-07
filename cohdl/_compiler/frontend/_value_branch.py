from __future__ import annotations

from typing import Tuple


from cohdl._core._type_qualifier import TypeQualifier, Signal, Variable, Temporary
from cohdl._core._primitive_type import is_primitive

from cohdl._core._intrinsic import _BitSignalEvent, _BitSignalEventGroup


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

        for branch in branches:
            raw_obj = TypeQualifier.decay(branch.obj)
            if is_primitive(raw_obj):
                temp = Temporary[type(raw_obj)]()

                for b in branches:
                    b._redirect(temp)

                return temp

        obj = object.__new__(cls)
        return obj

    def __init__(self, branches: list[_ValueBranch]):
        # avoid double initialization if __new__ returns an existing
        # _MergedBranch object (possible when branches contains a single _MergedBranch object)
        if not hasattr(self, "_cohdl_init_complete"):
            for branch in branches:
                assert isinstance(branch, _ValueBranch)
                assert not branch.obj is self

            self.branches = branches
            self._cohdl_init_complete = True

    def _getitem(self, *args):
        _MergedBranch([branch.__getitem__(*args) for branch in self.branches])

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
