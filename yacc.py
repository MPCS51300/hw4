import ply.yacc as yacc
import lexer
import json, sys

tokens = lexer.tokens 

#######
# Parser
#######

class Func():
    def __init__(self, name, return_type, args):
        self.name = name
        self.return_type = return_type
        self.args = args
    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, 
            indent=4)

class CompilerException(Exception):
    def __init__(self, m):
        self.message = m

funcs_declare = {} 
variables = {}
current_func_prefix = None

logicOps = ["eq", "gt", "lt", "and", "or"]
arithOps = ["add", "sub",  "mul", "div"]
uOps = ["not", "minus"]

precedence = (
    ('right', 'ASSIGN'),
    ('left', 'OR'),
    ('left', 'AND'),
    ('left', 'EQUAL'),
    ('left', 'SMALLERTHAN', 'GREATERTHAN'), 
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
    ('right', 'NEGATE', 'UMINUS'),
 )

def p_prog(p):
    '''
    prog : externs funcs
    '''
    p[0] = {"name" : "prog"}
    p[0]["externs"] = p[1]
    p[0]["funcs"] = p[2]

def p_externs(p):
    '''
    externs : 
            | extern
            | extern externs
    '''
    p[0] = {"name" : "externs"}
    if len(p) >= 2:
        p[0]["externs"] = [p[1]]
    if len(p) == 3:
        if "externs" in p[2]:
            p[0]["externs"].extend(p[2]["externs"])

def p_funcs(p):
    '''
    funcs : func
          | func funcs
    '''
    p[0] = {"name" : "funcs"}
    p[0]["funcs"] =[p[1]]
    if len(p) == 3:
        if "funcs" in p[2]:
            p[0]["funcs"].extend(p[2]["funcs"])

def p_extern(p):
    '''
    extern : EXTERN type globid LPARENTHESE RPARENTHESE SEMICOLON
           | EXTERN type globid LPARENTHESE tdecls RPARENTHESE SEMICOLON
    '''
    p[0] = {"name" : "extern"}
    p[0]["ret_type"] = p[2]
    p[0]["globid"]  = p[3]
    if len(p) == 8:
        p[0]["tdecls"] = p[5]

def p_func(p):
    '''
    func : DEF type globid LPARENTHESE RPARENTHESE blk
         | DEF type globid LPARENTHESE vdecls RPARENTHESE blk
    '''
    p[0] = {"name" : "func"}
    p[0]["ret_type"] = p[2]
    p[0]["globid"]  = p[3]
    if len(p) == 7:
        p[0]["blk"] = p[6]
    if len(p) == 8:
        p[0]["vdecls"] = p[5]
        p[0]["blk"] = p[7]


    

def p_blk(p):
    '''
    blk : LBRACE RBRACE
        | LBRACE stmts RBRACE
    '''
    p[0] = {"name" : "blk"}
    if len(p) == 4:
        p[0]["contents"] = p[2]


def p_stmts(p):
    '''
    stmts : stmt
          | stmt stmts
    '''
    p[0] = {"name" : "stmts"}
    p[0]["stmts"] = [p[1]]
    if len(p) == 3:
        if "stmts" in p[2]:
            p[0]["stmts"].extend(p[2]["stmts"])

def p_stmt0(p):
    '''
    stmt : blk
         | RETURN SEMICOLON
         | RETURN exp SEMICOLON
         | vdecl ASSIGN exp SEMICOLON
         | exp SEMICOLON
         | WHILE LPARENTHESE exp RPARENTHESE stmt
         | IF LPARENTHESE exp RPARENTHESE stmt
         | IF LPARENTHESE exp RPARENTHESE stmt ELSE stmt
         | PRINT exp SEMICOLON
    '''
    p[0] = {}
    if len(p) == 2:
        p[0] = p[1]
    elif p[1] == "return":
        p[0]["name"] = "ret"
        if len(p) == 4:
            p[0]["exp"] = p[2]
    elif len(p) == 5:
        p[0]["name"] = "vardeclstmt"
        p[0]["vdecl"] = p[1]
        p[0]["exp"] = p[3]
    elif len(p) == 3:
        p[0]["name"] = "expstmt"
        p[0]["exp"] = p[1]
    elif p[1] == "while":
        p[0]["name"] = "while"
        p[0]["cond"] = p[3]
        p[0]["stmt"] = p[5]
    elif p[1] == "if":
        p[0]["name"] = "if"
        p[0]["cond"] = p[3]
        p[0]["stmt"] = p[5]
        if len(p) == 8:
            p[0]["else_stmt"] = p[7]
    elif p[1] == "print":
        p[0]["name"] = "print"
        p[0]["exp"] = p[2]

def p_stmt1(p):
    '''
    stmt : PRINT SLIT SEMICOLON
    '''
    p[0] = {"name" : "printslit", "string" : p[2]}

def p_exps(p):
    '''
    exps : exp
         | exp COMMA exps
    ''' 
    p[0] = {"name" : "exps"}
    if len(p) >= 2:
        p[0]["exps"] = [p[1]]    
    if len(p) == 4:
        if "exps" in p[3]:
            p[0]["exps"].extend(p[3]["exps"])

def p_exp0(p):
    '''
    exp : LPARENTHESE exp RPARENTHESE
        | binop
        | uop
        | globid LPARENTHESE exps RPARENTHESE
        | globid LPARENTHESE RPARENTHESE
    '''
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 5:
        p[0] = {
            "name": "funccall",
            "globid": p[1],
            "params": p[3]
        }
    elif p[1] == "(":
        p[0] = p[2]
    else:
        p[0] = {
            "name": "funccall",
            "globid": p[1],
        }

def p_exp1(p):
    '''
    exp : VARID
    '''
    p[0] = {
        "name": "varval",
        "var": p[1]
    }

def p_exp2(p):
    '''
    exp : lit
    '''
    p[0] = p[1]

def p_binop(p):
    '''
    binop : arith-ops
          | logic-ops
          | VARID ASSIGN exp
          | LBRACKET type RBRACKET exp
    '''
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 4:
        p[0] = {
            "name": "assign",
            "var": p[1],
            "exp": p[3],
            "exptype": "assign"
        }
    else:
        p[0] = {
            "name": "caststmt",
            "type": p[2],
            "exp": p[4]
        }

def p_arithOps(p):
    '''
    arith-ops : exp TIMES exp
              | exp DIVIDE exp
              | exp PLUS exp
              | exp MINUS exp
    '''
    op = ""
    if p[2] == '+':
        op = "add"
    elif p[2] == '-':
        op = "sub"
    elif p[2] == '*':
        op = "mul"
    elif p[2] == '/':
        op = "div"
    p[0] = {
        "name": "binop",
        "op": op,
        "lhs": p[1],
        "rhs": p[3]
    }

def p_logicOps(p):
    '''
    logic-ops : exp EQUAL exp
              | exp SMALLERTHAN exp
              | exp GREATERTHAN exp
              | exp AND exp
              | exp OR exp
    '''
    op = ""
    if p[2] == "==":
        op = "eq"
    elif p[2] == "<":
        op = "lt"
    elif p[2] == ">":
        op = "gt"
    elif p[2] == "&&":
        op = "and"
    elif p[2] == "||":
        op = "or"
    p[0] = {
        "name": "binop",
        "op": op,
        "lhs": p[1],
        "rhs": p[3]
    }


def p_uop(p):
    '''
    uop : NEGATE exp 
        | MINUS exp %prec UMINUS
    '''
    if p[1]=='!':
        p[0] = {
            "name": "uop",
            "op": "not",
            "exp": p[2]
        }
    else:
        p[0] = {
            "name": "uop",
            "op": "minus",
            "exp": p[2]
        }

def p_lit0(p):
    '''
    lit : true
        | false
    '''
    p[0] = p[1]

def p_lit1(p):
    '''
    lit : FNUMBER
    '''
    p[0] = {
        "name": "lit",
        "value": p[1],
        "exptype": "float"
    }

def p_lit2(p):
    '''
    lit : NUMBER
    '''
    p[0] = {
        "name": "lit",
        "value": p[1],
        "exptype": "int"
    }

def p_true(p):
    '''
    true : TRUE
    '''
    p[0] = {
        "name": "lit",
        "value": p[1] == "true",
        "exptype": "bool"
    }

def p_false(p):
    '''
    false : FALSE
    '''
    p[0] = {
        "name": "lit",
        "value": p[1] == "true",
        "exptype": "bool"
    }

def p_globid(p):
    '''
    globid : IDENT
    '''
    p[0] = p[1]

def p_type(p):
    '''
    type : INT
         | CINT
         | FLOAT
         | BOOL
         | VOID
    '''
    p[0] = p[1]

def p_refType(p):
    '''
    type : REF type
    '''
    p[0] = 'ref ' + p[2]

def p_noAliasRefType(p):
    '''
    type : NOALIAS REF type
    '''
    p[0] = 'noalias ref ' + p[3]

def p_vdecls(p):
    '''
    vdecls : vdecl COMMA vdecls
           | vdecl
    '''
    p[0] = {"name" : "vdecls"}
    if len(p) >= 2:
        p[0]["vars"] = [p[1]]    
    if len(p) == 4:
        if "vars" in p[3]:
            p[0]["vars"].extend(p[3]["vars"])

def p_tdecls(p):
    '''
    tdecls : type
           | type COMMA tdecls
    '''
    p[0] = {"name" : "tdecls"}
    if len(p) >= 2:
        p[0]["types"] = [p[1]]    
    if len(p) == 4:
        if "types" in p[3]:
            p[0]["types"].extend(p[3]["types"])

def p_vdecl(p):
    '''
    vdecl : type VARID
    '''
    p[0] = {
        "node": "vdecl",
        "type": p[1],
        "var": p[2]
    }

def not_same_type(left_type, right_type):
    ltype = left_type.split()[-1]
    rtype = right_type.split()[-1]
    return ltype != rtype

def can_cast(cast_type, exp_type):
    exp_type = exp_type.split()[-1] # get the type if exp_type is ref type
    if cast_type == exp_type:
        return True
    elif cast_type in ["int", "cint", "float"] and exp_type in ["int", "cint", "float"]:
        return True
    elif cast_type == "bool" and exp_type == "bool":
        return True
    else:
        return False

def check_violation(node):
    global funcs_declare
    global current_func_prefix
    global variables
    global logicOps
    global arithOps
    global uOps

    if type(node) is list:
        for v in node:
            check_violation(v)

    elif type(node) is dict:
        #Check: <vdecl> may not have void type.
        #Check: a ref type may not contain a 'ref' or 'void' type.
        if "node" in node:
            if node["type"] == "void":
                raise CompilerException("error: <vdecl> type cannot be void")
            elif "noalias" not in node["type"]:
                if "ref" in node["type"][3:] or "void" in node["type"][3:]:
                    raise CompilerException("error: a ref type may not contain a 'ref' or 'void' type.")
            elif "noalias" in node["type"]:
                if "ref" in node["type"][11:] or "void" in node["type"][11:]:
                    raise CompilerException("error: a ref type may not contain a 'ref' or 'void' type.")
            if current_func_prefix != None:
                variables[current_func_prefix+" "+node["var"]] = node["type"]
            else:
                variables[node["var"]] = node["type"]
        
        if "name" in node:
            #store exptype in node
            if node["name"] == "varval":
                varval_key = current_func_prefix + " " + node["var"]
                if varval_key not in variables:
                    raise CompilerException("error: variable " + node["var"] + " has not been declared")
                node["exptype"] = variables[varval_key]

            #Check: ref var initializer must be a variable.
            elif node["name"] == "vardeclstmt":
                if "exp" not in node or "vdecl" not in node:
                    raise CompilerException("error: ref var initializer must be a variable.")
                elif "name" not in node["exp"]:
                    raise CompilerException("error: ref var initializer must be a variable.")
                elif "type" not in node["vdecl"]:
                    raise CompilerException("error: ref var initializer must be a variable.")
                elif node["vdecl"]["type"][0:3] == "ref" and node["exp"]["name"] != "varval":
                    raise CompilerException("error: ref var initializer must be a variable.")

            #Check: all functions must be declared before use
            elif node["name"] == "funccall":
                if node["globid"] not in funcs_declare:
                    raise CompilerException("error: function " + node["globid"] + " has not been declared")
                if "params" in node and "exps" in node["params"]:
                    for x in range(len(node["params"]["exps"])):
                        if "ref" in funcs_declare[node["globid"]].args[x] and node["params"]["exps"][x]["name"] != "varval":
                            raise CompilerException("error: ref var initializer must be a variable.")
                node["exptype"] = funcs_declare[node["globid"]].return_type

            #Check: a function may not return a ref type.
            #Check: all programs define the "run" function with the right type.
            elif node["name"] == "func":
                args=[]
                if node["globid"] == "run":
                    if "run" in funcs_declare:
                        raise CompilerException("error: run function should only declare once")
                    elif node['ret_type'] != "int":
                        raise CompilerException("error: run function should only return int type")
                    elif "vdecls" in node:
                        raise CompilerException("error: run function should take no arguments")
                else:
                    if "ref" in node['ret_type']:
                        raise CompilerException("error: function cannot return ref type")
                    if "vdecls" in node:
                        for arg in node["vdecls"]["vars"]:
                            args.append(arg["type"])
                funcs_declare[node["globid"]] = Func(node["globid"], node['ret_type'], args)
                current_func_prefix = node["ret_type"]+" "+node["globid"]

            elif node["name"] == "extern":
                args=[]
                if "tdecls" in node and "types" in node["tdecls"]:
                    args = node["tdecls"]["types"]
                funcs_declare[node["globid"]] = Func(node["globid"], node['ret_type'], args)

        #visit children node
        for k, v in node.items():
            if v is list or dict:
                check_violation(v)

        #Check: the types on both sides of binops are the same
        if "op" in node:
            if node["op"] in logicOps:
                if not_same_type(node["lhs"]["exptype"], node["rhs"]["exptype"]):
                    raise CompilerException("error: the type on two sides do not match")
                node["exptype"] = "bool"

            elif node["op"] in arithOps:
                if not_same_type(node["lhs"]["exptype"], node["rhs"]["exptype"]):
                    raise CompilerException("error: the type on two sides do not match")
                node["exptype"] = node["rhs"]["exptype"]

            elif node["op"] in uOps:
                node["exptype"] = node["exp"]["exptype"]

        if "name" in node:
            if node["name"] == "assign":
                if current_func_prefix is not None:
                    var_key = current_func_prefix + " " + node["var"]
                else:
                    var_key = node["var"]
                if var_key not in variables:
                    raise CompilerException("error: variable " + node["var"] + " has not been declared")
                temp = node
                while temp["exp"]["exptype"] == "assign":
                    temp = temp["exp"]
                if not_same_type(variables[var_key], temp["exp"]["exptype"]):
                    raise CompilerException("error: the type on two sides do not match")
            
            elif node["name"] == "caststmt":
                if can_cast(node["type"], node["exp"]["exptype"]):
                    node["exptype"] = node["type"]
                else:
                    raise CompilerException("error: cannot cast {} to {}", node["exp"]["exptype"], node["type"])

            elif node["name"] == "func":
                for k, v in variables.copy().items():
                    if k.startswith(current_func_prefix):
                        variables.pop(k)
                current_func_prefix = None

def check_run():
    global funcs_declare
    if "run" not in funcs_declare:
        raise CompilerException("error: run function should be declared once.")

# The function called by ekcc.py
def parse(input_content):
    parser = yacc.yacc()
    result = parser.parse(input_content)

    #Compiler ruturns ( ast tree, error message) 
    try:
        check_violation(result)
        check_run()
    except CompilerException as e:
        return (None, e.message)

    return (result, None)

    
