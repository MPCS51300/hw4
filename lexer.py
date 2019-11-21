import ply.lex as lex

reserved = {
    'int' : 'INT',
    'cint' : 'CINT',
    'float' : 'FLOAT',
    'bool' : 'BOOL',
    'void' : 'VOID',
    'ref' : 'REF',
    'noalias' : 'NOALIAS',
    'return' : 'RETURN',
    'while' : 'WHILE',
    'if' : 'IF',
    'else' : 'ELSE',
    'print' : 'PRINT',
    'def' : 'DEF',
    "extern" : 'EXTERN',
    "true" : 'TRUE',
    "false" : 'FALSE'
 }

tokens = list(reserved.values()) + [
    #number
    'FNUMBER', 'NUMBER',
    # arithmetic
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'ASSIGN',
    # compare
    'EQUAL', 'GREATERTHAN', 'SMALLERTHAN', 
    # logical operations
    'AND', 'OR', 'NEGATE',
    # (),{},[]
    'LPARENTHESE', 'RPARENTHESE', 'LBRACE', 'RBRACE', 'LBRACKET', 'RBRACKET',
    # delimiter
    'COMMA', 'SEMICOLON',
    # slit
    'SLIT',
    # ident
    'IDENT',
    # varid
    'VARID'
]

# arithmetic
t_PLUS = r"\+"
t_MINUS = r'\-'
t_TIMES = r'\*'
t_DIVIDE = r'\/'
t_ASSIGN = r'\='
# compare
t_EQUAL = r'\=\='
t_GREATERTHAN = r'\>'
t_SMALLERTHAN = r'\<'
# logical operations
t_AND = r'\&\&'
t_OR = r'\|\|'
t_NEGATE = r'\!'
# (),{},[]
t_LPARENTHESE = r'\('
t_RPARENTHESE = r'\)'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'
# delimiter
t_COMMA = r'\,'
t_SEMICOLON = r'\;'

t_ignore  = ' \t'

t_VARID = r'\$[a-zA-Z_][a-zA-Z_0-9]*'

def t_SLIT(t):
    r'"[^"\n\r]*"'
    t.value = str(t.value)[1:-1]
    return t

def t_newline(t):
    r'[\n\r]+'
    t.lexer.lineno += 1
    pass

def t_error(t):
    print("Illegal characters: " + t.value[0])
    t.lexer.skip(1)

def t_IDENT(t):
    r'[a-zA-Z_]+[a-zA-Z_0-9]*'
    t.type = reserved.get(t.value, "IDENT")
    return t

def t_FNUMBER(t):
    r'\d+[\.]\d+'
    t.value = float(t.value)
    return t 

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_comments(t):
    r'\#[^\r\n]*'
    pass

lexer = lex.lex()