from cohdl._compiler.backend.vhdl._vhdl_assembler import VhdlAssembler, VhdlMakeLibrary


def generate_vhdl(input, *, additional_reserved_names: set[str] = None):
    vhdl = VhdlAssembler(additional_reserved_names=additional_reserved_names).apply(
        input
    )
    return VhdlMakeLibrary().apply(vhdl)
