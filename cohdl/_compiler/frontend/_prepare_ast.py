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
)

from cohdl._core._primitive_type import is_primitive

from cohdl._core import _intrinsic_operations as intr_op
from cohdl._core._intrinsic_operations import AssignMode
from cohdl._core._intrinsic_definitions import _All, _Any, _Bool, always

from cohdl._core._context import Context, ContextType
from cohdl.utility.id_map import IdMap

from ._value_branch import _MergedBranch, ObjTraits
from . import _prepare_ast_out as out
from cohdl._core._boolean import _Boolean, _BooleanLiteral

from cohdl._core._collect_ast_and_scope import (
    InstantiatedFunction,
    FunctionDefinition,
    _Unbound,
)


#
#
#


def _make_comparable(lhs, rhs):
    if isinstance(lhs, _type_qualifier.TypeQualifier) or is_primitive(lhs):
        if isinstance(rhs, _type_qualifier.TypeQualifier) or is_primitive(rhs):
            return lhs, rhs

        return lhs, type(_type_qualifier.TypeQualifier.decay(lhs))(rhs)

    if isinstance(rhs, _type_qualifier.TypeQualifier) or is_primitive(rhs):
        return type(_type_qualifier.TypeQualifier.decay(rhs))(lhs), rhs

    raise AssertionError(f"invalid comparisson between {lhs} and {rhs}")


#
#
#


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


class PrepareAst:
    @staticmethod
    def convert_sequential(ctx: Context) -> out.Sequential:
        conv = PrepareAst(ctx.instantiate_fn(), ContextType.SEQUENTIAL)
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
        conv = PrepareAst(ctx.instantiate_fn(), ContextType.CONCURRENT)
        call = conv.convert_call()

        assert isinstance(call, out.Call)
        return out.Concurrent(
            ctx.name(), call.code(), ctx.attributes(), ctx.source_location()
        )

    def convert_boolean(self, arg, bound=None):
        # use for bool(arg) and boolean contexts like
        # 'if arg:', 'a if arg else b' and 'arg1 and arg2 or arg3'

        bound = [] if bound is None else bound

        if isinstance(arg, _type_qualifier.TypeQualifier):
            assert not issubclass(
                arg.type, cohdl.enum.Enum
            ), "arg may not be used in boolean contexts"
            return out.Boolean(out.Value(arg, bound))

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
        if not _has_intrinsic_replacement(fn):
            return out.Value(fn(*args, **kwargs), [])

        replacement = _intrinsic_replacements[fn]

        if not replacement.is_special_case:
            return out.Value(replacement.fn(*args, **kwargs), [])

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

            sub = self.subcall(fn_def, [], {})
            assert sub.result() is None

            # close coroutine to suppress
            # RuntimeWarning: couroutine was never awaited
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
                    _make_comparable(result.arg, cond)[1],
                    expr,
                )
                for cond, expr in result.branches.items()
            ]

            return out.SelectWith(result.arg, branches, result.default)

        if isinstance(result, _Any):
            return out.Any([x for x in result.iterable], [])

        if isinstance(result, _All):
            return out.All([x for x in result.iterable], [])

        if isinstance(result, _Bool):
            return self.convert_boolean(result.value)

        if isinstance(result, range):
            return out.Value(result, [])

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
                [out.Assign(result.index_temp, result.index, AssignMode._INFER, [])],
            )

        if isinstance(result, intr_op._IntrinsicDeclaration):
            if result.assigned_value is None:
                return out.Value(result.new_obj, [])
            else:
                if (
                    isinstance(result.new_obj, Signal)
                    and self._context is ContextType.SEQUENTIAL
                ):
                    signal_alias = Temporary[result.new_obj.type]()
                    bound = [
                        out.SignalAlias(
                            result.new_obj, signal_alias, result.assigned_value, []
                        ),
                    ]
                else:
                    bound = []

                return out.Value(
                    result.new_obj,
                    [
                        out.Assign(
                            result.new_obj,
                            result.assigned_value,
                            AssignMode._INFER,
                            bound,
                        )
                    ],
                )

        if result is NotImplemented:
            return out.Value(result, [])

        raise AssertionError(f"not implemented for {fn}")

    def __init__(
        self,
        fn_def: InstantiatedFunction,
        context: ContextType,
        parent: PrepareAst | None = None,
        first_arg=None,
    ):
        super().__init__()

        for name, value in fn_def.scope().items():
            if (
                isinstance(value, (Signal, Variable, Temporary))
                and value._root._name is None
            ):
                value._root._name = name

        self._fn_def = fn_def
        self._context = context
        self._parent = parent

        # copy scope dict so it can be modified during the compilation
        # without affection possible future compilations to the same function
        self._scope = {**fn_def.scope()}
        self._super_arg = fn_def.super_arg()

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
        try:
            return self.apply_impl(inp)
        except Exception as err:
            if isinstance(inp, ast.AST):
                lineno = inp.lineno
            else:
                lineno = None

            if not hasattr(err, "_cohdl_trace"):
                if isinstance(inp, ast.AST):
                    print(self.error(str(err), lineno))
                err._cohdl_trace = True
            else:
                print(self.error(f"used in {type(inp)}", lineno))

            raise err

    def throw_error(self, msg: str, offset: int):
        raise AssertionError(self.error(msg, offset))

    def error(self, msg: str, offset: int | None):
        if offset is None:
            return f"{msg}\n    @ {self.context_location()}\n"

        return f"{msg}\n    @ {self.context_location().relative(offset)}\n"

    def context_location(self):
        return self._fn_def.location()

    def subcall(self, fn, args: list, kwargs: dict[str, Any]) -> out.Statement:
        if isinstance(fn, InstantiatedFunction):
            return PrepareAst(fn, self._context, self).convert_call()

        # TODO: cleanup
        is_builtin_method = type(fn) is type("".__eq__)

        if type(fn) is type({}.items):
            if fn.__name__ != "__new__" and fn.__self__ is not builtins:
                is_builtin_method = True

        if inspect.isbuiltin(fn) or is_builtin_method:
            if is_builtin_method:
                args.insert(0, fn.__self__)
                fn = getattr(type(fn.__self__), fn.__name__)

            # fn is a builtin function or method
            # must be intrinsic to be usable in synthesizable context
            assert _is_intrinsic(fn)
            return self.convert_intrinsic(fn, args, kwargs)

        if inspect.ismethod(fn):
            args.insert(0, fn.__self__)
            fn = fn.__func__

        if _is_intrinsic(fn):
            return self.convert_intrinsic(fn, args, kwargs)
        if isinstance(fn, out.FunctionDef):
            return PrepareAst(
                fn.bind_args(args, kwargs), self._context, self
            ).convert_call()

        if inspect.iscoroutinefunction(fn):
            return out.Value(fn(*args, **kwargs), [])

        bound_stmts = []

        if not isinstance(fn, FunctionDefinition):

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
            fn_def.bind_args(args, kwargs), self._context, self
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
        assert self._scope[name] is _Unbound
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
        class _LockVar:
            ...

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
                for target, elem in zip(self.target, item):
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

    def apply_impl(self, inp):
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

        if isinstance(inp, ast.Nonlocal):
            # nonlocal is already handled during scope capture
            return out.Nop()

        if isinstance(inp, ast.Starred):
            if isinstance(inp.ctx, ast.Store):
                value = _return_stack.top()

                assert value.aug_assign is None
                assert isinstance(value.value, list)

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
                    assert self.name_bound(inp.id)
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
                        assert rhs.aug_assign is not None
                        return self._do_aug_assign(
                            rhs.aug_assign, getattr(value, inp.attr), rhs.value
                        )
                    else:
                        cls_value = getattr(type(value), inp.attr)

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
                                rhs.aug_assign, getattr(value, inp.attr), rhs.value
                            )

                        if rhs.aug_assign is None:
                            return self.subcall(fset, [fself, rhs.value], {})
                        else:
                            getter = self.subcall(fget, [fself], {})
                            assignment = self._do_aug_assign(
                                rhs.aug_assign, getter.result(), rhs.value, [getter]
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
                # in the expected behaviour in python (only the empty string evaluates to False)
                # and CoHDL (BitVector literals containing only zeros evalue to False) could leed to confusing results
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
                else:
                    runtime_vars.append(result)

            if isinstance(inp.op, ast.And):
                if not all(const_vars):
                    return out.Value(False, [*val_expr, *bool_expr])
                return out.All(runtime_vars, [*val_expr, *bool_expr])

            if isinstance(inp.op, ast.Or):
                if any(const_vars):
                    return out.Value(True, [*val_expr, *bool_expr])
                return out.Any(runtime_vars, [*val_expr, *bool_expr])

            raise AssertionError(f"invalid operator {inp.op}")

        if isinstance(inp, ast.BinOp):
            lhs = cast(out.Expression, self.apply(inp.left))
            rhs = cast(out.Expression, self.apply(inp.right))

            val_lhs = lhs.result()
            val_rhs = rhs.result()

            def overloaded_operator(default_op, reverse_op):
                if ObjTraits.hasattr(val_lhs, default_op):
                    call = self.subcall(
                        ObjTraits.getattr(val_lhs, default_op), [val_rhs], {}
                    )

                    call.add_bound_statement(lhs)
                    call.add_bound_statement(rhs)

                    if ObjTraits.get(call.result()) is not NotImplemented:
                        return call

                reverse_call = self.subcall(
                    ObjTraits.getattr(val_rhs, reverse_op), [val_lhs], {}
                )

                reverse_call.add_bound_statement(lhs)
                reverse_call.add_bound_statement(rhs)

                assert ObjTraits.get(reverse_call.result()) is not NotImplemented
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

            def overloaded_operator(fn_name):
                assert ObjTraits.hasattr(arg, fn_name)
                call = self.subcall(ObjTraits.getattr(arg, fn_name), [], {})

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

                if isinstance(operator, ast.Is):
                    return out.Value(val_lhs is val_rhs, [lhs, rhs])
                elif isinstance(operator, ast.IsNot):
                    return out.Value(val_lhs is not val_rhs, [lhs, rhs])
                elif isinstance(operator, ast.Eq):
                    first_result = self.subcall(val_lhs.__eq__, [val_rhs], {})

                    if first_result.result() is NotImplemented:
                        result = self.subcall(val_rhs.__eq__, [val_lhs], {})
                    else:
                        result = first_result
                elif isinstance(operator, ast.NotEq):
                    first_result = self.subcall(val_lhs.__ne__, [val_rhs], {})

                    if first_result.result() is NotImplemented:
                        result = self.subcall(val_rhs.__ne__, [val_lhs], {})
                    else:
                        result = first_result
                elif isinstance(operator, ast.Gt):
                    first_result = self.subcall(val_lhs.__gt__, [val_rhs], {})

                    if first_result.result() is NotImplemented:
                        result = self.subcall(val_rhs.__lt__, [val_lhs], {})
                    else:
                        result = first_result
                elif isinstance(operator, ast.Lt):
                    first_result = self.subcall(val_lhs.__lt__, [val_rhs], {})

                    if first_result.result() is NotImplemented:
                        result = self.subcall(val_rhs.__gt__, [val_lhs], {})
                    else:
                        result = first_result
                elif isinstance(operator, ast.GtE):
                    first_result = self.subcall(val_lhs.__ge__, [val_rhs], {})

                    if first_result.result() is NotImplemented:
                        result = self.subcall(val_rhs.__le__, [val_lhs], {})
                    else:
                        result = first_result
                elif isinstance(operator, ast.LtE):
                    first_result = self.subcall(val_lhs.__le__, [val_rhs], {})

                    if first_result.result() is NotImplemented:
                        result = self.subcall(val_rhs.__ge__, [val_lhs], {})
                    else:
                        result = first_result
                else:
                    raise AssertionError(f"operator {operator} not yet supported")

                assert (
                    result.result() is not NotImplemented
                ), f"operation '{operator}' not implemented for operands '{val_lhs}' and '{val_rhs}'"

                result.add_bound_statement(lhs)
                result.add_bound_statement(rhs)

                return result

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
                    assert isinstance(result, bool)

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

                split = self._split_target(inp.elts, rhs.value)

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
            keys = [cast(out.Expression, self.apply(key)) for key in inp.keys]
            values = [cast(out.Expression, self.apply(value)) for value in inp.values]

            value = {key.result(): value.result() for key, value in zip(keys, values)}

            return out.Value(value, cast(list[out.Statement], values))

        if isinstance(inp, ast.Subscript):
            value_expr = cast(out.Expression, self.apply(inp.value))
            slice_expr = cast(out.Expression, self.apply(inp.slice))

            value_result = ObjTraits.get(value_expr.result())
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
                    bound=[elem],
                )

            if isinstance(inp.ctx, ast.Load):
                if isinstance(value_result, (list, dict, str)):
                    item = value_result[slice_result]
                    return out.Value(item, [value_expr])

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
            assert (
                self.is_async()
            ), "await expressions can only be used in async contexts"

            value_expr = cast(out.Expression, self.apply(inp.value))
            result = value_expr.result()

            if isinstance(result, (_type_qualifier.TypeQualifier, _BooleanLiteral)):
                return out.Await(out.Value(result, [value_expr]), primitive=True)

            assert inspect.iscoroutine(result)

            fn_def = FunctionDefinition.from_coroutine(
                result,
            )

            # close coroutine to suppress
            # RuntimeWarning: couroutine was never awaited
            result.close()

            sub = self.subcall(fn_def, [], {})
            sub.add_bound_statement(value_expr)

            return out.Await(sub, primitive=False)

        if isinstance(inp, ast.While):
            assert self.is_async(), "while loops can only be used in async contexts"

            test = cast(out.Expression, self.apply(inp.test))

            body = cast(out.CodeBlock, self.apply(inp.body))

            assert len(inp.orelse) == 0, "else branch of while loops is not supported"

            if body.contains_break() or body.contains_continue():
                assert not ObjTraits.runtime_variable(
                    test.result()
                ), "test condition of while loops containing break or continue statements must be constant"
                assert bool(
                    test.result()
                ), "constant test condition of while loop must evaluate to true"

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

            for elt in iterable:
                target.unpack(elt)

                body = self.apply(inp.body)
                assert isinstance(body, out.CodeBlock)
                assert (
                    not body.contains_continue()
                ), "for loops cannot contain continue statements"

                if body.empty():
                    target.restore_locals()
                    break

                is_first = body_cnt == 0
                body_cnt += 1

                if body.contains_break():
                    # for loop containing breaks are used to generate if-else chains
                    # this is only possible, when the body of the loop contains only
                    # a single if statement where break is the last statement in the
                    # body of the loop

                    if is_first:
                        use_if_else = True
                    else:
                        assert use_if_else

                    # for loops containing break can only
                    # contain a single if statement without an orelse block
                    assert len(body.statements()) == 1
                    if_stmt = body.statements()[0]
                    assert isinstance(if_stmt, out.If)
                    assert if_stmt._orelse.empty()

                    if_body = if_stmt._body.statements()

                    # ensure, that the trailing break statement is
                    # the only one in the loop body
                    for substmt in if_body[:-1]:
                        assert not substmt.contains_break()

                    assert isinstance(if_body[-1], out.Break)

                    # remove break statement since it only serves as a marker
                    # and is not needed after it was detected
                    del if_body[-1]

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
                ), "for else only supported for the special case where the for loop contains only a single if statement with trailing break"
                return out.CodeBlock(result)

            #
            # handle special case, where for loop contains break
            # use cond select to model if else chain
            #

            assert (
                self._context is ContextType.SEQUENTIAL
            ), "for containing break statement only allowed in sequential context"

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

                    subject_val, pattern_val = _make_comparable(
                        subject_val, pattern_val
                    )

                    pattern._result = pattern_val

                    cond = out.Compare(
                        out.Compare.Operator.EQ, subject, pattern, Temporary[bool]()
                    )
                    body = cast(out.CodeBlock, self.apply(case.body))
                    cases.append((cond, body))
                else:
                    raise AssertionError()

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
                assert len(inp.args) == 1
                assert len(inp.keywords) == 0

                arg_expr = self.apply(inp.args[0])

                self.add_always_expr(arg_expr)
                return out.Value(arg_expr.result(), [])

            #
            #
            #

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
                    assert len(args) == 0
                    assert len(kwargs) == 0

                    class_info = self.lookup_name("__class__")
                    obj_info = self.super_arg()

                    return out.Value(super(class_info, obj_info), bound_expressions)

                #
                # obj_type is no special case, construct a new object
                #

                # non default __new__ not (yet) supported

                assert _is_intrinsic(obj_type.__new__)

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
                        [*bound_expressions, result, out.Return(out.Value(new_obj, []))]
                    ),
                )

            result = self.subcall(func_ref, args, kwargs)
            result._bound_statements = [*bound_expressions, *result._bound_statements]
            return result

        if isinstance(inp, ast.Return):
            if inp.value is None:
                return out.Return(out.Value(None, []))

            return out.Return(cast(out.Expression, self.apply(inp.value)))

        if isinstance(inp, ast.FunctionDef):
            bound_stmt = []

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
                ),
            )

            # function declaration has no runtime effect other than declaring values for default arguments
            return out.CodeBlock(bound_stmt)


#
#
#
# convert instances
#
#
#


class ConvertPythonInstance:
    def apply(self, inp):
        if isinstance(inp, Entity):
            # convert template
            template = self.apply(type(inp))

            # do not instantiate template at this point (hdl converter translates templates independently)
            # instead wrap template and all connected ports and instantiate only if needed

            return out.Entity(
                template,
                inp.port_definitions,
                inp.generic_definitions,
            )

        if isinstance(inp, type):
            assert issubclass(inp, cohdl._core._context.Entity)

            if inp._info.instantiated_template is None:
                if inp._info.extern:
                    inp._info.instantiated_template = out.EntityTemplate(
                        inp._info, None, None
                    )
                else:
                    #
                    # instantiate template with ports/generics
                    # to collect all subinstances/contexts used in
                    # the architecture
                    #

                    inp(**inp._info.ports, **inp._info.generics)
                    assert isinstance(inp._info.instantiated, inp)

                    inp._info.instantiated_template = out.EntityTemplate(
                        inp._info,
                        [
                            self.apply(block)
                            for block in inp._info.instantiated.contained_blocks()
                        ],
                        [
                            self.apply(ctx)
                            for ctx in inp._info.instantiated.contained_contexts()
                        ],
                    )

            return inp._info.instantiated_template

        if isinstance(inp, Block):
            return out.Block(
                inp._name,
                [self.apply(block) for block in inp._subblocks],
                [self.apply(ctx) for ctx in inp._subcontext],
                inp._attributes,
            )

        if isinstance(inp, Context):
            ctx_type = inp.context_type()

            if ctx_type is ContextType.CONCURRENT:
                return PrepareAst.convert_concurrent(inp)
            elif ctx_type is ContextType.SEQUENTIAL:
                return PrepareAst.convert_sequential(inp)

            raise AssertionError(f"invalid context type '{ctx_type}'")
