from __future__ import print_function

from ctypes import CFUNCTYPE, c_int, c_float

import llvmlite.binding as llvm

# All these initializations are required for code generation!
llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()  # yes, even this one

def create_execution_engine():
    """
    Create an ExecutionEngine suitable for JIT code generation on
    the host CPU.  The engine is reusable for an arbitrary number of
    modules.
    """
    # Create a target machine representing the host
    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    # And an execution engine with an empty backing module
    backing_mod = llvm.parse_assembly("")
    engine = llvm.create_mcjit_compiler(backing_mod, target_machine)
    return engine


def compile_ir(engine, llvm_ir, should_optimize):
    """
    Compile the LLVM IR string with the given engine.
    The compiled module object is returned.
    """
    # Create a LLVM module object from the IR
    mod = llvm.parse_assembly(str(llvm_ir))

    if should_optimize:
        pmb = llvm.create_pass_manager_builder()
        pmb.opt_level = 3

        fpm = llvm.create_function_pass_manager(mod)
        pmb.populate(fpm)

        pm = llvm.create_module_pass_manager()
        pmb.populate(pm)
        
        pm.run(mod)

    mod.verify()
    # Now add the module and make sure it is ready for execution
    engine.add_module(mod)
    engine.finalize_object()
    engine.run_static_constructors()
    return str(mod)

# The function called by ekcc
def compile_and_execute(llvm_ir, should_optimize):
    engine = create_execution_engine()
    mod = compile_ir(engine, llvm_ir, should_optimize)

    # Look up the function pointer (a Python int)
    func_ptr = engine.get_function_address("run")
    # Run the function via ctypes
    cfunc = CFUNCTYPE(c_int)(func_ptr)
    res = cfunc()
    return mod
