#
#
#

from .reg import *
from .reg import _primitive_as_int
from cohdl.utility.code_writer import TextBlock


class Content:

    def __init__(self):
        self.name = None
        self.desc = None
        self.sw = None
        self.hw = None
        self.encode = None

        self.sub_content = []

    def to_list(self):
        result = []

        if self.name is not None:
            result.append(f'name = "{self.name}";')

        if self.desc is not None:
            result.append(f'desc = "{self.desc}";')

        if self.sw is not None:
            result.append(f"sw = {self.sw};")

        if self.hw is not None:
            result.append(f"hw = {self.hw};")

        if self.encode is not None:
            result.append(f"encode = {self.encode};")

        result.extend(self.sub_content)

        return result

    def append(self, raw):
        self.sub_content.append(raw)

    def add_description(self, input: type, metadata: list | None = None):
        if metadata is not None:
            for entry in metadata:
                if isinstance(entry, str):
                    self.desc = entry.strip()
                    return

        for elem in input.mro():
            if elem is object:
                return
            if elem.__doc__ is not None:
                self.desc = elem.__doc__.strip()
                return

    def add_meta(self, metadata: type | None):
        if metadata is None:
            return

        for info in metadata:
            if isinstance(info, str):
                self.desc = info
            elif isinstance(info, Access):
                self.sw = info.name
            elif isinstance(info, HwAccess):
                self.hw = info.name


class ComponentBlock(TextBlock):
    def __init__(
        self,
        typename: str,
        component_name: str | None = None,
        content: Content = [],
        trailer="};",
    ):
        if component_name is None:
            title = f"{typename} {{"
        else:
            title = f"{typename} {component_name} {{"

        super().__init__(title=title, content=content.to_list(), trailer=trailer)


def _find_enums(root: RegFile, result_set: set):
    for subtype in root._member_types_.values():
        if issubclass(subtype, RegFile):
            _find_enums(subtype, result_set)
        elif issubclass(subtype, Register):
            for fieldtype in subtype._field_types_.values():
                assert issubclass(fieldtype, FieldBase)
                arg = fieldtype._field_arg

                if arg.is_enum():
                    result_set.add(arg.underlying)


def _add_description(input: type, content: list, metadata: list | None = None):
    if metadata is not None:
        for entry in metadata:
            if isinstance(entry, str):
                content.append(f'desc = "{entry.strip()}";')
                return

    for elem in input.mro():
        if elem is object:
            return
        if elem.__doc__ is not None:
            content.append(f'desc = "{elem.__doc__.strip()}";')
            return


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

    if issubclass(input, RegFile):
        content = Content()

        member_metadata = input._metadata_

        if name is None:
            content.name = escape(input.__name__.split("[")[0])
        else:
            content.name = escape(name)

        content.add_description(input, metadata)

        if issubclass(input, AddrMap):
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

        return ComponentBlock("addrmap", content.name, content=content, trailer=trailer)
    elif issubclass(input, Register):
        content = Content()
        content.add_description(input, metadata)

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
        content = Content()
        content.add_meta(metadata)

        arg = input._field_arg

        trailer_loc = f"[{arg.offset+arg.width-1}:{arg.offset}]"

        if arg.is_enum():
            content.encode = escape(arg.underlying.__name__)

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

        return ComponentBlock(
            "field",
            content=content,
            trailer="}" + f" {escape(name)} {trailer_loc}{trailer_default};",
        )
    elif issubclass(input, FlagField):
        content = Content()
        content.add_meta(metadata)

        arg = input._field_arg
        trailer_loc = f"[{arg.offset}:{arg.offset}]"

        return ComponentBlock(
            "field",
            content=content,
            trailer="}" + f" {escape(name)} {trailer_loc} = 0;",
        )
    elif issubclass(input, StdEnum):
        content = Content()
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
    elif issubclass(input, (Input, Output, GenericRegister)):
        content = Content()

        content.add_description(input, metadata)
        content.add_meta(metadata)

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
    elif issubclass(input, Memory):
        content = Content()
        content.add_description(input, metadata)
        content.add_meta(metadata)

        if not input._writable_:
            content.sw = "r"

        content.append(f"mementries = {input._word_count_};")
        content.append(f"memwidth = {input._word_width_()};")

        return ComponentBlock(
            "external mem",
            content=content,
            trailer="}" + f" {escape(name)} @ 0x{input._parent_offset_:0x};",
        )

    raise AssertionError(f"invalid input {input}")


def to_system_rdl(input: AddrMap | type[AddrMap]):
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
