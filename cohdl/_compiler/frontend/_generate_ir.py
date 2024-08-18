from __future__ import annotations

import enum
from typing import Any

from cohdl._core._ir import _repr as ir
from cohdl._core._ir import AccessFlags

from . import _prepare_ast_out as out
from ._traceback import pretty_traceback_active
from cohdl._core._primitive_type import is_primitive


from cohdl._core import (
    _boolean,
    Bit,
    _type_qualifier,
    Signal,
    Temporary,
    Variable,
    Null,
)
from cohdl._core._intrinsic_operations import AssignMode

from cohdl.utility import IdMap, IdSet


class IrGenerator:
    class Mode(enum.Enum):
        CONCURRENT = enum.auto()
        SEQUENTIAL = enum.auto()
        BLOCK = enum.auto()

    @staticmethod
    def convert_sequential(inp: out.Sequential):
        assert (
            not inp.code().returns()
        ), f"return from top level sequential function not possible"

        converter = IrGenerator(IrGenerator.Mode.SEQUENTIAL)
        converter.apply(inp.code(), open_blocks=[converter.code()])

        always_expr = None

        if len(inp.always_expr()) != 0:
            always_converter = IrGenerator(IrGenerator.Mode.CONCURRENT)
            always_converter.apply(
                inp.always_expr(), open_blocks=[always_converter.code()]
            )

            # concurrent block for always assignments
            concurrent = ir.Concurrent("always", always_converter.code(), {}, None)

            temp_replacement = IdMap()

            def find_temporaries(obj, access: AccessFlags):
                if isinstance(obj, Temporary):
                    parent = obj._root

                    if access.is_written():
                        temp_replacement[parent] = Signal[parent.type]()
                    elif parent not in temp_replacement:
                        raise AssertionError(
                            f"always expression cannot inherit temporaries (found {obj._root})"
                        )
                return obj

            def replace_temporaries(obj, access: AccessFlags):
                if isinstance(obj, Temporary):
                    parent = obj._root
                    if parent in temp_replacement:
                        return Signal[obj.type](
                            obj.type(),
                            _root=temp_replacement[parent],
                            _ref_spec=obj._ref_spec,
                        )

                return obj

            # replace temporaries in always expression
            # with signals, this is required, because
            # only signals can be shared between blocks
            # and the result must be available in the
            # sequential context
            concurrent.visit_referenced_objects(find_temporaries)

            concurrent.visit_referenced_objects(replace_temporaries)
            converter.code().visit_referenced_objects(replace_temporaries)

            always_expr = concurrent

        return ir.Sequential(
            inp.name(),
            converter.code(),
            always_expr,
            inp.sensitivity(),
            inp.attributes(),
            inp.source_location(),
        )

    @staticmethod
    def convert_concurrent(inp: out.Concurrent):
        converter = IrGenerator(IrGenerator.Mode.CONCURRENT)
        converter.apply(inp.code(), open_blocks=[converter.code()])

        return ir.Concurrent(
            inp.name(), converter.code(), inp.attributes(), inp.source_location()
        )

    def __init__(
        self,
        mode: IrGenerator.Mode,
    ):
        super().__init__()
        self._mode = mode
        self._code = ir.CodeBlock([], parent=None)
        self._sensitivity = []

    def code(self):
        return self._code

    def add_sensitivity(self, sensitivity):
        assert self._mode is IrGenerator.Mode.SEQUENTIAL
        self._sensitivity.append(sensitivity)

    def _convert_bound(self, inp: out.Statement, open_blocks: list[ir.CodeBlock]):
        for bound in inp.bound_statements():
            open_blocks = self.apply(bound, open_blocks=open_blocks)

        return open_blocks

    _break_result: list[ir.CodeBlock] = []
    _continue_result: list[ir.CodeBlock] = []

    # list of code blocks in the function, that ended in return
    # not open during rest of function
    # must be added to open blocks after end of function
    returned_blocks: list[ir.CodeBlock] = []

    #
    #
    #
    #

    def apply(self, inp: out.Statement, open_blocks: list[ir.CodeBlock]):
        prev_frame = ir.Statement._current_frame

        try:
            ir.Statement._current_frame = inp._frame
        except AttributeError:
            pass

        result = self._apply_impl(inp, open_blocks)

        ir.Statement._current_frame = prev_frame

        return result

    def _apply_impl(self, inp, open_blocks: list[ir.CodeBlock]):
        if isinstance(inp, out.Statement) and not isinstance(
            inp, (out.While, out.Await)
        ):
            open_blocks = self._convert_bound(inp, open_blocks)

        if isinstance(inp, out.Assign):
            target = inp.target()
            value = inp.value()
            mode = inp._mode

            if mode is AssignMode.AUTO:
                if isinstance(target, Signal):
                    mode = AssignMode.NEXT
                elif isinstance(target, Temporary):
                    mode = AssignMode._TEMP
                elif isinstance(target, Variable):
                    mode = AssignMode.VALUE
                else:
                    raise AssertionError("invlaid target")

            if mode is AssignMode.NEXT:
                for block in open_blocks:
                    block.append(ir.SignalAssignment(target, value))
            elif mode is AssignMode.PUSH:
                for block in open_blocks:
                    block.append(ir.SignalPush(target, value))
            elif mode is AssignMode.VALUE:
                for block in open_blocks:
                    block.append(ir.VariableAssignment(target, value))
            elif mode is AssignMode._TEMP:
                if self._mode is IrGenerator.Mode.SEQUENTIAL:
                    for block in open_blocks:
                        block.append(ir.VariableAssignment(target, value))
                else:
                    assert self._mode is IrGenerator.Mode.CONCURRENT
                    for block in open_blocks:
                        block.append(ir.SignalAssignment(target, value))
            else:
                raise AssertionError(f"invalid AssignMode {mode}")

            return open_blocks

        if isinstance(inp, out.SignalAlias):
            for block in open_blocks:
                block.append(ir._SignalAlias(inp._signal, inp._replacement))

            return open_blocks

        if isinstance(inp, out.UnaryOp):
            op = inp._op
            arg = inp._arg
            result = inp.result()

            open_blocks = self.apply(arg, open_blocks=open_blocks)

            for block in open_blocks:
                block.append(ir.UnaryOp(op, arg.result(), result))

            return open_blocks

        if isinstance(inp, out.BinOp):
            op = inp._op
            lhs = inp._lhs
            rhs = inp._rhs
            result = inp.result()

            open_blocks = self.apply(lhs, open_blocks=open_blocks)
            open_blocks = self.apply(rhs, open_blocks=open_blocks)

            for block in open_blocks:
                block.append(ir.BinOp(op, lhs.result(), rhs.result(), result))

            return open_blocks

        if isinstance(inp, out.Compare):
            op = inp._op
            lhs = inp._lhs
            rhs = inp._rhs

            open_blocks = self.apply(lhs, open_blocks=open_blocks)
            open_blocks = self.apply(rhs, open_blocks=open_blocks)

            for block in open_blocks:
                block.append(ir.Compare(op, lhs.result(), rhs.result(), inp.result()))

            return open_blocks

        if isinstance(inp, out.All):
            for block in open_blocks:
                block.append(ir.All(inp._conditions, inp.result()))

            return open_blocks

        if isinstance(inp, out.Any):
            for block in open_blocks:
                block.append(ir.Any(inp._conditions, inp.result()))

            return open_blocks

        if isinstance(inp, out.If):
            test = inp._test
            body = inp._body
            orelse = inp._orelse

            open_blocks = self.apply(test, open_blocks=open_blocks)
            ret_blocks: IdMap[Any, ir.CodeBlock] = IdMap()

            for block in open_blocks:
                code_body = ir.CodeBlock([], parent=block)
                code_orelse = ir.CodeBlock([], parent=block)

                # if statement must be added to the code block before the branches
                # are parsed because there is a special case when await/while statements
                # are the first statements in a sequential and the checks for this case
                # will fail, when the first If statement in a sequential is added after
                # parsing the branches
                block.append(ir.If(test.result(), code_body, code_orelse))

                open_body = self.apply(body, open_blocks=[code_body])
                open_orelse = self.apply(orelse, open_blocks=[code_orelse])

                #
                ##
                #

                def any_transition(root, blocks):
                    if len(blocks) == 0:
                        return True
                    return any(block is not root for block in blocks)

                def all_transition(root, blocks):
                    return all(block is not root for block in blocks)

                any_body = any_transition(code_body, open_body)
                all_body = all_transition(code_body, open_body)
                any_orelse = any_transition(code_orelse, open_orelse)
                all_orelse = all_transition(code_orelse, open_orelse)

                if not any_body and not any_orelse:
                    # no transitions, continue with parent block
                    ret_blocks[block] = block
                elif all_body and all_orelse:
                    # all blocks contain transitions,
                    # continue in new states and not in parent
                    for open in [*open_body, *open_orelse]:
                        ret_blocks[open] = open
                else:
                    if not any_body:
                        # no transition in body, but at least one in orelse
                        # continue in body rather than parent because
                        # otherwise transitions could be overwritten
                        ret_blocks[code_body] = code_body

                        for open in open_orelse:
                            ret_blocks[open] = open
                    elif not any_orelse:
                        # no transitions in orelse, but at least one in body
                        ret_blocks[code_orelse] = code_orelse

                        for open in open_body:
                            ret_blocks[open] = open
                    else:
                        for open in [*open_body, *open_orelse]:
                            ret_blocks[open] = open

            return [*ret_blocks.values()]

        if isinstance(inp, out.Call):
            # store returned blocks of parent Call
            # restore before return
            prev_returned_blocks = IrGenerator.returned_blocks
            own_returned_blocks = []
            IrGenerator.returned_blocks = own_returned_blocks

            # convert function code
            result = self.apply(inp._code, open_blocks=open_blocks)

            # add blocks, that ended with return
            result.extend(own_returned_blocks)

            # restore returned blocks of parent Call
            IrGenerator.returned_blocks = prev_returned_blocks

            return result

            # TODO: check if this works in all cases and improves the generated VHDL

            root_groups: IdMap[ir.CodeBlock, list[ir.CodeBlock]] = IdMap()

            for block in result:
                root = block._root

                if root in root_groups:
                    root_groups[root].append(block)
                else:
                    root_groups[root] = [block]

            if len(root_groups) == 1:
                root_group, *rest = root_groups.values()
                return [ir.CodeBlock.common_block(root_group)]
            return result

        if isinstance(inp, out.Return):
            final = inp._final_bound_statements

            if len(final) != 0:
                # translate possible __exit__ block introduced by with/async with statement
                open_blocks = self.apply(inp._final_bound_statements, open_blocks)

            IrGenerator.returned_blocks.extend(open_blocks)

            # nothing to add to  blocks until end of Call
            # returned_blocks will be added to open_blocks of call
            return []

        if isinstance(inp, out.Await):
            if len(open_blocks) == 0:
                return open_blocks

            ctx = ir.StatemachineContext.get()

            if inp._awaitable_primitive:
                for expr_before in inp._expr_before:
                    open_blocks = self.apply(expr_before, open_blocks=open_blocks)

                if ctx.at_start():
                    # special case for sequential instances with `await` as
                    # first statement. Empty first state is used to avoid
                    # delay of one tick at start of instance.
                    new_state = ctx.first_state()
                else:
                    new_block = ir.CodeBlock([], parent=None)
                    new_state = ir._State(new_block, new_block)
                    ctx.add_state(new_state)

                    for block in open_blocks:
                        # add transition at front of block to allow
                        # contained await expressions to overwrite them
                        block.addfront(ir._Transition(new_state))

                result_list = self.apply(
                    inp.bound_statements(), open_blocks=[new_state.code()]
                )

                # assert first is new_state
                assert len(result_list) == 1

                if isinstance(inp.result(), _boolean._BooleanLiteral):
                    # boolean literals do not require If Statements

                    if inp.result() is _boolean.false:
                        # waiting for cohdl.false stops the statemachine,
                        # the following code is never executed
                        # return empty list, there are no open blocks after await false
                        # because execution stops at that point
                        return []

                    assert (
                        inp.result() is _boolean.true
                    ), f"internal error: expected boolean literal, got {inp.result()}"
                else:
                    if_body = ir.CodeBlock([], parent=new_state.open_block())
                    new_state.append(
                        ir.If(
                            inp.result(),
                            if_body,
                            ir.CodeBlock([], parent=new_state.open_block()),
                        )
                    )
                    new_state.set_open_block(if_body)

                return [new_state._open_block]
            else:
                # await expression
                return self.apply(inp.bound_statements(), open_blocks=open_blocks)

        if isinstance(inp, out.While):
            assert (
                inp._test.result() is not False
            ), "internal error: while loops with always false argument should be filtered in the previous compiler stage"

            ctx = ir.StatemachineContext.get()

            if ctx.at_start():
                # special case for sequential instances with `while` as
                # first statement. Empty first state is used to avoid
                # delay of one tick at start of instance.
                new_state = ctx.first_state()
                # add a Nop to mark the state as used
                # so contained statments do not detect
                # the state as empty
                new_state.code().append(ir.Nop())
            else:
                new_block = ir.CodeBlock([], parent=None)
                new_state = ir._State(new_block, new_block)

                for block in open_blocks:
                    # add transition at front of block to allow
                    # contained await expressions to overwrite them
                    block.addfront(ir._Transition(new_state))

                ctx.add_state(new_state)

            # evaluate bound statements before continuing with
            # actual code of while loop
            open_blocks = self._convert_bound(inp, [new_state._open_block])

            assert (
                len(open_blocks) == 1
            ), "internal error: maybe caused by await expression in argument of while loop"
            open_block = open_blocks[0]

            body = ir.CodeBlock([], parent=open_block)
            ret_blocks = []

            prev_continue_result = IrGenerator._continue_result
            prev_break_result = IrGenerator._break_result

            continue_result = []
            break_result = []

            IrGenerator._continue_result = continue_result
            IrGenerator._break_result = break_result

            try:
                # write converted code into body of if statement
                for open_body in self.apply(inp._body, open_blocks=[body]):
                    # add transition to start of while loop
                    # add to front so the transition can be overwritten
                    # by contained await expressions
                    open_body.addfront(ir._Transition(new_state))
            finally:
                IrGenerator._continue_result = prev_continue_result
                IrGenerator._break_result = prev_break_result

            for continue_block in continue_result:
                assert (
                    continue_block.common_block([continue_block, body]) is None
                ), "continue-statement cannot be defined in first state of while-loop (would lead to infinite recursion)"

                if inp._test.result() is True:
                    # for while loops with constant condition
                    # body is the first block in the loop, add statements until
                    # first state change in place of continue
                    continue_block.append(body)
                else:
                    # while loops with runtime variable conditions, continue-statements behave like
                    # break statements if the condition is false. Otherwise the behavior is the same
                    # as a while loop with constant True condition.

                    continue_blocks = self.apply(inp._test, [continue_block])

                    for block in continue_blocks:
                        break_block = ir.CodeBlock([], parent=continue_block)
                        block.append(ir.If(inp._test.result(), body, break_block))
                        ret_blocks.append(break_block)

            # codeblocks, that end with a break statement
            # are the new open blocks to be populated after the while loop
            ret_blocks.extend(break_result)

            if inp._test.result() is True:
                # while loop with constant, true condition
                # exits via break/return are handled earlier
                open_block.append(body)
                return ret_blocks
            else:
                orelse = ir.CodeBlock([], parent=open_block)
                open_block.append(ir.If(inp._test.result(), body, orelse))
                open_block.get_parent_state().set_open_block(orelse)
                return [orelse, *ret_blocks]

        if isinstance(inp, out.Continue):
            # store list of open blocks
            # so while loop can replace continue with statements
            IrGenerator._continue_result.extend(open_blocks)

            # no open blocks after continue since continue is always the last
            # statement in a codeblock
            return []

        if isinstance(inp, out.Break):
            # store list of open blocks
            # so while loop can continue after break
            IrGenerator._break_result.extend(open_blocks)

            # no open blocks after break since break is always the last
            # statement in a codeblock
            return []

        if isinstance(inp, out.Statemachine):
            assert (
                len(open_blocks) == 1
            ), "statemachine instantiated in more than one path"

            parent_block = open_blocks[0]

            ctx = ir.StatemachineContext.enter(inp._name)

            statemachine_end = self.apply(inp._body, open_blocks=[ctx.first_block()])

            parent_block.append(ir.StatemachineContext.finish(statemachine_end))

            return open_blocks

        if isinstance(inp, out.ResetContext):
            for block in open_blocks:
                block.append(ir._ResetContext())
            return open_blocks

        if isinstance(inp, out.ResetPushed):
            for block in open_blocks:
                block.append(ir._ResetPushed())
            return open_blocks

        if isinstance(inp, out.CodeBlock):
            return self.apply(inp.statements(), open_blocks=open_blocks)

        if isinstance(inp, list):
            for stmt in inp:
                open_blocks = self.apply(stmt, open_blocks=open_blocks)

                if stmt.returns_always():
                    break

            return open_blocks

        if isinstance(inp, out.Value):
            return open_blocks

        if isinstance(inp, out.Boolean):
            for block in open_blocks:
                block.append(ir.Boolean(inp.value(), inp.result()))

            return open_blocks

        if isinstance(inp, out.Nop):
            return open_blocks

        if isinstance(inp, out.ResetInstance):
            for block in open_blocks:
                block.append(ir.ResetInstance(inp.get_obj()))

            return open_blocks

        if isinstance(inp, out.IfExpr):
            hook_body = inp._hook_body
            hook_orelse = inp._hook_orelse

            open_blocks = self.apply(inp._body, open_blocks=open_blocks)
            open_blocks = self.apply(inp._orelse, open_blocks=open_blocks)
            open_blocks = self.apply(inp._test, open_blocks=open_blocks)

            for block in open_blocks:
                if hook_body.has_redirect():
                    assert len(hook_body.redirects) == len(hook_orelse.redirects)
                    for branch_body, branch_orelse in zip(
                        hook_body.redirects, hook_orelse.redirects
                    ):
                        test_val = inp._test.result()

                        if issubclass(test_val.type, _boolean._Boolean):
                            true_val = _boolean._Boolean(True)
                        else:
                            assert issubclass(test_val.type, Bit)
                            true_val = Bit(True)

                        block.append(
                            ir.SelectWith(
                                test_val,
                                [
                                    (true_val, branch_body.source),
                                ],
                                default=branch_orelse.source,
                                result=branch_body.target,
                            )
                        )

            return open_blocks

        if isinstance(inp, out.SelectWith):
            branch_hooks = inp._branch_hooks
            first_hook = branch_hooks[0]

            for block in open_blocks:
                if first_hook.has_redirect():
                    for nr, redirect in enumerate(first_hook.redirects):
                        branches = [
                            (cond, hook.redirects[nr].source)
                            for cond, hook in zip(inp._conditions, branch_hooks)
                        ]

                        if inp._default_hook is not None:
                            block.append(
                                ir.SelectWith(
                                    inp._arg,
                                    branches,
                                    inp._default_hook.redirects[nr].source,
                                    redirect.target,
                                )
                            )
                        else:
                            block.append(
                                ir.SelectWith(
                                    inp._arg,
                                    branches,
                                    None,
                                    redirect.target,
                                )
                            )

            return open_blocks

        if isinstance(inp, out.CondSelect):

            def gen_case_when(
                value: out.Expression,
                conds: list[out.Value],
                bodies: list[out.CodeBlock],
                default: out.CodeBlock | None,
                open_blocks: list[ir.CodeBlock],
            ):
                # convert parameter bodies to internal representation
                def gen_bodies(parent_block):
                    ret = []

                    for code in bodies:
                        code_block = ir.CodeBlock([], parent=parent_block)
                        converted = self.apply(code, open_blocks=[code_block])

                        if len(converted) != 1 or converted[0] is not code_block:
                            # generating case-when not possible, when a branch contains a transition
                            # return None to fall back to if-else implementation
                            return None

                        ret.append(code_block)
                    return ret

                conditions = [expr.result() for expr in conds]

                for block in open_blocks:
                    new_blocks = self.apply(value, open_blocks=[block])

                    if default is None:
                        for new_block in new_blocks:
                            ir_bodies = gen_bodies(new_block)

                            if ir_bodies is None:
                                return None

                            new_block.append(
                                ir.CaseWhen(
                                    value.result(),
                                    [
                                        (cond, body)
                                        for cond, body in zip(conditions, ir_bodies)
                                    ],
                                    None,
                                )
                            )
                    else:
                        for new_block in new_blocks:
                            default_body = ir.CodeBlock([], parent=block)
                            converted = self.apply(default, open_blocks=[default_body])

                            if len(converted) != 1 or converted[0] is not default_body:
                                return None

                            ir_bodies = gen_bodies(new_block)

                            if ir_bodies is None:
                                return None

                            new_block.append(
                                ir.CaseWhen(
                                    value.result(),
                                    [
                                        (cond.result(), body)
                                        for cond, body in zip(conds, ir_bodies)
                                    ],
                                    default_body,
                                )
                            )

                return open_blocks

            def try_gen_case_when(
                inp: out.CondSelect,
                open_blocks: list[ir.CodeBlock],
            ):
                if inp.returns():
                    # fallback to if-else implementation
                    return None

                lhs_map = IdMap()
                rhs_map = IdMap()

                lhs_expr = []
                rhs_expr = []

                bodies = []

                for expr, body in inp._branches:
                    if body.contains_break() or body.contains_continue():
                        # handling of state transitions and break/continue statements is complex
                        # better opt out of case-when statement and instead use already implemented
                        # if-else chain
                        return None

                    if isinstance(expr, out.Compare) and expr._op is expr.Operator.EQ:

                        lhs = expr._lhs
                        rhs = expr._rhs

                        lhs_expr.append(lhs)
                        rhs_expr.append(rhs)

                        lhs_map.map_self(lhs.result())
                        rhs_map.map_self(rhs.result())

                        bodies.append(body)
                    else:
                        return None

                def check_value(map: IdMap):
                    # same value is used in every equality check
                    return len(map) == 1

                def check_branches(map: IdMap):
                    for cond in map.values():
                        assert is_primitive(_type_qualifier.TypeQualifier.decay(cond))

                        if isinstance(cond, _type_qualifier.TypeQualifier):
                            return False
                    return True

                if check_value(lhs_map) and check_branches(rhs_map):
                    return gen_case_when(
                        lhs_expr[0], rhs_expr, bodies, inp._default, open_blocks
                    )

                if check_value(rhs_map) and check_branches(lhs_map):
                    return gen_case_when(
                        rhs_expr[0], lhs_expr, bodies, inp._default, open_blocks
                    )

                return None

            if len(inp._branches) == 0:
                if inp._default is None:
                    return open_blocks
                return self.apply(inp._default, open_blocks=open_blocks)

            #
            # construct a case when statement if possible
            #

            case_when = try_gen_case_when(inp, open_blocks)

            if case_when is not None:
                return case_when

            #
            # fallback to nested if statements
            #

            if inp.returns():
                assert inp.returns_always()

            if inp._default is not None:
                rewritten = inp._default
            else:
                rewritten = out.CodeBlock([])

            for branch in inp._branches[::-1]:
                expr, code = branch

                rewritten = out.If(expr, code, out.CodeBlock([rewritten]))

            return self.apply(rewritten, open_blocks=open_blocks)

        if isinstance(inp, out.Assert):
            for block in open_blocks:
                result_blocks = self.apply(inp._cond, open_blocks=[block])

                assert (
                    len(result_blocks) == 1 and result_blocks[0] is block
                ), "transitions are not allowed in assertion test"

                msg = inp._msg

                if msg is not None:
                    assert isinstance(msg, out.Expression)
                    msg = msg.result()

                block.append(ir.Assert(inp._cond.result(), msg))

            return open_blocks

        if isinstance(inp, out.InlineCode):
            result = inp.result()

            if isinstance(result, out.InlineCode):
                result = None

            for block in open_blocks:
                code = ir.InlineCode(inp.options, result)
                block.append(code)

            return open_blocks

        if isinstance(inp, out.Comment):
            for block in open_blocks:
                block.append(ir.Comment(inp.lines))

            return open_blocks

        raise AssertionError(f"cannot convert {inp}")


#
#
#
# instance converters
#
#
#


class ConvertInstance:
    def __init__(
        self, template: IdMap[out.EntityTemplate, ir.EntityTemplate] | None = None
    ) -> None:
        super().__init__()

        self._entity_templates: IdMap[out.EntityTemplate, ir.EntityTemplate] = (
            IdMap() if template is None else template
        )

    def lookup_template(self, source: out.EntityTemplate) -> ir.EntityTemplate | None:
        if source in self._entity_templates:
            return self._entity_templates[source]
        return None

    def add_template(self, source: out.EntityTemplate, result: ir.EntityTemplate):
        self._entity_templates[source] = result

    @staticmethod
    def detect_uninitialized_temporaries(ctx: ir.Context):
        invalid_temporaries = set()
        written_temporaries = set()

        def check_used_temporaries(obj, access: AccessFlags):
            if access is AccessFlags.READ:
                if isinstance(obj, Temporary):
                    # This assertion ensures, that all temporaries are initialized
                    # before they are used. Check your code for temporaries,
                    # that are defined in a if or match statement and used outside of it.
                    #
                    # In the following example the temporary 'var' is invalid at the location
                    # of the assignment to 'some_output' because it is only initialized when
                    # 'some_signal' is true.
                    #
                    # >>> if some_signal:
                    # >>>     var = inp_a | inp_b
                    # >>> some_output <<= var        # error occurs in this line
                    root_id = id(obj._root)
                    assert (
                        root_id not in invalid_temporaries
                    ), "temporary might not be initialized"

                    assert (
                        root_id in written_temporaries
                    ), "temporary read before it was written (defined outside current context?)"
            elif access is AccessFlags.WRITE:
                written_temporaries.add(id(obj._root))

            return obj

        def search_invalid_temporaries(code: ir.CodeBlock):
            nonlocal invalid_temporaries

            local_temporaries = set()

            for stmt in code._content:
                if isinstance(stmt, ir.If):
                    check_used_temporaries(stmt._test, AccessFlags.READ)

                    # Find all temporaries defined in body and mark them
                    # as invalid because they might not be defined
                    body_temporaries = search_invalid_temporaries(stmt._body)
                    invalid_temporaries |= body_temporaries

                    # Find all temporaries defined in else branch and mark
                    # them as invalid because they might not be defined.
                    else_temporaries = search_invalid_temporaries(stmt._orelse)
                    invalid_temporaries |= else_temporaries

                    always_defined = body_temporaries & else_temporaries

                    # When a temporary is defined in both blocks
                    # if is always defined and thus valid.
                    invalid_temporaries.difference_update(always_defined)
                    local_temporaries |= always_defined

                elif isinstance(stmt, ir.CodeBlock):
                    local_temporaries |= search_invalid_temporaries(stmt)
                elif isinstance(stmt, ir.CaseWhen):
                    check_used_temporaries(stmt._value, AccessFlags.READ)

                    always_defined = None

                    for branch_cond, branch_code in stmt._branches:
                        check_used_temporaries(branch_cond, AccessFlags.READ)
                        branch_temporaries = search_invalid_temporaries(branch_code)
                        invalid_temporaries |= branch_temporaries

                        if always_defined is None:
                            always_defined = branch_temporaries
                        else:
                            always_defined.difference_update(branch_temporaries)

                    if stmt._default is not None:
                        default_temporaries = search_invalid_temporaries(stmt._default)
                        invalid_temporaries |= default_temporaries

                        if always_defined is None:
                            always_defined = branch_temporaries
                        else:
                            always_defined.difference_update(branch_temporaries)

                    invalid_temporaries.difference_update(always_defined)
                    local_temporaries |= always_defined

                else:
                    ir._visit_referenced_objects(stmt, check_used_temporaries)

                    if isinstance(stmt, ir.Expression) and isinstance(
                        stmt._result, Temporary
                    ):
                        root = stmt._result._root

                        if not root._maybe_uninitialized:
                            root_id = id(root)

                            local_temporaries.add(root_id)
                            invalid_temporaries.discard(root_id)

                    elif isinstance(stmt, ir.VariableAssignment) and isinstance(
                        stmt._target, Temporary
                    ):
                        root = stmt._target._root

                        if not root._maybe_uninitialized:
                            root_id = id(root)
                            local_temporaries.add(root_id)
                            invalid_temporaries.discard(root_id)

            return local_temporaries

        search_invalid_temporaries(ctx.code())

    @staticmethod
    def cleanup_unused(ctx: ir.Context):
        used_temporaries = IdSet()

        def find_used_temp(obj, access: AccessFlags):
            if access.is_read() and isinstance(obj, Temporary):
                root = obj._root
                used_temporaries.add(root)

            return obj

        ctx.visit_referenced_objects(find_used_temp)

        def remove_unused_assignments(stmt):
            if isinstance(stmt, ir.Expression) and isinstance(stmt.result(), Temporary):
                root = stmt.result()._root

                if root not in used_temporaries:
                    return ir.CodeBlock([], None)
            elif isinstance(stmt, ir.VariableAssignment) and isinstance(
                stmt._target, Temporary
            ):
                root = stmt._target._root

                if root not in used_temporaries:
                    return ir.CodeBlock([], None)

            return stmt

        ctx.visit(remove_unused_assignments)

        return ctx

    @staticmethod
    def cleanup_bool_cast(ctx: ir.Context):
        # The previous stages of the compiler produce some
        # redundant casts from Temporary[bool] to Temporary[bool].
        # This function removes these casts and replaces all uses
        # of the cast result with the cast input.
        # This is a purely cosmetic operation to make the generated
        # HDL more readable.

        replacement_map = IdMap()

        def search_unneeded_bool_casts(stmt):
            if isinstance(stmt, ir.Boolean):
                source = stmt._arg
                target = stmt._result
                if (
                    isinstance(source, Temporary)
                    and isinstance(target, Temporary)
                    and source._root is source
                    and target._root is target
                    and source.type is _boolean.boolean
                    and target.type is _boolean.boolean
                ):
                    replacement_map[target] = source
                    return ir.Nop()

            return stmt

        ctx.visit(search_unneeded_bool_casts)

        def replace_temporaries(obj, access):
            if obj in replacement_map:
                return replacement_map[obj]

            return obj

        ctx.visit_referenced_objects(replace_temporaries)
        return ctx

    #
    #
    #

    def apply(self, inp):
        try:
            if isinstance(inp, out.EntityTemplate):
                ir_template = self.lookup_template(inp)

                if ir_template is None:
                    ir_template = ir.EntityTemplate(
                        inp._info,
                        [self.apply(block) for block in inp.subblocks()],
                        [self.apply(ctx) for ctx in inp.contexts()],
                    )

                    self.add_template(inp, ir_template)

                return ir_template

            if isinstance(inp, out.Entity):
                template = self.apply(inp.template())

                return ir.Entity(
                    template,
                    inp._info.name,
                    inp.port_definitions(),
                    inp.generic_definitions(),
                )
            if isinstance(inp, out.Block):
                return ir.Block(
                    "<BLOCK>",
                    [self.apply(subinst) for subinst in inp.subblocks()],
                    [self.apply(ctx) for ctx in inp.contexts()],
                    inp._attributes,
                )

            if isinstance(inp, out.Concurrent):
                result = IrGenerator.convert_concurrent(inp)

                written_temporaries = set()

                def check_variables_and_temporaries(obj, access):
                    assert not isinstance(
                        obj, Variable
                    ), "variables cannot be used in concurrent contexts"

                    if isinstance(obj, Temporary):
                        if access is AccessFlags.READ:
                            assert (
                                id(obj._root) in written_temporaries
                            ), "temporary read before it was written (defined outside current context?)"
                        else:
                            written_temporaries.add(id(obj._root))

                    return obj

                result.visit_referenced_objects(check_variables_and_temporaries)

                if result.attributes.get("cleanup_unused", True):
                    result = ConvertInstance.cleanup_unused(result)

                if result.attributes.get("zero_init_temporaries", False):
                    # only used for unit tests
                    # (required because ghdl terminates with an overflow error
                    # when uninitialized integer values are used)

                    def visit_obj(obj, access):
                        if isinstance(obj, Temporary):
                            obj._default = obj.type(Null)
                        return obj

                    result.visit_referenced_objects(visit_obj)
                return result

            if isinstance(inp, out.Sequential):
                result = IrGenerator.convert_sequential(inp)

                ConvertInstance.detect_uninitialized_temporaries(result)

                if result.attributes.get("cleanup_unused", True):
                    result = ConvertInstance.cleanup_unused(result)
                if result.attributes.get("cleanup_bool_cast", True):
                    result = ConvertInstance.cleanup_bool_cast(result)
                if result.attributes.get("zero_init_temporaries", False):
                    # only used for unit tests
                    # (required because ghdl terminates with an overflow error
                    # when uninitialized integer values are used)

                    def visit_obj(obj, access):
                        if isinstance(obj, Temporary):
                            obj._default = obj.type(Null)
                        return obj

                    result.visit_referenced_objects(visit_obj)
                return result

            raise AssertionError(f"cannot convert {inp}")
        except ir.VisitException as err:
            if pretty_traceback_active():
                src = err.src_statement

                if src._frame is not None:
                    src._frame.apply_to_exception(err.original)

                raise err.original
            raise
