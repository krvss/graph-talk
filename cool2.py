from ut import *
from debug import ProcessDebugger
import re

# Shared variables
LINE_NO = 'line_no'

# Constants
EOF = chr(255)

TOKEN_DICT = dict((
    ('CLASS', 'CLASS'),
    ('ELSE', 'ELSE'),
    ('FI', 'FI'),
    ('IF', 'IF'),
    ('IN', 'IN'),
    ('INHERITS', 'INHERITS'),
    ('LET', 'LET'),
    ('LOOP', 'LOOP'),
    ('POOL', 'POOL'),
    ('THEN', 'THEN'),
    ('WHILE', 'WHILE'),
    ('CASE', 'CASE'),
    ('ESAC', 'ESAC'),
    ('OF', 'OF'),
    ('=>', 'DARROW'),
    ('NEW', 'NEW'),
    ('ISVOID', 'ISVOID'),
    ('<-', 'ASSIGN'),
    ('NOT', 'NOT'),
    ('ERROR', 'ERROR'),
    ('LET_STMT', 'LET_STMT'),
    ('<=', 'LE')
))

SINGLE_CHAR_OP = ('@', '+', '-', '<', '{', '}', '.', ',', ':', ';', '(', ')', '=', '*', '/', '~')

# Regexes
INTEGER = '[0-9]+'
BOOLEAN = r'(t[r|R][u|U][e|E])|(f[a|A][l|L][s|S][e|E])'

IDENTIFIER = "[A-Za-z0-9_]*"
TYPE_ID = "[A-Z]" + IDENTIFIER
OBJECT_ID = "[a-z]" + IDENTIFIER

WHITE_SPACE = r'[ \f\t\v]+'
EOL = r'(\n\r|\r\n|\n){1}'

# Root -> Statement -> Boolean, Integer, Operator, Simple operator


def print_token(line_no, token, data=''):
    print '# %s %s %s' % (line_no, token, data)


def build_root():
    b = GraphBuilder('COOL program')
    statement = b.loop(True).select('Statement').current

    # Operators
    b.at(statement).parse_rel(TOKEN_DICT.keys(), ignore_case=True).act('Operator',
                              lambda line_no, last_parsed: print_token(line_no, TOKEN_DICT[last_parsed.upper()]))

    b.at(statement).parse_rel(SINGLE_CHAR_OP).act('Single Char Operator',
                              lambda line_no, last_parsed: print_token(line_no, last_parsed))

    # Integers
    b.at(statement).parse_rel(re.compile(INTEGER)).act('Integer',
                              lambda line_no, last_parsed: print_token(line_no, 'INT_CONST', last_parsed))

    # Booleans
    b.at(statement).parse_rel(re.compile(BOOLEAN)).act('Boolean',
                              lambda line_no, last_parsed: print_token(line_no, 'BOOL_CONST', last_parsed.upper()))

    # Object ID
    b.at(statement).parse_rel(re.compile(OBJECT_ID)).act('Object ID',
                              lambda line_no, last_parsed: print_token(line_no, 'OBJECTID', last_parsed))

    # Type ID
    b.at(statement).parse_rel(re.compile(TYPE_ID)).act('Object ID',
                              lambda line_no, last_parsed: print_token(line_no, 'TYPEID', last_parsed))

    # New line: increment the counter
    b.at(statement).parse_rel(re.compile(EOL)).act('New Line',
                              lambda line_no: {UPDATE_CONTEXT: {LINE_NO: line_no + 1}})

    # Skipping white space
    b.at(statement).parse_rel(re.compile(WHITE_SPACE), None)

    # Stopping
    b.at(statement).parse_rel(EOF, OK)

    return b.graph


root = build_root()

name = 'grading/all_else_true.cl.cool'

with open(name) as f:
    content = f.read()
    #content = 'eLSE'
    content += EOF
    parser = ParsingProcess2()
    #ProcessDebugger(parser, True)
    parser(root, text=content, line_no=1)