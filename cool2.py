from ut import *
from debug import ProcessDebugger
import re

# Shared variables
LINE_NO = 'line_no'
ERROR_TOKEN = 'ERROR'
STRING_BODY = 'string_body'

# Constants
EOF = chr(255)
ZERO_CHAR = chr(0)
MAX_STR_CONST = 1

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
IDENTIFIER = '[A-Za-z0-9_]*'
EOL = '(\n\r|\r\n|\n){1}'
ESC_EOL = r'\\' + EOL

R_BOOLEAN = re.compile('(t[r|R][u|U][e|E])|(f[a|A][l|L][s|S][e|E])')

R_INTEGER = re.compile('[0-9]+')

R_WHITE_SPACE = re.compile('[ \f\t\v]+')

R_EOL = re.compile(EOL)
R_ESC_EOL = re.compile(ESC_EOL)

R_ANY_CHAR = re.compile('.')

R_OBJECT_ID = re.compile('[a-z]' + IDENTIFIER)
R_TYPE_ID = re.compile('[A-Z]' + IDENTIFIER)


# Graph builder
builder = GraphBuilder('COOL program')


def print_token(line_no, token, data=''):
    print '# %s %s %s' % (line_no, token, data)


def print_and_error(line_no, token, data=''):  # TODO Generalize
    print_token(line_no, token, data)

    if token == ERROR_TOKEN:
        return ERROR


def inc_line_no(line_no, inc=1):
    return {UPDATE_CONTEXT: {LINE_NO: line_no + inc}}


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
    builder.at(statement).parse_rel(R_WHITE_SPACE)

    # Complex notions
    add_inline_comment(statement)
    add_multiline_comment(statement)
    add_strings(statement)

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
    builder.at(statement).parse_rel('(*').complex('Multi-line comment')
    multiline_comment_body = builder.loop('*').select('Multi-line comment body').current

    builder.at(multiline_comment_body).parse_rel(R_EOL, inc_line_no)
    builder.at(multiline_comment_body).parse_rel(EOF).act('EOF in comment',
                                                lambda line_no: print_and_error(line_no, ERROR_TOKEN, 'EOF in comment'))

    builder.at(multiline_comment_body).parse_rel('(*', statement.owner.notion('Multi-line comment'))  # Nested comment
    builder.at(multiline_comment_body).parse_rel('*)', BREAK)

    builder.at(multiline_comment_body).parse_rel(R_ANY_CHAR).default()  # Consuming chars (gulp!)


# Strings
def add_to_string(line_no, last_parsed, string_body):
    if not string_body:
        string_body = ''
    else:
        if len(string_body) == MAX_STR_CONST:
            return skip_string, print_token(line_no, ERROR_TOKEN, 'String constant too long')  # Too much!

    string_body += last_parsed
    return {UPDATE_CONTEXT: {STRING_BODY: string_body}}


def skip_string(line_no, text):
    end = re.search(r'[^\\]' + EOL, text)
    end_pos = end.span()[1] + 1 if end else len(text) - 2
    lines_count = len(re.findall(R_ESC_EOL, text[:end_pos]))

    if end_pos:
        lines_count += 1

    if lines_count:
        res = [inc_line_no(line_no, lines_count)]
    else:
        res = []

    res += [{PROCEED: end_pos}, BREAK]  # Keep the last char for further processing

    return res


def out_string(line_no, string_body):
    print_token(line_no, 'STR_CONST', string_body)
    return {DELETE_CONTEXT: STRING_BODY}


# String notion
def add_strings(statement):
    builder.at(statement).parse_rel('"').complex('String')
    string_chars = builder.loop('*').select('String char').current

    # If EOL matched stop the string
    builder.at(string_chars).parse_rel(R_EOL).check_only().act('Unescaped EOL',
        lambda line_no: [print_and_error(line_no, ERROR_TOKEN, 'Unterminated string constant'), skip_string])

    # If 0 character matched - skip the rest of the string
    builder.at(string_chars).parse_rel(ZERO_CHAR).act_rel(
        lambda line_no: [print_and_error(line_no, ERROR_TOKEN, 'String contains null character.'), skip_string])

    builder.at(string_chars).parse_rel('"', BREAK)

    # Just a good char
    builder.at(string_chars).parse_rel(R_ANY_CHAR, add_to_string)





def add_errors(statement):
    builder.at(statement).parse_rel('*)').act('Unmatched multi-line',
                                          lambda line_no: print_and_error(line_no, ERROR_TOKEN, 'Unmatched multi-line'))


#p = ParsingProcess2()
#r = p(1)

build_root()

root = builder.graph

name = 'grading/nestedcomment.cool'

with open(name) as f:
    #content = f.read()
    #content = '''"qb\\\na\n"1'''
    content = '''"q\\\nb\\\ndddd"1'''
    #content = '''(* \n '''
    content += EOF
    parser = ParsingProcess2()
    #ProcessDebugger(parser, True)
    parser(root, text=content, line_no=1)