from __future__ import annotations

from typing import Iterator, TypeVar, Generic, Callable, overload, Iterable


T = TypeVar("T")
U = TypeVar("U")


class Span(Generic[T]):
    def __init__(self, content: list[T]):
        self._data = [*content]

    def size(self) -> int:
        return len(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def first(self, n) -> Span[T]:
        return Span(self._data[0:n])

    def last(self, n) -> Span[T]:
        return Span(self._data[-n:])

    def subspan(self, offset, cnt) -> Span[T]:
        return Span(self._data[offset : offset + cnt])

    @overload
    def __getitem__(self, x: int) -> T:
        ...

    @overload
    def __getitem__(self, x: slice) -> Span[T]:
        ...

    def __getitem__(self, x):
        if isinstance(x, slice):
            return Span(self._data[x])

        assert isinstance(x, int)
        return self._data[x]

    def __item__(self):
        return self._data

    def __iter__(self) -> Iterator[T]:
        return self._data.__iter__()

    def iter_extend(self, value):
        def gen():
            iter = self._data.__iter__()
            try:
                while True:
                    yield next(iter)
            except StopIteration:
                while True:
                    yield value

        return gen()

    @staticmethod
    def from_iter(iter, modifyer=None) -> Span:
        if modifyer is not None:
            data = [modifyer(x) for x in iter]
        else:
            data = [x for x in iter]

        return Span(data)

    @staticmethod
    def from_zip_iter(*iters, modifyer) -> Span:
        return Span([modifyer(*args) for args in zip(*iters)])

    def generate(self, fn: Callable[[T], U]) -> Span[U]:
        return Span([fn(x) for x in self._data])

    def apply(self, fn: Callable[[T], None]):
        for item in self._data:
            fn(item)

    def apply_zip(self, fn: Callable[[T, U], None], other: Iterable[U]):
        for a, b in zip(self._data, other):
            fn(a, b)

    def __str__(self) -> str:
        return f"{[*self]}"

    def __repr__(self) -> str:
        return f"{[*self]}"
