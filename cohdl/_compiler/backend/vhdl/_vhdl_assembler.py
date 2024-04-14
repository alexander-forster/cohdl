from __future__ import annotations

import enum

from cohdl._core._ir import repr as ir
from cohdl._core._type_qualifier import (
    Signal,
    Temporary,
    Port,
    TypeQualifier,
)
from cohdl.utility import IdMap
from cohdl.utility.id_map import IdSet

from cohdl._core._inline import InlineRaw, InlineVhdl
from cohdl._core._intrinsic import _SensitivityAll, _SensitivityList

from . import _vhdl_repr as vhdl


def assign_temporary(target, source: vhdl.Expression, kwargs):
    ctx: Context = kwargs["context"]
    assert isinstance(target, (Temporary, Signal))

    if ctx is Context.CONCURRENT:
        # temporaries in concurrent statements are implemented as Signals
        return vhdl.SignalAssignment(vhdl.Target(target), source)
    else:
        return vhdl.VariableAssignment(vhdl.Target(target), source)


class _StmtAssembler:
    @staticmethod
    def convert_statement(stmt: ir.Statement, *args, **kwargs):
        return _StmtAssembler().apply(stmt, *args, **kwargs)

    #
    #
    #
    #

    def apply(self, inp, *args, **kwargs):
        if isinstance(
            inp, (ir.SignalAssignment | ir.SignalPush | ir.VariableAssignment)
        ):
            ctx: Context = kwargs["context"]

            if isinstance(inp, ir.SignalAssignment):
                is_signal_assign = True
            elif isinstance(inp, ir.SignalPush):
                assert ctx is Context.SEQUENTIAL
                is_signal_assign = True
            elif isinstance(inp, ir.VariableAssignment):
                assert (
                    ctx is Context.SEQUENTIAL
                ), "variable assignment only possible in sequential contexts"
                is_signal_assign = False
            else:
                raise AssertionError()

            if is_signal_assign:
                return vhdl.SignalAssignment(
                    vhdl.Target(inp._target), vhdl.Value(inp._source)
                )
            else:
                return vhdl.VariableAssignment(
                    vhdl.Target(inp._target), vhdl.Value(inp._source)
                )

        if isinstance(inp, ir.Nop):
            return vhdl.Nop()

        if isinstance(inp, ir.Comment):
            return vhdl.Comment(inp.lines)

        if isinstance(inp, ir.BinOp):
            return assign_temporary(
                inp.result(),
                vhdl.BinOp(
                    inp._op,
                    vhdl.Value(inp._lhs),
                    vhdl.Value(inp._rhs),
                    inp.result(),
                ),
                kwargs,
            )

        if isinstance(inp, ir.UnaryOp):
            return assign_temporary(
                inp.result(),
                vhdl.UnaryOp(inp._op, vhdl.Value(inp._arg), inp.result()),
                kwargs,
            )

        if isinstance(inp, ir.Compare):
            return assign_temporary(
                inp.result(),
                vhdl.Compare(
                    inp._op,
                    vhdl.Value(inp._lhs),
                    vhdl.Value(inp._rhs),
                    inp.result(),
                ),
                kwargs,
            )

        if isinstance(inp, ir.Boolean):
            return assign_temporary(
                inp.result(), vhdl.Boolean(vhdl.Value(inp._arg)), kwargs
            )

        if isinstance(inp, ir.All):
            return assign_temporary(
                inp.result(),
                vhdl.All([vhdl.Value(arg) for arg in inp._args], inp.result()),
                kwargs,
            )

        if isinstance(inp, ir.Any):
            return assign_temporary(
                inp.result(),
                vhdl.Any([vhdl.Value(arg) for arg in inp._args], inp.result()),
                kwargs,
            )

        if isinstance(inp, ir.CodeBlock):
            return vhdl.CodeBlock(
                [self.apply(stmt, **kwargs) for stmt in inp.content()]
            )

        if isinstance(inp, ir.If):

            def conv(ev: ir.Event | ir.EventGroup):
                if isinstance(ev, ir.Event):
                    return vhdl.Event(vhdl.Value(ev.sig), ev.event_type)
                else:
                    if ev.operation is ir.EventGroup.Operation.AND:
                        return vhdl.All([conv(e) for e in ev.events], True)
                    else:
                        return vhdl.Any([conv(e) for e in ev.events], True)

            if isinstance(inp._test, (ir.Event, ir.EventGroup)):
                test = conv(inp._test)
            else:
                test = vhdl.Boolean(vhdl.Value(inp._test))

            return vhdl.If(
                test,
                self.apply(inp._body, **kwargs),
                self.apply(inp._orelse, **kwargs),
            )

        if isinstance(inp, ir.SelectWith):
            if inp._default is None:
                default = None
            else:
                default = vhdl.Value(inp._default)

            use_case_when = kwargs["context"] is Context.SEQUENTIAL

            if use_case_when:
                result = inp.result()

                if isinstance(result, Signal):
                    Assignment = vhdl.SignalAssignment
                else:
                    Assignment = vhdl.VariableAssignment

                if default is not None:
                    default = vhdl.CodeBlock([Assignment(vhdl.Target(result), default)])

                return vhdl.CaseWhen(
                    vhdl.Value(inp._arg),
                    [
                        (
                            vhdl.Constant(branch[0]),
                            vhdl.CodeBlock(
                                [Assignment(vhdl.Target(result), vhdl.Value(branch[1]))]
                            ),
                        )
                        for branch in inp._branches
                    ],
                    default,
                )

            return vhdl.SelectWith(
                vhdl.Value(inp._arg),
                [
                    (vhdl.Constant(branch[0]), vhdl.Value(branch[1]))
                    for branch in inp._branches
                ],
                default,
                vhdl.Target(inp.result()),
            )

        if isinstance(inp, ir.CaseWhen):
            branches = []

            for branch in inp._branches:
                cond = vhdl.Constant(branch.cond)
                code = self.apply(branch.code, **kwargs)

                branches.append((cond, code))

            if inp._default is None:
                default = None
            else:
                default = self.apply(inp._default, **kwargs)

            return vhdl.CaseWhen(vhdl.Value(inp._value), branches, default)

        if isinstance(inp, ir.Assert):
            return vhdl.Assert(vhdl.Boolean(vhdl.Value(inp._cond)), inp._msg)

        if isinstance(inp, ir.InlineCode):
            for option in inp.options:
                if isinstance(option, (InlineRaw, InlineVhdl)):
                    if inp.result is not None:
                        return assign_temporary(
                            inp.result, vhdl.InlineCode(option, inp.result), kwargs
                        )
                    else:
                        return vhdl.InlineCode(option, inp.result)

            raise AssertionError("no vhdl option for the inline code exists")

        raise AssertionError(f"cannot convert {inp}")


#
#
#
# instances
#
#
#


class Context(enum.Enum):
    SEQUENTIAL = enum.auto()
    CONCURRENT = enum.auto()


class VhdlAssembler:
    def __init__(self):
        self._known_templates: IdMap[ir.EntityTemplate, vhdl.Entity] = IdMap()
        self._stmt_assembler = _StmtAssembler()

    def convert_stmt(self, stmt, **kwargs):
        return self._stmt_assembler.apply(stmt, **kwargs)

    def _get_known_templates(self):
        return self._known_templates

    def _add_template(self, inp, ret):
        assert inp not in self._known_templates
        self._known_templates[inp] = ret

    #
    #
    #
    #

    def apply(self, inp, **kwargs):
        if isinstance(inp, ir.Entity):
            scope = kwargs["parent_scope"]

            for val in inp.get_ports().values():
                scope.declare(val._root)

            # call convert template to add it to
            # the list of vhdl Entities
            entity = self.apply(inp.get_template(), scope=scope)

            return vhdl.EntityInst(scope, entity, inp.get_ports(), inp.get_generics())

        if isinstance(inp, ir.EntityTemplate):
            if inp in self._get_known_templates():
                return self._get_known_templates()[inp]

            module_scope = vhdl.ModuleScope()
            entity_scope = vhdl.EntityScope(module_scope)
            arch_scope = vhdl.ArchScope(entity_scope)

            output_ports = []

            for name, port in inp.port_declarations().items():
                entity_scope.declare(port, name_hint=name)

                if port.direction() == Port.Direction.OUTPUT:
                    output_ports.append(port)

            for name, generic in inp.generic_declarations().items():
                entity_scope.declare(generic, name_hint=name)

            if "reserved_names" in inp._attributes:
                reserved_names = inp._attributes["reserved_names"]

                for name in reserved_names:
                    arch_scope.reserve_name(name)

            blocks = []

            # search buffer ports
            buffer_ports = output_ports
            # create buffer signals
            buffer_assignments = []

            alias_scope = vhdl.AliasScope(arch_scope)

            for port in buffer_ports:
                if port.has_default():
                    buffer = Signal[port.type](
                        port.default(),
                        name=(
                            f"buffer{port.name()}"
                            if port.name().endswith("_")
                            else f"buffer_{port.name()}"
                        ).strip("_"),
                    )
                else:
                    buffer = Signal[port.type](
                        name=(
                            f"buffer{port.name()}"
                            if port.name().endswith("_")
                            else f"buffer_{port.name()}"
                        ).strip("_")
                    )

                buffer_assignments.append(
                    vhdl.SignalAssignment(vhdl.Target(port), vhdl.Value(buffer))
                )

                arch_scope.declare(buffer)
                alias_scope.set_alias(port, buffer)

            # assign buffer to port
            # use buffer instead of port

            blocks.append(
                vhdl.Concurrent(arch_scope, buffer_assignments, "buffer assignment", {})
            )

            # convert subblocks
            for block in inp.subblocks():
                blocks.append(
                    self.apply(block, **{**kwargs, "parent_scope": alias_scope})
                )

            for ctx in inp.contexts():
                blocks.append(
                    self.apply(ctx, **{**kwargs, "parent_scope": alias_scope})
                )

            ret = vhdl.Entity(inp.info(), alias_scope, blocks)  # type: ignore

            arch = vhdl.Architecture(alias_scope, ret, blocks)
            entity_scope.declare(arch)
            ret._arch = arch

            self._add_template(inp, ret)

            module_scope.complete_setup()

            return ret

        if isinstance(inp, ir.Block):
            return vhdl.Block(
                kwargs["parent_scope"],
                [self.apply(subblock, **kwargs) for subblock in inp.subblocks()]
                + [self.apply(ctx, **kwargs) for ctx in inp.contexts()],
                name=inp.name(),
                attributes=inp._attributes,
            )

        if isinstance(inp, ir.Concurrent):
            parent_scope: vhdl.VhdlScope = kwargs["parent_scope"]

            def collect_objects(obj, access):
                if isinstance(obj, TypeQualifier):
                    parent_scope.declare(obj._root)
                return obj

            inp.code().visit_referenced_objects(collect_objects)

            return vhdl.Concurrent(
                parent_scope,
                [
                    _StmtAssembler.convert_statement(
                        stmt, **{**kwargs, "context": Context.CONCURRENT}
                    )
                    for stmt in inp.code().content()
                ],
                inp.name(),
                inp.attributes,
            )

        if isinstance(inp, ir.Sequential):
            parent_scope: vhdl.VhdlScope = kwargs["parent_scope"]
            scope = vhdl.ProcessScope(parent_scope)

            def collect_objects(obj, access):
                if isinstance(obj, TypeQualifier):
                    scope.declare(obj._root)
                return obj

            inp.visit_referenced_objects(collect_objects)

            kwargs = {**kwargs, "context": Context.SEQUENTIAL}

            code = vhdl.CodeBlock(
                [self.convert_stmt(inp._code, context=Context.SEQUENTIAL)]
            )

            #
            #
            #

            proc_name = inp.name()

            if proc_name is None:
                proc_name = "process"

            # since process(all) is not supported prior to VHDL-2008
            # instead search for all signals, that are read in the process
            # and specify them explicitly in the sensitivity list
            if isinstance(inp._sensitivity, _SensitivityAll):
                read_roots = IdSet()

                def find_read_roots(obj, access: ir.AccessFlags):
                    if access is ir.AccessFlags.READ and isinstance(obj, Signal):
                        read_roots.add(obj._root)
                    return obj

                inp.visit_referenced_objects(find_read_roots)

                sensitivity = _SensitivityList(read_roots)
            else:
                sensitivity = inp._sensitivity

            proc = vhdl.Process(scope, code, sensitivity, inp.attributes)
            parent_scope.declare(proc, name_hint=proc_name)

            if inp._always_expr is not None:
                concurrent = vhdl.Concurrent(
                    scope,
                    [
                        self.convert_stmt(
                            inp._always_expr.code(), context=Context.CONCURRENT
                        )
                    ],
                    f"always - {proc_name}",
                    {},
                )

                return vhdl.Block(
                    scope,
                    [
                        concurrent,
                        proc,
                    ],
                    None,
                    {},
                )

            return proc


class VhdlMakeLibrary:
    def apply(self, inp):
        assert isinstance(inp, vhdl.Instance)
        return vhdl.Library.from_top_entity(inp)
