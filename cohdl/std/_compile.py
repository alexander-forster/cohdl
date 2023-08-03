import os

from cohdl._compiler.frontend import generate_internal_representation
from cohdl._compiler.backend import generate_vhdl


class VhdlCompiler:
    @classmethod
    def to_ir(cls, entity):
        return generate_internal_representation(entity)

    @classmethod
    def to_vhdl_library(cls, top_entity):
        ir = generate_internal_representation(top_entity)
        return generate_vhdl(ir)

    @classmethod
    def to_string(cls, top_entity):
        return str(cls.to_vhdl_library(top_entity).write())

    @classmethod
    def to_dir(cls, top_entity, target_dir, *, mkdir: bool = False) -> list[str]:
        if not os.path.exists(target_dir):
            if mkdir:
                os.mkdir(target_dir)
            else:
                raise AssertionError(f"target directory '{target_dir}' does not exist")

        return cls.to_vhdl_library(top_entity).write_dir(target_dir)
