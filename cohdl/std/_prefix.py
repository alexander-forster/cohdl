from __future__ import annotations

from cohdl._core._intrinsic import _intrinsic
from cohdl._core import TypeQualifierBase, is_primitive_type


class _Prefix:
    _existing_prefix: dict[str, int] = {}
    _prefix_scope: list[_Prefix] = []

    @staticmethod
    def _parent_prefix():
        if len(_Prefix._prefix_scope) == 0:
            return None
        return _Prefix._prefix_scope[-1]

    @_intrinsic
    def __init__(self, prefix: str, subprefix=False):
        if not subprefix and len(_Prefix._prefix_scope) != 0:
            prefix = _Prefix._prefix_scope[-1].name(prefix)

        lower = prefix.lower()
        cnt = _Prefix._existing_prefix.get(lower, 0)
        _Prefix._existing_prefix[lower] = cnt + 1

        if cnt == 0:
            self._prefix = prefix
        else:
            if prefix.endswith("_"):
                self._prefix = f"{prefix}{cnt}"
            else:
                self._prefix = f"{prefix}_{cnt}"

        self._scope_active = 0
        self._used_names = []

    @_intrinsic
    def subprefix(self, subname: str):
        return _Prefix(self.name(subname), subprefix=True)

    @_intrinsic
    def name(self, name: str | None) -> str:
        if name is None:
            return self._prefix

        lower = name.lower()
        assert (
            not lower in self._used_names
        ), f"name '{name}' already used with this prefix '{self._prefix}'"
        self._used_names.append(lower)
        return f"{self._prefix}_{name}"

    @_intrinsic
    def prefix_str(self) -> str:
        return self._prefix

    @_intrinsic
    def __enter__(self):
        if self._scope_active == 0:
            _Prefix._prefix_scope.append(self)
        self._scope_active += 1
        return self

    @_intrinsic
    def __exit__(self, type, value, traceback):
        assert self._scope_active, "attempt to exit inactive scope"
        self._scope_active -= 1

        if self._scope_active == 0:
            assert _Prefix._prefix_scope.pop() is self
        return None


@_intrinsic
def prefix(base_name: str) -> _Prefix:
    return _Prefix(base_name)


@_intrinsic
def name(name: str) -> str:
    parent = _Prefix._parent_prefix()

    if parent is None:
        return name
    return parent.name(name)


class _NamedQualifier:
    @_intrinsic
    def __init__(self, type, qualifier, name):
        self.type = type

        if isinstance(qualifier, _NamedQualifier):
            self.qualifier = qualifier.qualifier

            if name is None:
                self.prefix = qualifier.prefix
            else:
                self.prefix = qualifier.prefix.subprefix(name)
        else:
            self.qualifier = qualifier
            assert name is not None
            self.prefix = prefix(name)

    def __call__(self, *args, **kwargs):
        if self.type is None:
            assert len(args) == 1 and len(kwargs) == 0
            T = type(TypeQualifierBase.decay(args[0]))
        else:
            T = self.type

        if is_primitive_type(T) or T is bool or T is int:
            name = self.prefix.name(kwargs.get("name", None))
            return self.qualifier[T](*args, **{**kwargs, "name": name})
        else:
            with self.prefix:
                return T(
                    *args,
                    **kwargs,
                    _qualifier_=_NamedQualifier(None, self, None),
                )

    @_intrinsic
    def __getitem__(self, T):
        return _NamedQualifier(T, self, None)


class _NamedQualifierBuilder:
    @_intrinsic
    def __getitem__(self, qualifier_name):
        qualifier, name = qualifier_name
        return _NamedQualifier(None, qualifier, name)


NamedQualifier = _NamedQualifierBuilder()
