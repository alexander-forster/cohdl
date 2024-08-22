from __future__ import annotations

from abc import abstractmethod
import enum
import typing

from typing import Callable, Tuple, cast

from cohdl._core._type_qualifier import (
    Signal,
    Variable,
    Temporary,
    Port,
    Generic,
    TypeQualifier,
    Offset,
    Slice,
)

from cohdl._core._bit import Bit
from cohdl._core._intrinsic import (
    _BitSignalEvent,
    _BitSignalEventGroup,
)

from cohdl.utility import IndentBlock, IdMap, IdSet
from cohdl.utility.source_location import SourceLocation
from cohdl.utility.virtual_traceback import VirtualFrame

from cohdl._core._intrinsic import _SensitivitySpec, _SensitivityAll, _SensitivityList
from cohdl._core._primitive_type import is_primitive
from cohdl._core import enum as cohdl_enum
from cohdl._core._context import EntityInfo

from cohdl._core import _InlineCode
from cohdl._core import _intrinsic_operations as intr_op


class VisitException(Exception):
    def __init__(self, src_statement: Statement, original: Exception):

        if isinstance(original, VisitException):
            self.with_traceback(original.original.__traceback__)
            self.src_statement = original.src_statement
            self.original = original.original
        else:
            self.with_traceback(original.__traceback__)
            self.src_statement = src_statement
            self.original = original


class AccessFlags(enum.Flag):
    _ZERO = 0
    READ = enum.auto()
    WRITE = enum.auto()
    PUSH = enum.auto()

    def short_repr(self) -> str:
        ret = ""

        def field(flag: AccessFlags, letter: str):
            nonlocal ret

            ret += letter if flag & self else "-"

        field(AccessFlags.READ, "r")
        field(AccessFlags.WRITE, "w")
        field(AccessFlags.PUSH, "p")

        return ret

    def is_read(self):
        return bool(self & AccessFlags.READ)

    def is_pushed(self):
        return bool(self & AccessFlags.PUSH)

    def is_written(self):
        return bool(self & AccessFlags.WRITE)


def _visit_referenced_objects(self, operation):
    # used to include objects in refspec in visited_objects

    def visit_single_object(obj, access):
        if isinstance(obj, TypeQualifier):
            for ref in obj._ref_spec:
                if isinstance(ref, Offset):
                    if isinstance(ref.offset, TypeQualifier):
                        ref.offset = operation(ref.offset, AccessFlags.READ)

                elif isinstance(ref, Slice):
                    if isinstance(ref.start, TypeQualifier):
                        ref.start = operation(ref.start, AccessFlags.READ)
                    if isinstance(ref.stop, TypeQualifier):
                        ref.stop = operation(ref.stop, AccessFlags.READ)
                else:
                    raise AssertionError("invalid ref_spec")

        return operation(obj, access)

    return self.visit_objects(visit_single_object)


class Statement:
    _current_frame = None

    @staticmethod
    def _obj_str(obj) -> str:
        return f"id: {id(obj):#x}, {obj}"

    def __init__(self):
        self._parent_state: _State | None = None
        self._frame: VirtualFrame = Statement._current_frame

    def visit(self, operation):
        try:
            return operation(self)
        except Exception as err:
            raise VisitException(self, err)

    @abstractmethod
    def visit_objects(
        self, operation: Callable[[typing.Any, AccessFlags], typing.Any]
    ): ...

    visit_referenced_objects = _visit_referenced_objects

    def set_parent_state(self, state: _State):
        self._state = state

    def get_parent_state(self) -> _State:
        return self._state

    @abstractmethod
    def update_transitions(self, state_map: IdMap):
        """
        point target of all transitions in the statement to new state defined in state_map
        """
        raise AssertionError("abstract method called")

    @abstractmethod
    def copy(self) -> Statement:
        raise AssertionError("abstract method called")

    @abstractmethod
    def dump(self) -> IndentBlock: ...


class Expression(Statement):
    def __init__(
        self,
        result,
    ):
        self._result = result
        super().__init__()

    def result(self):
        return self._result

    @abstractmethod
    def copy(self) -> Expression:
        raise AssertionError("abstract method called")

    @abstractmethod
    def dump(self) -> IndentBlock: ...

    @abstractmethod
    def visit_objects(self, operation):
        try:
            self._result = operation(self._result, AccessFlags.WRITE)
        except Exception as err:
            raise VisitException(self, err)

    def update_transitions(self, state_map: IdMap):
        pass


class CodeBlock(Statement):
    def __init__(self, content: list[Statement], parent: CodeBlock | None):
        if None in content:
            raise AssertionError("ERROR")

        self._content: list[Statement] = []
        self._parent = parent

        self._level: int = 0 if parent is None else parent._level + 1
        self._root: CodeBlock = self if parent is None else parent._root

        for stmt in content:
            if isinstance(stmt, CodeBlock):
                self._content.extend(stmt._content)
            else:
                self._content.append(stmt)

        super().__init__()

    def _fix_alias(self):
        # replace all reads from locally constructed signals
        # with reads from a temporary

        alias_map = IdMap()

        def collect_alias(node):
            if isinstance(node, _SignalAlias):
                alias_map[node.signal] = node.replacement
                return Nop()
            return node

        self.visit(collect_alias)

        def apply_alias(obj, access: AccessFlags):
            # replace all reads from aliased signals with replacement
            if access is AccessFlags.READ and hasattr(obj, "_root"):
                if obj._root in alias_map:
                    return Temporary[obj.type](
                        obj._value, _root=alias_map[obj._root], _ref_spec=obj._ref_spec
                    )
            return obj

        self.visit_objects(apply_alias)

    def get_parent_block(self, level):
        assert (
            self._level >= level
        ), "internal error: wrong nesting order of code blocks"

        if self._level == level:
            return self

        assert self._parent is not None, "internal error: code block has no parent"
        return self._parent.get_parent_block(level)

    @classmethod
    def common_block(cls, blocks: list[CodeBlock]):
        """
        check, if a and b are sub-blocks of a common parent
        return common parent, if it exists
        otherwise return None
        """

        if len(blocks) == 0:
            return None

        min_level = min(block._level for block in blocks)

        blocks = [block.get_parent_block(min_level) for block in blocks]

        level = min_level

        while True:
            first, *rest = blocks
            if all(block is first for block in rest):
                return first

            if level == 0:
                return None
            level -= 1

            blocks = [block._parent for block in blocks]

    def visit(self, operation):
        try:
            self._content = [stmt.visit(operation) for stmt in self._content]
            return operation(self)
        except Exception as err:
            raise VisitException(self, err)

    def visit_objects(self, operation: Callable):
        try:
            for stmt in self._content:
                stmt.visit_objects(operation)
        except Exception as err:
            raise VisitException(self, err)

    def update_transitions(self, state_map: IdMap):
        for stmt in self._content:
            stmt.update_transitions(state_map)

    # TODO: decide, if parent argument required,
    # breaks symmetry with other statements
    # maybe set parent of copy to None and set parent when
    # when adding the copy to the parent codeblock
    def copy(self, parent: CodeBlock | None) -> CodeBlock:
        return CodeBlock(
            [
                stmt.copy(self) if isinstance(stmt, CodeBlock) else stmt.copy()
                for stmt in self._content
            ],
            parent,
        )

    def empty(self) -> bool:
        # comments are considered empty so they don't affect
        # the special case where an await expression is the first
        # statement in a sequential context
        return len(self._content) == 0 or all(
            isinstance(elem, Comment) for elem in self._content
        )

    def addfront(self, stmt: Statement):
        if stmt is None:
            raise AssertionError("ERROR")
        self._content.insert(0, stmt)

    def append(self, stmt: Statement):
        if stmt is None:
            raise AssertionError("ERROR")
        self._content.append(stmt)

    def content(self) -> list[Statement]:
        return self._content

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title="Codeblock", content=[stmt.dump() for stmt in self._content]
        )


class Nop(Statement):
    def __init__(self):
        super().__init__()

    def visit_objects(self, operation: Callable):
        pass

    def copy(self):
        return Nop()

    def dump(self):
        return IndentBlock(title="Nop", content=[])


class Comment(Statement):
    def __init__(self, lines: list[str] = None):
        super().__init__()
        self.lines = lines if lines is not None else []

    def visit_objects(self, operation: Callable):
        pass

    def copy(self):
        return Comment([*self.lines])

    def dump(self) -> IndentBlock:
        return IndentBlock(title="Comment", content=[*self.lines])


class Event:
    Type = _BitSignalEvent.Type

    def __init__(self, event: _BitSignalEvent):
        self.sig = event.sig
        self.event_type = event.event_type

    def visit(self, operation):
        try:
            return operation(self)
        except Exception as err:
            raise VisitException(self, err)

    def visit_objects(self, operation: Callable):
        try:
            self.sig = operation(self.sig, AccessFlags.READ)
        except Exception as err:
            raise VisitException(self, err)

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title="_Event",
            content=[
                IndentBlock(title="type", content=str(self.event_type)),
            ],
        )


class EventGroup:
    Operation = _BitSignalEventGroup.Operation

    def __init__(self, event_grp: _BitSignalEventGroup):
        self.operation = event_grp.operation
        self.events = []

        for event in event_grp.events:
            if isinstance(event, _BitSignalEvent):
                self.events.append(Event(event))
            elif isinstance(event, _BitSignalEventGroup):
                self.events.append(EventGroup(event.operation, event.events))

    def visit(self, operation):
        try:
            self.events = [operation(event) for event in self.events]
            return operation(self)
        except Exception as err:
            raise VisitException(self, err)

    def visit_objects(self, operation: Callable):
        try:
            for event in self.events:
                event.visit_objects(operation)
        except Exception as err:
            raise VisitException(self, err)

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title="_EventGroup",
            content=[
                IndentBlock(title="operation", content=str(self.operation)),
                *[event.dump() for event in self.events],
            ],
        )


class If(Statement):
    def __init__(
        self,
        test,
        body: CodeBlock,
        orelse: CodeBlock,
    ):
        if isinstance(test, _BitSignalEvent):
            self._test = Event(test)
        elif isinstance(test, _BitSignalEventGroup):
            self._test = EventGroup(test)
        else:
            self._test = test

        self._body = body
        self._orelse = orelse

        super().__init__()

    def visit(self, operation):
        try:
            if isinstance(self._test, (Event, EventGroup)):
                self._test = self._test.visit(operation)

            self._body = self._body.visit(operation)
            self._orelse = self._orelse.visit(operation)
            return operation(self)
        except Exception as err:
            raise VisitException(self, err)

    def visit_objects(self, operation: Callable):
        try:
            if isinstance(self._test, (Event, EventGroup)):
                self._test.visit_objects(operation)
            else:
                self._test = operation(self._test, AccessFlags.READ)

            self._body.visit_objects(operation)
            self._orelse.visit_objects(operation)
        except Exception as err:
            raise VisitException(self, err)

    def copy(self) -> If:
        return If(self._test, self._body.copy(None), self._orelse.copy(None))

    def update_transitions(self, state_map: IdMap):
        self._body.update_transitions(state_map)
        self._orelse.update_transitions(state_map)

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title="If",
            content=[
                IndentBlock(title="test", content=Statement._obj_str(self._test)),
                IndentBlock(title="body", content=self._body.dump()),
                IndentBlock(title="orelse", content=self._orelse.dump()),
            ],
        )


class Compare(Expression):
    Operator = intr_op.ComparisonOperator

    def __init__(
        self,
        op: Compare.Operator,
        lhs,
        rhs,
        result: Temporary[Bit],
    ):
        self._op = op
        self._lhs = lhs
        self._rhs = rhs

        super().__init__(result)

    def visit_objects(self, operation: Callable):
        try:
            self._lhs = operation(self._lhs, AccessFlags.READ)
            self._rhs = operation(self._rhs, AccessFlags.READ)
            self._result = operation(self._result, AccessFlags.WRITE)
        except Exception as err:
            raise VisitException(self, err)

    def copy(self) -> Compare:
        return Compare(self._op, self._lhs, self._rhs, self.result())

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"Compare, op = {self._op}",
            content=[
                f"lhs    = {Statement._obj_str(self._lhs)}",
                f"rhs    = {Statement._obj_str(self._rhs)}",
                f"result = {Statement._obj_str(self.result())}",
            ],
        )


class UnaryOp(Expression):
    Operator = intr_op.UnaryOperator

    def __init__(
        self,
        op: UnaryOp.Operator,
        arg,
        result,
    ):
        assert is_primitive(TypeQualifier.decay(arg))
        assert is_primitive(TypeQualifier.decay(result))
        assert isinstance(op, UnaryOp.Operator)

        self._op = op
        self._arg = arg

        super().__init__(result)

    def visit_objects(self, operation: Callable):
        try:
            self._arg = operation(self._arg, AccessFlags.READ)
            self._result = operation(self._result, AccessFlags.WRITE)
        except Exception as err:
            raise VisitException(self, err)

    def copy(self) -> UnaryOp:
        return UnaryOp(self._op, self._arg, self.result())

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"UnaryOp, op = {self._op}",
            content=[
                f"arg    = {Statement._obj_str(self._arg)}",
                f"result = {Statement._obj_str(self.result())}",
            ],
        )


class BinOp(Expression):
    Operator = intr_op.BinaryOperator

    def __init__(
        self,
        op: BinOp.Operator,
        lhs,
        rhs,
        result,
    ):
        self._op = op
        self._lhs = lhs
        self._rhs = rhs

        super().__init__(
            result,
        )

    def visit_objects(self, operation: Callable):
        try:
            self._lhs = operation(self._lhs, AccessFlags.READ)
            self._rhs = operation(self._rhs, AccessFlags.READ)
            self._result = operation(self._result, AccessFlags.WRITE)
        except Exception as err:
            raise VisitException(self, err)

    def copy(self) -> BinOp:
        return BinOp(self._op, self._lhs, self._rhs, self.result())

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"BinOp, op = {self._op}",
            content=[
                f"lhs    = {Statement._obj_str(self._lhs)}",
                f"rhs    = {Statement._obj_str(self._rhs)}",
                f"result = {Statement._obj_str(self.result())}",
            ],
        )


class All(Expression):
    """
    and operation over arbitrary number of arguments
    """

    def __init__(self, args: list, result):
        self._args = args

        super().__init__(result)

    def visit_objects(self, operation: Callable):
        try:
            self._args = [operation(arg, AccessFlags.READ) for arg in self._args]
            self._result = operation(self._result, AccessFlags.WRITE)
        except Exception as err:
            raise VisitException(self, err)

    def copy(self) -> All:
        return All([*self._args], self.result())

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"All, len = {len(self._args)}",
            content=[
                f"{n}: {Statement._obj_str(arg)}" for n, arg in enumerate(self._args)
            ],
        )


class Any(Expression):
    """
    or operation over arbitrary number of arguments
    """

    def __init__(self, args: list, result):
        self._args = args

        super().__init__(result)

    def visit_objects(self, operation: Callable):
        try:
            self._args = [operation(arg, AccessFlags.READ) for arg in self._args]
            self._result = operation(self._result, AccessFlags.WRITE)
        except Exception as err:
            raise VisitException(self, err)

    def copy(self) -> Any:
        return Any([*self._args], self.result())

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"All, len = {len(self._args)}",
            content=[
                f"{n}: {Statement._obj_str(arg)}" for n, arg in enumerate(self._args)
            ],
        )


class SignalAssignment(Statement):
    def __init__(self, target_signal: Signal, source, frame=None):
        self._target = target_signal
        self._source = source

        super().__init__()

        if frame is not None:
            self._frame = frame

    def visit_objects(self, operation: Callable):
        try:
            self._target = operation(self._target, AccessFlags.WRITE)

            if isinstance(self._source, (tuple, list)):
                # special case for assignment to arrays
                self._source = [
                    operation(elem, AccessFlags.READ) for elem in self._source
                ]
            else:
                self._source = operation(self._source, AccessFlags.READ)
        except Exception as err:
            raise VisitException(self, err)

    def copy(self) -> SignalAssignment:
        return SignalAssignment(self._target, self._source)

    def update_transitions(self, state_map: IdMap):
        pass

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"SignalAssignment",
            content=[
                f"target = {Statement._obj_str(self._target)}",
                f"source = {Statement._obj_str(self._source)}",
            ],
        )


class SignalPush(Statement):
    def __init__(self, target_signal: Signal, source):
        self._target = target_signal
        self._source = source

        super().__init__()

    def visit_objects(self, operation: Callable):
        try:
            self._target = operation(self._target, AccessFlags.PUSH)

            if isinstance(self._source, (tuple, list)):
                # special case for assignment to arrays
                self._source = [
                    operation(elem, AccessFlags.READ) for elem in self._source
                ]
            else:
                self._source = operation(self._source, AccessFlags.READ)
        except Exception as err:
            raise VisitException(self, err)

    def copy(self) -> SignalPush:
        return SignalPush(self._target, self._source)

    def update_transitions(self, state_map: IdMap):
        pass

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"SignalPush",
            content=[
                f"target = {Statement._obj_str(self._target)}",
                f"source = {Statement._obj_str(self._source)}",
            ],
        )


class _SignalAlias(Statement):
    """
    _SignalAlias is used during parsing to indicate, that reads from
    a signal should instead refer to the given replacement.
    This allows signals to be used in the same state they are initialized.
    """

    def __init__(self, signal: Signal, replacement: Temporary):
        self.signal = signal
        self.replacement = replacement

    def visit_objects(self, operation: Callable): ...

    def copy(self) -> _SignalAlias:
        return _SignalAlias(self.signal, self.replacement)

    def update_transitions(self, state_map: IdMap):
        raise AssertionError("_SignalAlias should not be present after parsing")

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"_SignalAlias",
            content=[
                f"signal = {Statement._obj_str(self.signal)}",
                f"replacement = {Statement._obj_str(self.replacement)}",
            ],
        )


class VariableAssignment(Statement):
    def __init__(self, target_var, source):
        self._target = target_var
        self._source = source

        super().__init__()

    def visit_objects(self, operation: Callable):
        try:
            self._target = operation(self._target, AccessFlags.WRITE)

            if isinstance(self._source, (tuple, list)):
                # special case for assignment to arrays
                self._source = [
                    operation(elem, AccessFlags.READ) for elem in self._source
                ]
            else:
                self._source = operation(self._source, AccessFlags.READ)
        except Exception as err:
            raise VisitException(self, err)

    def copy(self) -> VariableAssignment:
        return VariableAssignment(self._target, self._source)

    def update_transitions(self, state_map: IdMap):
        pass

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title="VariableAssignment",
            content=[
                f"target = {Statement._obj_str(self._target)}",
                f"source = {Statement._obj_str(self._source)}",
            ],
        )


class ResetInstance(Statement):
    """
    statement, that indicates, that a given synthesizable
    should be set to its default value
    """

    def __init__(self, obj):
        self._obj = obj

        super().__init__()

    def visit_objects(self, operation: Callable):
        try:
            self._obj = operation(self._obj, AccessFlags.WRITE)
        except Exception as err:
            raise VisitException(self, err)

    def copy(self) -> ResetInstance:
        return ResetInstance(self._obj)

    def update_transitions(self, state_map: IdMap):
        pass

    def dump(self) -> IndentBlock:
        return IndentBlock(title=f"ResetInstance ({self._obj})")


#
#
# intrinsic functions
#
#


class Boolean(Expression):
    def __init__(
        self,
        arg,
        result: Temporary[Bit],
    ):
        self._arg = arg
        super().__init__(result)

    def visit_objects(self, operation: Callable):
        try:
            self._arg = operation(self._arg, AccessFlags.READ)
            self._result = operation(self._result, AccessFlags.WRITE)
        except Exception as err:
            raise VisitException(self, err)

    def dump(self) -> str:
        return "Boolean"

    def copy(self) -> Boolean:
        return Boolean(self._arg, self._result)


class SelectWith(Expression):
    def __init__(
        self,
        arg,
        branches: list[Tuple[Any, Any]],
        default: Any | None,
        result,
    ):
        self._arg = arg
        self._branches = [[*branch] for branch in branches]
        self._default = default

        super().__init__(result)

    def visit_objects(self, operation: Callable):
        try:
            self._arg = operation(self._arg, AccessFlags.READ)

            self._branches = [
                [operation(a, AccessFlags.READ), operation(b, AccessFlags.READ)]
                for a, b in self._branches
            ]

            if self._default is not None:
                self._default = operation(self._default, AccessFlags.READ)

            self._result = operation(self._result, AccessFlags.WRITE)
        except Exception as err:
            raise VisitException(self, err)

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

    def copy(self) -> SelectWith:
        return SelectWith(
            self._arg, [(a, b) for a, b in self._branches], self._default, self._result
        )


class CaseWhen(Statement):
    class Branch:
        def __init__(self, cond, body: CodeBlock):
            self.cond = cond
            self.code = body

        def __iter__(self):
            return iter((self.cond, self.code))

    def __init__(
        self, value, branches: list[Tuple], default: CodeBlock | None, frame=None
    ):
        self._value = value
        self._branches = [CaseWhen.Branch(cond, body) for cond, body in branches]
        self._default = default
        super().__init__()

        if frame is not None:
            self._frame = frame

    def visit(self, operation):
        try:
            for branch in self._branches:
                branch.code = branch.code.visit(operation)

            if self._default is not None:
                self._default = self._default.visit(operation)

            return operation(self)
        except Exception as err:
            raise VisitException(self, err)

    def visit_objects(self, operation: Callable):
        try:
            new_branches = []

            for branch in self._branches:
                cond = operation(branch.cond, AccessFlags.READ)
                branch.code.visit_objects(operation)

                new_branches.append(CaseWhen.Branch(cond, branch.code))

            self._branches = new_branches

            if self._default is not None:
                self._default.visit_objects(operation)

            self._value = operation(self._value, AccessFlags.READ)
        except Exception as err:
            raise VisitException(self, err)

    def dump(self) -> IndentBlock:
        if self._default is None:
            return IndentBlock(
                title="CaseWhen",
                content=[
                    IndentBlock([f"{branch.cond}", branch.code.dump()])
                    for branch in self._branches
                ],
            )
        else:
            return IndentBlock(
                title="CaseWhen",
                content=[
                    IndentBlock([f"{branch.cond}", branch.code.dump()])
                    for branch in self._branches
                ]
                + [IndentBlock(title="default", content=self._default.dump())],
            )

    def copy(self) -> CaseWhen:
        return CaseWhen(
            self._value,
            [(branch.cond, branch.code.copy()) for branch in self._branches],
            None if self._default is None else self._default.copy(),
        )

    def update_transitions(self, state_map: IdMap):
        for branch in self._branches:
            branch.code.update_transitions(state_map)

        if self._default is not None:
            self._default.update_transitions(state_map)


class CondSelect(Statement):
    def __init__(
        self, branches: list[Tuple[Expression, CodeBlock]], default: CodeBlock | None
    ):
        self._branches = branches
        self._default = default
        super().__init__()

    def visit(self, operation):
        try:
            self._branches = [
                (expr.visit(operation), branch.visit(operation))
                for expr, branch in self._branches
            ]

            if self._default is not None:
                self._default = self._default.visit(operation)

            return operation(self)
        except Exception as err:
            raise VisitException(self, err)

    def visit_objects(self, operation: Callable):
        try:
            for branch in self._branches:
                branch[0].visit_objects(operation)
                branch[1].visit_objects(operation)

            if self._default is not None:
                self._default.visit_objects(operation)
        except Exception as err:
            raise VisitException(self, err)

    def dump(self) -> IndentBlock:
        if self._default is None:
            return IndentBlock(
                title="CondSelect",
                content=[
                    IndentBlock(
                        [expr.dump(), code.dump()] for expr, code in self._branches
                    )
                ],
            )
        else:
            return IndentBlock(
                title="CondSelect",
                content=[
                    IndentBlock(
                        [expr.dump(), code.dump()] for expr, code in self._branches
                    )
                ]
                + [IndentBlock(title="default", content=self._default.dump())],
            )

    def copy(self) -> CondSelect:
        return CondSelect(
            [(expr.copy(), code.copy()) for expr, code in self._branches],
            None if self._default is None else self._default.copy(),
        )

    def update_transitions(self, state_map: IdMap):
        for branch in self._branches:
            branch[1].update_transitions(state_map)

        if self._default is not None:
            self._default.update_transitions(state_map)


class _State(Statement):
    def __init__(self, code: CodeBlock, open_block: CodeBlock):
        self._code = code
        self._state_id = None

        # a code block that is part of self._code
        # and used to add statments
        self._open_block = open_block

        code.set_parent_state(self)
        open_block.set_parent_state(self)

        # init without used objects because
        # code is not complete at this point
        # instead tracked_objects is overridden and calls
        # self._code.tracked_objects()
        super().__init__()

    def fix_alias(self):
        # replace all reads from locally constructed signals
        # with reads from a temporary

        self._code._fix_alias()

    def visit(self, operation):
        try:
            self._code = self._code.visit(operation)
            return operation(self)
        except Exception as err:
            raise VisitException(self, err)

    def visit_objects(self, operation: Callable):
        self._code.visit_objects(operation)

    def code(self):
        return self._code

    def set_state_id(self, id: cohdl_enum.Enum):
        self._state_id = id

    def get_state_id(self):
        return self._state_id

    def update_transitions(self, state_map: IdMap):
        self._code.update_transitions(state_map)

    def copy(self) -> _State:
        class DummyOpenBlock:
            """
            open_block is only required during parsing,
            when copying a complete State DummyOpenBlock is passed instead
            it should never be used
            """

            def set_parent_state(self, state):
                pass

        return _State(self._code.copy(), cast(CodeBlock, DummyOpenBlock()))

    def empty(self) -> bool:
        return self._code.empty()

    def open_block(self):
        return self._open_block

    def append(self, stmt: Statement):
        self._open_block.append(stmt)
        stmt.set_parent_state(self)

    def set_open_block(self, open_block: CodeBlock):
        self._open_block = open_block
        open_block.set_parent_state(self)

    def dump(self) -> IndentBlock:
        return IndentBlock(title=f"State, id: {id(self):#x}", content=self._code.dump())


class _Transition(Statement):
    def __init__(self, next_state: _State):
        super().__init__()
        self._next_state = next_state

    def visit_objects(self, operation: Callable):
        pass

    def copy(self) -> _Transition:
        return _Transition(self._next_state)

    def dump(self) -> IndentBlock:
        return IndentBlock(title=f"Transition, target={self._next_state}", content=[])


class _ResetContext(Statement):
    def visit_objects(self, operation: Callable):
        pass

    def copy(self):
        return _ResetContext()

    def dump(self) -> IndentBlock:
        return IndentBlock(title=f"ResetContext")


class _ResetPushed(Statement):
    def visit_objects(self, operation: Callable):
        pass

    def copy(self):
        return _ResetPushed()

    def dump(self) -> IndentBlock:
        return IndentBlock(title=f"ResetPushed", content=[])


class BitSignalEvent(Expression):
    Type = _BitSignalEvent.Type

    def __init__(self, event_type: BitSignalEvent.Type, arg, result):
        super().__init__(result)
        self.arg = arg
        self.event_type = event_type

    def visit_objects(self, operation: Callable):
        try:
            self.arg = operation(self.arg, AccessFlags.READ)
            self._result = operation(self._result, AccessFlags.WRITE)
        except Exception as err:
            raise VisitException(self, err)

    def copy(self):
        return BitSignalEvent(self.event_type, self.arg, self.result())

    def dump(self) -> IndentBlock:
        return IndentBlock(title=f"BitsignalEvent")


class StatemachineContext:
    _singleton: StatemachineContext | None = None

    @staticmethod
    def enter(name: str):
        assert (
            StatemachineContext._singleton is None
        ), "error nested StatemachineContext"
        ctx = StatemachineContext(name)
        StatemachineContext._singleton = ctx
        return ctx

    @staticmethod
    def get():
        ctx = StatemachineContext._singleton
        assert ctx is not None, "internal error: requested statemachine context"
        return ctx

    @staticmethod
    def finish(open_blocks):
        assert (
            StatemachineContext._singleton is not None
        ), "internal error: finished StatemachineContext with no active singleton"
        ctx = StatemachineContext._singleton
        StatemachineContext._singleton = None

        ctx._fix_signal_alias()

        if len(ctx._states) == 0:
            return CodeBlock([], None)
        elif len(ctx._states) == 1:
            # when the statemachine consists of only one state,
            # it can be treated as a normal code block
            # no transition logic is needed

            code = ctx._states[0].code()

            def remove_transitions(stmt):
                if isinstance(stmt, _Transition):
                    return Nop()
                return stmt

            code.visit(remove_transitions)

            return code

        # if a statemachine contains multiple states
        # add a transition back to the first state to all code blocks, that reach the end
        # of the sequential block
        # insert transition at the front of the block because it is possible, that
        # the final block already contains transitions (potentially in nested if statements)
        # that would be shadowed by a transition at the very end
        for open_block in open_blocks:
            open_block.addfront(_Transition(ctx.first_state()))

        return Statemachine(ctx)

    def _check_temporaries(self):
        for state in self._states:
            used_temporaries: IdMap[Any, bool] = IdMap()

            def check(obj, access: AccessFlags):
                if isinstance(obj, Temporary):
                    if obj._root not in used_temporaries:
                        # the first access to a temporary within a
                        # state must be a write access
                        # since writes to temporaries are only possible during
                        # construction this check also ensures, that
                        # no temporary is used (read) outside the single
                        # state it is valid in
                        assert (
                            access is AccessFlags.WRITE
                        ), "Temporary objects may not be shared between states"
                        used_temporaries[obj._root] = True
                return obj

            state.visit_objects(check)

    def _fix_signal_alias(self):
        for state in self._states:
            state.fix_alias()

    def _set_state_signal(self, signal):
        def set_signal(stmt):
            if isinstance(stmt, _Transition):
                stmt._state_signal = signal
            return stmt

        for state in self._states:
            state.visit(set_signal)

    def __init__(self, name: str | None = None):
        first_block = CodeBlock([], None)
        self._first = _State(first_block, first_block)
        self._states: list[_State] = [self._first]
        self._name = name

    def first_block(self):
        return self._first.code()

    def at_start(self):
        return self._first.empty()

    def first_state(self):
        return self._first

    def add_state(self, state: _State):
        self._states.append(state)


class Statemachine(Statement):
    def __init__(self, ctx: StatemachineContext):
        super().__init__()

        self._ctx = ctx

        name = ctx._name
        states = ctx._states

        if name is None:
            enum_name = "process_state"
        else:
            if name.startswith("_"):
                enum_name = f"state{name}"
            else:
                enum_name = f"state_{name}"

        self._state_type = cohdl_enum.Enum(
            enum_name, [f"state_{nr}" for nr in range(len(states))]
        )

        state_name = f"s{name}" if name.startswith("_") else f"s_{name}"

        self._current_state = Signal[self._state_type](
            self._state_type(1), name=state_name
        )

        ctx._set_state_signal(self._current_state)

        self._state_id = IdMap()

        for nr, state in enumerate(states):
            self._state_id[state] = self._state_type(nr + 1)

    def check_temporaries(self):
        self._ctx._check_temporaries()

    def as_case_when(self):
        def replace_transition(stmt):
            if isinstance(stmt, _Transition):
                return SignalAssignment(
                    self._current_state, self._state_id[stmt._next_state], stmt._frame
                )
            else:
                return stmt

        for state in self._ctx._states:
            state.visit(replace_transition)

        return CaseWhen(
            self._current_state,
            [(self._state_id[state], state.code()) for state in self._ctx._states],
            None,
            self._frame,
        )

    def visit(self, operation):
        try:
            self._ctx._states = [state.visit(operation) for state in self._ctx._states]
            return operation(self)
        except Exception as err:
            raise VisitException(self, err)

    def visit_objects(self, operation):
        try:
            self._current_state = operation(self._current_state, AccessFlags.READ)

            for state in self._ctx._states:
                state.visit_objects(operation)
        except Exception as err:
            raise VisitException(self, err)

    def dump(self):
        return IndentBlock("Statemachine")

    def copy(self):
        copied_states = [state.copy() for state in self._ctx._states]

        state_map = IdMap()

        for state, cpy_state in zip(self._ctx._states, copied_states):
            state_map[state] = (cpy_state, self)

        for cpy_state in copied_states:
            cpy_state.update_transitions(state_map)

    def update_transitions(self, state_map: IdMap):
        raise AssertionError("TODO")


#
# Assertions
#


class Assert(Statement):
    def __init__(self, cond, msg):
        self._cond = cond
        self._msg = msg
        super().__init__()

    def visit_objects(self, operation: Callable):
        try:
            self._cond = operation(self._cond, AccessFlags.READ)
        except Exception as err:
            raise VisitException(self, err)

    def update_transitions(self, state_map: IdMap):
        pass

    def copy(self) -> Assert:
        return Assert(self._cond, self._msg)

    def dump(self) -> IndentBlock:
        return IndentBlock(title=f"Assertation", content=str(self._msg))


#
# inline code
#


class InlineCode(Statement):
    def __init__(self, options: list[_InlineCode], result):
        self.options = options
        self.result = result

    def visit_objects(self, operation):
        try:

            def visit_nodes(nodes: list[_InlineCode.Node]):
                updated = []

                for node in nodes:
                    if isinstance(node, _InlineCode.Text):
                        updated.append(node)
                    elif isinstance(node, _InlineCode.Object):
                        access = AccessFlags.READ if node.read else AccessFlags.WRITE
                        updated.append(
                            _InlineCode.Object(operation(node.obj, access), node.read)
                        )
                    elif isinstance(node, _InlineCode.SubCode):
                        for option in node.options:
                            assert isinstance(option, _InlineCode)
                            visit_nodes(option.content)
                    else:
                        raise AssertionError("invalid content")

                return updated

            for option in self.options:
                visit_nodes(option.content)

            if self.result is not None:
                self.result = operation(self.result, AccessFlags.WRITE)
        except Exception as err:
            raise VisitException(self, err)

    def copy(self):
        return InlineCode([o.copy() for o in self.options])

    def dump(self):
        return IndentBlock(title="InlineCode")


#
#
# Instances
#
#


class Block:
    def __init__(
        self,
        name: str | None,
        subblocks: list[Block],
        contexts: list[Context],
        attributes: dict,
    ):
        self._name = name
        self._subblocks = subblocks
        self._contexts = contexts
        self._attributes = attributes

    def name(self):
        return self._name

    def subblocks(self) -> list[Block]:
        return self._subblocks

    def contexts(self):
        return self._contexts

    def all_contexts(self):
        # iterate over all nested contexts

        for ctx in self._contexts:
            yield ctx

        for sub in self._subblocks:
            yield from sub.all_contexts()

    def all_blocks(self):
        # iterate over all nested blocks

        yield self

        for sub in self._subblocks:
            yield from sub.all_blocks()

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title="Block",
            content=[
                IndentBlock(
                    title="Subblocks", content=[inst.dump() for inst in self._subblocks]
                ),
                IndentBlock(
                    title="Contexts", content=[inst.dump() for inst in self._contexts]
                ),
            ],
        )


#
# synthesizable contexts
#


class Context:
    def __init__(
        self,
        name: str,
        code: CodeBlock,
        attributes: dict,
        source_location: SourceLocation,
    ):
        self._name = name
        self._code = code
        self.attributes = attributes
        self._source_location = source_location

    def visit(self, operation):
        try:
            self._code = self._code.visit(operation)
        except Exception as err:
            raise VisitException(self, err)

    def visit_objects(self, operation):
        self._code.visit_objects(operation)

    # TODO: maybe make this the default
    # and always visit all referenced objects
    visit_referenced_objects = _visit_referenced_objects

    def code(self):
        return self._code

    def name(self):
        return self._name

    def source_location(self):
        return self._source_location


class Concurrent(Context):
    def __init__(
        self,
        name: str,
        code: CodeBlock,
        attributes: dict,
        source_location: SourceLocation,
    ):
        super().__init__(name, code, attributes, source_location)

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title="Concurrent",
            content=[
                IndentBlock(title="code", content=self._code.dump()),
            ],
        )


class Sequential(Context):
    def _pushed_resettable_signals(self):
        pushed = IdSet()
        resettable = IdSet()

        def visit_objects(obj, access: AccessFlags):
            if access & AccessFlags.PUSH:
                pushed.add(obj._root)

            if access & (AccessFlags.PUSH | AccessFlags.WRITE):
                root = obj._root
                if root.has_default() and not root._noreset:
                    resettable.add(root)

            return obj

        self.visit_objects(visit_objects)

        def visit_statements(stmt):
            if isinstance(stmt, _ResetContext):
                return CodeBlock(
                    [
                        (
                            SignalAssignment(r, r.default(), stmt._frame)
                            if isinstance(r, Signal)
                            else VariableAssignment(r, r.default())
                        )
                        for r in resettable
                    ],
                    None,
                )
            elif isinstance(stmt, _ResetPushed):
                return CodeBlock(
                    [
                        SignalAssignment(sig, sig.default(), stmt._frame)
                        for sig in pushed
                    ],
                    None,
                )

            return stmt

        self._code.visit(visit_statements)

    def __init__(
        self,
        name: str,
        code: CodeBlock,
        always_expr: Concurrent | None,
        sensitivity: _SensitivitySpec | None,
        attributes: dict,
        source_location: SourceLocation,
    ):
        if sensitivity is None:
            sensitivity = _SensitivityAll()

        assert isinstance(sensitivity, _SensitivitySpec)
        super().__init__(name, code, attributes, source_location)
        self._always_expr = always_expr
        self._sensitivity = sensitivity

        def translate_statemachine(stmt):
            if isinstance(stmt, Statemachine):
                stmt.check_temporaries()
                return stmt.as_case_when()
            else:
                return stmt

        code.visit(translate_statemachine)

        self._pushed_resettable_signals()
        code._fix_alias()

    def visit(self, operation):
        try:
            if self._always_expr is not None:
                self._always_expr._code = self._always_expr._code.visit(operation)
            super().visit(operation)
        except Exception as err:
            raise VisitException(self, err)

    def visit_objects(self, operation: Callable):
        try:
            if self._always_expr is not None:
                self._always_expr.code().visit_objects(operation)

            if isinstance(self._sensitivity, _SensitivityList):
                signals = self._sensitivity.signals
                signals = [operation(sig, AccessFlags.READ) for sig in signals]
            else:
                assert isinstance(self._sensitivity, _SensitivityAll)

            super().visit_objects(operation)
        except Exception as err:
            raise VisitException(self, err)

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title="Sequential",
            content=[
                IndentBlock(title="code", content=self._code.dump()),
            ],
        )


class EntityTemplate(Block):
    """
    entity with unconstrained ports, generics
    """

    def __init__(
        self,
        info: EntityInfo,
        subblocks: list[Block],
        contexts: list[Context],
    ):
        super().__init__(info.name, subblocks, contexts, info.attributes)
        self._info = info

        #
        # check signal usage
        #

        written_in = IdMap()
        used_in = IdMap()

        current_ctx: Context

        def check_usage(obj, access: AccessFlags):
            # check, that signals are only written in a single context
            if access is AccessFlags.WRITE or access is AccessFlags.PUSH:
                if isinstance(obj, Port) and obj.is_input():
                    raise AssertionError(
                        f"writing to input port '{obj._root._name}' not allowed"
                    )

                if isinstance(obj, (Signal, Variable, Temporary)):
                    obj_root = obj._root
                    if obj_root in written_in:
                        assert written_in[obj_root] is current_ctx, (
                            f"object '{obj_root}, name={obj_root.name()}' written in multiple contexts\n"
                            " written in this context\n"
                            f"{current_ctx.source_location()}\n"
                            " also written in this context\n"
                            f"{written_in[obj_root].source_location()}\n"
                        )
                    else:
                        written_in[obj_root] = current_ctx

            # check, that Variables and Temporaries are only used in a single context
            if isinstance(obj, (Temporary, Variable)):
                obj_root = obj._root
                if obj_root in used_in:
                    assert used_in[obj_root] is current_ctx, (
                        f"object '{obj_root}' used in multiple contexts\n"
                        " first found here\n"
                        f"{current_ctx.source_location()}\n"
                        " also found here\n"
                        f"{used_in[obj_root].source_location()}\n"
                    )
                else:
                    used_in[obj_root] = current_ctx

            return obj

        for ctx in self.all_contexts():
            current_ctx = ctx
            ctx.visit_objects(check_usage)

        for block in self.all_blocks():
            if isinstance(block, Entity):
                port_decl = block._template._info.ports

                for name, sig in block._ports.items():
                    decl: Port = port_decl[name]

                    if not decl.is_output():
                        continue

                    sig_root: Signal = sig._root

                    if sig_root in written_in:
                        other = written_in[sig_root]
                        current_name = f"entity instantiation: {block.name()}"

                        if isinstance(other, Entity):
                            other_name = f"entity instantiation: {other.name()}"
                        else:
                            other_name = f"{other.source_location()}"

                        raise AssertionError(
                            f"object '{sig_root}, name={sig_root.name()}' written in multiple contexts\n"
                            " written in this context\n"
                            f"{current_name}\n"
                            " also written in this context\n"
                            f"{other_name}\n"
                        )
                    else:
                        written_in[sig_root] = block

    def info(self):
        return self._info

    def extern(self):
        return self._info.extern

    def port_declarations(self) -> dict[str, Port]:
        return self._info.ports

    def generic_declarations(self) -> dict[str, Generic]:
        return self._info.generics

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"EntityTemplate {self._name}",
            content=[
                IndentBlock(
                    title="Ports",
                    content=[repr(port) for port in self._info.ports.values()],
                ),
                IndentBlock(
                    title="Subinstances",
                    content=[inst.dump() for inst in self._subblocks],
                ),
                IndentBlock(
                    title="Contexts",
                    content=[inst.dump() for inst in self._contexts],
                ),
            ],
        )


class Entity(Block):
    def __init__(
        self,
        template: EntityTemplate,
        name,
        ports: dict[str, Signal],
        generics: dict[str, Any],
    ):
        self._template: EntityTemplate = template

        self._ports: dict[str, Signal] = ports
        self._generics: dict[str, Any] = generics

        super().__init__(name, [], [], {})

    def get_ports(self):
        return self._ports

    def get_generics(self):
        return self._generics

    def get_template(self) -> EntityTemplate:
        return self._template

    def dump(self) -> IndentBlock:
        return IndentBlock(
            title=f"Entity ({self._name})",
            content=[
                IndentBlock(title="template", content=self._template.dump()),
                IndentBlock(
                    title="ports",
                    content=[f"{name}, {port}" for name, port in self._ports.items()],
                ),
            ],
        )
