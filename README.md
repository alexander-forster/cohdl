# CoHDL

CoHDL is a hardware description language embedded in Python. It translates a subset of Python into synthesizable VHDL.

---

## examples/introduction

You can find an introduction and many examples in this [documentation repository](https://github.com/alexander-forster/cohdl_documentation).

## features

At its core CoHDLs language model is very similar to VHDL. Designs are made up of signals and variables built from types like `Bit` and `BitVector`. There are concurrent contexts, for expressions that would appear in the architecture scope of VHDL entities and sequential contexts equivalent to VHDL processes.

Code that uses only basic features also found in VHDL (if-statements, signal/variable assignments, arithmetic operators and so on) essentially looks like VHDL written in Python syntax. On top of that CoHDL supplies many additional features


### coroutines

The initial motivation for CoHDL was to explore how well coroutines, found in many modern programming languages, translate to the domain of hardware description languages.

CoHDL turns Pythons async/await style coroutines into VHDL state machines. This process is completely deterministic and allows clock accurate modeling of sequential processes. The main advantage over explicit state machine implementations is, that coroutines are reusable.

Common sequences such as AXI transactions can be defined once and instantiated whenever needed.

### supported Python subset

The following is an incomplete list of Python constructs supported in synthesizable contexts

* statements
    * if
    * for
    * if expressions
    * generator expressions
    * most operators
* functions
    * arbitrary argument types
    * default arguments
    * keyword arguments
    * variadic arguments
    * compile time recursion
    * compile time evaluated builtin functions
* classes
    * member access
    * methods
    * operator overloading
    * inheritance
    * overriding methods
* python container types
    * list
    * dict
* coroutines

### meta programming

Since CoHDL is embedded in Python, it is possible to run arbitrary code before and after the compilation. This can be used to load configuration files or run external programs like simulators or synthesis tools on the generated VHDL.

For a working example of this checkout [cohdl_xil](https://github.com/alexander-forster/cohdl_xil). It generates Makefile projects for CoHDL designs targeting Xilinx FPGAs.

---
## getting started

CoHDL requires Python3.10 or higher and has no further dependencies. You can install it by running

```shell
python3 -m pip install cohdl
```

in a terminal window. You should then be able to run the code snippets, found in the [introduction repository](https://github.com/alexander-forster/cohdl_documentation) and implement own designs.
