from __future__ import annotations
from _ast import Lambda
from cohdl.utility.source_location import SourceLocation
from cohdl.utility.virtual_traceback import VirtualFrame


from abc import abstractmethod

import ast
import inspect
import textwrap
from typing import Any, Iterable, Tuple


class _Unbound:
    """
    singleton that indicates a local variables name that is not bound to a specific value
    """


def optional(arg, generator):
    return generator() if arg is None else arg


class _ClassifyNames(ast.NodeVisitor):
    """
    process a block of code and determine, which names are local
    and which are inherited from the parent scope
    """

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            self.used_names.add(node.id)

            if node.id not in self._explicit_nonlocal:
                self.local_names.add(node.id)
        else:
            raise AssertionError(f"invalid context for name `{node.id}`")

    def visit_Nonlocal(self, node: ast.Nonlocal) -> Any:
        for name in node.names:
            assert (
                name not in self.used_names
            ), f"name {name} used before nonlocal declaration"
            self.used_names.add(name)
            self._explicit_nonlocal.add(name)

    def visit_ClassDef(self, node: ast.ClassDef):
        raise AssertionError(f"class definition in local function not supported")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)

    def _visit_fn_or_lambda(self, node: ast.FunctionDef | ast.Lambda):
        args = node.args

        self.generic_visit_list(args.defaults)
        self.generic_visit_list(args.kw_defaults)

        subargs = [arg.arg for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs]]

        if args.kwarg is not None:
            subargs.append(args.kwarg.arg)
        if args.vararg is not None:
            subargs.append(args.vararg.arg)

        sub_visitor = _ClassifyNames(subargs, node.body)

        self.used_names.update(sub_visitor.nonlocals())

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        self.used_names.add(node.name)
        self.local_names.add(node.name)

        self._visit_fn_or_lambda(node)

        self.generic_visit_list(node.decorator_list)

    def visit_Lambda(self, node: Lambda) -> Any:
        self._visit_fn_or_lambda(node)

    def visit_Try(self, node: ast.Try) -> Any:

        # mark names declared in try statements as used
        # try statements are not synthesizable but can occur
        # in inactive if-bodies (example if not cohdl.evaluated())
        for handler in node.handlers:
            if handler.name is not None:
                self.used_names.add(handler.name)
                self.local_names.add(handler.name)

    def __init__(self, args, body: list | ast.AST):
        self.used_names: set[str] = set()
        self.local_names: set[str] = set(args)
        self._explicit_nonlocal: set[str] = set()

        # explicitly mark __class__ as used
        # (required by super() call)
        self.used_names.add("__class__")
        super().__init__()

        if isinstance(body, list):
            self.generic_visit_list(body)
        else:
            self.visit(body)

    def generic_visit_list(self, inp: list):
        for stmt in inp:
            self.visit(stmt)

    def all_names(self):
        return self.used_names | self.local_names

    def local(self):
        return self.local_names

    def nonlocals(self):
        return self.used_names - self.local_names


class _ScopeBase:
    def _capture_env(self, local_names, nonlocal_names, global_dict, nonlocal_dict):
        result = {}

        builtins = global_dict["__builtins__"] if "__builtins__" in global_dict else {}

        for name in local_names:
            result[name] = _Unbound

        for name in nonlocal_names:
            if name in nonlocal_dict:
                result[name] = nonlocal_dict[name]
            elif name in global_dict:
                result[name] = global_dict[name]
            elif isinstance(builtins, dict) and name in builtins:
                result[name] = builtins[name]
            elif hasattr(builtins, name):
                result[name] = getattr(builtins, name)
            else:
                # special case for possibly unbound cell __class__
                assert name == "__class__", f"invalid name '{name}'"

        return result

    @abstractmethod
    def capture(self) -> dict[str, Any]:
        """
        returns a dictionary that contains all names used in the scope,
        local names are set to _Unbound, function arguments are treated like globals
        """
        ...


class ScopeRef(_ScopeBase):
    def __init__(
        self,
        local_names: Iterable[str],
        nonlocal_names: Iterable[str],
        global_dict: dict,
        nonlocal_dict: dict,
    ):
        self._scope = self._capture_env(
            local_names, nonlocal_names, global_dict, nonlocal_dict
        )

    def capture(self) -> dict[str, Any]:
        return self._scope


class FunctionDefinition:
    # A mapping over all previously parsed function definitions.
    # The id() of function objects is used as a key.
    # The values are tuples of FunctionDefinition and the function
    # object to prevent possible key collisions after garbage collection
    # of the function.
    _known_definitions: dict[int, tuple[FunctionDefinition, Any]] = {}

    @staticmethod
    def from_ast_body(
        fn: list[ast.stmt],
        name: str,
        scope_ref: _ScopeBase,
        is_async: bool,
        posonly: list[str] | None = None,
        args: list[str] | None = None,
        kwonly: list[str] | None = None,
        defaults: dict | None = None,
        kwdefaults: dict | None = None,
        vararg: str | None = None,
        kwarg: str | None = None,
        self_arg=_Unbound,
        *,
        location: SourceLocation,
    ):
        posonly = optional(posonly, list)
        args = optional(args, list)
        kwonly = optional(kwonly, list)
        defaults = optional(defaults, dict)
        kwdefaults = optional(kwdefaults, dict)

        return FunctionDefinition(
            fn,
            name,
            scope_ref,
            is_async,
            posonly=posonly,
            args=args,
            kwonly=kwonly,
            defaults=defaults,
            kwdefaults=kwdefaults,
            vararg=vararg,
            kwarg=kwarg,
            self_arg=self_arg,
            location=location,
        )

    @staticmethod
    def from_ast_fn(
        fn_def: ast.FunctionDef | ast.AsyncFunctionDef,
        name: str,
        global_dict: dict,
        nonlocal_dict: dict,
        self_arg=_Unbound,
        default_converter=lambda x: x,
        captured_defaults: (
            dict | None
        ) = None,  # if set to None ast representation is used for defaults
        *,
        location: SourceLocation,
        add_self_to_nonlocal=False,
    ):
        if isinstance(fn_def, (ast.FunctionDef, ast.Lambda)):
            is_async = False
        elif isinstance(fn_def, ast.AsyncFunctionDef):
            is_async = True
        else:
            raise AssertionError(f"expected function definition not `{fn_def}`")

        posonly: list[str] = [arg.arg for arg in fn_def.args.posonlyargs]
        kwonly: list[str] = [arg.arg for arg in fn_def.args.kwonlyargs]
        args: list[str] = [arg.arg for arg in fn_def.args.args]

        vararg = None if fn_def.args.vararg is None else fn_def.args.vararg.arg
        kwarg = None if fn_def.args.kwarg is None else fn_def.args.kwarg.arg

        fn_args = [*posonly, *kwonly, *args]

        if vararg is not None:
            fn_args.append(vararg)
        if kwarg is not None:
            fn_args.append(kwarg)

        names = _ClassifyNames(fn_args, fn_def.body)

        try:
            scope_ref = ScopeRef(
                names.local_names, names.nonlocals(), global_dict, nonlocal_dict
            )
        except Exception as err:
            frame = VirtualFrame(location, {**global_dict, **nonlocal_dict}, None)
            frame.apply_to_exception(err)
            raise

        if captured_defaults is None:
            defaults = fn_def.args.defaults
            arg_names = [*posonly, *args][-len(defaults) :]
            defaults = {
                name: default_converter(default)
                for name, default in zip(arg_names, defaults)
            }

            kwdefaults = fn_def.args.kw_defaults
            arg_names = kwonly[-len(kwdefaults) :]
            kwdefaults = {
                name: default_converter(default)
                for name, default in zip(arg_names, kwdefaults)
                if default is not None
            }
        else:
            # TODO: check, whether it is ok to use captured_defaults directly without
            # parsing stage (will share Signals/Variables between uses of same function)
            defaults = fn_def.args.defaults
            arg_names = [*posonly, *args][-len(defaults) :] if len(defaults) > 0 else []

            defaults = {name: captured_defaults[name] for name in arg_names}

            kwdefaults = fn_def.args.kw_defaults
            arg_names = kwonly[-len(kwdefaults) :] if len(kwdefaults) > 0 else []

            kwdefaults = {
                name: captured_defaults[name]
                for name, default in zip(arg_names, kwdefaults)
                if default is not None
            }

        if isinstance(fn_def, ast.Lambda):
            # wrap lambda expression in return to make it consistent
            # with normal functions
            body = [ast.Return(fn_def.body)]
        else:
            body = fn_def.body

        result = FunctionDefinition.from_ast_body(
            body,
            name,
            scope_ref,
            is_async,
            posonly,
            args,
            kwonly,
            defaults,
            kwdefaults,
            vararg,
            kwarg,
            self_arg=self_arg,
            location=location,
        )

        if add_self_to_nonlocal:
            scope_ref._scope[name] = result

        return result

    @staticmethod
    def from_coroutine(coroutine):
        assert inspect.iscoroutine(coroutine)

        if id(coroutine) in FunctionDefinition._known_definitions:
            return FunctionDefinition._known_definitions[id(coroutine)][0]

        def parse_source(source):
            parsed = ast.parse(textwrap.dedent(source))
            assert isinstance(parsed, ast.Module)
            assert len(parsed.body) == 1
            return parsed

        self_arg = _Unbound

        assert not coroutine.cr_running, "running coroutine not allowed in this context"

        code = coroutine.cr_code
        frame = coroutine.cr_frame

        name = coroutine.__name__
        body = parse_source(inspect.getsource(frame)).body[0]
        location = SourceLocation(code.co_filename, code.co_firstlineno, name)

        global_dict = frame.f_globals
        locals_dict = frame.f_locals

        result = FunctionDefinition.from_ast_fn(
            body,
            name,
            global_dict=global_dict,
            nonlocal_dict=locals_dict,
            self_arg=self_arg,
            default_converter=lambda x: x,
            captured_defaults=locals_dict,
            location=location,
        )

        args = []
        kwargs = {}

        for posonly_name in result._posonly:
            args.append(locals_dict[posonly_name])

        for arg_name in result._args:
            args.append(locals_dict[arg_name])

        if result._vararg is not None:
            args.extend(locals_dict[result._vararg])

        for kwarg_name in result._kwonly:
            kwargs[kwarg_name] = locals_dict[kwarg_name]

        for kwonly_name in result._kwonly:
            kwargs[kwarg_name] = locals_dict[kwonly_name]

        if result._kwarg is not None:
            kwargs.update(locals_dict[result._kwarg])

        result = result.bind_args(args, kwargs)

        FunctionDefinition._known_definitions[id(coroutine)] = (result, coroutine)

        return result

    @staticmethod
    def from_callable(callable, default_converter=lambda x: x):
        assert not inspect.iscoroutine(callable)

        if id(callable) in FunctionDefinition._known_definitions:
            return FunctionDefinition._known_definitions[id(callable)][0]

        def parse_source(source):
            parsed = ast.parse(textwrap.dedent(source))
            assert isinstance(parsed, ast.Module)
            assert len(parsed.body) == 1
            return parsed

        self_arg = _Unbound

        if inspect.ismethod(callable):
            self_arg = callable.__self__
            fn = callable.__func__
            name: str = callable.__name__
        elif not inspect.isfunction(callable):
            self_arg = callable
            fn = type(callable).__call__
            name: str = type(callable).__name__
        else:
            fn = callable
            name: str = fn.__name__

        assert inspect.isfunction(fn)

        parsed = parse_source(inspect.getsource(fn))

        if fn.__name__ == "<lambda>":
            lambda_nodes: list[ast.Lambda] = []

            class _SearchNode(ast.NodeVisitor):
                def visit_Lambda(self, node: ast.Lambda) -> Any:
                    lambda_nodes.append(node)
                    return self.generic_visit(node)

            _SearchNode().visit(parsed)

            assert (
                len(lambda_nodes) == 1
            ), "multiple lambdas in same source line not supported"

            body = lambda_nodes[0]
        else:
            body = parsed.body[0]

        assert isinstance(body, (ast.FunctionDef, ast.Lambda))

        closure_vars = inspect.getclosurevars(fn)

        global_dict = fn.__globals__

        signature = inspect.signature(fn)

        captured_defaults = {
            name: value.default
            for name, value in signature.parameters.items()
            if value.default is not value.empty
        }

        code = fn.__code__
        location = SourceLocation(code.co_filename, code.co_firstlineno, name)

        result = FunctionDefinition.from_ast_fn(
            body,
            name,
            global_dict=global_dict,
            nonlocal_dict=closure_vars.nonlocals,
            self_arg=self_arg,
            default_converter=default_converter,
            captured_defaults=captured_defaults,
            location=location,
        )

        FunctionDefinition._known_definitions[id(callable)] = [result, callable]

        return result

    def __init__(
        self,
        body: list[ast.stmt],
        name: str,
        scope_ref: _ScopeBase,
        is_async: bool,
        posonly: list[str],
        args: list[str],
        kwonly: list[str],
        defaults: dict[str, Any],
        kwdefaults: dict[str, Any],
        vararg: str | None,
        kwarg: str | None,
        self_arg=_Unbound,
        *,
        location: SourceLocation,
    ):
        self._location = location

        self._body = body
        self._name = name
        self._scope_ref = scope_ref
        self._is_async = is_async

        self._posonly = posonly
        self._args = args
        self._kwonly = kwonly

        self._vararg = vararg
        self._kwarg = kwarg

        self._defaults = defaults
        self._kwdefaults = kwdefaults

        self._self_arg = self_arg

    def location(self) -> SourceLocation:
        return self._location

    def name(self) -> str:
        return self._name

    def is_async(self):
        return self._is_async

    def body(self):
        return self._body

    def bind_args(self, args: list | Tuple, kwargs: dict) -> InstantiatedFunction:
        """
        assign given arguments to local names in the instantiated function
        """

        args = [*args]

        if self._self_arg is not _Unbound:
            args.insert(0, self._self_arg)

        scope = self._scope_ref.capture()

        # reverse order of args so list.pop can be used to process
        # the arguments in order (pop removes and returns last element of list)
        args = args[::-1]

        class _Dummy: ...

        class _NoSuperArg: ...

        super_arg = _Dummy

        def add_arg(name, val, variadic=False):
            nonlocal super_arg

            if variadic:
                # if the first argument is variadic
                # (*arg or **kwarg) it cannot be interpreted
                # as the object argument of super()
                super_arg = _NoSuperArg
            if super_arg is _Dummy:
                super_arg = val
            scope[name] = val

        for posonly in self._posonly:
            assert (
                posonly not in kwargs or self._kwarg is not None
            ), f"position only argument `{posonly}` may not be passed as keyword argument"

            if len(args) != 0:
                add_arg(posonly, args.pop())
            else:
                add_arg(posonly, self._defaults[posonly])

        for arg in self._args:
            if len(args) != 0:
                assert arg not in kwargs, f"got multiple values for argument `{arg}`"
                add_arg(arg, args.pop())
            elif arg in kwargs:
                add_arg(arg, kwargs[arg])
                del kwargs[arg]
            else:
                if arg in self._defaults:
                    add_arg(arg, self._defaults[arg])
                else:
                    raise AssertionError(f"missing paramerter `{arg}`")

        if self._vararg is None:
            assert len(args) == 0, f"to many arguments passed to function `{args}`"
        else:
            # function has a *vararg parameter, assign remaining
            # non-keyword arguments to this value, undo reversing of arguments from
            # start of function
            add_arg(self._vararg, tuple(args[::-1]))

        for kwonly in self._kwonly:
            if kwonly in kwargs:
                add_arg(kwonly, kwargs[kwonly])
                del kwargs[kwonly]
            else:
                add_arg(kwonly, self._kwdefaults[kwonly])

        if self._kwarg is None:
            assert (
                len(kwargs) == 0
            ), f"to many keyword arguments passed to function `{self._name}`"
        else:
            # function has a **kwarg parameter, assign remaining keyword arguments
            # to this value
            add_arg(self._kwarg, {**kwargs})

        if super_arg is _Dummy or super_arg is _NoSuperArg:
            return InstantiatedFunction(self, scope)

        return InstantiatedFunction(self, scope, super_arg=super_arg)


class InstantiatedFunction:
    def __init__(
        self,
        definition: FunctionDefinition,
        scope: dict,
        super_arg=_Unbound,
    ):
        self._definition = definition
        self._location = definition.location()
        self._scope = scope
        self._super_arg = super_arg

    def location(self):
        return self._definition.location()

    def name(self):
        return self._definition.name()

    def scope(self):
        return self._scope

    def is_async(self) -> bool:
        return self._definition.is_async()

    def body(self):
        return self._definition.body()

    def super_arg(self):
        return self._super_arg
