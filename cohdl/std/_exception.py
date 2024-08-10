from __future__ import annotations

from cohdl._core._intrinsic import _intrinsic


class StdException(Exception):
    _print_info = True

    @classmethod
    @_intrinsic
    def print_exception_infos(cls, enable=True):
        cls._print_info = enable

    @_intrinsic
    def add_info(self, msg: str | list | tuple, *args, **kwargs):
        if isinstance(msg, str):
            msg = [msg.format(*args, **kwargs)]

        for nr, line in enumerate(msg):

            if nr == 0:
                line = ">> " + line
            else:
                line = "   " + line

            if self._print_info:
                print(line)
            self.add_note(line)

    @classmethod
    @_intrinsic
    def raise_err(cls, msg: str, *args, **kwargs):
        msg = msg.format(*args, **kwargs)
        err = cls(msg)

        err.add_info(msg)

        for handler in StdExceptionHandler._handler_list[::-1]:
            if issubclass(cls, handler.type):
                if handler.info is not None:
                    err.add_info(handler.info)

                if handler.handler_fn is not None:
                    handler.handler_fn(err)

        raise err

    @classmethod
    @_intrinsic
    def raise_if(cls, cond: bool, msg: str, *args, **kwargs):
        if cond:
            cls.raise_err(msg, *args, **kwargs)


class StdExceptionHandler:
    _handler_list: list[StdExceptionHandler] = []

    @_intrinsic
    def __init__(self, handler_fn=None, info: str = None, type=StdException):
        self.handler_fn = handler_fn
        self.info = info
        self.type = type

    @_intrinsic
    def __enter__(self):
        self._handler_list.append(self)

    @_intrinsic
    def __exit__(self, exception, type, traceback):
        assert self._handler_list.pop() is self, "invalid handler stack"


#
#
#


class RefQualifierFail(StdException):
    pass


class SerializationFail(StdException):
    pass
