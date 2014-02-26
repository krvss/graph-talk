from ut import *
from debug import ProcessDebugger
import re

# Shared variables
LINE_NO = 'line_no'
ERROR_TOKEN = 'ERROR'

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
    (ERROR_TOKEN, ERROR_TOKEN),
    ('LET_STMT', 'LET_STMT'),
    ('<=', 'LE')
))

SINGLE_CHAR_OP = ('@', '+', '-', '<', '{', '}', '.', ',', ':', ';', '(', ')', '=', '*', '/', '~')

# Regexes

IDENTIFIER = "[A-Za-z0-9_]*"

R_BOOLEAN = re.compile('(t[r|R][u|U][e|E])|(f[a|A][l|L][s|S][e|E])')

R_INTEGER = re.compile('[0-9]+')

R_WHITE_SPACE = re.compile('[ \f\t\v]+')
R_EOL = re.compile('(\n\r|\r\n|\n){1}')
R_ANY_CHAR = re.compile('.')

R_OBJECT_ID = re.compile('[a-z]' + IDENTIFIER)
R_TYPE_ID = re.compile('[A-Z]' + IDENTIFIER)


# Graph builder
builder = GraphBuilder('COOL program')


def print_token(line_no, token, data=''):
    print '# %s %s %s' % (line_no, token, data)


def print_and_error(line_no, token, data=''):
    print_token(line_no, token, data)

    if token == ERROR_TOKEN:
        return ERROR


def inc_line_no(line_no):
    return {UPDATE_CONTEXT: {LINE_NO: line_no + 1}}


def build_root():
    global builder
    statement = builder.loop(True).select('Statement').current

    # Operators
    builder.at(statement).parse_rel(TOKEN_DICT.keys(), ignore_case=True).act('Operator',
                                   lambda line_no, last_parsed: print_token(line_no, TOKEN_DICT[last_parsed.upper()]))

    builder.at(statement).parse_rel(SINGLE_CHAR_OP).act('Single Char Operator',
                                   lambda line_no, last_parsed: print_token(line_no, last_parsed))

    # Integers
    builder.at(statement).parse_rel(R_INTEGER).act('Integer',
                                   lambda line_no, last_parsed: print_token(line_no, 'INT_CONST', last_parsed))

    # Booleans
    builder.at(statement).parse_rel(R_BOOLEAN).act('Boolean',
                                   lambda line_no, last_parsed: print_token(line_no, 'BOOL_CONST', last_parsed.upper()))

    # Object ID
    builder.at(statement).parse_rel(R_OBJECT_ID).act('Object ID',
                                   lambda line_no, last_parsed: print_token(line_no, 'OBJECTID', last_parsed))

    # Type ID
    builder.at(statement).parse_rel(R_TYPE_ID).act('Object ID',
                                   lambda line_no, last_parsed: print_token(line_no, 'TYPEID', last_parsed))

    # New line: increment the counter
    builder.at(statement).parse_rel(R_EOL).act('New Line', inc_line_no)

    # Skipping white space
    builder.at(statement).parse_rel(R_WHITE_SPACE, None)

    # Complex notions
    add_inline_comment(statement)
    add_multiline_comment(statement)

    # Errors
    add_errors(statement)

    # Stopping
    builder.at(statement).parse_rel(EOF, OK)


# One-line comment notion
def add_inline_comment(statement):
    builder.at(statement).parse_rel('--').complex('Inline comment')
    inline_comment_chars = builder.loop('*').select('Inline comment chars').current

    builder.at(inline_comment_chars).parse_rel([R_EOL, EOF], BREAK).check_only()  # No need to parse here, just done
    builder.at(inline_comment_chars).parse_rel(R_ANY_CHAR).default()  # Just skip


# Multi-line comment notion
def add_multiline_comment(statement):
    multiline_comment = builder.at(statement).parse_rel('(*').complex('Multi-line comment').current
    multiline_comment_body = builder.loop('*').select('Multi-line comment body').current
    builder.at(multiline_comment).parse_rel('*)')  # It is necessary to have the comment closed

    builder.at(multiline_comment_body).parse_rel(R_EOL).act('New Line in comment', inc_line_no)
    builder.at(multiline_comment_body).parse_rel(EOF).act('EOF in comment',
                                          lambda line_no: print_and_error(line_no, ERROR_TOKEN, 'EOF in comment'))

    builder.at(multiline_comment_body).parse_rel('(*', statement.owner.notion('Multi-line comment'))  # Nested comment
    builder.at(multiline_comment_body).parse_rel('*)').check_only().act('End Multi-line comment', BREAK)  # Done with the body

    builder.at(multiline_comment_body).parse_rel(R_ANY_CHAR).default()  # Consuming chars (gulp!)


def add_errors(statement):
    builder.at(statement).parse_rel('*)').act('Unmatched multi-line',
                                          lambda line_no: print_and_error(line_no, ERROR_TOKEN, 'Unmatched multi-line'))



build_root()

root = builder.graph

name = 'grading/all_else_true.cl.cool'

with open(name) as f:
    #content = f.read()
    content = '''(* (* *) \n*) 2 -- lol \n 3'''
    content += EOF
    parser = ParsingProcess2()
    #ProcessDebugger(parser, True)
    parser(root, text=content, line_no=1)