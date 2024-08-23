from __future__ import annotations


from cohdl._compiler.frontend._prepare_ast import ConvertPythonInstance
from cohdl._compiler.frontend._generate_ir import ConvertInstance


def generate_internal_representation(instance):
    with ConvertPythonInstance() as inst:
        preprocessed = inst.apply(instance)

    return ConvertInstance().apply(preprocessed)
