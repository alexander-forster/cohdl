from __future__ import annotations

import ast
import inspect
import builtins

import typing
from typing import Iterable, Any, cast

import cohdl


from cohdl._core import Signal, Variable, Temporary
from cohdl._core import _type_qualifier
from cohdl._core import Block, Entity
from cohdl._core._intrinsic import (
    _is_intrinsic,
    _has_intrinsic_replacement,
    _intrinsic_replacements,
    _SelectWith,
    _CoroutineStep,
    _SensitivitySpec,
    _SensitivityList,
    _SensitivityAll,
    _ResetContext,
    _ResetPushed,
    _BitSignalEvent,
    _BitSignalEventGroup,
    _IntrinsicComment,
    _IntrinsicInlineEntity,
)
from cohdl._core import _intrinsic, Null, Full

from cohdl._core._primitive_type import is_primitive

from cohdl._core import _intrinsic_operations as intr_op
from cohdl._core._intrinsic_operations import AssignMode
from cohdl._core._intrinsic_definitions import (
    _All,
    _Any,
    _Bool,
    always,
    _is_expr_function,
)

from cohdl._core._context import Context, ContextType
from cohdl.utility.virtual_traceback import VirtualFrame

from ._value_branch import _MergedBranch, _ValueBranch, ObjTraits
from . import _prepare_ast_out as out
from cohdl._core._boolean import _Boolean, _BooleanLiteral
from cohdl._core._boolean import true as cohdl_true
from cohdl._core._array import Array
from cohdl._core._bit_vector import BitVector

from cohdl._core._collect_ast_and_scope import (
    InstantiatedFunction,
    FunctionDefinition,
    _Unbound,
)


from ._traceback import pretty_traceback_active

_parent_frame: None | VirtualFrame = None
_inline_declared_entities: list = []

#
#
#


def _make_static_comparable(lhs, rhs):
    assert not isinstance(
        rhs, _type_qualifier.TypeQualifier
    ), f"branch value '{rhs}' must be constant"

    decay = _type_qualifier.TypeQualifier.decay
    lhs_val = decay(lhs)

    assert is_primitive(
        lhs_val
    ), f"selector value must have primitive type, not {type(lhs_val)}"

    if isinstance(lhs_val, BitVector):
        return lhs.bitvector, type(lhs_val)(rhs).bitvector

    return lhs, type(lhs_val)(rhs)


#
#
#


class _Noreturn:
    def __init__(self, reason):
        self.reason = reason


class _ReturnStack:
    class _NewEntry:
        def __init__(self, stack: _ReturnStack, value, aug_assign) -> None:
            self.stack = stack
            self.value = value
            self.aug_assign = aug_assign

        def __enter__(self):
            self.stack._stack.append(self)

        def __exit__(self, a, b, c):
            del self.stack._stack[-1]

    def __init__(self):
        self._stack: list[_ReturnStack._NewEntry] = []

    def enter(self, value, aug_assign=None):
        return _ReturnStack._NewEntry(self, value, aug_assign)

    def top(self):
        return self._stack[-1]


_return_stack = _ReturnStack()

#
#
#

_noreturn_top_sequential = _Noreturn("cannot exit from sequential context")
_noreturn_top_concurrent = _Noreturn("cannot exit from concurrent context")
_noreturn_statemachine = _Noreturn("cannot exit from state machine")


class PrepareAst:
    @staticmethod
    def convert_sequential(ctx: Context) -> out.Sequential:
        conv = PrepareAst(
            ctx.instantiate_fn(),
            ContextType.SEQUENTIAL,
            noreturn=_noreturn_top_sequential,
        )
        call = conv.convert_call()

        assert isinstance(call, out.Call)

        return out.Sequential(
            ctx.name(),
            call.code(),
            always_expr=conv._always_exprs,
            sensitivity=conv._sensitivity,
            attributes=ctx.attributes(),
            source_location=ctx.source_location(),
        )

    @staticmethod
    def convert_concurrent(ctx: Context) -> out.Concurrent:
        conv = PrepareAst(
            ctx.instantiate_fn(),
            ContextType.CONCURRENT,
            noreturn=_noreturn_top_concurrent,
        )
        call = conv.convert_call()

        assert isinstance(call, out.Call)
        return out.Concurrent(
            ctx.name(), call.code(), ctx.attributes(), ctx.source_location()
        )

    def convert_always_block(self, body: list[ast.AST], line_offset):
        location = self.context_location().relative(line_offset)
        call = PrepareAst(
            InstantiatedFunction(
                FunctionDefinition.from_ast_body(
                    body,
                    "always",
                    self._fn_def.scope(),
                    is_async=False,
                    # use self.context_location without offset because
                    # line offsets of statements contained in with block
                    # are relative to the enclosing function
                    location=self.context_location(),
                ),
                self._scope,
                super_arg=self._super_arg,
            ),
            ContextType.CONCURRENT,
            parent=self,
            mutable_scope=True,
        ).convert_call()

        assert isinstance(call, out.Call)

        return out.Concurrent("always", call.code(), {}, location)

    def convert_boolean(self, arg, bound=None):
        # use for bool(arg) and boolean contexts like
        # 'if arg:', 'a if arg else b' and 'arg1 and arg2 or arg3'

        bound = [] if bound is None else bound

        if isinstance(arg, _type_qualifier.TypeQualifier):
            assert not issubclass(
                arg.type, cohdl.enum.Enum
            ), "enum type may not be used in boolean contexts"
            return out.Boolean(out.Value(arg, bound))

        if isinstance(arg, (_BitSignalEvent, _BitSignalEventGroup)):
            return out.Value(arg, bound)

        if isinstance(arg, _MergedBranch):
            assert False, "TODO"

        bool_fn = getattr(arg, "__bool__")
        subexpr = self.subcall(bool_fn, [], {})
        bound.append(subexpr)

        subresult = subexpr.result()

        if not ObjTraits.runtime_variable(subresult):
            assert (
                subresult is True or subresult is False
            ), f"__bool__ should return bool or TypeQualifier[bool] not {subresult}"
            return out.Value(bool(subresult), bound)

        if isinstance(subresult, _type_qualifier.TypeQualifier):
            assert issubclass(
                subresult.type, (_Boolean, cohdl.Bit)
            ), f"__bool__ should return bool, Bit or TypeQualifier[bool] not {subresult}"

        return out.Value(subresult, bound)

    def convert_intrinsic(self, fn, args, kwargs):

        try:
            if not _has_intrinsic_replacement(fn):
                ret = fn(*args, **kwargs)

                if isinstance(ret, intr_op._IntrinsicSynthesizableFunctionCall):
                    return self.subcall(ret.callable, ret.args, ret.kwargs)

                return out.Value(ret, [])

            replacement = _intrinsic_replacements[fn]

            if not replacement.is_special_case:
                return out.Value(replacement.fn(*args, **kwargs), [])
        except BaseException as err:
            if pretty_traceback_active() and _parent_frame is not None:
                _parent_frame.apply_to_exception(err, extend=True)
                err._cohdl_virtual = True

            raise

        if replacement.evaluate:
            return self.subcall(replacement.fn, args, kwargs)

        if replacement.assignment_spec is not None:
            target = args[replacement.assignment_spec.nr_target]
            source = args[replacement.assignment_spec.nr_source]

            if isinstance(source, _MergedBranch):
                assert not isinstance(target, _MergedBranch)
                assert isinstance(target, _type_qualifier.TypeQualifier)

                if isinstance(target, _type_qualifier.Temporary):
                    source._redirect_values(target)
                    return out.Nop()
                else:
                    target_temp = _type_qualifier.Temporary[target.type]()
                    source._redirect_values(target_temp)

                    args = [*args]
                    args[replacement.assignment_spec.nr_source] = target_temp

        result = replacement.fn(*args, **kwargs)

        if isinstance(result, _SensitivitySpec):
            self.add_sensitivity(result)
            return out.Nop()

        if isinstance(result, _CoroutineStep):
            fn_def = FunctionDefinition.from_coroutine(result.coro)

            sub = self.subcall(fn_def, [], {}, noreturn=_noreturn_statemachine)
            assert (
                sub.result() is None
            ), "the coroutine handed to cohdl.coroutine_step should not return a value"

            # close coroutine to suppress
            # RuntimeWarning: coroutine was never awaited
            result.coro.close()

            return out.Statemachine(sub._code, result.coro.__name__)

        if isinstance(result, _ResetContext):
            return out.ResetContext()

        if isinstance(result, _ResetPushed):
            return out.ResetPushed()

        if isinstance(result, _SelectWith):
            branches = [
                (
                    # convert cond from str literal to compatible primitive
                    # according to argument
                    _make_static_comparable(result.arg, cond)[1],
                    expr,
                )
                for cond, expr in result.branches.items()
            ]

            return out.SelectWith(result.arg, branches, result.default)

        if isinstance(result, _Any):
            exprs = [self.convert_boolean(x) for x in result.iterable]

            var_elems = []
            always_true = False

            for val in result.iterable:
                if isinstance(val, _type_qualifier.TypeQualifier):
                    var_elems.append(val)
                else:
                    converted = self.convert_boolean(val)
                    expr_result = converted.result()
                    exprs.append(converted)

                    if isinstance(expr_result, bool):
                        always_true = always_true or expr_result
                    else:
                        var_elems.append(expr_result)

            if always_true:
                return out.Value(True, exprs)

            if len(var_elems) == 0:
                return out.Value(False, exprs)

            return out.Any(var_elems, exprs)

        if isinstance(result, _All):
            exprs = [self.convert_boolean(x) for x in result.iterable]

            var_elems = []
            always_false = False

            for val in result.iterable:
                if isinstance(val, _type_qualifier.TypeQualifier):
                    var_elems.append(val)
                else:
                    converted = self.convert_boolean(val)
                    expr_result = converted.result()
                    exprs.append(converted)

                    if isinstance(expr_result, bool):
                        always_false = always_false or not expr_result
                    else:
                        var_elems.append(expr_result)

            if always_false:
                return out.Value(False, exprs)

            if len(var_elems) == 0:
                return out.Value(True, exprs)

            return out.All(var_elems, exprs)

        if isinstance(result, _Bool):
            return self.convert_boolean(result.value)

        if isinstance(result, range):
            return out.Value(result, [])

        #
        #
        #

        if isinstance(result, _intrinsic._IsInstance):
            assert not isinstance(
                result.type, _MergedBranch
            ), f"type argument not runtime constant: could be any of {[branch.obj for branch in result.type.branches]}"
            if isinstance(result.type, tuple):
                if any(isinstance(elem, _MergedBranch) for elem in result.type):
                    for nr, elem in enumerate(result.type, start=1):
                        assert not isinstance(
                            elem, _MergedBranch
                        ), f"type argument {nr} not runtime constant: could be any of {[branch.obj for branch in elem.branches]}"

            if isinstance(result.obj, _MergedBranch):
                return out.Value(result.obj.isinstance(result.type), [])
            return out.Value(isinstance(result.obj, result.type), [])

        if isinstance(result, _intrinsic._IsSubclass):
            if isinstance(result.cls, _MergedBranch):
                return out.Value(result.cls.issubclass(result.type), [])
            return out.Value(issubclass(result.cls, result.type), [])

        if isinstance(result, _intrinsic._Type):
            if isinstance(result.obj, _MergedBranch):
                return out.Value(result.obj.type(), [])
            return out.Value(type(result.obj), [])

        if isinstance(result, _intrinsic._Id):
            if isinstance(result.obj, _MergedBranch):
                return out.Value(result.obj.id(), [])
            return out.Value(id(result.obj), [])

        #
        #
        #

        if isinstance(result, intr_op._IntrinsicAssignment):
            if result.mode is AssignMode.NEXT:
                return out.Assign(result.target, result.source, AssignMode.NEXT, [])
            if result.mode is AssignMode.PUSH:
                return out.Assign(result.target, result.source, AssignMode.PUSH, [])
            if result.mode is AssignMode.VALUE:
                return out.Assign(result.target, result.source, AssignMode.VALUE, [])

            raise AssertionError(f"invalid result.mode {result.mode}")

        if isinstance(result, intr_op._IntrinsicBinOp):
            return out.BinOp(
                result.op,
                out.Value(result.lhs, []),
                out.Value(result.rhs, []),
                result.result,
            )

        if isinstance(result, intr_op._IntrinsicUnaryOp):
            return out.UnaryOp(result.op, out.Value(result.arg, []), result.result)

        if isinstance(result, intr_op._IntrinsicComparison):
            return out.Compare(
                result.op,
                out.Value(result.lhs, []),
                out.Value(result.rhs, []),
                result.result,
            )

        if isinstance(result, intr_op._IntrinsicConstElemAccess):
            return out.Value(result.obj, [])

        if isinstance(result, intr_op._IntrinsicElemAccess):
            return out.Value(
                result.obj,
                [out.Assign(result.index_temp, result.index, AssignMode.AUTO, [])],
            )

        if isinstance(result, intr_op._IntrinsicSynthesizableFunctionCall):
            return self.subcall(result.callable, result.args, result.kwargs)

        if isinstance(result, intr_op._IntrinsicDeclaration):
            if result.assigned_value is None:
                return out.Value(result.new_obj, [])
            else:
                bound = []

                if isinstance(
                    result.assigned_value, _type_qualifier.TypeQualifier
                ) or is_primitive(result.assigned_value):
                    assigned = result.assigned_value
                elif isinstance(result.assigned_value, (list, tuple)) and isinstance(
                    _type_qualifier.TypeQualifier.decay(result.new_obj), Array
                ):
                    assigned = result.assigned_value
                elif isinstance(result.assigned_value, _MergedBranch):
                    pass
                else:
                    assigned = result.new_obj.type(result.assigned_value)

                if (
                    not result.delayed_init
                    and isinstance(result.new_obj, Signal)
                    and self._context is ContextType.SEQUENTIAL
                ):
                    sig_name = result.new_obj._name

                    signal_alias = Temporary[result.new_obj.type](
                        maybe_uninitialized=result.new_obj._maybe_uninitialized,
                        name=(f"alias_{sig_name}" if sig_name is not None else "alias"),
                    )

                    if isinstance(result.assigned_value, _MergedBranch):
                        result.assigned_value._redirect_values(signal_alias)
                    else:
                        bound.append(
                            out.Assign(
                                signal_alias,
                                assigned,
                                out.AssignMode.AUTO,
                                [],
                            ),
                        )

                    bound.append(out.SignalAlias(result.new_obj, signal_alias, []))

                if isinstance(result.assigned_value, _MergedBranch):
                    result.assigned_value._redirect_values(result.new_obj)
                else:
                    bound.append(
                        out.Assign(
                            result.new_obj,
                            assigned,
                            AssignMode.AUTO,
                            [],
                        )
                    )

                return out.Value(result.new_obj, bound)

        if isinstance(result, _IntrinsicComment):
            return out.Comment(result.lines)

        if isinstance(result, _IntrinsicInlineEntity):
            assert (
                self._context is ContextType.CONCURRENT
            ), "inline entity definition only allowed in concurrent contexts or always expression"
            _inline_declared_entities.append(result.entity)
            return out.Value(None, [])

        if result is NotImplemented:
            return out.Value(result, [])

        raise AssertionError(f"not implemented for {fn}")

    def __init__(
        self,
        fn_def: InstantiatedFunction,
        context: ContextType,
        parent: PrepareAst | None = None,
        first_arg=None,
        mutable_scope=False,
        noreturn: _Noreturn = None,
    ):
        self._last_apply_inp = None

        for name, value in fn_def.scope().items():
            if (
                isinstance(value, (Signal, Variable, Temporary))
                and value._root._name is None
            ):
                value._root._name = name

        self._fn_def = fn_def
        self._context = context
        self._parent = parent
        self._noreturn = noreturn

        # copy scope dict so it can be modified during the compilation
        # without affection possible future compilations to the same function
        self._scope = {**fn_def.scope()} if not mutable_scope else fn_def.scope()
        self._super_arg = fn_def.super_arg()

        self._frame = VirtualFrame(
            fn_def._location, self._scope, None if parent is None else parent._frame
        )

        # required to resolve super()
        # not used otherwise
        self._first_arg = first_arg

        # used in sequential contexts
        # all always expressions and sensitivity
        # specifiers are collected in these lists
        # TODO: create class Context, put always and sensitivity there
        self._always_exprs: list[out.Expression] = (
            [] if parent is None else parent._always_exprs
        )
        self._sensitivity = None if parent is None else parent._sensitivity

    def get_sensitivity(self):
        if self._parent is None:
            return self._sensitivity
        else:
            return self._parent.get_sensitivity()

    def add_sensitivity(self, sens):
        if self._parent is None:
            if self._sensitivity is None:
                self._sensitivity = sens
            elif isinstance(self._sensitivity, _SensitivityAll):
                return
            elif isinstance(self._sensitivity, _SensitivityList):
                if isinstance(sens, _SensitivityAll):
                    self._sensitivity = sens
                else:
                    assert isinstance(sens, _SensitivityList)
                    self._sensitivity.signals.extend(sens.signals)

        else:
            self._parent.add_sensitivity(sens)

    def add_always_expr(self, expr):
        if self._parent is None:
            self._always_exprs.append(expr)
        else:
            self._parent.add_always_expr(expr)

    def apply(self, inp):
        global _parent_frame
        prev_parent_frame = _parent_frame

        try:
            frame = out.AstVirtualFrame(inp, self._frame, prev_parent_frame)

            _parent_frame = frame
            result = self.apply_impl(inp)
            result._frame = frame
            _parent_frame = prev_parent_frame

            return result
        except BaseException as err:
            if pretty_traceback_active():
                if not hasattr(err, "_cohdl_virtual"):
                    frame = self._frame if _parent_frame is None else _parent_frame
                    frame.apply_to_exception(err)
                    err._cohdl_virtual = True
                raise
            else:
                if isinstance(inp, ast.AST) and hasattr(inp, "lineno"):
                    lineno = inp.lineno
                else:
                    lineno = None

                self.context_location().file

                if not hasattr(err, "_cohdl_trace"):
                    if isinstance(inp, ast.AST):
                        print(self.error(str(err), lineno))
                    err._cohdl_trace = True
                else:
                    print(self.error(f"used in {type(inp)}", lineno))

                raise err
        finally:
            _parent_frame = prev_parent_frame

    def throw_error(self, msg: str, offset: int):
        raise AssertionError(self.error(msg, offset))

    def error(self, msg: str, offset: int | None):
        if offset is None:
            return f"{msg}\n    @ {self.context_location()}\n"

        return f"{msg}\n    @ {self.context_location().relative(offset)}\n"

    def context_location(self):
        return self._fn_def.location()

    def subcall(
        self, fn, args: list, kwargs: dict[str, Any], noreturn=None
    ) -> out.Statement:
        if isinstance(fn, InstantiatedFunction):
            return PrepareAst(fn, self._context, self, noreturn=noreturn).convert_call()

        if isinstance(fn, _MergedBranch):
            first, *rest = fn.branches

            is_builtin_method = type(first.obj) is type("".__eq__)

            if is_builtin_method or inspect.ismethod(first.obj):
                if is_builtin_method:
                    func = getattr(type(first.obj.__self__), first.obj.__name__)

                    for r in rest:
                        assert func is getattr(
                            type(r.obj.__self__), r.obj.__name__
                        ), "methods in merged branch differ"
                else:
                    func = first.obj.__func__

                    for r in rest:
                        assert func is r.obj.__func__, "methods in merged branch differ"

                merged_self = _MergedBranch(
                    [
                        _ValueBranch(branch.hook, branch.obj.__self__)
                        for branch in fn.branches
                    ]
                )

                args.insert(0, merged_self)
                fn = func

            else:
                fn = first.obj

                for r in rest:
                    assert fn is r.obj, "functions in merged branch differ"

        is_builtin_method = type(fn) is type("".__eq__)
        original_fn = fn

        if type(fn) is type({}.items):
            if fn.__name__ != "__new__" and fn.__self__ is not builtins:
                is_builtin_method = True

        if inspect.isbuiltin(fn) or is_builtin_method:
            if is_builtin_method:
                original_fn = fn.__self__
                args.insert(0, fn.__self__)
                fn = getattr(type(fn.__self__), fn.__name__)

            # fn is a builtin function or method
            # must be intrinsic to be usable in synthesizable context
            assert _is_intrinsic(
                fn
            ), f"function {original_fn} not supported in synthesizable contexts"
            return self.convert_intrinsic(fn, args, kwargs)

        if inspect.ismethod(fn):
            args.insert(0, fn.__self__)
            fn = fn.__func__

        if _is_intrinsic(fn):
            return self.convert_intrinsic(fn, args, kwargs)
        if isinstance(fn, out.FunctionDef):
            return PrepareAst(
                fn.bind_args(args, kwargs), self._context, self, noreturn=noreturn
            ).convert_call()

        if inspect.iscoroutinefunction(fn):
            return out.Value(fn(*args, **kwargs), [])

        bound_stmts = []

        if not isinstance(fn, FunctionDefinition):
            if not inspect.isfunction(fn):
                return self.subcall(getattr(fn, "__call__"), args, kwargs)

            def default_converter(x):
                stmt = self.apply(x)
                bound_stmts.append(stmt)

                return stmt.result()

            fn_def = FunctionDefinition.from_callable(
                fn, default_converter=default_converter
            )
        else:
            fn_def = fn

        return PrepareAst(
            fn_def.bind_args(args, kwargs), self._context, self, noreturn=noreturn
        ).convert_call()

    def convert_call(self) -> out.Statement | out.SelectWith:
        return out.Call(
            out.CodeBlock([self.apply(stmt) for stmt in self._fn_def.body()])
        )

    def is_async(self) -> bool:
        return self._fn_def.is_async()

    def super_arg(self):
        return self._super_arg

    def lookup_name(self, name):
        return self._scope[name]

    def set_local(self, name, value):
        assert self._scope[name] is _Unbound, f"name '{name}' already used in scope"
        self._scope[name] = value

    def unset_local(self, name: str):
        # used by for loop to restore locals to previous state
        self._scope[name] = _Unbound

    def unset_locals(self, names: Iterable[str]):
        for name in names:
            self._scope[name] = _Unbound

    def bound_names(self) -> set[str]:
        return set(
            [name for name, value in self._scope.items() if value is not _Unbound]
        )

    def name_bound(self, name):
        return self._scope[name] is not _Unbound

    class Target:
        class _LockVar: ...

        def __init__(self, ast_target, converter: PrepareAst, is_top=True):
            self.converter = converter

            if is_top:
                self.declared_variables: set[str] = set()
                self.initial_bound = converter.bound_names()

            if isinstance(ast_target, ast.Name):
                self.target = ast_target.id
            else:
                self.target = [
                    PrepareAst.Target(elt, converter, False) for elt in ast_target.elts
                ]

        def unpack(self, item):
            if isinstance(self.target, str):
                self.converter.set_local(self.target, item)
            else:
                for target, elem in zip(self.target, item, strict=True):
                    target.unpack(elem)

        def restore_locals(self):
            # find names that were declared since initial_locals were recorded
            # accumulate them over all loops
            new_bound = self.converter.bound_names() - self.initial_bound
            self.declared_variables |= new_bound
            self.converter.unset_locals(new_bound)

        def lock_variables(self):
            # values that are declared in loops are not accessible
            # outside of them
            for name in self.declared_variables:
                self.converter.unset_local(name)

            # old implementation, prevent reuse of variable names that
            # are declared in loops
            #
            # # declare all new introduced names with dummy value
            # #  to prevent them from being reused
            # for name in self.declared_variables:
            #    self.converter.set_local(name, PrepareAst.Target._LockVar)

    def _split_target(self, targets: list, source: list):
        starred_index = None

        for nr, target in enumerate(targets):
            if isinstance(target, ast.Starred):
                assert starred_index is None
                starred_index = nr

        if starred_index is None:
            assert len(source) == len(targets)
            return source
        else:
            assert len(source) >= len(targets) - 1
            after_starred = len(targets) - starred_index - 1

            assert after_starred >= 0

            if after_starred == 0:
                return [*source[0:starred_index], source[starred_index:]]
            else:
                return [
                    *source[0:starred_index],
                    source[starred_index:-after_starred],
                    *source[-after_starred:],
                ]

    def _do_aug_assign(self, op, target, src, bound=[]):
        if isinstance(op, ast.LShift):
            result_expr = self.subcall(target.__ilshift__, [src], {})
        elif isinstance(op, ast.BitXor):
            result_expr = self.subcall(target.__ixor__, [src], {})
        elif isinstance(op, ast.MatMult):
            result_expr = self.subcall(target.__imatmul__, [src], {})
        else:
            raise AssertionError(f"invalid assignment operator '{op}'")

        assert (
            result_expr.result() is target
        ), "assignment operators are not allowed to change the target object"

        result_expr._bound_statements.extend(bound)
        return result_expr

    #
    #
    #
    #
    #

    def apply_impl(self, inp) -> out.Statement:
        last_inp = self._last_apply_inp
        self._last_apply_inp = inp

        def translate_await(value_expr: out.Expression):
            assert (
                self.is_async()
            ), "await expressions can only be used in async contexts"

            result = value_expr.result()

            if isinstance(value_expr, out.CohdlExpr):
                assert isinstance(
                    result, (_type_qualifier.TypeQualifier, _BooleanLiteral)
                ), "`cohdl.expr` should always return a primitive type"
                return out.Await(out.Value(result, [value_expr]), primitive=True)

            if isinstance(result, (_type_qualifier.TypeQualifier, _BooleanLiteral)):
                assert not isinstance(
                    result, _type_qualifier.Temporary
                ), "Temporaries can not be awaited, you can use the `await cohdl.expr(...)` pattern to fix this problem"

                return out.Await(
                    out.Value(result, []), primitive=True, expr_before=[value_expr]
                )

            assert inspect.iscoroutine(result), "argument is not a coroutine"

            fn_def = FunctionDefinition.from_coroutine(
                result,
            )

            # close coroutine to suppress
            # RuntimeWarning: coroutine was never awaited
            result.close()

            sub = self.subcall(fn_def, [], {})
            sub.add_bound_statement(value_expr)

            return out.Await(sub, primitive=False)

        if isinstance(inp, ast.Assign):
            value_expr = self.apply(inp.value)

            with _return_stack.enter(value_expr.result()):
                return out.CodeBlock(
                    [value_expr, *[self.apply(target) for target in inp.targets]]
                )

        if isinstance(inp, ast.AugAssign):
            value_expr = cast(out.Expression, self.apply(inp.value))

            with _return_stack.enter(value_expr.result(), inp.op):
                return out.CodeBlock([value_expr, self.apply(inp.target)])

        if isinstance(inp, ast.AnnAssign):
            value_expr = cast(out.Expression, self.apply(inp.value))

            with _return_stack.enter(value_expr.result()):
                return out.CodeBlock([value_expr, self.apply(inp.target)])

        if isinstance(inp, ast.Nonlocal):
            # nonlocal is already handled during scope capture
            return out.Nop()

        if isinstance(inp, ast.Starred):
            if isinstance(inp.ctx, ast.Store):
                value = _return_stack.top()

                assert (
                    value.aug_assign is None
                ), "only operator '=' is allowed in starred assignment"
                assert isinstance(value.value, (list, tuple)), "expected list or tuple"

                # convert name object
                return self.apply(inp.value)
            elif isinstance(inp.ctx, ast.Load):
                value_expr = self.apply(inp.value)
                return out.StarredValue(value_expr.result(), [value_expr])
            else:
                raise AssertionError(
                    f"invalid context '{inp.ctx}' of starred expression"
                )

        if isinstance(inp, ast.Name):
            if isinstance(inp.ctx, ast.Store):
                rhs = _return_stack.top()

                if rhs.aug_assign is None:
                    assert not self.name_bound(
                        inp.id
                    ), f"assignment to already used name '{inp.id}' not possible"
                    self.set_local(inp.id, rhs.value)
                    return out.Nop()
                else:
                    assert self.name_bound(
                        inp.id
                    ), f"name '{inp.id}' has no associated value at this point"
                    lhs = self.lookup_name(inp.id)

                    return self._do_aug_assign(rhs.aug_assign, lhs, rhs.value)
            elif isinstance(inp.ctx, ast.Load):
                assert self.name_bound(inp.id), f"name '{inp.id}' not found in scope"
                return out.Value(self.lookup_name(inp.id), [])

            raise AssertionError(f"invalid variable context {inp.ctx}")

        if isinstance(inp, ast.Attribute):
            value_expr = cast(out.Expression, self.apply(inp.value))
            value_result = value_expr.result()

            if isinstance(inp.ctx, ast.Store):
                rhs = _return_stack.top()

                value = value_expr.result()

                if ObjTraits.hasattr(value, inp.attr):
                    if inp.attr in vars(value):
                        assert (
                            rhs.aug_assign is not None
                        ), "assignments to existing attributes require one of the following operators '<<=', '^='  or '@='"
                        return self._do_aug_assign(
                            rhs.aug_assign,
                            getattr(value, inp.attr),
                            rhs.value,
                            bound=[value_expr],
                        )
                    else:
                        cls_value = getattr(ObjTraits.gettype(value), inp.attr)

                        if isinstance(cls_value, property):
                            fset = cls_value.fset
                            fget = cls_value.fget
                            fself = value
                        elif hasattr(cls_value, "__set__"):
                            fset = cls_value.__set__
                            fget = cls_value.__get__
                            fself = value
                        else:
                            assert rhs.aug_assign is not None
                            return self._do_aug_assign(
                                rhs.aug_assign,
                                getattr(value, inp.attr),
                                rhs.value,
                                bound=[value_expr],
                            )

                        if rhs.aug_assign is None:
                            return self.subcall(fset, [fself, rhs.value], {})
                        else:
                            getter = self.subcall(fget, [fself], {})
                            assignment = self._do_aug_assign(
                                rhs.aug_assign,
                                getter.result(),
                                rhs.value,
                                [value_expr, getter],
                            )

                            # per definition aug assignment operators must return the self object
                            # thus getter.result() is also the updated value of the assignment and
                            # passed on to the setter
                            result = self.subcall(fset, [fself, getter.result()], {})

                            result.add_bound_statement(value_expr)
                            result.add_bound_statement(assignment)
                            return result

                assert ObjTraits.init_active(
                    value
                ), f"declaring member variable '{inp.attr}' not possible"
                assert rhs.aug_assign is None
                setattr(value, inp.attr, rhs.value)
                return out.Nop()

            elif isinstance(inp.ctx, ast.Load):
                if ObjTraits.hasattr(value_result, inp.attr):
                    attr = ObjTraits.getattr(value_result, inp.attr)
                    return out.Value(attr, [value_expr])

                raise AssertionError(
                    f"attemted access to non existing member '{inp.attr}' of object '{value_result}'"
                )
            else:
                raise AssertionError(f"invalid attribute context '{inp.ctx}'")

        if isinstance(inp, list):
            return out.CodeBlock([self.apply(elem) for elem in inp])

        if isinstance(inp, ast.If):
            inp_expr = self.apply(inp.test)
            test = self.convert_boolean(inp_expr.result(), [inp_expr])
            test_result = test.result()

            if isinstance(test_result, bool):
                if test_result:
                    block = self.apply(inp.body)
                else:
                    block = self.apply(inp.orelse)

                block.add_bound_statement(test)
                return block
            else:
                assert (
                    self._context is ContextType.SEQUENTIAL
                ), "if statements with non constant argument are only allowed in sequential contexts"

                return out.If(
                    test,
                    self.apply(inp.body),
                    self.apply(inp.orelse),
                )

        if isinstance(inp, ast.BoolOp):
            val_expr = [cast(out.Expression, self.apply(val)) for val in inp.values]

            val_results = [val.result() for val in val_expr]

            for val_result in val_results:
                # strings are not allowed in boolean contexts because the difference
                # in the expected behavior in python (only the empty string evaluates to False)
                # and CoHDL (BitVector literals containing only zeros evaluate to False) could lead to confusing results
                assert not isinstance(
                    val_result, str
                ), "str cannot be used in boolean contexts"

            bool_expr = [self.convert_boolean(val_result) for val_result in val_results]

            bool_resuls = [expr.result() for expr in bool_expr]

            runtime_vars = []
            const_vars = []

            for result in bool_resuls:
                if isinstance(result, bool):
                    const_vars.append(result)
                elif isinstance(result, (_BitSignalEvent, _BitSignalEventGroup)):
                    raise AssertionError(
                        "rising/falling edge not allowed as argument of logical and/or use binary operators instead"
                    )
                else:
                    runtime_vars.append(result)

            if isinstance(inp.op, ast.And):
                if not all(const_vars):
                    return out.Value(False, [*val_expr, *bool_expr])
                elif len(runtime_vars) == 0:
                    return out.Value(True, [*val_expr, *bool_expr])
                return out.All(runtime_vars, [*val_expr, *bool_expr])

            if isinstance(inp.op, ast.Or):
                if any(const_vars):
                    return out.Value(True, [*val_expr, *bool_expr])
                elif len(runtime_vars) == 0:
                    return out.Value(False, [*val_expr, *bool_expr])
                return out.Any(runtime_vars, [*val_expr, *bool_expr])

            raise AssertionError(f"invalid operator {inp.op}")

        if isinstance(inp, ast.BinOp):
            lhs = cast(out.Expression, self.apply(inp.left))
            rhs = cast(out.Expression, self.apply(inp.right))

            val_lhs = lhs.result()
            val_rhs = rhs.result()

            type_lhs = ObjTraits.gettype(val_lhs)
            type_rhs = ObjTraits.gettype(val_rhs)

            def overloaded_operator(default_op, reverse_op):
                if ObjTraits.hasattr(type_lhs, default_op):
                    call = self.subcall(
                        ObjTraits.getattr(type_lhs, default_op), [val_lhs, val_rhs], {}
                    )

                    call.add_bound_statement(lhs)
                    call.add_bound_statement(rhs)

                    if ObjTraits.get(call.result()) is not NotImplemented:
                        return call

                reverse_call = self.subcall(
                    ObjTraits.getattr(type_rhs, reverse_op), [val_rhs, val_lhs], {}
                )

                reverse_call.add_bound_statement(lhs)
                reverse_call.add_bound_statement(rhs)

                assert (
                    ObjTraits.get(reverse_call.result()) is not NotImplemented
                ), f"both '{default_op}' and '{reverse_op}' returned NotImplemented"
                return reverse_call

            op = inp.op

            if isinstance(op, ast.Add):
                return overloaded_operator("__add__", "__radd__")
            if isinstance(op, ast.Sub):
                return overloaded_operator("__sub__", "__rsub__")
            if isinstance(op, ast.BitOr):
                return overloaded_operator("__or__", "__ror__")
            if isinstance(op, ast.BitAnd):
                return overloaded_operator("__and__", "__rand__")
            if isinstance(op, ast.BitXor):
                return overloaded_operator("__xor__", "__rxor__")
            if isinstance(op, ast.MatMult):
                return overloaded_operator("__matmul__", "__rmatmul__")
            if isinstance(op, ast.LShift):
                return overloaded_operator("__lshift__", "__rlshift__")
            if isinstance(op, ast.RShift):
                return overloaded_operator("__rshift__", "__rrshift__")
            if isinstance(op, ast.Mult):
                return overloaded_operator("__mul__", "__rmul__")
            if isinstance(op, ast.FloorDiv):
                return overloaded_operator("__floordiv__", "__rfloordiv__")
            if isinstance(op, ast.Div):
                return overloaded_operator("__truediv__", "__rtruediv__")
            if isinstance(op, ast.Mod):
                return overloaded_operator("__mod__", "__rmod__")
            if isinstance(op, ast.Pow):
                return overloaded_operator("__pow__", "__rpow__")

            raise AssertionError(f"operator {op} not yet supported")

        if isinstance(inp, ast.UnaryOp):
            op = inp.op

            operand = cast(out.Expression, self.apply(inp.operand))
            arg = operand.result()
            type_arg = ObjTraits.gettype(arg)

            def overloaded_operator(fn_name):
                assert ObjTraits.hasattr(
                    type_arg, fn_name
                ), f"type '{type_arg}' as no attribute '{fn_name}'"
                call = self.subcall(ObjTraits.getattr(type_arg, fn_name), [arg], {})

                call.add_bound_statement(operand)
                return call

            if isinstance(op, ast.Invert):
                return overloaded_operator("__inv__")
            if isinstance(op, ast.USub):
                return overloaded_operator("__neg__")
            if isinstance(op, ast.UAdd):
                return overloaded_operator("__pos__")
            if isinstance(op, ast.Not):
                bool_arg = self.convert_boolean(arg, [operand])

                if isinstance(bool_arg.result(), bool):
                    return out.Value(not bool_arg.result(), [bool_arg])

                result = out.UnaryOp(
                    out.UnaryOp.Operator.INV, bool_arg, Temporary[bool]()
                )

                return result

            raise AssertionError(f"operator not supported {op}")

        if isinstance(inp, ast.Compare):

            def single_compare(
                operator: ast.cmpop, lhs: out.Expression, rhs: out.Expression
            ):
                val_lhs = lhs.result()
                val_rhs = rhs.result()

                type_lhs = ObjTraits.gettype(val_lhs)
                type_rhs = ObjTraits.gettype(val_rhs)

                def evaluate(normal_name, reverse_name):
                    first_result = self.subcall(
                        ObjTraits.getattr(type_lhs, normal_name), [val_lhs, val_rhs], {}
                    )

                    if first_result.result() is NotImplemented:
                        result = self.subcall(
                            ObjTraits.getattr(type_rhs, reverse_name),
                            [val_rhs, val_lhs],
                            {},
                        )
                    else:
                        result = first_result

                    assert (
                        result.result() is not NotImplemented
                    ), f"operation '{operator}' not implemented for operands '{val_lhs}' and '{val_rhs}'"

                    result.add_bound_statement(lhs)
                    result.add_bound_statement(rhs)

                    return result

                if isinstance(operator, ast.Is):
                    if isinstance(val_lhs, _MergedBranch):
                        result = val_lhs._is(val_rhs)
                    else:
                        result = val_lhs is val_rhs

                    return out.Value(result, [lhs, rhs])
                elif isinstance(operator, ast.IsNot):
                    if isinstance(val_lhs, _MergedBranch):
                        result = not val_lhs._is(val_rhs)
                    else:
                        result = val_lhs is not val_rhs

                    return out.Value(result, [lhs, rhs])

                elif isinstance(operator, ast.Eq):
                    return evaluate("__eq__", "__eq__")
                elif isinstance(operator, ast.NotEq):
                    return evaluate("__ne__", "__ne__")
                elif isinstance(operator, ast.Gt):
                    return evaluate("__gt__", "__lt__")
                elif isinstance(operator, ast.Lt):
                    return evaluate("__lt__", "__gt__")
                elif isinstance(operator, ast.GtE):
                    return evaluate("__ge__", "__le__")
                elif isinstance(operator, ast.LtE):
                    return evaluate("__le__", "__ge__")
                else:
                    raise AssertionError(f"operator {operator} not yet supported")

            comparators = cast(
                list[out.Expression],
                [
                    self.apply(inp.left),
                    *[self.apply(cmp) for cmp in inp.comparators],
                ],
            )

            single_cmps = []
            is_first = True

            for operator, lhs, rhs in zip(inp.ops, comparators, comparators[1:]):
                if not is_first:
                    lhs = out.Value(lhs.result(), [])

                single = single_compare(operator, lhs, rhs)

                if not ObjTraits.runtime_variable(single.result()):
                    result = ObjTraits.get(single.result())
                    assert isinstance(result, bool), f"expected bool but got '{result}'"

                    # if a single comparissons is constant and false
                    # the entire expression evaluates to false
                    if not bool(result):
                        return out.Value(False, comparators)
                else:
                    is_first = False
                    single_cmps.append(single)

            # if all comparissons are constant and truthy
            # the entire expression evaluates to true
            if len(single_cmps) == 0:
                return out.Value(True, comparators)

            if len(single_cmps) == 1:
                return single_cmps[0]
            else:
                return out.All([cmp.result() for cmp in single_cmps], single_cmps)

        if isinstance(inp, ast.Pass):
            return out.Nop()

        if isinstance(inp, ast.Constant):
            return out.Value(inp.value, [])

        if isinstance(inp, ast.Tuple):
            if isinstance(inp.ctx, ast.Store):
                rhs = _return_stack.top()
                assert rhs.aug_assign is None

                result = []

                for target, source in zip(
                    inp.elts, self._split_target(inp.elts, rhs.value)
                ):
                    with _return_stack.enter(source):
                        result.append(self.apply(target))

                return out.CodeBlock(result)
            elif isinstance(inp.ctx, ast.Load):
                elts = [cast(out.Expression, self.apply(elt)) for elt in inp.elts]
                return out.Value(
                    tuple([elt.result() for elt in elts]),
                    cast(list[out.Statement], elts),
                )

            raise AssertionError(f"invalid context {inp.ctx}")

        if isinstance(inp, ast.List):
            elts = [cast(out.Expression, self.apply(elt)) for elt in inp.elts]

            value = []
            bound = []

            for elt in elts:
                if isinstance(elt, out.StarredValue):
                    value.extend(elt.result())
                    bound.extend(elt.bound_statements())
                else:
                    value.append(elt.result())
                    bound.append(elt)

            return out.Value(value, cast(list[out.Statement], bound))

        if isinstance(inp, ast.Dict):
            result = {}
            bound_statements = []

            for key_expr, val_expr in zip(inp.keys, inp.values, strict=True):
                if key_expr is None:
                    value = self.apply(val_expr)
                    bound_statements.append(value)
                    result.update(value.result())
                else:
                    key = self.apply(key_expr)
                    bound_statements.append(key)
                    value = self.apply(val_expr)
                    bound_statements.append(value)
                    result[key.result()] = value.result()

            return out.Value(result, bound_statements)

        if isinstance(inp, ast.Subscript):
            value_expr = cast(out.Expression, self.apply(inp.value))
            slice_expr = cast(out.Expression, self.apply(inp.slice))

            value_result = value_expr.result()
            slice_result = ObjTraits.get(slice_expr.result())

            if isinstance(inp.ctx, ast.Store):
                rhs = _return_stack.top()

                elem = self.subcall(value_result.__getitem__, [slice_result], {})

                assert (
                    rhs.aug_assign is not None
                ), "assignment to subscript expression is only possible using the operators '<<=', '^=' and '@='"
                return self._do_aug_assign(
                    rhs.aug_assign,
                    elem.result(),
                    rhs.value,
                    bound=[value_expr, slice_expr, elem],
                )

            if isinstance(inp.ctx, ast.Load):
                if isinstance(value_result, (list, dict, str)):
                    item = value_result[slice_result]
                    return out.Value(item, [value_expr, slice_expr])

                else:
                    if isinstance(value_result, type):
                        meta = value_result.__class__

                        if hasattr(meta, "__getitem__"):
                            # special case for types that define __getitem__ in their metaclass
                            # required, because a definition of __getitem__ in the derived class
                            # would shadow the class method
                            # add value_result as self/cls param

                            method = getattr(meta, "__getitem__")
                            args = [value_result, slice_result]
                        elif hasattr(value_result, "__class_getitem__"):
                            method = getattr(value_result, "__class_getitem__")
                            args = [slice_result]
                        else:
                            raise AssertionError(
                                f"class '{value_result}' does not override the subscript operator"
                            )
                    else:
                        method = ObjTraits.getattr(value_result, "__getitem__")
                        args = [slice_result]

                    call_expr = self.subcall(
                        method,
                        args,
                        {},
                    )

                    call_expr.add_bound_statement(value_expr)
                    call_expr.add_bound_statement(slice_expr)

                    return call_expr

            raise AssertionError(f"invalid context {inp.ctx}")

        if isinstance(inp, ast.Slice):
            start = (
                out.Value(None, [])
                if inp.lower is None
                else cast(out.Expression, self.apply(inp.lower))
            )
            stop = (
                out.Value(None, [])
                if inp.upper is None
                else cast(out.Expression, self.apply(inp.upper))
            )
            step = (
                out.Value(None, [])
                if inp.step is None
                else cast(out.Expression, self.apply(inp.step))
            )

            return out.Value(
                slice(start.result(), stop.result(), step.result()), [start, stop, step]
            )

        if isinstance(inp, ast.Expr):
            return self.apply(inp.value)

        if isinstance(inp, ast.Await):
            return translate_await(self.apply(inp.value))

        if isinstance(inp, ast.While):
            assert self.is_async(), "while loops can only be used in async contexts"
            assert (
                len(inp.orelse) == 0
            ), "while loops with else statement are not supported"

            test = cast(out.Expression, self.apply(inp.test))
            test = self.convert_boolean(test.result(), [test])

            if test.result() is False:
                # ignore the body of always false while loops
                # treat them as a single clock delay for equivalence with
                # runtime false while arguments
                return out.Await(out.Value(cohdl_true, []), True, expr_before=[test])

            body = cast(out.CodeBlock, self.apply(inp.body))

            assert len(inp.orelse) == 0, "else branch of while loops is not supported"

            return out.While(test, body)

        if isinstance(inp, ast.Break):
            return out.Break()

        if isinstance(inp, ast.Continue):
            return out.Continue()

        if isinstance(inp, ast.IfExp):
            inp_expr = self.apply(inp.test)

            test = self.convert_boolean(inp_expr.result(), [inp_expr])
            test_result = test.result()

            if isinstance(test_result, bool):
                # both body and orelse must be bound because they
                # might have side effects in function calls
                # this is different from if statements because
                # if expressions are not short circuiting
                if test_result:
                    body = cast(out.Expression, self.apply(inp.body))
                    return out.Value(body.result(), [test, body])
                else:
                    orelse = cast(out.Expression, self.apply(inp.orelse))
                    return out.Value(orelse.result(), [test, orelse])

            body = cast(out.Expression, self.apply(inp.body))
            orelse = cast(out.Expression, self.apply(inp.orelse))

            if body.result() is orelse.result():
                return out.Value(body.result(), [test, body, orelse])

            return out.IfExpr(test, body, orelse)

        if isinstance(inp, ast.For):
            target = PrepareAst.Target(inp.target, self)

            iterable_expr = cast(out.Expression, self.apply(inp.iter))
            iterable = iterable_expr.result()

            result: list[out.Statement] = []

            body_cnt = 0
            use_if_else = False
            uses_return = False

            for elt in iterable:
                target.unpack(elt)

                body = self.apply(inp.body)
                assert isinstance(body, out.CodeBlock)
                assert (
                    not body.contains_continue()
                ), "for loops cannot contain continue statements"

                if body.empty():
                    target.restore_locals()
                    continue

                is_first = body_cnt == 0
                body_cnt += 1

                body_breaks = body.contains_break()
                body_returns = body.returns()

                if body_breaks or body_returns:
                    # for loop containing breaks or returns are used to generate if-else chains
                    # this is only possible, when the body of the loop contains only
                    # a single if statement where break/return is the last statement in the
                    # body of the loop

                    assert not (
                        body_breaks and body_returns
                    ), "using both break and return is not allowed in this context"

                    if is_first:
                        use_if_else = True
                        uses_return = body_returns
                    else:
                        assert use_if_else
                        assert uses_return is body_returns

                    # for loops containing break can only
                    # contain a single if statement without an orelse block
                    assert (
                        len(body.statements()) == 1
                    ), "for-loops containing break may only contain a single if statement"
                    if_stmt = body.statements()[0]
                    assert isinstance(
                        if_stmt, out.If
                    ), "for-loops containing break may only contain a single if statement"
                    assert (
                        if_stmt._orelse.empty()
                    ), "for-loops containing break may only contain a single if statement, else branch not allowed"

                    if_body = if_stmt._body.statements()

                    if uses_return:
                        # ensure, that the body of the if statement
                        # always leeds to a return statement
                        assert (
                            if_stmt._body.returns_always()
                        ), "all branches in the if statements must return"
                        assert isinstance(
                            if_body[-1], out.Return
                        ), "the last statement in the if block must be a return"
                    else:
                        # ensure, that the trailing break statement is
                        # the only one in the loop body
                        for substmt in if_body[:-1]:
                            assert (
                                not substmt.contains_break()
                            ), "the if body may only contain a single break statement (at the end)"

                        assert isinstance(
                            if_body[-1], out.Break
                        ), "the if body must end in a break statement"

                        # remove break statement since it only serves as a marker
                        # and is not needed after it was detected
                        del if_body[-1]
                        if_stmt._body._contains_break = False

                    # add only if statement to collected
                    result.append(if_stmt)
                else:
                    assert not use_if_else
                    result.append(body)

                target.restore_locals()

            target.lock_variables()

            if not use_if_else:
                if body_cnt == 0:
                    assert len(result) == 0

                    # since loops containing an if statements terminated with break
                    # are allowed to have an else block, so are empty for loops since
                    # they are equivalent to the former case running zero times
                    return self.apply(inp.orelse)

                assert (
                    len(inp.orelse) == 0
                ), "for else only supported for the special case where the for loop contains only a single if statement with trailing break or return"
                return out.CodeBlock(result)

            #
            # handle special case, where for loop contains break
            # use cond select to model if else chain
            #

            assert (
                self._context is ContextType.SEQUENTIAL
            ), "for containing break/return statement only allowed in sequential context"

            if len(inp.orelse) == 0:
                default = None
            else:
                default = self.apply(inp.orelse)

            return out.CondSelect(
                [(if_stmt._test, if_stmt._body) for if_stmt in result], default
            )

        if isinstance(inp, ast.ListComp):
            assert (
                len(inp.generators) == 1
            ), "nested generator in list comprehension not supported"
            gen = inp.generators[0]

            assert isinstance(gen, ast.comprehension)

            target = PrepareAst.Target(gen.target, self)

            iterable_expr = cast(out.Expression, self.apply(gen.iter))
            iterable = iterable_expr.result()

            bound_expr: list[out.Expression] = []
            result_expr: list[out.Expression] = []

            for elt in iterable:
                target.unpack(elt)
                expr = self.apply(inp.elt)

                excluded = False

                for ifexpr in gen.ifs:
                    ifexpr = self.apply(ifexpr)
                    ifexpr_converted = self.convert_boolean(ifexpr.result(), [ifexpr])
                    ifexpr_result = ifexpr_converted.result()

                    assert isinstance(
                        ifexpr_result, bool
                    ), "trailing if expressions of comprehensions may not depend on runtime variable objects"

                    if not ifexpr_result:
                        excluded = True

                    bound_expr.append(ifexpr_converted)

                if not excluded:
                    result_expr.append(expr)
                    bound_expr.append(expr)

                target.restore_locals()

            return out.Value([x.result() for x in result_expr], bound_expr)

        if isinstance(inp, ast.DictComp):
            assert (
                len(inp.generators) == 1
            ), "nested generator in dict comprehension not supported"
            gen = inp.generators[0]

            assert isinstance(gen, ast.comprehension)

            target = PrepareAst.Target(gen.target, self)

            iterable_expr = cast(out.Expression, self.apply(gen.iter))
            iterable = iterable_expr.result()

            bound_expr: list[out.Expression] = []

            result = {}

            for elt in iterable:
                target.unpack(elt)

                key_expr = self.apply(inp.key)
                val_expr = self.apply(inp.value)

                excluded = False

                for ifexpr in gen.ifs:
                    ifexpr = self.apply(ifexpr)
                    ifexpr_converted = self.convert_boolean(ifexpr.result(), [ifexpr])
                    ifexpr_result = ifexpr_converted.result()

                    assert isinstance(
                        ifexpr_result, bool
                    ), "trailing if expressions of comprehensions may not depend on runtime variable objects"

                    if not ifexpr_result:
                        excluded = True

                    bound_expr.append(ifexpr_converted)

                if not excluded:
                    key = key_expr.result()

                    assert (
                        key not in result
                    ), "duplicate key in dict generated by dict comprehension"

                    result[key] = ObjTraits.get(val_expr.result())
                    bound_expr.append(key_expr)
                    bound_expr.append(val_expr)

                target.restore_locals()

            return out.Value(result, bound_expr)

        if isinstance(inp, ast.GeneratorExp):
            raise AssertionError(
                f"raw generator expressions are not supported, should be wrapped in a list []"
            )

        if isinstance(inp, ast.MatchValue):
            return self.apply(inp.value)

        if isinstance(inp, ast.Match):
            subject = cast(out.Expression, self.apply(inp.subject))

            cases: list[typing.Tuple[out.Expression, out.CodeBlock]] = []
            default_body = None

            for case in inp.cases:
                assert (
                    default_body is None
                ), "default branch must be last branch of match statement"

                if isinstance(case.pattern, ast.MatchAs):
                    default_body = cast(out.CodeBlock, self.apply(case.body))
                    break
                if isinstance(case.pattern, ast.MatchValue):
                    pattern = cast(out.Expression, self.apply(case.pattern))

                    subject_val, pattern_val = subject.result(), pattern.result()

                    subject_val, pattern_val = _make_static_comparable(
                        subject_val, pattern_val
                    )

                    pattern._result = pattern_val

                    cond = out.Compare(
                        out.Compare.Operator.EQ, subject, pattern, Temporary[bool]()
                    )
                    body = cast(out.CodeBlock, self.apply(case.body))
                    cases.append((cond, body))
                else:
                    raise AssertionError(f"unsupported match pattern '{case.pattern}'")

            return out.CondSelect(cases, default_body)

        if isinstance(inp, ast.Assert):
            test = self.apply(inp.test)
            result = test.result()

            if not ObjTraits.runtime_variable(result):
                if result:
                    return out.Nop()
                else:
                    if inp.msg is None:
                        raise AssertionError(f"assertion failed")

                    msg = self.apply(inp.msg)
                    raise AssertionError(f"assertion failed: '{msg.result()}'")

            if inp.msg is None:
                return out.Assert(test, None)
            return out.Assert(test, self.apply(inp.msg))

        if isinstance(inp, ast.JoinedStr):
            #
            # hdl injection
            #
            def is_inline_code(s, node):
                if not isinstance(node, ast.FormattedValue):
                    if isinstance(node, ast.Constant):
                        assert isinstance(node.value, str)
                        return node.value.isspace()
                    return False

                expr = s.apply(node.value)
                result = expr.result()

                return issubclass(result, cohdl._InlineCode)

            is_inline = [is_inline_code(self, val) for val in inp.values]

            def collect_inline_code(node: ast.FormattedValue):
                value_expr = self.apply(node.value)
                value = value_expr.result()

                content = []

                assert isinstance(node.format_spec, ast.JoinedStr)

                for elem in node.format_spec.values:
                    if isinstance(elem, ast.FormattedValue):
                        elem_expr = self.apply(elem.value)
                        elem_value = elem_expr.result()

                        if isinstance(elem_value, out.InlineCode):
                            content.append(
                                cohdl._InlineCode.SubCode(elem_value.options)
                            )
                        else:
                            if isinstance(elem_value, _type_qualifier.TypeQualifier):
                                if elem.conversion == 114:
                                    is_read = True
                                else:
                                    is_read = False
                                    assert elem.conversion == -1

                                content.append(
                                    cohdl._InlineCode.Object(elem_value, is_read)
                                )
                            else:
                                content.append(cohdl._InlineCode.Text(str(elem_value)))
                    elif isinstance(elem, ast.Constant):
                        content.append(cohdl._InlineCode.Text(elem.value))

                return value(content)

            if any(is_inline):
                assert all(is_inline)
                return out.InlineCode(
                    [
                        collect_inline_code(val)
                        for val in inp.values
                        if not isinstance(val, ast.Constant)
                    ]
                )
            else:
                raise AssertionError("not implemented")

        if isinstance(inp, ast.Call):
            func_expr = cast(out.Expression, self.apply(inp.func))
            func_ref = func_expr.result()

            # special case for always expressions in sequential blocks
            if func_ref is always:
                assert (
                    self._context is ContextType.SEQUENTIAL
                ), "cohdl.always can only be used in cohdl.sequential contexts"
                assert (
                    len(inp.args) == 1 and len(inp.keywords) == 0
                ), "cohdl.always expects a single positional argument and no keyword arguments"
                # change context type while the always expression is evaluated
                self._context = ContextType.CONCURRENT
                arg_expr = self.apply(inp.args[0])
                self._context = ContextType.SEQUENTIAL

                self.add_always_expr(arg_expr)
                return out.Value(arg_expr.result(), [])

            # special case for expr expressions in sequential blocks
            if func_ref is cohdl.expr:
                assert isinstance(
                    last_inp, ast.Await
                ), "cohdl.expr may only be used as a wrapper around the argument of await expressions"
                assert (
                    len(inp.args) == 1 and len(inp.keywords) == 0
                ), "cohdl.expr expects a single positional argument and no keyword arguments"

                arg_expr = self.apply(inp.args[0])
                return out.CohdlExpr(arg_expr.result(), [arg_expr])

            #
            #
            #

            def convert_call():
                nonlocal func_ref
                bound_expressions: list[out.Statement] = [
                    func_expr,
                ]

                arg_expr: list[out.Expression] = []

                for arg in inp.args:
                    expr = cast(out.Expression, self.apply(arg))

                    if isinstance(expr, out.StarredValue):
                        bound_expressions.extend(expr.bound_statements())
                        for item in expr.result():
                            arg_expr.append(out.Value(item, []))
                    else:
                        bound_expressions.append(expr)
                        arg_expr.append(expr)

                kwarg_expr: dict[str, out.Expression] = {}

                for kwarg in inp.keywords:
                    expr = cast(out.Expression, self.apply(kwarg.value))
                    bound_expressions.append(expr)
                    if kwarg.arg is None:
                        kwdict = expr.result()
                        assert isinstance(kwdict, dict)

                        for name, value in kwdict.items():
                            kwarg_expr[name] = out.Value(value, [])
                    else:
                        assert isinstance(kwarg.arg, str)
                        kwarg_expr[kwarg.arg] = expr

                args: list[Any] = [expr.result() for expr in arg_expr]
                kwargs: dict[str, Any] = {
                    name: expr.result() for name, expr in kwarg_expr.items()
                }

                if isinstance(func_ref, type) and not _is_intrinsic(func_ref):
                    # call is constructor of type obj_type
                    obj_type = func_ref

                    if issubclass(obj_type, super):
                        assert (
                            len(args) == 0 and len(kwargs) == 0
                        ), "only super() without arguments is supported in synthesizable contexts"

                        class_info = self.lookup_name("__class__")
                        obj_info = self.super_arg()

                        return out.Value(super(class_info, obj_info), bound_expressions)

                    #
                    # obj_type is no special case, construct a new object
                    #

                    # non default __new__ not (yet) supported

                    new_call = self.subcall(obj_type.__new__, [obj_type, *args], kwargs)
                    new_obj = new_call.result()

                    if not isinstance(new_obj, obj_type):
                        return new_call

                    if obj_type.__init__ is object.__init__:
                        # emulated type has no __init__ function
                        # no call required
                        return out.Value(new_obj, bound_expressions)

                    args.insert(0, new_obj)
                    func_ref = obj_type.__init__

                    # set flag to indicate, that declarations are allowed
                    new_obj._cohdl_init_active = True
                    result = self.subcall(func_ref, args, kwargs)
                    del new_obj._cohdl_init_active

                    assert isinstance(result, (out.Call, out.Value))

                    # add a return statement that returns the self argument
                    # so expressions that use the constructor receive the constructed object
                    return out.Call(
                        out.CodeBlock(
                            [
                                *bound_expressions,
                                result,
                                out.Return(out.Value(new_obj, [])),
                            ]
                        ),
                    )

                result = self.subcall(func_ref, args, kwargs)

                result._bound_statements = [
                    *bound_expressions,
                    *result._bound_statements,
                ]
                return result

            converted = convert_call()

            if inspect.ismethod(func_ref):
                base_function = func_ref.__func__
            else:
                base_function = func_ref

            # special case for expr expressions in sequential blocks
            if _is_expr_function(base_function):
                return out.CohdlExpr(converted.result(), [converted])

            return converted

        if isinstance(inp, ast.Return):
            assert (
                self._noreturn is None
            ), f"return not allowed: {self._noreturn.reason}"

            if inp.value is None:
                return out.Return(out.Value(None, []))

            return out.Return(cast(out.Expression, self.apply(inp.value)))

        if isinstance(inp, ast.FunctionDef):
            bound_stmt = []

            loc = self._fn_def.location().relative(1)
            loc.function = inp.name

            assert (
                len(inp.decorator_list) == 0
            ), "decorators on local functions not supported"

            def default_converter(x):
                stmt = self.apply(x)
                bound_stmt.append(stmt)
                return stmt

            self.set_local(
                inp.name,
                FunctionDefinition.from_ast_fn(
                    inp,
                    inp.name,
                    # global dict is empty because all globals are already contained in self._scope and passed to nonlocal_dict
                    global_dict={},
                    nonlocal_dict=self._scope,
                    default_converter=default_converter,
                    location=loc,
                    add_self_to_nonlocal=True,
                ),
            )

            # function declaration has no runtime effect other than declaring values for default arguments
            return out.CodeBlock(bound_stmt)

        if isinstance(inp, ast.Lambda):
            bound_stmt = []

            loc = self._fn_def.location().relative(1)
            loc.function = f"LAMBDA_{loc.line+inp.lineno-1}"

            def default_converter(x):
                stmt = self.apply(x)
                bound_stmt.append(stmt)
                return stmt

            return out.Value(
                FunctionDefinition.from_ast_fn(
                    inp,
                    "lambda_expr",
                    # global dict is empty because all globals are already contained in self._scope and passed to nonlocal_dict
                    global_dict={},
                    nonlocal_dict=self._scope,
                    default_converter=default_converter,
                    location=loc,
                ),
                bound_statements=bound_stmt,
            )

        if isinstance(inp, ast.With):
            items = inp.items

            exit_list = []

            result_statements = []
            first_target = None

            for item in items:
                context_expr = self.apply(item.context_expr)
                result_statements.append(context_expr)
                context = context_expr.result()

                if context is always:
                    assert (
                        self._context is ContextType.SEQUENTIAL
                    ), "cohdl.always can only be used in cohdl.sequential contexts"
                    assert (
                        len(items) == 1
                    ), "with statement containing cohdl.always context can only have a single item"
                    assert (
                        item.optional_vars is None
                    ), "with statement containing cohdl.always can not define a target"

                    always_block = self.convert_always_block(inp.body, inp.lineno)

                    result_statements.append(always_block.code())

                    for stmt in result_statements:
                        assert (
                            not stmt.returns()
                        ), "cannot return from cohdl.always context"

                    self.add_always_expr(out.CodeBlock(result_statements))
                    return out.CodeBlock([])
                else:
                    enter = type(context).__enter__
                    exit_list.append((context, type(context).__exit__))

                    call_expr = self.subcall(enter, [context], {})
                    result_statements.append(call_expr)

                    if item.optional_vars is not None:
                        target = PrepareAst.Target(item.optional_vars, self)
                        target.unpack(call_expr.result())

                        if first_target is None:
                            first_target = target

            result_statements.append(self.apply(inp.body))

            for context, fn in exit_list[::-1]:
                returns_always = 0
                for stmt in result_statements:
                    stmt: out.Statement
                    if stmt.returns():
                        returns_always = returns_always or stmt.returns_always()
                        for return_path in stmt._return_paths:
                            return_path._final_bound_statements.append(
                                self.subcall(fn, [context, None, None, None], {})
                            )

                if not returns_always:
                    result_statements.append(
                        self.subcall(fn, [context, None, None, None], {})
                    )

            if first_target is not None:
                first_target.restore_locals()

            return out.CodeBlock(result_statements)

        if isinstance(inp, ast.AsyncWith):
            assert (
                self.is_async()
            ), "async with expressions can only be used in async contexts"

            items = inp.items

            exit_list = []

            result_statements = []
            first_target = None

            for item in items:
                context_expr = self.apply(item.context_expr)
                result_statements.append(context_expr)
                context = context_expr.result()

                enter = type(context).__aenter__
                exit_list.append((context, type(context).__aexit__))

                call_expr = translate_await(self.subcall(enter, [context], {}))
                result_statements.append(call_expr)

                if item.optional_vars is not None:
                    target = PrepareAst.Target(item.optional_vars, self)
                    target.unpack(call_expr.result())

                    if first_target is None:
                        first_target = target

            result_statements.append(self.apply(inp.body))

            for context, fn in exit_list[::-1]:
                returns_always = 0
                for stmt in result_statements:
                    stmt: out.Statement
                    if stmt.returns():
                        returns_always = returns_always or stmt.returns_always()
                        for return_path in stmt._return_paths:
                            return_path._final_bound_statements.append(
                                translate_await(
                                    self.subcall(fn, [context, None, None, None], {})
                                )
                            )

                if not returns_always:
                    result_statements.append(
                        translate_await(
                            self.subcall(fn, [context, None, None, None], {})
                        )
                    )

            if first_target is not None:
                first_target.restore_locals()

            return out.CodeBlock(result_statements)

        raise AssertionError(f"invalid ast node {inp}")


#
#
#
# convert instances
#
#
#

_active_converter_instance = None


class ConvertPythonInstance:
    def _entity_instantiation_handler(self, entity_info):
        self._entity_infos.append(entity_info)

    def __enter__(self):
        from cohdl._core._context import _set_entity_instantiation_handler

        global _active_converter_instance
        assert (
            _active_converter_instance is None
        ), "only one converter instance can be active at a given time"
        _active_converter_instance = self

        _set_entity_instantiation_handler(self._entity_instantiation_handler)

        self._entity_infos = []
        return self

    def __exit__(self, *args):
        from cohdl._core._context import _set_entity_instantiation_handler

        global _active_converter_instance
        assert _active_converter_instance is self, "exit does not match enter"
        _active_converter_instance = None
        _set_entity_instantiation_handler(None)

        for info in self._entity_infos:
            # delete instantiation info from entity after compilation is complete
            # this is done so future compilations do not contain cached results
            # from the current run
            info._discard_instantiation()

    def apply(self, inp):
        assert (
            _active_converter_instance is self
        ), "apply may only be called on the active converter instance"

        if isinstance(inp, Entity):
            # convert template
            template = self.apply(type(inp))

            # do not instantiate template at this point (hdl converter translates templates independently)
            # instead wrap template and all connected ports and instantiate only if needed

            return out.Entity(
                template,
                inp._cohdl_port_definitions,
                inp._cohdl_generic_definitions,
            )

        if isinstance(inp, type):
            assert issubclass(inp, cohdl._core._context.Entity)

            if inp._cohdl_info.instantiated_template is None:
                if inp._cohdl_info.extern:
                    inp._cohdl_info.instantiated_template = out.EntityTemplate(
                        inp._cohdl_info.copy(), None, None
                    )
                else:
                    #
                    # instantiate template with ports/generics
                    # to collect all subinstances/contexts used in
                    # the architecture
                    #

                    inp(_cohdl_instantiate_only=True)
                    instantiated = inp._cohdl_info.instantiated
                    assert isinstance(instantiated, inp)

                    #

                    converted_blocks = [
                        self.apply(block)
                        for block in instantiated._cohdl_block_info._subblocks
                    ]

                    converted_contexts = [
                        self.apply(ctx)
                        for ctx in instantiated._cohdl_block_info._subcontext
                    ]

                    global _inline_declared_entities
                    while len(_inline_declared_entities) != 0:
                        inline_entities = _inline_declared_entities
                        _inline_declared_entities = []

                        for inline_entity in inline_entities:
                            converted_blocks.append(self.apply(inline_entity))

                    #

                    inp._cohdl_info.instantiated_template = out.EntityTemplate(
                        inp._cohdl_info.copy(), converted_blocks, converted_contexts
                    )

            return inp._cohdl_info.instantiated_template

        if isinstance(inp, Block):
            info = inp._cohdl_block_info

            return out.Block(
                info._name,
                [self.apply(block) for block in info._subblocks],
                [self.apply(ctx) for ctx in info._subcontext],
                info._attributes,
            )

        if isinstance(inp, Context):
            ctx_type = inp.context_type()

            if ctx_type is ContextType.CONCURRENT:
                return PrepareAst.convert_concurrent(inp)
            elif ctx_type is ContextType.SEQUENTIAL:
                return PrepareAst.convert_sequential(inp)

            raise AssertionError(f"invalid context type '{ctx_type}'")
