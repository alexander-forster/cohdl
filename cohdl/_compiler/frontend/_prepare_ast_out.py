from __future__ import annotations
from abc import abstractmethod

from typing import Tuple

import cohdl
import typing
import ast

from cohdl._core import _type_qualifier

from cohdl._core import _intrinsic_operations as intr_op
from cohdl._core._intrinsic_operations import AssignMode

from cohdl._core._collect_ast_and_scope import FunctionDefinition
from cohdl._core._context import EntityInfo

from cohdl import Temporary, Signal

from cohdl import Bit
from cohdl.utility.code_writer import IndentBlock, TextBlock
from cohdl.utility.virtual_traceback import VirtualFrame

from ._value_branch import _ValueBranchHook, _ValueBranch, _MergedBranch


class AstVirtualFrame(VirtualFrame):
    """
    A virtual frame derived from an ast entry relative to the function frame
    it is used in
    """

    def __init__(
        self, ast: ast.AST, fn_frame: VirtualFrame, parent_frame: VirtualFrame | None
    ):
        super().__init__(fn_frame._location, fn_frame._scope, parent_frame)
        self._ast = ast

    def location(self):
        try:
            return self._location.relative(self._ast.lineno)
        except AttributeError:
            # self._ast might not have a lineno attribute
            # fall back to function location
            return self._location

    def ignore(self, prev: VirtualFrame) -> bool:
        # ignore statements in traceback because only function calls
        # and the expression, that caused the error are relevant
        if isinstance(
            self._ast,
            (
                list,
                ast.If,
                ast.While,
                ast.For,
                ast.With,
                ast.AsyncWith,
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            return True

        # only generate one traceback frame per source line
        if self.location() == prev.location():
            return True

        return False


class Statement:
    def __init__(
        self,
        returns_always=False,
        return_paths: list[Return] | None = None,
        bound_statements: list[Statement] | None = None,
        contains_break=False,
        contains_continue=False,
    ):
        self._returns_always = returns_always
        self._return_paths = return_paths or []
        self._bound_statements = [] if bound_statements is None else bound_statements
        self._contains_break = contains_break
        self._contains_continue = contains_continue
        self._frame: AstVirtualFrame

    def add_bound_statement(self, stmt: Statement):
        self._bound_statements.append(stmt)

    def bound_statements(self) -> list[Statement]:
        return self._bound_statements

    def return_paths(self) -> list[Return]:
        return self._return_paths

    def returns(self) -> bool:
        return len(self._return_paths) != 0

    def returns_always(self) -> bool:
        return self._returns_always

    def contains_break(self) -> bool:
        return self._contains_break

    def contains_continue(self) -> bool:
        return self._contains_continue

    def dump_bound(self):
        return TextBlock(
            title="bound", content=[stmt.dump() for stmt in self._bound_statements]
        )

    @abstractmethod
    def dump(self) -> IndentBlock:
        raise AssertionError("abstract method called")


class Expression(Statement):
    def __init__(
        self,
        result,
        bound_statements: list[Statement] | None = None,
    ):
        assert not isinstance(result, _ValueBranch)
        self._result = result
        super().__init__(bound_statements=bound_statements)

    def result(self):
        return self._result

    @abstractmethod
    def dump(self) -> IndentBlock:
        raise AssertionError("abstract method called")


class Nop(Statement):
    def __init__(self):
        super().__init__(False, None)

    def dump(self) -> IndentBlock:
        return IndentBlock(title="Nop", content=self.dump_bound())


class Comment(Statement):
    def __init__(self, lines: list[str]):
        super().__init__(False, None)
        self.lines = lines

    def dump(self) -> IndentBlock:
        return IndentBlock(title="Comment", content=[*self.lines])


class StarredValue(Expression):
    def __init__(self, result, bound_statements: list[Statement] | None = None):
        super().__init__(result, bound_statements)


class Assign(Expression):
    def __init__(
        self,
        target,
        value,
        mode: AssignMode,
        bound_statements: list,
    ):
        self._target = target
        self._value = value
        self._mode = mode

        super().__init__(target, bound_statements)

    def target(self):
        return self._target

    def value(self):
        return self._value

    def dump(self) -> IndentBlock:
        return TextBlock(
            title=f"Assign (target={self._target}, value={self._value}, mode={self._mode})",
            content=self.dump_bound(),
        )


class InlineCode(Expression):
    def __init__(self, options: list[cohdl._InlineCode]):
        self.options = options
        self.expr_type = options[0].expr_type

        for option in options:
            assert (
                option.expr_type is self.expr_type
            ), "all languages must return the same type"

        if self.expr_type is None:
            super().__init__(self)
        else:
            super().__init__(Temporary[self.expr_type]())

    def dump(self):
        return IndentBlock(title="InlineCode", content=self.dump_bound())


class CodeBlock(Statement):
    def __init__(self, stmts: list[Statement]):
        self._stmts: list[Statement] = []

        returns_always = False
        return_paths: list[Return] = []

        contains_break = False
        contains_continue = False

        for stmt in stmts:
            if isinstance(stmt, CodeBlock):
                self._stmts.extend(stmt.statements())
            else:
                self._stmts.append(stmt)

            if stmt.contains_break():
                contains_break = True

            if stmt.contains_continue():
                contains_continue = True

            if stmt.returns():
                return_paths.extend(stmt.return_paths())

            if stmt.returns_always():
                returns_always = True
                break

        super().__init__(
            returns_always=returns_always,
            return_paths=return_paths,
            contains_break=contains_break,
            contains_continue=contains_continue,
        )

    def empty(self) -> bool:
        return len(self._stmts) == 0

    def statements(self) -> list[Statement]:
        return self._stmts

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title="CodeBlock", content=[stmt.dump() for stmt in self._stmts]
        )


class Value(Expression):
    def __init__(self, value: typing.Any, bound_statements: list[Statement]):
        super().__init__(value, bound_statements=bound_statements)

    def dump(self):
        return IndentBlock(
            title=f"Value (value={self.result()})", content=self.dump_bound()
        )


class CohdlExpr(Value):
    """
    special case for cohdl.expr(...)
    """

    def dump(self):
        return IndentBlock(title=f"CohdlExpr (value={self.result()})", content=[])


class SignalAlias(Statement):
    """
    Signals, that are constructed in sequential contexts
    are not valid until the next cycle. To allow using the value
    immediately after its construction a Temporary is used in place of
    all ready during this initial state.
    """

    def __init__(self, signal, replacement, bound_statements: list[Statement]):
        super().__init__(bound_statements=bound_statements)
        self._signal = signal
        self._replacement = replacement

    def dump(self):
        return "SignalAlias"


class Boolean(Expression):
    """
    cast input value to a boolean (single bit)
    """

    def __init__(self, value: Expression):
        self._value = value.result()

        super().__init__(
            Temporary[bool](),
            bound_statements=[value],
        )

    def value(self):
        return self._value

    def dump(self):
        return IndentBlock(title="Boolean", content=[])


class If(Statement):
    def __init__(self, test: Expression, body: CodeBlock, orelse: CodeBlock):
        self._test = test
        self._body = body
        self._orelse = orelse

        returns_always = self._body.returns_always() and self._orelse.returns_always()
        return_paths = self._body.return_paths() + self._orelse.return_paths()

        super().__init__(
            returns_always,
            return_paths,
            contains_break=body.contains_break() or orelse.contains_break(),
            contains_continue=body.contains_continue() or orelse.contains_continue(),
        )

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"If",
            content=[
                IndentBlock(title="test", content=self._test.dump()),
                IndentBlock(title="body", content=self._body.dump()),
                IndentBlock(title="orelse", content=self._orelse.dump()),
            ],
        )


class BinOp(Expression):
    Operator = intr_op.BinaryOperator

    def __init__(
        self, op: BinOp.Operator, lhs: Expression, rhs: Expression, result
    ) -> None:
        self._op = op
        self._lhs = lhs
        self._rhs = rhs

        super().__init__(result)

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"BinOp (operator={self._op})",
            content=[
                IndentBlock(title="lhs", content=self._lhs.dump()),
                IndentBlock(title="rhs", content=self._rhs.dump()),
            ],
        )


class UnaryOp(Expression):
    Operator = intr_op.UnaryOperator

    def __init__(self, op: UnaryOp.Operator, arg: Expression, result):
        self._op = op
        self._arg = arg

        super().__init__(result, [])

    def arg(self):
        return self._arg.result()

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"UnaryOp (operator={self._op})",
            content=[IndentBlock(title="arg", content=self._arg.dump())],
        )


class Compare(Expression):
    Operator = intr_op.ComparisonOperator

    def __init__(self, op: Compare.Operator, lhs: Expression, rhs: Expression, result):
        self._op = op
        self._lhs = lhs
        self._rhs = rhs

        super().__init__(result)

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"SingleCompare (operator={self._op})",
            content=[
                IndentBlock(title="lhs", content=self._lhs.dump()),
                IndentBlock(title="rhs", content=self._rhs.dump()),
            ],
        )


class All(Expression):
    def __init__(self, conditions: list, bound_expressions: list[Expression]):
        super().__init__(
            _type_qualifier.Temporary[bool](),
            bound_statements=bound_expressions,
        )

        self._conditions = conditions

    def dump(self) -> str:
        return "all"


class Any(Expression):
    def __init__(self, conditions: list, bound_expressions: list[Expression]):
        super().__init__(
            _type_qualifier.Temporary[bool](),
            bound_statements=bound_expressions,
        )

        self._conditions = conditions

    def dump(self) -> str:
        return "any"


count = 0


class IfExpr(Expression):
    def __init__(self, test: Expression, body: Expression, orelse: Expression):
        global count
        self._test = test
        self._body = body
        self._orelse = orelse

        self._hook_orelse = _ValueBranchHook(name="hookorelse")
        count = count + 1
        self._hook_body = _ValueBranchHook(name="hookbody")
        count = count + 1

        result = _MergedBranch(
            [
                _ValueBranch(self._hook_body, body.result()),
                _ValueBranch(self._hook_orelse, orelse.result()),
            ]
        )

        super().__init__(result)

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title="IfExpr",
            content=[
                IndentBlock(title="test", content=self._test.dump()),
                IndentBlock(title="body", content=self._body.dump()),
                IndentBlock(title="orelse", content=self._orelse.dump()),
            ],
        )


class Return(Statement):
    def __init__(self, expr: Expression):
        self._hook = _ValueBranchHook(name="return")
        self._branch = _ValueBranch(self._hook, expr.result())

        # used by context managers
        # separate from normal _bound_statements
        # because __exit__ code must run after return value redirect
        self._final_bound_statements = []

        super().__init__(
            returns_always=True, return_paths=[self], bound_statements=[expr]
        )

    def bound_statements(self) -> list[Statement]:
        return super().bound_statements() + [
            Assign(redirect.target, redirect.source, AssignMode.AUTO, [])
            for redirect in self._hook.redirects
        ]

    def branch(self) -> _ValueBranch:
        return self._branch

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title="Return", content=f"nr_redirects={len(self._hook.redirects)}"
        )


class While(Statement):
    def __init__(self, test: Expression, body: CodeBlock):
        self._test = test
        self._body = body

        super().__init__(
            False,
            [*body.return_paths()],
            bound_statements=[test],
            contains_break=False,  # while loop consumes contained break statements
            contains_continue=False,  # while loop consumes contained continue statements
        )

    def uses_break(self) -> bool:
        return self._body.contains_break()

    def uses_continue(self) -> bool:
        return self._body.contains_continue()

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title="While",
            content=[
                IndentBlock(title="test", content=self._test.dump()),
                IndentBlock(title="body", content=self._body.dump()),
                IndentBlock(title="orelse", content=self._orelse.dump()),
            ],
        )


class Break(Statement):
    def __init__(self):
        super().__init__(contains_break=True)

    def dump(self) -> IndentBlock:
        return IndentBlock(title="break")


class Continue(Statement):
    def __init__(self):
        super().__init__(contains_continue=True)

    def dump(self) -> IndentBlock:
        return IndentBlock(title="continue")


class Await(Expression):
    def __init__(
        self, expr: Expression, primitive: bool, expr_before: list | None = None
    ):
        expr_result = expr.result()
        self._awaitable_primitive = primitive
        self._expr_before = expr_before if expr_before is not None else []
        super().__init__(expr_result, bound_statements=[expr])

    def dump(self) -> IndentBlock:
        return IndentBlock(title="Await", content=self.dump_bound())


class Call(Expression):
    def __init__(self, code: CodeBlock):
        self._code = code
        result = _MergedBranch([stmt.branch() for stmt in code.return_paths()])

        if code.returns() and result is not None:
            assert code.returns_always()

        super().__init__(result)

    def code(self) -> CodeBlock:
        return self._code

    def dump(self) -> IndentBlock:
        return IndentBlock(title=f"Call -> {self.result()}", content=self._code.dump())


class ResetInstance(Statement):
    def __init__(self, obj):
        assert isinstance(obj, _type_qualifier.TypeQualifier) and obj.has_default()
        self._obj = obj
        super().__init__()

    def get_obj(self):
        return self._obj

    def dump(self) -> IndentBlock:
        return IndentBlock(title=f"ResetInstance {self._obj}")


class FunctionDef(Statement):
    def __init__(self, fn_def: FunctionDefinition):
        bound_statements = []
        super().__init__(bound_statements=bound_statements)

        self._fn_def = fn_def

    def bind_args(self, args, kwargs):
        return self._fn_def.bind_args(args, kwargs)

    def dump(self) -> IndentBlock:
        return IndentBlock(title=f"FunctionDef ({self._fn_def.name()})")


#
#
# special intrinsic
#
#


class SelectWith(Expression):
    def __init__(
        self,
        arg,
        branches: list[Tuple[Value, typing.Any]],
        default: typing.Any | None,
    ):
        self._arg = arg
        self._conditions = [branch[0] for branch in branches]
        self._branches = branches
        self._default = default

        self._branch_hooks: list[_ValueBranchHook] = []

        branch_values = []

        for branch in branches:
            try:
                arg == branch[0]
            except:
                pass
                # raise AssertionError(f"argument not comparable to all branches")

            hook = _ValueBranchHook()
            self._branch_hooks.append(hook)
            branch_values.append(_ValueBranch(hook, branch[1]))

        if default is None:
            self._default_hook = None
        else:
            self._default_hook = _ValueBranchHook()
            branch_values.append(_ValueBranch(self._default_hook, default))

        super().__init__(
            _MergedBranch(branch_values),
            bound_statements=[],
        )

    def dump(self) -> IndentBlock:
        if self._default is None:
            default = []
        else:
            default = [IndentBlock(title="[default]", content=f"{self._default}")]

        return IndentBlock(
            title="SelectWith",
            content=[
                IndentBlock(title=f"[{cond}]", content=f"{value}")
                for cond, value in self._branches
            ]
            + default,
        )


class CondSelect(Statement):
    def __init__(
        self, branches: list[Tuple[Expression, CodeBlock]], default: CodeBlock | None
    ):
        self._branches = branches
        self._default = default

        code_default = [] if default is None else [default]
        code_branches = [branch[1] for branch in branches]

        returns = any(branch.returns() for branch in code_branches + code_default)

        return_paths = []

        if returns:
            # if any branch returns all branches must always return
            assert all(
                branch.returns_always() for branch in code_branches + code_default
            )

            for branch in code_branches + code_default:
                return_paths.extend(branch.return_paths())

        super().__init__(returns, return_paths)

    def dump(self) -> IndentBlock:
        if self._default is not None:
            return IndentBlock(
                title="CondSelect",
                content=[
                    IndentBlock([expr.dump(), code.dump()])
                    for expr, code in self._branches
                ]
                + [IndentBlock(title="[default]", content=self._default.dump())],
            )
        else:
            return IndentBlock(
                title="CondSelect",
                content=[
                    IndentBlock([expr.dump(), code.dump()])
                    for expr, code in self._branches
                ],
            )


class Statemachine(Statement):
    def __init__(self, body: CodeBlock, name: str):
        super().__init__()
        self._body = body
        self._name = name

    def dump(self) -> IndentBlock:
        return IndentBlock(title="Statemachine", content=self._body.dump())


class ResetContext(Statement):
    def dump(self):
        return IndentBlock(title="ResetContext", content=[])


class ResetPushed(Statement):
    def dump(self):
        return IndentBlock(title="ResetPushed", content=[])


#
# Assertation
#


class Assert(Statement):
    def __init__(self, cond: Expression, message: str | None):
        super().__init__()

        self._cond = cond
        self._msg = message

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title="Assertation",
            content=[
                IndentBlock(title="condition", content=self._cond.dump()),
                IndentBlock(title="message", content=self._msg),
            ],
        )


#
#
#
# instances
#
#
#


class Block:
    def __init__(self, info: EntityInfo, subblocks, contexts, attributes):
        self._info = info
        self._subblocks = subblocks
        self._contexts = contexts
        self._attributes = attributes

    def subblocks(self):
        return self._subblocks

    def contexts(self):
        return self._contexts

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"Block",
            content=[sub.dump() for sub in self._subblocks],
        )


class EntityTemplate(Block):
    def __init__(self, info: EntityInfo, subblocks: list | None, contexts: list | None):
        if info.extern:
            assert (
                subblocks is None and contexts is None
            ), "extern blocks cannot contain subbocks or synthesizable contexts"

            super().__init__(info, [], [], {})
        else:
            super().__init__(info, subblocks, contexts, info.attributes)

    def extern(self):
        return self._info.extern

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"EntityTemplate ({self._info.name})",
            content=[
                IndentBlock(
                    title="Ports",
                    content=[repr(port) for port in self._info.ports],
                ),
                IndentBlock(
                    title="Subinstances",
                    content=[inst.dump() for inst in self.subinstances()],
                ),
            ],
        )


class Entity(Block):
    def __init__(
        self,
        template: EntityTemplate,
        port_definitions: dict[str, Signal],
        generic_definitions: dict[str, Any],
    ):
        for name, port in template._info.ports.items():
            port._assign_(port_definitions[name], AssignMode.NEXT)

        super().__init__(template._info, [], [], template._info.attributes)
        self._template = template
        self._port_definitions = port_definitions
        self._generic_definitions = generic_definitions

    def template(self) -> EntityTemplate:
        return self._template

    def port_definitions(self) -> dict[str, Signal]:
        return self._port_definitions

    def generic_definitions(self):
        return self._generic_definitions

    def instantiate(self) -> Block:
        raise NotImplementedError()

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title="EntityWrapper",
            content=[
                IndentBlock(title="template", content=self._template.dump()),
                IndentBlock(
                    title="port definitions",
                    content=[
                        f"{name}: {value}"
                        for name, value in self._port_definitions.items()
                    ],
                ),
            ],
        )


#
# synthesizable contexts
#


class Context:
    def __init__(self, name: str, code: CodeBlock, attributes: dict, source_location):
        self._name = name
        self._code = code
        self._attributes = attributes
        self._source_loc = source_location

    def name(self):
        return self._name

    def attributes(self):
        return self._attributes

    def code(self):
        return self._code

    def source_location(self):
        return self._source_loc


class Concurrent(Context):
    def __init__(self, name, code: CodeBlock, attributes: dict, source_location):
        super().__init__(name, code, attributes, source_location)

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"Concurrent (name={self._name})",
            content=self._code.dump(),
        )


class Sequential(Context):
    def __init__(
        self,
        name,
        code: CodeBlock,
        always_expr: list,
        sensitivity: list,
        attributes: dict,
        source_location,
    ):
        super().__init__(name, code, attributes, source_location)
        self._always_expr = always_expr
        self._sensitivity = sensitivity

    def sensitivity(self):
        return self._sensitivity

    def always_expr(self):
        return self._always_expr

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"Sequential (name={self._name})",
            content=self._code.dump(),
        )
