#
#
#

from .reg import *
from .reg import _primitive_as_int
from cohdl.utility.code_writer import TextBlock


class ComponentBlock(TextBlock):
    def __init__(
        self, typename: str, component_name: str | None = None, content=[], trailer="};"
    ):
        if component_name is None:
            title = f"{typename} {{"
        else:
            title = f"{typename} {component_name} {{"

        super().__init__(title=title, content=content, trailer=trailer)


def _find_enums(root: RegisterDevice, result_set: set):
    for subtype in root._member_types_.values():
        if issubclass(subtype, RegisterDevice):
            _find_enums(subtype, result_set)
        elif issubclass(subtype, Register):
            for fieldtype in subtype._field_types_.values():
                assert issubclass(fieldtype, FieldBase)
                arg = fieldtype._field_arg

                if arg.is_enum():
                    result_set.add(arg.underlying)


def _add_description(input: type, content: list):
    for elem in input.mro():
        if elem is object:
            return
        if elem.__doc__ is not None:
            content.append(f'desc = "{elem.__doc__.strip()}";')
            return


def _add_field_args(metadata: type, content: list):
    if metadata is None:
        return

    desc = None
    sw_access = None

    for info in metadata:
        if isinstance(info, str):
            desc = info
        elif isinstance(info, Access):
            sw_access = info.name

    if desc is not None:
        content.append(f'desc = "{desc}";')

    if sw_access is not None:
        content.append(f"sw = {sw_access};")


def _add_meta_args(metadata: type, content: list):
    if metadata is None:
        return

    desc = None
    sw_access = None
    hw_access = None

    for info in metadata:
        if isinstance(info, str):
            desc = info
        elif isinstance(info, Access):
            sw_access = info.name
        elif isinstance(info, HwAccess):
            hw_access = info.name

    if desc is not None:
        content.append(f'desc = "{desc}";')

    if sw_access is not None:
        content.append(f"sw = {sw_access};")

    if hw_access is not None:
        content.append(f"hw = {hw_access};")


def _impl_to_system_rdl(input, name: str | None = None, metadata=None):
    escape = _systemrdl_escape

    if issubclass(input, RegisterDevice):
        content = [""]

        member_metadata = input._metadata_

        if name is None:
            base_name = input.__name__.split("[")[0]
            content.append(f'name = "{escape(base_name)}";')
        else:
            base_name = name
            content.append(f'name = "{escape(name)}";')

        _add_description(input, content)

        if issubclass(input, RootDevice):
            content.append(f"default regwidth = {input._register_tools_._word_width_};")
            content.append("")

            enumerations = set()
            _find_enums(input, enumerations)

            for enumtype in enumerations:
                content.append(_impl_to_system_rdl(enumtype))
            trailer = "};"
        else:
            trailer = "} " + f"{escape(name)} @ 0x{input._parent_offset_:0x};"

        for member_name, member_type in input._member_types_.items():
            content.append("")
            content.append(
                _impl_to_system_rdl(
                    member_type, member_name, member_metadata.get(member_name, None)
                )
            )
            content.append("")

        return ComponentBlock("addrmap", base_name, content=content, trailer=trailer)
    elif issubclass(input, Register):
        content = [""]

        _add_description(input, content)

        for field_name, field_type in input._field_types_.items():
            content.append("")
            content.append(
                _impl_to_system_rdl(
                    field_type, field_name, input._metadata_.get(field_name, None)
                )
            )

        return ComponentBlock(
            "reg",
            content=content,
            trailer="}" + f" {escape(name)} @ 0x{input._parent_offset_:0x};",
        )
    elif issubclass(input, Field):
        content = []

        arg = input._field_arg

        trailer_loc = f"[{arg.offset+arg.width-1}:{arg.offset}]"

        if arg.is_enum():
            enum_name = arg.underlying.__name__
            content.append(f"encode = {escape(enum_name)};")

        if arg.default is None:
            trailer_default = ""
        else:
            underlying = input._cohdlstd_underlying()
            default = underlying(arg.default)

            if issubclass(underlying, StdEnum):
                default = _primitive_as_int(default.raw)
            else:
                default = _primitive_as_int(default)

            trailer_default = f" = {escape(default)}"

        _add_meta_args(metadata, content)

        return ComponentBlock(
            "field",
            content=content,
            trailer="}" + f" {escape(name)} {trailer_loc}{trailer_default};",
        )
    elif issubclass(input, FlagField):
        content = []

        arg = input._field_arg
        trailer_loc = f"[{arg.offset}:{arg.offset}]"

        _add_meta_args(metadata, content)

        return ComponentBlock(
            "field",
            content=content,
            trailer="}" + f" {escape(name)} {trailer_loc} = 0;",
        )
    elif issubclass(input, StdEnum):
        content = []
        enum_name = input.__name__.split("[")[0]

        for enumerator_name, enumerator in input.__members__.items():
            enum_def = f"{_systemrdl_escape(enumerator_name)} = {_primitive_as_int(enumerator.raw)}"

            info = enumerator.info

            if info is None:
                enum_def += ";"
            else:
                enum_def += f' {{ desc = "{info}"; }};'

            content.append(enum_def)

        return ComponentBlock("enum", _systemrdl_escape(enum_name), content=content)
    elif issubclass(input, (Input, Output)):
        content = [""]

        _add_description(input, content)
        _add_meta_args(metadata, content)

        if issubclass(input, Input):
            access = f"sw = r;"
        else:
            access = f"sw = w;"

        content.append(f"field {{ {access} }} \\all [31:0];")

        return ComponentBlock(
            "reg",
            content=content,
            trailer="}" + f" {escape(name)} @ 0x{input._parent_offset_:0x};",
        )

    raise AssertionError(f"invalid input {input}")


def to_system_rdl(input: RootDevice | type[RootDevice]):
    if not isinstance(input, type):
        input = type(input)

    return _impl_to_system_rdl(input).dump()


def _systemrdl_escape(inp: str):
    if inp in systemrdl_reserved:
        return f"\{inp}"
    return inp


systemrdl_reserved = {
    "abstract",
    "accesstype",
    "addressingtype",
    "addrmap",
    "alias",
    "all",
    "bit",
    "boolean",
    "bothedge",
    "compact",
    "component",
    "componentwidth",
    "constraint",
    "default",
    "encode",
    "enum",
    "external",
    "false",
    "field",
    "fullalign",
    "hw",
    "inside",
    "internal",
    "level",
    "longint",
    "mem",
    "na",
    "negedge",
    "nonsticky",
    "number",
    "onreadtype",
    "onwritetype",
    "posedge",
    "property",
    "r",
    "rclr",
    "ref",
    "reg",
    "regalign",
    "regfile",
    "rset",
    "ruser",
    "rw",
    "rw1",
    "signal",
    "string",
    "struct",
    "sw",
    "this",
    "true",
    "type",
    "unsigned",
    "w",
    "w1",
    "wclr",
    "woclr",
    "woset",
    "wot",
    "wr",
    "wset",
    "wuser",
    "wzc",
    "wzs",
    "wzt",
}
