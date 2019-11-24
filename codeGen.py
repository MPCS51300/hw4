from llvmlite import ir
import llvmlite.binding as llvm
import ctypes

def load_var(builder, pointer):
    while pointer.type.is_pointer:
        pointer = builder.load(pointer)
    return pointer

def get_pointer(builder, pointer):
    if not pointer.type.is_pointer:
        return pointer
    next_pointer = builder.load(pointer)
    while pointer.type.is_pointer and next_pointer.type.is_pointer:
        pointer = builder.load(pointer)
        next_pointer = builder.load(pointer)
    return pointer

def generate_type(typ):
    if typ == "int":
        return ir.IntType(32)
    elif typ == "float":
        return ir.FloatType()
    elif typ == "void":
        return ir.VoidType()
    elif typ == "bool":
        return ir.IntType(1)
    elif "ref" in typ:
        if "int" in typ:
            return ir.PointerType(ir.IntType(32))
        elif "float" in typ:
            return ir.PointerType(ir.FloatType())
        elif "bool" in typ:
            return ir.PointerType(ir.IntType(1))
    elif typ == "slit":
        return ir.PointerType(ir.IntType(8))

def generate_slit(string):
    c_str_val = ir.Constant(ir.ArrayType(ir.IntType(8), len(string)), bytearray(string.encode("utf8")))
    return c_str_val

def generate_arg(ast, module, undefined_args):
    # Declare function
    fnty = ir.FunctionType(generate_type("int"), [generate_type("int")])
    func = ir.Function(module, fnty, name = "arg")
    entry = func.append_basic_block("entry")
    builder = ir.IRBuilder(entry)

    # dummy switch else, switch end
    bbelse = builder.append_basic_block("switch.else")
    bbend = builder.append_basic_block("switch.end")
    switch = builder.switch(func.args[0], bbelse)
    with builder.goto_block(bbelse):
        builder.ret(ir.Constant(generate_type("int"), 0))
    with builder.goto_block(bbend):
        builder.ret(ir.Constant(generate_type("int"), 0))

    # build switch blocks
    for idx, arg in enumerate(undefined_args):
        bbi = builder.append_basic_block("switch.%d" % idx)
        switch.add_case(idx, bbi)
        with builder.goto_block(bbi):
            builder.ret(ir.Constant(generate_type("int"), int(arg)))

def generate_argf(ast, module, undefined_args):
    # Declare function
    fnty = ir.FunctionType(generate_type("float"), [generate_type("int")])
    func = ir.Function(module, fnty, name = "argf")
    entry = func.append_basic_block("entry")
    builder = ir.IRBuilder(entry)

    # dummy switch else, switch end
    bbelse = builder.append_basic_block("switch.else")
    bbend = builder.append_basic_block("switch.end")
    switch = builder.switch(func.args[0], bbelse)
    with builder.goto_block(bbelse):
        builder.ret(ir.Constant(generate_type("float"), float(0)))
    with builder.goto_block(bbend):
        builder.ret(ir.Constant(generate_type("float"), float(0)))

    # build switch blocks
    for idx, arg in enumerate(undefined_args):
        bbi = builder.append_basic_block("switch.%d" % idx)
        switch.add_case(idx, bbi)
        with builder.goto_block(bbi):
            builder.ret(ir.Constant(generate_type("float"), float(arg)))

def generate_extern(ast, module, undefined_args):
    if ast["globid"] == "arg":
        generate_arg(ast, module, undefined_args)
    elif ast["globid"] == "argf":
        generate_argf(ast, module, undefined_args)
    else:  
        args = []
        ret_type = generate_type(ast["ret_type"])
        if "tdecls" in ast:
            for typ in ast["tdecls"]["types"]:
                args.append(generate_type(typ))

        fnty = ir.FunctionType(ret_type, args)
        func = ir.Function(module, fnty, name=ast["globid"])

def generate_externs(ast, module, undefined_args):
    if "externs" in ast:
        for extern in ast["externs"]:
            generate_extern(extern, module, undefined_args)

def generate_binop(ast, module, builder, variables):
    op = ast["op"]
    exptype = ast["exptype"]

    lhs = generate_exp(ast["lhs"], module, builder, variables)
    rhs = generate_exp(ast["rhs"], module, builder, variables)
    # load if it is a pointer
    # if lhs.type.is_pointer:
    #     lhs = builder.load(lhs)
    # if rhs.type.is_pointer:
    #     rhs = builder.load(rhs)
    lhs = load_var(builder, lhs)
    rhs = load_var(builder, rhs)

    if exptype == "bool":
        if op == "and":
            return builder.and_(lhs, rhs)
        elif op == "or":
            return builder.or_(lhs, rhs)
        else:
            if "int" in ast["lhs"]["exptype"]: 
                if op == "lt":
                    return builder.icmp_signed("<", lhs, rhs)
                elif op == "gt":
                    return builder.icmp_signed(">", lhs, rhs)
                elif op == "eq":
                    return builder.icmp_signed("==", lhs, rhs)
            elif "float" in ast["lhs"]["exptype"]:
                if op == "lt":
                    return builder.fcmp_ordered("<", lhs, rhs)
                elif op == "gt":
                    return builder.fcmp_ordered(">", lhs, rhs)
                elif op == "eq":
                    return builder.fcmp_ordered("==", lhs, rhs)
    elif "int" in exptype:
        if op == "add":
            return builder.add(lhs, rhs)
        elif op == "sub":
            return builder.sub(lhs, rhs)
        elif op == "mul":
            return builder.mul(lhs, rhs)
        elif op == "div":
            return builder.udiv(lhs, rhs)
    elif "float" in exptype:
        if op == "add":
            return builder.fadd(lhs, rhs)
        elif op == "sub":
            return builder.fsub(lhs, rhs)
        elif op == "mul":
            return builder.fmul(lhs, rhs)
        elif op == "div":
            return builder.fdiv(lhs, rhs)
    elif exptype == "void":
        pass

def generate_uop(ast, module, builder, variables):
    op = ast["op"]
    exptype = ast["exptype"]
    if op == "not":
        return builder.not_(generate_exp(ast["exp"], module, builder, variables))
    elif op == "minus":
        exp = generate_exp(ast["exp"], module, builder, variables)
        # if exp.type.is_pointer:
        #     exp = builder.load(exp)
        exp = load_var(builder, exp)
        if "float" in ast["exptype"]:
            return builder.fsub(ir.Constant(generate_type("float"), 0.0), exp)
        elif  "int" in ast["exptype"]:
            return builder.sub(ir.Constant(generate_type("int"), 0), exp)

def is_int(typ):
    return "int" in typ

def is_float(typ):
    return "float" in typ

def generate_caststmt(ast, module, builder, variables):
    typ = generate_type(ast["type"])
    exp = generate_exp(ast["exp"], module, builder, variables)
    # if exp.type.is_pointer:
    #     exp = builder.load(exp)
    exp = load_var(builder, exp)
    if is_int(ast["type"]) and is_int(ast["exp"]["exptype"]):
        exp = builder.trunc(exp, ir.IntType(32))
    elif is_int(ast["type"]) and is_float(ast["exp"]["exptype"]):
        exp = builder.fptoui(exp, ir.IntType(32))
    elif is_float(ast["type"])and is_float(ast["exp"]["exptype"]):
        exp = builder.fptrunc(exp, ir.FloatType())
    elif is_float(ast["type"]) and is_int(ast["exp"]["exptype"]):
        exp = builder.uitofp(exp, ir.FloatType())
    return exp

def generate_assign(ast, module, builder, variables):
    exp = generate_exp(ast["exp"], module, builder, variables)
    # if exp.type.is_pointer:
    #     exp = builder.load(exp)
    exp = load_var(builder, exp)
    # if ast["var"] == "$d":
    #     print("exp: ", exp, ";exp type: ", exp.type)
    #     print("var?:", ast["var"], "; variables[ast['var']]:", variables[ast["var"]], "; type?:", variables[ast["var"]].type)
    builder.store(exp, variables[ast["var"]])
    return variables[ast["var"]]

def generate_funccall(ast, module, builder, variables):
    # if ast["globid"] == "fib":
    #     for k,v in variables.items():
    #         print(k," : ",v)

    fn = module.get_global(ast["globid"])
    args = []
    if "params" not in ast or "exps" not in ast["params"]:
        pass
    else:
        for exp in ast["params"]["exps"]:
            args.append(generate_exp(exp, module, builder, variables))
        
        # Customize arg to the desired type
        for idx, arg, fn_arg in zip(list(range(len(args))), args, fn.args):
            arg = get_pointer(builder, arg)
            if type(arg.type) == type(fn_arg.type):
                args[idx] = arg
            else:
                if fn_arg.type.is_pointer:
                    if arg.type.is_pointer:
                        args[idx] = arg
                    else:
                        args[idx] = arg.as_pointer
                else:
                    if arg.type.is_pointer:
                        args[idx] = builder.load(arg)
                    else:
                        args[idx] = arg
    return builder.call(fn, args)

def generate_exp(ast, module, builder, variables):
    name = ast["name"]
    if name == "binop":
        return generate_binop(ast, module, builder, variables)
    elif name == "caststmt":
        return generate_caststmt(ast, module, builder, variables)
    elif name == "uop":
        return generate_uop(ast, module, builder, variables)
    elif name == "lit":
        return ir.Constant(generate_type(ast["exptype"]), ast["value"])
    elif name == "varval":
        return variables[ast["var"]] 
    elif name == "assign":
        return generate_assign(ast, module, builder, variables)
    elif name == "funccall":
        return generate_funccall(ast, module, builder, variables)

def generate_stmt(ast, module, builder, func, variables):
    name = ast["name"]
    if name == "blk":
        generate_blk(ast, module, builder, func, variables)
    elif name == "if":
        pred = generate_exp(ast["cond"], module, builder, variables)
        if "else_stmt" in ast:
            with builder.if_else(pred) as (then, otherwise):
                with then:
                    generate_stmt(ast["stmt"], module, builder, func, variables)
                with otherwise:
                    generate_stmt(ast["else_stmt"], module, builder, func, variables)
        else:
            with builder.if_then(pred):
                generate_stmt(ast["stmt"], module, builder, func, variables)
    elif name == "ret":
        if "exp" in ast:
            exp = generate_exp(ast["exp"], module, builder, variables)
            # if exp.type.is_pointer:
            #     exp = builder.load(exp)
            exp = load_var(builder, exp)
            builder.ret(exp)
        else:
            builder.ret_void()
    elif name == "vardeclstmt": 
        exp = generate_exp(ast["exp"], module, builder, variables)
        variables[ast["vdecl"]["var"]] = builder.alloca(exp.type)
        if "noalias" in ast["vdecl"]["type"]:
            variables[ast["vdecl"]["var"]].add_attribute("noalias")
        if "ref" not in ast["vdecl"]["type"]:
            exp = load_var(builder, exp)
        builder.store(exp, variables[ast["vdecl"]["var"]])
    elif name == "expstmt":
        generate_exp(ast["exp"], module, builder, variables)
    elif name == "while":
        loop_head = func.append_basic_block("loop.header")
        loop_body = func.append_basic_block("loop.body")
        loop_end = func.append_basic_block("loop.end")
        builder.branch(loop_head)
        builder.position_at_end(loop_head)
        cond = generate_exp(ast["cond"], module, builder, variables)
        builder.cbranch(cond, loop_body, loop_end)
        builder.position_at_end(loop_body)
        #loop body
        generate_stmt(ast["stmt"], module, builder, func, variables)
        #jump to loop head
        builder.branch(loop_head)
        builder.position_at_end(loop_end)
    elif name == "print":
        value = generate_exp(ast["exp"], module, builder, variables)
        if value.type.is_pointer:
            value = load_var(builder, value)
            if value.type == ir.FloatType():
                global_fmt = module.get_global("fstr_float")
                value = builder.fpext(value, ir.DoubleType(), name='float_double')
            elif value.type == ir.IntType(32):
                global_fmt = module.get_global("fstr_int")
            elif value.type == ir.IntType(1):
                global_fmt = module.get_global("fstr_int")
                value = builder.zext(value, ir.IntType(32), name='bool_int')
        elif value.type == ir.IntType(32):
            global_fmt = module.get_global("fstr_int")
        elif value.type == ir.IntType(1):
            global_fmt = module.get_global("fstr_int")
            value = builder.zext(value, ir.IntType(32), name='bool_int')
        else:
            global_fmt = module.get_global("fstr_float")
            value = builder.fpext(value, ir.DoubleType(), name='float_double')
        printf_func = module.get_global("printf")
        voidptr_ty = ir.IntType(8).as_pointer()
        fmt_arg = builder.bitcast(global_fmt, voidptr_ty)
        #call printf function
        builder.call(printf_func, [fmt_arg, value])
    elif name == "printslit":
        # construct c_str
        c_str_val = generate_slit(ast["string"]+"\0")
        c_str = builder.alloca(c_str_val.type)
        builder.store(c_str_val, c_str)
        printf_func = module.get_global("printf")
        global_fmt = module.get_global("fstr_slit")
        voidptr_ty = ir.IntType(8).as_pointer()
        fmt_arg = builder.bitcast(global_fmt, voidptr_ty)
        # Call print Function
        builder.call(printf_func, [fmt_arg, c_str])

def generate_blk(ast, module, builder, func, variables):
    if "contents" in ast:
        for stmt in ast["contents"]["stmts"]:
            generate_stmt(stmt, module, builder, func, variables)

def generate_func(ast, module):
    args_types = [] # the types of args in llvmlite
    args_names = [] # the names of args in llvmlite
    variables = {}  # the local vairables in the current function, key: variable name, value: variable type
    ret_type = generate_type(ast["ret_type"])
    if "vdecls" in ast:
        for vdecl in ast["vdecls"]["vars"]:
            args_types.append(generate_type(vdecl["type"]))
            args_names.append(vdecl["var"])

    # Adds function to module
    fnty = ir.FunctionType(ret_type, args_types)
    func = ir.Function(module, fnty, name=ast["globid"])

    # add_attribute("noalias")
    if "vdecls" in ast:
        for idx, vdecl in enumerate(ast["vdecls"]["vars"]):
            if "noalias" in vdecl:
                func.args[idx].add_attribute("noalias")
    
    # Adds entry block to the function
    entry_block = func.append_basic_block(name="entry")
    builder = ir.IRBuilder(entry_block)

    # Allocates function arguments
    for arg, name in zip(func.args, args_names):
        if arg.type.is_pointer:
            variables[name] = arg
        else:
            ptr = builder.alloca(arg.type)
            variables[name]= ptr
            builder.store(arg, ptr)
    
    if "blk" in ast:
        result = generate_blk(ast["blk"], module, builder, func, variables)

    # Returns void if return type is void
    if not builder.block.is_terminated:
        builder.ret_void()
    
def generate_funcs(ast, module):
    for func in ast["funcs"]:
        generate_func(func, module)

def generate_prog(ast, module, undefined_args):
    if "externs" in ast and len(ast) > 1:
        generate_externs(ast["externs"], module, undefined_args)

    generate_funcs(ast["funcs"], module)

def declare_printf(module):
    #declare printf
    voidptr_ty = ir.IntType(8).as_pointer()
    printf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
    printf = ir.Function(module, printf_ty, name="printf")
    #int type
    fmt1 = "%d\n\0"
    c_fmt1 = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt1)), bytearray(fmt1.encode("utf8")))
    global_fmt1 = ir.GlobalVariable(module, c_fmt1.type, name="fstr_int")
    global_fmt1.linkage = 'internal'
    global_fmt1.global_constant = True
    global_fmt1.initializer = c_fmt1
    #slit type
    fmt2 = "%s\n\0"
    c_fmt2 = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt2)), bytearray(fmt2.encode("utf8")))
    global_fmt2 = ir.GlobalVariable(module, c_fmt2.type, name="fstr_slit")
    global_fmt2.linkage = 'internal'
    global_fmt2.global_constant = True
    global_fmt2.initializer = c_fmt2
    #float type
    fmt3 = "%f\n\0"
    c_fmt3 = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt3)), bytearray(fmt3.encode("utf8")))
    global_fmt3 = ir.GlobalVariable(module, c_fmt3.type, name="fstr_float")
    global_fmt3.linkage = 'internal'
    global_fmt3.global_constant = True
    global_fmt3.initializer = c_fmt3

# The function called by ekcc.py
def generate_code(ast, undefined_args):
    module = ir.Module(name="prog")
    declare_printf(module)
    generate_prog(ast, module, undefined_args)
    return module

