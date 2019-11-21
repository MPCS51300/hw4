import argparse, sys
import lexer, yacc, codeGen, binding
import yaml

def read_content(input_file):
    with open(input_file, 'r') as input:  
        content = input.read()
        return content

def write_to_file(output_file, content):
    if isinstance(output_file, str):
        with open(output_file, 'w') as output:  
            output.write(content)
    else:
        output_file.write(content)

parser = argparse.ArgumentParser(prog=sys.argv[0], 
                                 description='Compiler',
                                 usage="python3 ekcc.py [-h|-?] [-v] [-O] [-emit-ast|-emit-llvm] -o <output-file> <input-file>", 
                                 add_help=False)
parser.add_argument("-h", action="help", help="show this help message and exit")
parser.add_argument("-v", action="store_true", help="print information for debugging")
parser.add_argument("-O", action="store_true", help="enable optimization")
parser.add_argument("-emit-ast", action="store_true", default=False, help="generate AST")
parser.add_argument("-emit-llvm", action="store_true", default=False, help="generate LLVM IR")
parser.add_argument("-o", action="store", default=sys.stdout, help="set output file path")
parser.add_argument("input_file", help = "ek file to be compiled")
args, undefined = parser.parse_known_args()

exitcode = 0

if args.emit_ast and args.emit_llvm:
    raise Exception("Cannot emit_ast and emit_llvm at the same time")
else:
    content = read_content(args.input_file)
    ast, err_message = yacc.parse(content)
    if err_message != None:
        print(err_message)
        print("exit code: "+str(1))
        sys.exit(1)
    if args.emit_ast:
        write_to_file(args.o,  yaml.dump(ast))
    mod = codeGen.generate_code(ast, undefined)
    mod = binding.compile_and_execute(mod)
    if args.emit_llvm:
        write_to_file(args.o, mod)

print("exit code: "+str(exitcode))