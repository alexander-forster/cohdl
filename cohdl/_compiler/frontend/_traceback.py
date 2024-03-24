_pretty_traceback = True


def use_pretty_traceback(val: bool = True):
    """
    CoHDL inserts stack frames from traced python functions
    into the exception trace back. This makes it a lot easier to debug
    compilation errors because the call stack contains the actual code,
    that caused the issue and not the compiler functions used to
    translate it.

    This mode can be switched of using `cohdl.use_pretty_traceback(False)`.

    You probably only want to set this value to False if you want to debug an internal compiler issue.
    """

    global _pretty_traceback
    _pretty_traceback = val


def pretty_traceback_active():
    return _pretty_traceback
