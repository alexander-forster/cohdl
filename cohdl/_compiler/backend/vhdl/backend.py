from cohdl._compiler.backend.vhdl._vhdl_assembler import VhdlAssembler, VhdlMakeLibrary


def generate_vhdl(input):
    vhdl = VhdlAssembler().apply(input)
    return VhdlMakeLibrary().apply(vhdl)
