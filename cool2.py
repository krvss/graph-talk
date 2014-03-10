from ut import *
from debug import ProcessDebugger
import re
import sys

# Shared variables
LINE_NO = 'line_no'
ERROR_TOKEN = 'ERROR'
STRING_CONST = 'STR_CONST'

STRING_BODY = 'string_body'
STRING_ERROR = 'string_error'

# Constants
EOF = chr(255)
ZERO_CHAR = chr(0)
MAX_STR_CONST = 1024

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

result = ''

def print_token(line_no, token, data=''):
    global result

    if token in (ERROR_TOKEN, STRING_CONST):
        data = data.replace("\\", "\\\\")
        data = data.replace("\n", r"\n").replace("\t", r"\t").replace("\b", r"\b").\
               replace("\f", r"\f").replace('"', '\\"').replace('\r', '\\015').replace('\033', '\\033').\
               replace('\01', '\\001').replace('\02', '\\002').replace('\03', '\\003').replace('\04', '\\004').\
               replace('\00', '\\000').replace('\22', '\\022').replace('\13', '\\013')

        data = '"' + data + '"'

    result += '#%s %s %s\n' % (line_no, token, data) if data else '#%s %s\n' % (line_no, token)


def inc_line_no(line_no, inc=1):
    return {UPDATE_CONTEXT: {LINE_NO: line_no + inc}}


def build_root():
    global builder
    statement = builder.loop(True).select('Statement').current

    # Operators
    builder.at(statement).parse_rel(TOKEN_DICT.keys(), ignore_case=True).\
        act('Operator', lambda line_no, last_parsed: print_token(line_no, TOKEN_DICT[last_parsed.upper()]))

    builder.at(statement).parse_rel(SINGLE_CHAR_OP).\
        act('Single Char Operator', lambda line_no, last_parsed: print_token(line_no, '\'' + last_parsed + '\''))

    # Integers
    builder.at(statement).parse_rel(R_INTEGER).\
        act('Integer', lambda line_no, last_parsed: print_token(line_no, 'INT_CONST', last_parsed))

    # Booleans
    builder.at(statement).parse_rel(R_BOOLEAN).\
        act('Boolean', lambda line_no, last_parsed: print_token(line_no, 'BOOL_CONST', last_parsed.lower()))

    # Object ID
    builder.at(statement).parse_rel(R_OBJECT_ID).\
        act('Object ID', lambda line_no, last_parsed: print_token(line_no, 'OBJECTID', last_parsed))

    # Type ID
    builder.at(statement).parse_rel(R_TYPE_ID).\
        act('Object ID', lambda line_no, last_parsed: print_token(line_no, 'TYPEID', last_parsed))

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
    builder.at(inline_comment_chars).parse_rel(R_ANY_CHAR).default()  # Skip the chars


# Multi-line comment notion
def add_multiline_comment(statement):
    builder.at(statement).parse_rel('(*').complex('Multi-line comment')
    multiline_comment_body = builder.loop(True).select('Multi-line comment body').current

    builder.at(multiline_comment_body).parse_rel(R_EOL, inc_line_no)
    builder.at(multiline_comment_body).parse_rel(EOF).check_only().\
        act('EOF in comment', lambda line_no: [print_token(line_no, ERROR_TOKEN, 'EOF in comment'), BREAK])

    builder.at(multiline_comment_body).parse_rel('(*', statement.owner.notion('Multi-line comment'))  # Nested comment
    builder.at(multiline_comment_body).parse_rel('*)', BREAK)

    builder.at(multiline_comment_body).parse_rel(R_ANY_CHAR).default()  # Consuming chars (gulp!)


# Strings
# Adding character to the string
def add_to_string(last_parsed, string_body, string_error):
    if not string_body:
        string_body = ''
    else:
        if len(string_body) == MAX_STR_CONST:
            return {UPDATE_CONTEXT: {STRING_ERROR: 'overflow'}} if not string_error else None

    return {UPDATE_CONTEXT: {STRING_BODY: string_body + last_parsed}}


# Print the string and clean-up
def out_string(line_no, string_body, string_error):
    if string_error == 'unescaped_eol':
        print_token(line_no + 1, ERROR_TOKEN, 'Unterminated string constant')
    elif string_error == 'null_char':
        print_token(line_no, ERROR_TOKEN, 'String contains null character.')
    elif string_error == 'null_char_esc':
        print_token(line_no, ERROR_TOKEN, 'String contains escaped null character.')
    elif string_error == 'overflow':
        print_token(line_no, ERROR_TOKEN, 'String constant too long')
    elif string_error == 'eof':
        print_token(line_no, ERROR_TOKEN, 'EOF in string constant')
    else:
        if not string_body:
            string_body = ''
        print_token(line_no, STRING_CONST, string_body)

    return {DELETE_CONTEXT: [STRING_BODY, STRING_ERROR]}


# String notion itself
def add_strings(statement):
    string = builder.at(statement).parse_rel('"').complex('String').current
    string_chars = builder.loop(True).select('String chars').current
    builder.at(string).next_rel().act('Out string', out_string)

    # 0 character error
    builder.at(string_chars).parse_rel(ZERO_CHAR).act('Null character error',
                                                      lambda line_no: {UPDATE_CONTEXT: {STRING_ERROR: 'null_char'}})

    # If EOL matched stop the string with error or just break
    builder.at(string_chars).parse_rel(R_EOL).\
        check_only().act('EOL', lambda string_error: [BREAK if string_error else None,
                                                      {UPDATE_CONTEXT: {STRING_ERROR: 'unescaped_eol'}}, BREAK])
    # TODO: overriding errors
    # Stop if EOF
    builder.at(string_chars).parse_rel(EOF).\
        check_only().act('EOF error', lambda line_no: [{UPDATE_CONTEXT: {STRING_ERROR: 'eof'}}, BREAK])

    # Escapes
    escapes = builder.at(string_chars).parse_rel('\\').select('Escapes').current
    builder.at(escapes).parse_rel(R_EOL,
                  lambda string_body, string_error: tupled(add_to_string('\n', string_body, string_error), inc_line_no))

    builder.at(escapes).parse_rel('n', lambda string_body, string_error: add_to_string('\n', string_body, string_error))
    builder.at(escapes).parse_rel('t', lambda string_body, string_error: add_to_string('\t', string_body, string_error))
    builder.at(escapes).parse_rel('b', lambda string_body, string_error: add_to_string('\b', string_body, string_error))
    builder.at(escapes).parse_rel('f', lambda string_body, string_error: add_to_string('\f', string_body, string_error))

    builder.at(escapes).parse_rel(ZERO_CHAR).\
        act('Escaped null character error', lambda line_no: {UPDATE_CONTEXT: {STRING_ERROR: 'null_char_esc'}})

    builder.at(escapes).parse_rel(R_ANY_CHAR, add_to_string)

    # Finishing the string
    builder.at(string_chars).parse_rel('"', BREAK)

    # Just a good char
    builder.at(string_chars).parse_rel(R_ANY_CHAR, add_to_string).default()


def add_errors(statement):
    builder.at(statement).parse_rel('*)').act('Unmatched multi-line',
                                          lambda line_no: print_token(line_no, ERROR_TOKEN, 'Unmatched *)'))

    builder.at(statement).parse_rel(R_ANY_CHAR).default().\
        act('Unexpected character',
            lambda line_no, last_parsed: print_token(line_no, ERROR_TOKEN, last_parsed))

#p = ParsingProcess2()
#r = p(1)

build_root()

root = builder.graph


name = 'hello.cool'

import cProfile, pstats, StringIO, hotshot


def get_content(filename):
    with open(filename) as f:
        return f.read()


def lex_file(filename):
    return lex(get_content(filename))


def lex(content):
    global result
    result =''

    content += EOF
    parser = ParsingProcess2()

    #ProcessDebugger(parser, True)

    #pr = cProfile.Profile()
    #pr.enable()


    #prof = hotshot.Profile("ut.prof")
    #prof.start()

    r = parser(root, text=content, line_no=1)
    #print result
    print "Result - %s, remainder - %s, current - %s" % (r, parser.text, parser.current)

    #pr.disable()
    #s = StringIO.StringIO()
    #sortby = 'time'
    #ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    #ps.print_stats()
    #print s.getvalue()

    #prof.stop()
    #prof.close()

    return result


# Read file if any
if len(sys.argv) >= 2:
    print lex_file(sys.argv[1])
