from __future__ import annotations

from typing import Callable, TypeVar, Generic

S = TypeVar("S")
T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


class IdMap(Generic[S, T], dict[int, T]):
    @staticmethod
    def merge(
        *sources: IdMap[U, V], on_conflict: Callable | None = None
    ) -> IdMap[U, V]:
        result: dict[int, U] = {}

        if on_conflict is None:
            on_conflict = lambda a, b: a

        for source in sources:
            conflict_keys = result.keys() & source.keys()

            result.update(
                {
                    key: dict.__getitem__(source, key)
                    for key in source.keys() - conflict_keys
                }
            )

            result.update(
                {
                    key: (
                        dict.__getitem__(source, key)
                        if result[key] is dict.__getitem__(source, key)
                        else on_conflict(result[key], dict.__getitem__(source, key))
                    )
                    for key in conflict_keys
                }
            )

        return IdMap(result)

    def map_self(self, obj):
        self[obj] = obj

    def __getitem__(self, key_obj: S | int) -> T:
        if type(key_obj) is int:
            return super().__getitem__(key_obj)
        return super().__getitem__(id(key_obj))

    def __setitem__(self, key_obj: S | int, value: T) -> None:
        assert type(key_obj) is not str

        if type(key_obj) is int:
            return super().__setitem__(key_obj, value)
        return super().__setitem__(id(key_obj), value)

    def __delitem__(self, key_obj: S | int) -> None:
        if type(key_obj) is int:
            super().__delitem__(key_obj)
        else:
            super().__delitem__(id(key_obj))

    def __contains__(self, key_obj: S | int) -> bool:
        if type(key_obj) is int:
            return key_obj in dict.keys(self)
        return super().__contains__(id(key_obj))


class IdSet(Generic[T]):
    def __init__(self, *, _content: IdMap | None = None) -> None:
        self._content: IdMap[T, T] = IdMap() if _content is None else _content

    def __and__(self, other: IdSet[T]) -> IdSet[T]:
        keys = self._content.keys() & other._content.keys()
        return IdSet(_content=IdMap({key: self._content[key] for key in keys}))

    def __iter__(self):
        return iter(self._content.values())

    def add(self, element: T):
        self._content[element] = element

    def __contains__(self, element: T):
        return element in self._content

    def __len__(self) -> int:
        return len(self._content)

    def union(*others: IdSet[S]) -> IdSet[T | S]:
        return IdSet(_content=IdMap.merge(*[o._content for o in others]))

    def clear(self):
        self._content.clear()

    def update(self, *others):
        for o in others:
            for elt in o:
                self.add(elt)
