from __future__ import annotations

class _Prefix:
    def subprefix(self, subname: str) -> _Prefix:
        """
        Create a new prefix by concatenating self with `subname`.
        """

    def name(self, name: str | None) -> str:
        """
        Returns a new name by concatenating the prefix and the given name.
        """

    def prefix_str(self) -> str:
        """
        Returns the current prefix as a string.
        """

    def __enter__(self) -> _Prefix:
        """
        Starts a prefixed context.

        All calls to `std.prefix` and `std.name` will be prefixed
        with `self.prefix_str`.
        """

    def __exit__(self, type, value, traceback) -> None: ...

def prefix(base_name: str) -> _Prefix:
    """
    Request a new unique prefix built from `base_name`.

    The `std.prefix` utility exists to make it easier to track cohdl Signals/Variables
    in the generated HDL representation. Usage of this function is optional and has no
    runtime effect.

    >>> class Uart:
    >>>     def __init__(self, flow_control=False):
    >>>         p = std.prefix("uart")
    >>>         self.rx = Signal[Bit](name=p.name("rx"))
    >>>         self.tx = Signal[Bit](name=p.name("tx"))
    >>>
    >>>         # prefix can also be used in a with statement
    >>>         # and is then applied to all nested prefixes
    >>>         # and `std.name`
    >>>         with p:
    >>>             if flow_control:
    >>>                 self.rts = Signal[Bit](name=std.name("rts"))
    >>>                 self.cts = Signal[Bit](name=std.name("cts"))
    >>>         ...
    >>>
    >>> uart1 = Uart()
    >>> # will create two signals "uart_rx" and "uart_tx"
    >>> uart2 = Uart(True)
    >>> # will create four signals "uart_1_rx", "uart_1_tx", "uart_1_rts" and "uart_1_cts"
    >>> # the `1` is added to create a unique prefix to indicate, that all these signals
    >>> # belong to the same class.
    """

def name(name: str) -> str:
    """
    When this function is called in a prefixed context (see `std.prefix`) it returns
    a new name built by concatenating the prefix with `name`.
    Outside of prefixed contexts the argument is returned unchanged.
    """

class _NamedQualifier:
    def __getitem__(self, qualifier, name: str):
        return qualifier

NamedQualifier = _NamedQualifier()
"""
`NamedQualifier` has no runtime effect. It only affects the names
of Signals/Variables/Temporaries and is used to make the generated HDL more readable.

In the following example `plain_obj` and `named_obj` are functionally identical.
The names of new Signals constructed during the initialization of `plain_obj` are
random (unless explicitly defined).
The names of new Signals constructed during the initialization of `named_obj` are
derived from the given base name `my_name`.

>>> # plain_obj and named_obj are functionally identical
>>> # the Signals created during the initialization of named_obj
>>> # are named using the prefix 'my_name'.
>>> plain_obj = cohdl.Signal(old_obj)
>>> named_obj = NamedQualifier[cohdl.Signal, "my_name"](old_obj)
>>>
"""
