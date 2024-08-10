from __future__ import annotations

class StdException(Exception):
    """
    base class of exceptions raised by the cohdl standard library
    """

    @classmethod
    def print_exception_infos(cls, enable=True):
        """
        enable/disable printing of exception messages to stdout
        """

    def add_info(self, msg: str | list | tuple, *args, **kwargs):
        """
        add one or more lines of text to the exception
        """

    @classmethod
    def raise_err(cls, msg: str, *args, **kwargs):
        """
        Create a new instance of this class with a message obtained from `msg.format(*args, **kwargs)`.
        This function exists because the raise statement is not supported
        in synthesizable contexts.
        """

    @classmethod
    def raise_if(cls, cond: bool, msg: str, *args, **kwargs):
        """
        Call `cls.raise_err` with the provided arguments if `cond` is True.
        """

class StdExceptionHandler:
    """
    Add additional information to instances of `StdException`.
    This class exists because try statements are not supported in synthesizable contexts.
    """

    def __init__(
        self,
        handler_fn=None,
        info: str | tuple[str] | list[str] = None,
        type=StdException,
    ):
        """
        When a StdException, that is derived from `type`, is raised while this handler is active (see self.__enter__),

        * `handler_fn` is called with the exception object as its single argument
        * `info` is added to the exception
        """

    def __enter__(self):
        """
        Each instance of StdExceptionHandler is active for the duration of a with-statement.
        """

    def __exit__(self, exception, type, traceback):
        pass

#
#
#

class RefQualifierFail(StdException):
    """
    raised, when a call to `std.Ref` fails.
    """

class SerializationFail(StdException):
    """
    raised, when the serialization of a type fails.
    """
