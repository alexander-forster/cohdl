from __future__ import annotations
from abc import abstractmethod
import typing
from typing import Tuple

import cohdl

from cohdl._core._ir import repr as ir
from cohdl._core._primitive_type import _PrimitiveType
from cohdl._core._type_qualifier import (
    Port,
    TypeQualifier,
    Generic,
    RefSpec,
    Offset,
    Slice,
)
from cohdl._core._array import Array
from cohdl._core import _boolean, _Boolean
from cohdl._core._intrinsic import _SensitivitySpec, _SensitivityAll, _SensitivityList
from cohdl import (
    Signal,
    Variable,
    Temporary,
    Bit,
    BitOrder,
    BitVector,
    Unsigned,
    Signed,
    Integer,
    Null,
    Full,
    _NullFullType,
)

from cohdl._core._context import EntityInfo
from cohdl._core._inline import InlineVhdl
from cohdl._core._inline import InlineCode as _InlineCode

from cohdl._core import enum as cohdl_enum
from cohdl.utility import IdMap, IdSet
from cohdl.utility.code_writer import IndentBlock, TextBlock


def comment_list(comment: None | str | list[str]):
    if comment is None:
        return []
    if isinstance(comment, str):
        comment = [comment]

    return [f"-- {c}" for c in comment]


class Statement:
    def write(self, scope: VhdlScope) -> TextBlock | str:
        # return TextBlock or str without indentation
        # parent statements define indentation when required
        ...


class Expression(Statement):
    def __init__(self, result):
        self.result = result


class CodeBlock(Statement):
    def __init__(self, stmts: list[Statement]):
        self._stmts = stmts

    def empty(self) -> bool:
        if len(self._stmts) == 0:
            return True

        if all(isinstance(stmt, CodeBlock) for stmt in self._stmts):
            return all(block.empty() for block in self._stmts)
        return False

    def write(self, scope: VhdlScope, indent=True) -> TextBlock:
        return TextBlock(
            content=[
                (
                    stmt.write(scope, indent)
                    if isinstance(stmt, CodeBlock)
                    else stmt.write(scope)
                )
                for stmt in self._stmts
            ]
        )


class Value(Expression):
    def __init__(self, value):
        super().__init__(value)

    def write(self, scope: VhdlScope, target_hint=None, constrain=False):
        return scope.format_value(self.result, target_hint, constrain)


class Constant(Value): ...


class Literal(Constant):
    def write(self, scope: VhdlScope, target_hint=None) -> str:
        if target_hint is None:
            return scope.format_literal(self.result)
        return scope.format_cast(
            target_hint, self.result, scope.format_literal(self.result)
        )


class Target(Value):
    """represents a value that is the target of an assignment

    :param Value: Synthesizable value that is the target of the assignment
    """

    def write(self, scope: VhdlScope):
        return scope.format_target(self.result)


class Source(Value): ...


class Nop(Expression):
    def __init__(self):
        super().__init__(None)

    def write(self, scope: VhdlScope):
        return TextBlock([])


class Comment(Statement):
    def __init__(self, lines):
        super().__init__()
        self.lines = lines

    def write(self, scope: VhdlScope):
        return TextBlock([f"-- {line}" for line in self.lines])


class Boolean(Expression):
    def __init__(self, arg: Expression):
        super().__init__(_Boolean())
        self._arg = arg

    def write(self, scope: VhdlScope):
        arg_str = self._arg.write(scope)

        return scope.format_cast(self.result, self._arg.result, arg_str)


class Event(Expression):
    Type = ir.Event.Type

    def __init__(self, value: Source, event_type: Event.Type):
        self._value = value
        self._event_type = event_type
        super().__init__(_Boolean(True))

    def write(self, scope: VhdlScope):
        Type = Event.Type
        event = self._event_type

        if event is Type.RISING:
            return f"rising_edge({self._value.write(scope)})"
        if event is Type.FALLING:
            return f"falling_edge({self._value.write(scope)})"
        if event is Type.BOTH_EDGES:
            return f"rising_edge({self._value.write(scope)} or falling_edge({self._value.write(scope)})"
        if event is Type.HIGH:
            return f"{self._value.write(scope)} = '1'"
        if event is Type.LOW:
            return f"{self._value.write(scope)} = '0'"

        raise AssertionError()


class Compare(Expression):
    Operator = ir.Compare.Operator

    operator_string = {
        Operator.EQ: "=",
        Operator.NE: "/=",
        Operator.GT: ">",
        Operator.LT: "<",
        Operator.GE: ">=",
        Operator.LE: "<=",
    }

    def __init__(
        self,
        op,
        lhs: Expression,
        rhs: Expression,
        result,
    ):
        super().__init__(result)
        self._op = op
        self._lhs = lhs
        self._rhs = rhs

    def write(self, scope: VhdlScope):
        op = Compare.operator_string[self._op]

        return f"({self._lhs.write(scope)} {op} {self._rhs.write(scope)})"


class All(Expression):
    def __init__(self, args, result):
        super().__init__(result)
        self._args = args

    def write(self, scope: VhdlScope) -> str:
        if len(self._args) == 0:
            return "true"

        return scope.format_cast(
            self.result,
            _Boolean(),
            " and ".join([str(Boolean(arg).write(scope)) for arg in self._args]),
        )


class Any(Expression):
    def __init__(self, args, result):
        super().__init__(result)
        self._args = args

    def write(self, scope: VhdlScope) -> str:
        if len(self._args) == 0:
            return "false"

        return scope.format_cast(
            self.result,
            _Boolean(),
            " or ".join([str(Boolean(arg).write(scope)) for arg in self._args]),
        )


class BinOp(Expression):
    Operator = ir.BinOp.Operator

    operator_string = {
        Operator.ADD: "+",
        Operator.SUB: "-",
        Operator.MUL: "*",
        Operator.BIT_AND: "and",
        Operator.BIT_OR: "or",
        Operator.BIT_XOR: "xor",
        Operator.CONCAT: "&",
        Operator.MOD: "mod",
        Operator.FLOOR_DIV: "/",
    }

    def __init__(
        self,
        op: BinOp.Operator,
        lhs: Expression,
        rhs: Expression,
        result,
    ):
        super().__init__(result)
        self._op = op
        self._lhs = lhs
        self._rhs = rhs

    def write(self, scope: VhdlScope):
        if self._op is BinOp.Operator.LSHIFT:
            # cast rhs to integer
            shift = scope.format_cast(
                Integer(), self._rhs.result, self._rhs.write(scope)
            )
            return f"shift_left({self._lhs.write(scope)}, {shift})"

        if self._op is BinOp.Operator.RSHIFT:
            # cast rhs to integer
            shift = scope.format_cast(
                Integer(), self._rhs.result, self._rhs.write(scope)
            )
            return f"shift_right({self._lhs.write(scope)}, {shift})"

        # cohdl treats Signed and Unsigned as subclasses of BitVector
        # and allows all BitVector operations for them.
        # This includes concatenation. Since VHDL is not so permissive
        # we have to explicitly cast the values to BitVector here.
        if self._op is BinOp.Operator.CONCAT:
            if isinstance(TypeQualifier.decay(self._lhs.result), BitVector):
                self._lhs.result = self._lhs.result.bitvector

            if isinstance(TypeQualifier.decay(self._rhs.result), BitVector):
                self._rhs.result = self._rhs.result.bitvector

        op = BinOp.operator_string[self._op]
        return f"({self._lhs.write(scope)}) {op} ({self._rhs.write(scope)})"


class UnaryOp(Expression):
    Operator = ir.UnaryOp.Operator

    operator_string = {
        Operator.INV: "not ",
        Operator.NEG: "-",
    }

    def __init__(self, op, arg: Expression, result):
        super().__init__(result)
        self._op = op
        self._arg = arg

    def write(self, scope: VhdlScope):
        if self._op is UnaryOp.Operator.NOT:
            as_bool = Boolean(self._arg)

            return scope.format_cast(self.result, bool, f"not ({as_bool.write(scope)})")
        else:
            if self._op is self.Operator.BOOL:
                as_bool = Boolean(self._arg)
                return as_bool.write(scope)

            if self._op is self.Operator.ABS:
                return f"abs({self._arg.write(scope)})"

            op = UnaryOp.operator_string[self._op]
            return f"{op}({self._arg.write(scope)})"


class SignalAssignment(Statement):
    def __init__(self, target: Target, source: Expression):
        self._target = target
        self._source = source

    def write(self, scope: VhdlScope) -> str:
        decayed_target = TypeQualifier.decay(self._target.result)
        is_array = isinstance(decayed_target, Array)

        target = self._target.write(scope)

        if is_array:
            source = self._source.write(scope, decayed_target)
            return f"{target} <= {source};"
        else:
            source = self._source.write(scope)
            return f"{target} <= {scope.format_cast(self._target.result, self._source.result, source)};"


class VariableAssignment(Statement):
    def __init__(
        self,
        target: Target,
        source: Expression,
    ):
        self._target = target
        self._source = source

    def write(self, scope: VhdlScope) -> str:
        decayed_target = TypeQualifier.decay(self._target.result)
        is_array = isinstance(decayed_target, Array)

        target = self._target.write(scope)

        if is_array:
            source = self._source.write(scope, decayed_target)
            return f"{target} := {source};"
        else:
            source = self._source.write(scope)
            return f"{target} := {scope.format_cast(self._target.result, self._source.result, source)};"


class If(Statement):
    def __init__(self, test: Expression, body: CodeBlock, orelse: CodeBlock):
        self._test = test
        self._body = body
        self._orelse = orelse

    def write(self, scope: VhdlScope) -> TextBlock:
        if not self._orelse.empty():
            return TextBlock(
                [
                    f"if {self._test.write(scope)} then",
                    IndentBlock(self._body.write(scope)),
                    "else",
                    IndentBlock(self._orelse.write(scope)),
                    "end if;",
                ],
            )

        return TextBlock(
            [
                f"if {self._test.write(scope)} then",
                IndentBlock(self._body.write(scope)),
                "end if;",
            ],
        )


class SelectWith(Statement):
    def __init__(
        self,
        arg: Value,
        branches: list[Tuple[Constant, Value]],
        default,
        target: Target,
    ):
        self._arg = arg
        self._branches = branches
        self._default = default
        self._target = target

    def write(self, scope) -> TextBlock:
        if self._default is None:
            assert len(self._branches) != 0
            separators = "," * (len(self._branches) - 1) + ";"
        else:
            separators = "," * len(self._branches)

        assert isinstance(self._arg, Value)

        arg: Value = self._arg

        if isinstance(TypeQualifier.decay(arg.result), BitVector):
            root = TypeQualifier.decay(arg.result._root)

            if isinstance(root, Unsigned):
                arg = Value(arg.result.unsigned)
            elif isinstance(root, Signed):
                arg = Value(arg.result.signed)
            else:
                arg = Value(arg.result.bitvector)

        return TextBlock(
            [
                f"with {arg.write(scope, constrain=True)} select {self._target.write(scope)} <=",
                IndentBlock(
                    [
                        *[
                            f"{branch[1].write(scope, self._target.result)} when {branch[0].write(scope, self._arg.result)}{sep}"
                            for branch, sep in zip(self._branches, separators)
                        ],
                        *[
                            f"{default.write(scope, self._target.result)} when others;"
                            for default in [self._default]
                            if default is not None
                        ],
                    ],
                ),
            ],
        )


class CaseWhen(Statement):
    def __init__(
        self,
        cond: Expression,
        branches: list[Tuple[Constant, CodeBlock]],
        others: CodeBlock | None = None,
    ):
        self._cond = cond
        self._branches = branches
        self._others = others

    def write(self, scope) -> TextBlock:
        assert isinstance(self._cond, Value)

        cond: Value = self._cond

        if isinstance(TypeQualifier.decay(cond.result), BitVector):
            root = TypeQualifier.decay(cond.result._root)

            if isinstance(root, Unsigned):
                cond = Value(cond.result.unsigned)
            elif isinstance(root, Signed):
                cond = Value(cond.result.signed)
            else:
                cond = Value(cond.result.bitvector)

        def write_block(block: CodeBlock) -> TextBlock:
            if block.empty():
                return TextBlock("null;")
            return block.write(scope)

        return TextBlock(
            [
                f"case {cond.write(scope, constrain=True)} is",
                *[
                    IndentBlock(
                        [
                            f"when {value.write(scope, target_hint=cond.result)} =>",
                            IndentBlock(write_block(block)),
                        ]
                    )
                    for value, block in self._branches
                ],
                (
                    IndentBlock(["when others =>", IndentBlock("null;")])
                    if self._others is None
                    else IndentBlock(
                        ["when others =>", IndentBlock(self._others.write(scope))]
                    )
                ),
                "end case;",
            ],
        )


#
# assertations
#


class Assert(Statement):
    def __init__(self, test: Expression, message):
        self._test = test
        self._message = message

    def write(self, scope: VhdlScope) -> str:
        if self._message is None:
            return f"assert {self._test.write(scope)};"
        return f'assert {self._test.write(scope)} report "{self._message}";'


#
#
#


class InlineCode(Expression):
    def __init__(self, inline: _InlineCode, result):
        super().__init__(result)
        self.inline = inline

    def write(self, scope: VhdlScope) -> str:
        def write_content(content):
            result = ""

            for elem in content:
                if isinstance(elem, InlineVhdl.Text):
                    result += elem.text
                elif isinstance(elem, InlineVhdl.Object):
                    if elem.read:
                        result += scope.format_value(elem.obj)
                    else:
                        result += scope.format_target(elem.obj)
                elif isinstance(elem, InlineVhdl.SubCode):
                    found = False
                    for option in elem.options:
                        if isinstance(option, InlineVhdl):
                            result += write_content(option.content)
                            found = True
                            break

                    assert found, "inline code does not contain vhdl option"
                else:
                    raise AssertionError("invalid type")

            return result

        return self.inline.post_process(write_content(self.inline.content))


#
#
# instances
#
#


class VhdlScope:
    class _VectorSliceHint:
        """
        helper type used to format values
        indicates, that a BitVector was created as a slice of
        a Signed/Unsigned value
        """

        def __init__(self, start, stop):
            self.start = start
            self.stop = stop

    class Declaration:
        def __init__(self, obj, is_active=False, name_hint: str | None = None):
            self.obj = obj
            self.active: bool = is_active
            self.name_hint: str | None = name_hint

            # will be filled during setup
            self.name: str = "NOT_SET"

        def use(self):
            self.active = True

    def __init__(self, parent: VhdlScope | None = None):
        self._setup_complete = False
        self._parent = parent
        self._subscopes: list[VhdlScope] = []
        self._declarations: IdMap[typing.Any, VhdlScope.Declaration] = IdMap()
        self._used_names: set[str] = set()

        if parent is not None:
            parent._subscopes.append(self)

    def reserve_name(self, name):
        self._used_names.add(name)

    def declare(self, obj, _is_first=True, name_hint=None, *, _obj_only=False):
        type_declared = _obj_only

        # use declaration if it is required by multiple subscopes
        # (possibly overwritten by used declaration in parent scope)
        if obj in self._declarations:
            self._declarations[obj].use()

            if not _is_first:
                assert not isinstance(
                    obj, (Variable, Temporary)
                ), "variables and temporaries cannot be shared between scopes"
        else:
            if isinstance(obj, (type, Instance)):
                if _obj_only:
                    return

                if (
                    isinstance(obj, type)
                    and issubclass(obj, Array)
                    and issubclass(
                        obj._elemtype_, (cohdl_enum.Enum, cohdl_enum.DynamicEnum, Array)
                    )
                ):
                    self.declare(obj._elemtype_, True)
                    type_declared = True
            elif isinstance(obj, TypeQualifier):
                # type of signal must be declared before signal
                if (
                    issubclass(
                        obj.type, (cohdl_enum.Enum, cohdl_enum.DynamicEnum, Array)
                    )
                    and not _obj_only
                ):
                    self.declare(obj.type, True)

                if isinstance(obj, TypeQualifier) and not _obj_only:
                    for attr in obj._attributes:
                        self.declare(type(attr), name_hint=attr.name)

                type_declared = True
            else:
                # type of literals must be declared before use
                if isinstance(obj, (cohdl_enum.Enum, cohdl_enum.DynamicEnum)):
                    if not _obj_only:
                        self.declare(type(obj), True)
                        type_declared = True

                    # enumerator literals are already declared in declaration of enum type
                    return

                if isinstance(obj, type) and issubclass(obj, cohdl.Attribute):
                    pass
                else:
                    raise AssertionError(f"ignored declaration {obj}")

            # set first scope to active so it will be used if no enclosing scope
            # declares obj
            self._declarations[obj] = VhdlScope.Declaration(obj, _is_first, name_hint)

            if self._parent is not None:
                self._parent.declare(obj, False, name_hint, _obj_only=type_declared)

    def remove_declaration(self, obj):
        if obj in self._declarations:
            del self._declarations[obj]

            # loop in if because declaration can only exist in subscope
            # if it also exists in parent
            for scope in self._subscopes:
                scope.remove_declaration(obj)

    def complete_setup(self):
        assert not self._setup_complete

        declarations: IdMap[int, VhdlScope.Declaration] = IdMap()

        if self._parent is None:
            if self._used_names is None:
                used_names = set()
            else:
                used_names = set(self._used_names)
        else:
            used_names = set(self._parent._used_names) | self._used_names

        for id, decl in self._declarations.items():
            if decl.active:
                declarations[id] = decl
                for scope in self._subscopes:
                    scope.remove_declaration(id)

        self._declarations = declarations

        for id, decl in declarations.items():
            obj = decl.obj

            name: str

            override = None
            fallback = None

            if isinstance(obj, Port):
                override = obj.name()
            elif isinstance(obj, Signal):
                override = obj.name()
                fallback = "sig"
            elif isinstance(obj, Variable):
                override = obj.name()
                fallback = "var"
            elif isinstance(obj, Temporary):
                override = obj.name()
                fallback = "temp"
            elif isinstance(obj, Concurrent):
                fallback = "concurrent"
            elif isinstance(obj, Process):
                fallback = "proc"
            elif isinstance(obj, Entity):
                override = obj.name()
            elif isinstance(obj, Architecture):
                override = obj.name()
            elif isinstance(obj, EntityInst):
                fallback = "inst"
            elif isinstance(obj, type):
                if issubclass(obj, (cohdl_enum.Enum, cohdl_enum.DynamicEnum)):
                    override = obj.__name__
                elif issubclass(obj, Array):
                    fallback = "array_type"
                elif issubclass(obj, cohdl.Attribute):
                    override = obj.name
                else:
                    raise AssertionError(f"invalid obj {obj}")
            else:
                raise AssertionError(f"invalid obj {obj}")

            if override is not None:
                name = override
            elif decl.name_hint is not None:
                name = decl.name_hint
            elif fallback is not None:
                name = fallback
            else:
                raise AssertionError("Internal error, cannot name object")

            # remove leading and trailing underscores
            # since they are not allowed in vhdl
            name = name.strip("_")

            # avoid name collisions by appending counter to names
            if name.lower() in used_names:
                cnt = 1
                base_name = name
                name = base_name + str(cnt)

                while name.lower() in used_names:
                    cnt *= 2
                    name = base_name + str(cnt)

                step = cnt // 2

                while step:
                    name = base_name + str(cnt - step)

                    if name.lower() not in used_names:
                        cnt -= step

                    step //= 2

                name = base_name + str(cnt)

            decl.name = name
            used_names.add(name.lower())

        self._used_names = used_names
        self._setup_complete = True

        for scope in self._subscopes:
            scope.complete_setup()

    #
    # the following functions are valid after setup is complete
    #

    def declarations(self) -> dict:
        return {decl.name: decl.obj for decl in self._declarations.values()}

    def lookup_name(self, obj) -> str:
        if obj in self._declarations:
            return self._declarations[obj].name

        if self._parent is not None:
            return self._parent.lookup_name(obj)

        raise AssertionError(f"object {obj} not declared in scope")

    def dump(self) -> TextBlock:
        local_decl = []

        for decl in self._declarations.values():
            local_decl.append(
                f"active = {decl.active}, obj = {decl.obj}, name = {decl.name}"
            )

        return TextBlock(
            title=str(self),
            content=[*local_decl, *[sub.dump() for sub in self._subscopes]],
        )

    def _format_ref(
        self,
        obj,
        root_name,
        ref_spec: RefSpec | None,
        is_target: bool,
        constrain: bool = False,
    ):
        if isinstance(ref_spec, Offset):
            ref_spec.simplify()
            assert (
                len(ref_spec.base_offset) == 0
            ), "nested runtime variable offsets not implemented"

            result = f"{root_name}({self.format_value(ref_spec.offset, Integer())})"

            primitive_obj = TypeQualifier.decay(obj)
            obj_type = type(primitive_obj)

            if isinstance(primitive_obj, Array):
                result_type = primitive_obj._elemtype_
            else:
                assert isinstance(primitive_obj, BitVector)
                result_type = Bit

            return result, result_type

        if isinstance(ref_spec, Slice):
            ref_spec.simplify()

            assert (
                len(ref_spec.base_offset) == 0
            ), "runtime variable slices not implemented"

            if ref_spec.start >= ref_spec.stop:
                slice_result = f"{root_name}({ref_spec.start} downto {ref_spec.stop})"
            else:
                slice_result = f"{root_name}({ref_spec.start} to {ref_spec.stop})"

            width = abs(ref_spec.start - ref_spec.stop) + 1

            if is_target:
                return slice_result, BitVector[width]

            obj_type = obj.type

            if constrain:
                if issubclass(obj_type, Unsigned):
                    return f"unsigned'({slice_result})", Unsigned[width]
                if issubclass(obj_type, Signed):
                    return f"signed'({slice_result})", Signed[width]
                return f"std_logic_vector'({slice_result})", BitVector[width]

            if issubclass(obj_type, Unsigned):
                return f"unsigned({slice_result})", Unsigned[width]
            if issubclass(obj_type, Signed):
                return f"signed({slice_result})", Signed[width]
            return f"std_logic_vector({slice_result})", BitVector[width]

        raise AssertionError("error, cannot format input")

    def format_literal(self, obj) -> str:
        if isinstance(obj, (cohdl_enum.Enum, cohdl_enum.DynamicEnum)):
            return obj.name

        if isinstance(obj, bool):
            return str(obj).lower()
        if isinstance(obj, _boolean._Boolean):
            return str(obj._value).lower()
        if isinstance(obj, int):
            return str(obj)
        if isinstance(obj, str):
            return f'"{obj}"'

        if isinstance(obj, (Bit, cohdl.BitState)):
            return f"'{obj}'"
        if isinstance(obj, BitVector):
            if isinstance(obj, Unsigned):
                return f"unsigned'({self.format_literal(obj.bitvector)})"
            if isinstance(obj, Signed):
                return f"signed'({self.format_literal(obj.bitvector)})"
            return f'"{obj}"'
        if isinstance(obj, Integer):
            return f"{obj}"

        # return dummy strings for null and full values
        # replaced with actual values during cast to target type
        if obj is Null:
            return ">>NULL_LITERAL<<"
        if obj is Full:
            return ">>FULL_LITERAL>>"

        if not isinstance(obj, Array):
            assert isinstance(obj, Generic)

            obj = obj._wrapped

            if isinstance(obj, (int, float)):
                return str(obj)
            elif isinstance(obj, str):
                return f'"{obj}"'
        else:
            val = obj._value
            assert val is not None, "array has no default value"
            elemtype = obj._elemtype_

            # use ( 0 => ELEM0, 1 => ELEM1 ) notation because
            # ( ELEM0, ELEM1 ) form is not allowed for arrays with only a single element
            elemstr = [
                f"{nr} => {self.format_literal(elemtype(elem))}"
                for nr, elem in enumerate(val)
            ]

            if len(val) < obj._count_:
                elemstr.append(f"others => {self.format_literal(elemtype())}")

            return f'( {", ".join(elemstr)} )'

        raise AssertionError(f"cannot format {obj}")

    def format_declaration(self, name, obj) -> str:
        if isinstance(self, ProcessScope):
            is_signal = isinstance(obj, Signal)
            is_variable = isinstance(obj, (Variable, Temporary))
        else:
            is_signal = isinstance(obj, (Signal, Temporary))
            is_variable = False

        if is_signal or is_variable:
            type_str = "signal" if is_signal else "variable"
            attributes = []
            for attr in obj._attributes:
                attributes.append(
                    f"attribute {attr.name} of {name} : {type_str} is {self.format_literal(attr.value)};"
                )

        if isinstance(obj, type):
            if issubclass(obj, cohdl_enum.Enum):
                enumerators = list(obj.__members__.keys())
                return f"type {name} is ({', '.join(enumerators)});"
            elif issubclass(obj, cohdl_enum.DynamicEnum):
                enumerators = [member.name for member in obj.__members__]
                return f"type {name} is ({', '.join(enumerators)});"
            elif issubclass(obj, cohdl.Array):
                elemtype = obj._elemtype_

                if issubclass(elemtype, cohdl_enum.Enum):
                    first, *rest = elemtype._member_map_.values()
                    elem_obj = elemtype(first)
                else:
                    elem_obj = elemtype()

                return f"type {name} is array({0} to {obj._count_-1}) of {self.format_type(elem_obj)};"
            elif issubclass(obj, cohdl.Attribute):
                return f"attribute {obj.name} : {self.format_type(obj.attr_type)};"
            else:
                raise AssertionError(f"invalid type {obj}")

        elif is_signal:
            if not obj.has_default():
                return [f"signal {name} : {self.format_type(obj)};", *attributes]
            else:
                return [
                    f"signal {name} : {self.format_type(obj)} := {self.format_literal(obj.default())};",
                    *attributes,
                ]
        elif is_variable:
            assert isinstance(
                self, ProcessScope
            ), "variables can only be used in process scope"
            if not obj.has_default():
                return [f"variable {name} : {self.format_type(obj)};", *attributes]
            else:
                return [
                    f"variable {name} : {self.format_type(obj)} := {self.format_literal(obj.default())};",
                    *attributes,
                ]
        elif isinstance(obj, cohdl.Constant):
            return f"constant {name} : {self.format_type(obj)} := {self.format_literal(obj.get())};"

        raise AssertionError(f"invalid declaration {obj}")

    def format_declarations(self) -> list[str]:
        result = []

        for name, obj in self.declarations().items():
            if not isinstance(obj, Instance):
                decl = self.format_declaration(name, obj)

                if isinstance(decl, str):
                    result.append(decl)
                else:
                    result.extend(decl)

        return result

    def format_type(self, obj) -> str:
        if isinstance(obj, TypeQualifier):
            obj = obj.get()

        if isinstance(obj, (_boolean._Boolean)) or obj is bool:
            return "boolean"
        if isinstance(obj, Bit):
            return "std_logic"
        elif isinstance(obj, BitVector):
            if obj.order is BitOrder.DOWNTO:
                range_ = f"({obj.width - 1} downto 0)"
            else:
                range_ = f"(0 to {obj.width() - 1})"

            if isinstance(obj, Unsigned):
                type_ = "unsigned"
            elif isinstance(obj, Signed):
                type_ = "signed"
            elif isinstance(obj, BitVector):
                type_ = "std_logic_vector"
            else:
                raise AssertionError()

            return f"{type_}{range_}"
        elif isinstance(obj, (cohdl_enum.Enum, cohdl_enum.DynamicEnum)):
            return self.lookup_name(type(obj))
        elif isinstance(obj, cohdl.Array):
            return self.lookup_name(type(obj))
        elif isinstance(obj, Integer):
            assert obj.get_value() is not None
            return "integer"

        if issubclass(obj, str):
            return "string"
        if issubclass(obj, bool):
            return "boolean"
        if issubclass(obj, int):
            return "integer"

        raise AssertionError(f"cannot format {obj}")

    def format_value(self, obj, target_hint=None, constrain=False):
        if isinstance(obj, (cohdl_enum.Enum, cohdl_enum.DynamicEnum)):
            result = obj.name
        elif isinstance(obj, _PrimitiveType):
            result = self.format_literal(obj)
        elif isinstance(obj, (bool, _boolean._Boolean)):
            result = self.format_literal(obj)
        elif isinstance(obj, int):
            result = self.format_literal(obj)
        elif isinstance(obj, str):
            result = self.format_literal(obj)
        elif isinstance(obj, _NullFullType):
            result = self.format_literal(obj)
        elif isinstance(obj, cohdl.BitState):
            result = self.format_literal(obj)
        elif isinstance(obj, (list, tuple)):
            assert isinstance(target_hint, Array)
            assert len(obj) == len(target_hint)

            elem_type = target_hint._elemtype_
            elem_hint = elem_type()

            components = ", ".join(
                f"{index} => {self.format_cast(elem_hint, elem, self.format_value(elem))}"
                for index, elem in enumerate(obj)
            )
            return f"( {components} )"
        else:
            assert isinstance(obj, TypeQualifier)
            root_name = self.lookup_name(obj._root)

            if len(obj._ref_spec) == 0:
                result = self.format_vhdl_cast(obj, root_name)
            else:
                result = root_name
                parent = obj._root

                for ref in obj._ref_spec:
                    result, result_type = self._format_ref(
                        parent, result, ref, False, constrain
                    )
                    parent = ref.obj

                result = self.format_cast(obj.copy(), Signal[result_type](), result)

        if target_hint is None:
            return result

        return self.format_cast(target_hint, obj, result)

    def format_target(self, obj):
        assert isinstance(obj, (Signal, Variable, Temporary))

        root = obj._root
        result = self.lookup_name(root)
        parent = root

        for ref in obj._ref_spec:
            result, result_type = self._format_ref(parent, result, ref, True)

        return result

    def format_vhdl_cast(self, value, value_str):
        """
        perform cast so the vhdl type matches to cohdl type
        (required for bitvector/signed/unsigned properties)
        """

        if not isinstance(value, TypeQualifier):
            return value_str

        if not issubclass(value.type, BitVector):
            return value_str

        root_type = value._root.type

        if issubclass(root_type, Array):
            root_type = root_type.elemtype()

        value_type = value.type

        if root_type is value.type:
            return value_str

        if root_type.width == value_type.width:
            vhdl_type = root_type
        else:
            vhdl_type = BitVector[value_type.width]

        if issubclass(vhdl_type, Unsigned):
            if issubclass(value_type, Signed):
                return f"signed(std_logic_vector({value_str}))"
            if issubclass(value_type, BitVector):
                return f"std_logic_vector({value_str})"

        if issubclass(vhdl_type, Signed):
            if issubclass(value_type, Unsigned):
                return f"unsigned(std_logic_vector({value_str}))"
            if issubclass(value_type, BitVector):
                return f"std_logic_vector({value_str})"

        assert issubclass(vhdl_type, BitVector)

        if issubclass(value_type, Unsigned):
            return f"unsigned({value_str})"

        if issubclass(value_type, Signed):
            return f"signed({value_str})"

        raise AssertionError(f"assignment not supported {vhdl_type} -> {value.type}")

    def format_cast(self, target, value, value_str):
        """
        wrap value_str that corresponds to value in a cast function
        to make it assignable to target
        """

        target_type = type(TypeQualifier.decay(target))
        value_type = type(TypeQualifier.decay(value))

        vhdl_target_type = target_type

        if isinstance(target, TypeQualifier):
            if issubclass(target_type, BitVector):
                vhdl_target_type = type(TypeQualifier.decay(target._root))

                if target._ref_spec is not None:
                    for ref_spec in target._ref_spec:
                        if issubclass(vhdl_target_type, Array):
                            if isinstance(ref_spec, Offset):
                                vhdl_target_type = vhdl_target_type._elemtype_
                            else:
                                raise AssertionError("Array slices are not implemented")
                        else:
                            if issubclass(vhdl_target_type, Signed):
                                vhdl_target_type = Signed[target_type.width]
                            elif issubclass(vhdl_target_type, Unsigned):
                                vhdl_target_type = Unsigned[target_type.width]
                            else:
                                vhdl_target_type = BitVector[target_type.width]

        if issubclass(target_type, Bit):
            if issubclass(value_type, Bit):
                return value_str
            if issubclass(value_type, _Boolean):
                return f"cohdl_bool_to_std_logic({value_str})"
            if issubclass(value_type, _NullFullType):
                return self.format_literal(target_type(value))

        elif issubclass(target_type, (_Boolean, bool)):
            if issubclass(value_type, (_Boolean, bool)):
                return value_str
            if issubclass(value_type, Bit):
                return f"{value_str} = '1'"
            if issubclass(value_type, (Unsigned, Signed)):
                return f"({value_str} /= 0)"
            if issubclass(value_type, BitVector):
                zeros = "0" * value_type.width
                return f'({value_str} /= "{zeros}")'
            if issubclass(value_type, Integer):
                return f"({value_str} /= 0)"

        elif issubclass(target_type, BitVector):
            if issubclass(value_type, _NullFullType) or isinstance(value, BitVector):
                return self.format_literal(vhdl_target_type(value))

            if issubclass(value_type, Integer):
                if issubclass(target_type, Unsigned):
                    value_str = f"to_unsigned({value_str}, {target_type.width})"

                    if issubclass(vhdl_target_type, Unsigned):
                        return value_str
                    elif issubclass(vhdl_target_type, Signed):
                        return f"signed(std_logic_vector({value_str}))"
                    else:
                        return f"std_logic_vector({value_str})"

                elif issubclass(target_type, Signed):
                    value_str = f"to_signed({value_str}, {target_type.width})"

                    if issubclass(vhdl_target_type, Signed):
                        return value_str
                    elif issubclass(vhdl_target_type, Unsigned):
                        return f"unsigned(std_logic_vector({value_str}))"
                    else:
                        return f"std_logic_vector({value_str})"

                raise AssertionError("invalid target for integer assignment")

            if issubclass(vhdl_target_type, Unsigned):
                if issubclass(value_type, Unsigned):
                    if target_type.width == value_type.width:
                        return value_str
                    else:
                        assert target_type.width > value_type.width
                        return f"resize({value_str}, {target_type.width})"
                elif issubclass(value_type, Signed):
                    if issubclass(target_type, Signed):
                        if target_type.width != value_type.width:
                            assert target_type.width > value_type.width
                            value_str = f"resize({value_str}, {target_type.width})"
                    else:
                        assert target_type.width == value_type.width

                    return f"unsigned(std_logic_vector({value_str}))"
                else:
                    assert issubclass(value_type, BitVector)
                    assert target_type.width == value_type.width
                    return f"unsigned({value_str})"

            if issubclass(vhdl_target_type, Signed):
                if issubclass(value_type, Signed):
                    if target_type.width == value_type.width:
                        return value_str
                    else:
                        assert target_type.width > value_type.width
                        return f"resize({value_str}, {target_type.width})"
                elif issubclass(value_type, Unsigned):
                    if issubclass(target_type, Unsigned):
                        if target_type.width != value_type.width:
                            assert target_type.width > value_type.width
                            value_str = f"resize({value_str}, {target_type.width})"
                    elif issubclass(target_type, Signed):
                        assert target_type.width >= value_type.width
                        value_str = f"resize({value_str}, {target_type.width})"
                    else:
                        assert target_type.width == value_type.width

                    return f"signed(std_logic_vector({value_str}))"
                else:
                    assert issubclass(value_type, BitVector)
                    assert target_type.width == value_type.width
                    return f"signed({value_str})"

            if issubclass(vhdl_target_type, BitVector):
                if issubclass(value_type, Signed):
                    if issubclass(target_type, Signed):
                        if target_type.width != value_type.width:
                            assert target_type.width > value_type.width
                            value_str = f"resize({value_str}, {target_type.width})"
                    else:
                        assert not issubclass(target_type, Unsigned)
                        assert target_type.width == value_type.width

                    return f"std_logic_vector({value_str})"

                elif issubclass(value_type, Unsigned):
                    if issubclass(target_type, Unsigned):
                        if target_type.width != value_type.width:
                            assert target_type.width > value_type.width
                            value_str = f"resize({value_str}, {target_type.width})"
                    elif issubclass(target_type, Signed):
                        assert target_type.width > value_type.width
                        value_str = f"resize({value_str}, {target_type.width})"
                    else:
                        assert target_type.width == value_type.width

                    return f"std_logic_vector({value_str})"

                else:
                    assert issubclass(value_type, BitVector)
                    assert target_type.width == value_type.width
                    return value_str

            raise AssertionError(
                f"invalid {vhdl_target_type} - {target_type} - {value_type}"
            )

        elif issubclass(target_type, Integer):
            if issubclass(value_type, (Integer, int)):
                return value_str
            if issubclass(value_type, (Signed, Unsigned)):
                return f"to_integer({value_str})"

        elif issubclass(target_type, (cohdl_enum.Enum, cohdl_enum.DynamicEnum)):
            assert target_type is value_type
            return value_str

        elif issubclass(target_type, Array):
            assert issubclass(value_type, Array)
            assert target_type._elemtype_ is value_type._elemtype_
            return value_str

        raise AssertionError(f"error cannot convert from {value_type} to {target_type}")


class ProcessScope(VhdlScope):
    def declare(self, obj, _is_first=True, name_hint=None):
        # signals can't be declared in process scope
        if isinstance(obj, Signal) or isinstance(obj, Instance):
            assert self._parent is not None
            self._parent.declare(obj, True, name_hint)
        else:
            super().declare(obj, _is_first, name_hint)


class ModuleScope(VhdlScope):
    # source: https://redirect.cs.umbc.edu/portal/help/VHDL/reserved.html
    _vhdl_reserved = {
        "abs",
        "access",
        "after",
        "alias",
        "all",
        "and",
        "architecture",
        "array",
        "assert",
        "attribute",
        "begin",
        "block",
        "body",
        "buffer",
        "bus",
        "case",
        "component",
        "configuration",
        "constant",
        "disconnect",
        "downto",
        "else",
        "elsif",
        "end",
        "entity",
        "exit",
        "file",
        "for",
        "function",
        "generate",
        "generic",
        "group",
        "guarded",
        "if",
        "impure",
        "in",
        "inertial",
        "inout",
        "is",
        "label",
        "library",
        "linkage",
        "literal",
        "loop",
        "map",
        "mod",
        "nand",
        "new",
        "next",
        "nor",
        "not",
        "null",
        "of",
        "on",
        "open",
        "or",
        "others",
        "out",
        "package",
        "port",
        "postponed",
        "procedure",
        "process",
        "pure",
        "range",
        "record",
        "register",
        "reject",
        "rem",
        "report",
        "return",
        "rol",
        "ror",
        "select",
        "severity",
        "signal",
        "shared",
        "sla",
        "sll",
        "sra",
        "srl",
        "subtype",
        "then",
        "to",
        "transport",
        "type",
        "unaffected",
        "units",
        "until",
        "use",
        "variable",
        "wait",
        "when",
        "while",
        "with",
        "xnor",
        "xor",
        "default",
    }

    _additional_reserved = {
        "std_logic",
        "std_logic_vector",
        "signed",
        "unsigned",
        "resize",
    }

    def __init__(self):
        super().__init__()

        self._used_names = self._vhdl_reserved | self._additional_reserved


class EntityScope(VhdlScope): ...


class ArchScope(VhdlScope): ...


class AliasScope:
    def __init__(self, baseObject):
        self.__class__ = type(
            baseObject.__class__.__name__, (self.__class__, baseObject.__class__), {}
        )

        self.__dict__ = baseObject.__dict__
        self.__class__._alias_map_ = IdMap()  # type: ignore

    def set_alias(self, obj, replacement):
        self.__class__._alias_map_[obj] = replacement  # type: ignore

    def lookup_name(self, obj) -> str:
        if obj in self.__class__._alias_map_:  # type: ignore
            obj = self.__class__._alias_map_[obj]  # type: ignore
        return super().lookup_name(obj)  # type: ignore


class Instance:
    def __init__(self, scope: VhdlScope):
        self._scope = scope

    def scope(self):
        return self._scope

    @abstractmethod
    def write(self): ...

    def dump(self):
        return self.write()

    def sub_entities(self) -> IdSet[Entity]:
        return IdSet()


class Entity(Instance):
    def __init__(
        self,
        info: EntityInfo,
        parent_scope: VhdlScope,
        instances: list[Instance],
    ):
        super().__init__(EntityScope(parent_scope))
        parent_scope.declare(self)

        attributes = info.attributes

        sub_entities = IdSet()
        sub_entities.update(
            [
                inst
                for inst in instances
                if isinstance(inst, EntityInst) and not inst.extern()
            ]
        )

        self._name = info.name
        self._instances: list[Instance] = instances
        self._ports = info.ports
        self._generics = info.generics
        self._sub_entities = sub_entities
        self._path = "work" if "path" not in attributes else attributes["path"]
        self._extern = info.extern

        if info.extern:
            self._arch_name = attributes.get("arch_name", None)
        else:
            self._arch_name = attributes.get("arch_name", f"arch_{info.name}")

        self._arch: Architecture | None = None

    def architecture(self):
        assert self._arch is not None
        return self._arch

    def name(self):
        return self._name

    def path(self):
        return self._path

    def extern(self):
        return self._extern

    def sub_entities(self):
        return self._sub_entities

    def ports(self) -> dict[str, Port]:
        return self._ports

    def add_block(self, block: Block):
        self._blocks.append(block)

    def _generic_declarations(self) -> list[str]:
        raise AssertionError(
            "not implemented, generics can only be used when instantiating external entities"
        )

    def _port_declarations(self) -> list[str]:
        ret = []

        for name, port in self._ports.items():
            direction = port.direction()
            obj = port.get()

            if direction.is_input():
                dir_str = "in"
            elif direction.is_output():
                dir_str = "out"
            elif direction.is_inout():
                dir_str = "inout"
            else:
                raise AssertionError("invalid direction")

            ret.append(f"{name} : {dir_str} {self._scope.format_type(obj)};")

        if len(ret) != 0:
            # remove terminating semicolon
            ret[-1] = ret[-1][:-1]

        return ret

    def _generic_map(self) -> TextBlock:
        return TextBlock(
            title="generic (", content=[self._generic_declarations(), ");"]
        )

    def _port_map(self) -> TextBlock:
        return TextBlock(title="port (", content=[self._port_declarations(), ");"])

    def _library_declaration(self) -> TextBlock:
        extern_libraries = set()

        for entity in self._sub_entities:
            assert isinstance(entity, EntityInst)
            path = entity._entity.path()
            if path is not None and path != "work":
                lib_name = path.split(".")[0]
                extern_libraries.update([f"library {lib_name.lower()};"])

        return TextBlock(
            [
                "library ieee;",
                "use ieee.std_logic_1164.all;",
                "use ieee.numeric_std.all;",
                *extern_libraries,
            ]
        )

    def _entity_declaration(self) -> TextBlock:
        return TextBlock(
            [
                f"entity {self._name} is",
                IndentBlock(self._port_map()),
                f"end {self._name};",
            ]
        )

    def write(self) -> TextBlock:
        assert self._arch is not None

        return TextBlock(
            [
                self._library_declaration(),
                "\n",
                self._entity_declaration(),
                "\n",
                self._arch.write(),
            ],
        ).dump()


class Architecture(Instance):
    def __init__(self, scope: ArchScope, entity: Entity, instances: list[Instance]):
        super().__init__(scope)
        self._entity = entity
        self._instances = instances

    def name(self) -> str:
        hint = self._entity._arch_name

        if hint is None:
            return f"arch_{self._entity.name()}"
        return hint

    def arch_name(self):
        return self._scope.lookup_name(self)

    def entity_name(self):
        return self._scope.lookup_name(self._entity)

    def write_declarations(self):
        return self._scope.format_declarations()

    def write_instances(self):
        return [inst.write() for inst in self._instances]

    def write(self) -> TextBlock:
        return TextBlock(
            [
                f"architecture {self.arch_name()} of {self.entity_name()} is",
                # TODO cleanup
                IndentBlock(
                    [
                        *[
                            "function cohdl_bool_to_std_logic(inp: boolean) return std_logic is",
                            "begin",
                            "  if inp then",
                            "    return('1');",
                            "  else",
                            "    return('0');",
                            "  end if;",
                            "end function cohdl_bool_to_std_logic;",
                        ],
                        *self.write_declarations(),
                    ],
                ),
                "begin",
                IndentBlock(self.write_instances()),
                f"end architecture {self.arch_name()};",
            ]
        )


class Block(Instance):
    def __init__(
        self,
        parent_scope: VhdlScope,
        subblocks: list[Instance],
        name: str | None,
        attributes: dict,
    ):
        # use parent scope because declaration at block level is not supported
        super().__init__(parent_scope)

        self._subblocks = subblocks
        self._name = name
        self._attributes = attributes

    def sub_entities(self) -> IdSet[Entity]:
        return IdSet.union(*[subblock.sub_entities() for subblock in self._subblocks])

    def write(self) -> TextBlock:
        return TextBlock(
            [
                *([f"-- Block ({self._name})"] if self._name is not None else []),
                *comment_list(self._attributes.get("comment", None)),
                *[subblock.write() for subblock in self._subblocks],
                "\n",
            ],
        )


class Concurrent(Instance):
    def __init__(
        self,
        parent_scope: VhdlScope,
        stmts: list[Statement],
        name: str,
        attributes: dict,
    ):
        # use parent scope because declaration at concurrent level is not supported
        super().__init__(parent_scope)

        self._stmts = stmts
        self._name = name
        self._attributes = attributes

    def write(self) -> TextBlock:
        if self._name is None:
            return TextBlock(
                [
                    *comment_list(self._attributes.get("comment", None)),
                    *[stmt.write(self._scope) for stmt in self._stmts],
                ],
            )

        return TextBlock(
            [
                f"",
                f"-- CONCURRENT BLOCK ({self._name})",
                *comment_list(self._attributes.get("comment", None)),
                *[stmt.write(self._scope) for stmt in self._stmts],
            ],
        )


class Process(Instance):
    def __init__(
        self,
        scope: ProcessScope,
        code: CodeBlock,
        sensitivity: _SensitivitySpec,
        attributes: dict,
    ):
        super().__init__(scope)

        self._sensitivity = sensitivity
        self._code = code
        self._attributes = attributes

    def _write_declarations(self) -> list[str]:
        return self._scope.format_declarations()

    def _write_header(self) -> TextBlock:
        if isinstance(self._sensitivity, _SensitivityAll):
            sensitivity_list = "all"
        else:
            assert isinstance(self._sensitivity, _SensitivityList)
            sensitivity_list = ", ".join(
                self._scope.format_value(item) for item in self._sensitivity.signals
            )

        proc_name = self._scope.lookup_name(self)

        return TextBlock(
            content=[
                f"{proc_name}: process({sensitivity_list})",
                IndentBlock(self._write_declarations()),
            ],
        )

    def _write_body(self) -> TextBlock:
        return TextBlock(["begin", IndentBlock(self._code.write(self._scope, True))])

    def _write_end(self) -> str:
        return f"end process;"

    def write(self) -> TextBlock:
        return TextBlock(
            [
                "\n",
                *comment_list(self._attributes.get("comment", None)),
                self._write_header(),
                self._write_body(),
                self._write_end(),
            ],
        )


class EntityInst(Instance):
    def __init__(
        self,
        parent_scope: VhdlScope,
        entity: Entity,
        ports: dict[str, Signal],
        generics: dict[str, Any],
    ):
        super().__init__(parent_scope)

        parent_scope.declare(self, name_hint=f"comp_{entity.name()}")

        self._entity = entity
        self._ports = ports
        self._generics = generics

    def extern(self) -> bool:
        return self._entity.extern()

    def sub_entities(self) -> IdSet[Entity]:
        if self.extern():
            return IdSet()

        result = IdSet.union(self._entity.sub_entities())
        result.update([self._entity])
        return result

    def _generic_map(self) -> list[str]:
        entity = self._entity
        if len(entity._generics) == 0:
            return []

        generic_map: list[Tuple[str, str]] = []

        for generic_name in entity._generics:
            generic_map.append(
                (
                    generic_name,
                    self._scope.format_value(
                        self._generics[generic_name],
                    ),
                )
            )

        line_end = [","] * (len(generic_map) - 1) + [""]

        return [
            "generic map(",
            *[
                f"{port_name} => {local}{sep}"
                for (port_name, local), sep in zip(generic_map, line_end)
            ],
            ");",
        ]

    def _port_map(self) -> list[str]:
        if len(self._ports) == 0:
            return []

        port_map: list[Tuple[str, str]] = []

        for port_name in self._entity.ports():
            port_map.append(
                (port_name, self._scope.format_target(self._ports[port_name]))
            )

        line_end = [","] * (len(port_map) - 1) + [""]

        return [
            "port map(",
            *[
                f"{port_name} => {local}{sep}"
                for (port_name, local), sep in zip(port_map, line_end)
            ],
            ");",
        ]

    def write(self) -> TextBlock:
        port_map: list[Tuple[str, str]] = []

        for port_name in self._entity.ports():
            port_map.append(
                (port_name, self._scope.format_value(self._ports[port_name]))
            )

        entity_name = self._entity._name
        arch_name = self._entity._arch_name
        arch_spec = "" if arch_name is None else f"({arch_name})"
        path = self._entity._path

        comp_name = self._scope.lookup_name(self)

        return TextBlock(
            title=f"{comp_name}: entity {path}.{entity_name}{arch_spec}",
            content=[*self._generic_map(), *self._port_map()],
        )


import os


class Library(Instance):
    @staticmethod
    def from_top_entity(top_entity: Entity):
        entities = IdSet()

        def collect_subenties(parent_entity):
            for entity_inst in parent_entity.sub_entities():
                entity = entity_inst._entity
                entities.add(entity)
                collect_subenties(entity)

        collect_subenties(top_entity)

        return Library(
            top_entity,
            [top_entity, *entities],
            parent_scope=VhdlScope(),
        )

    def __init__(self, top_entity: Entity, entities: list[Entity], parent_scope):
        super().__init__(parent_scope)
        self._top_entity = top_entity
        self._entities: list[Entity] = entities

    def top_entity(self):
        return self._top_entity

    def write(self):
        return TextBlock([entity.write() for entity in self._entities]).dump()

    def write_dir(self, path):
        file_list = []

        for entity in self._entities:
            file_path = os.path.join(path, f"{entity.name()}.vhd")
            file_list.append(file_path)

            with open(file_path, "w") as file:
                print(entity.write(), file=file)

        return file_list
