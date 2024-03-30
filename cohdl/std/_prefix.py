from __future__ import annotations

from cohdl._core._intrinsic import _intrinsic


class _Prefix:
    _existing_prefix: dict[str, int] = {}
    _prefix_scope: list[_Prefix] = []

    @staticmethod
    def _parent_prefix():
        if len(_Prefix._prefix_scope) == 0:
            return None
        return _Prefix._prefix_scope[-1]

    @_intrinsic
    def __init__(self, prefix: str):
        if len(_Prefix._prefix_scope) != 0:
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

        self._scope_active = False
        self._used_names = []

    @_intrinsic
    def subprefix(self, subname: str):
        return _Prefix(f"{self._prefix}_{subname}")

    @_intrinsic
    def name(self, name: str) -> str:
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
        assert not self._scope_active, "attempt to enter already active scope"
        _Prefix._prefix_scope.append(self)
        self._scope_active = True
        return self

    @_intrinsic
    def __exit__(self, type, value, traceback):
        assert self._scope_active, "attempt to exit inactive scope"
        assert _Prefix._prefix_scope.pop() is self
        self._scope_active = False
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
