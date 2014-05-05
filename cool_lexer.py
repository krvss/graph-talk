# COOL lexer example
# (c) krvss 2011-2014

import re
import sys

from ut import *

# Shared variables
LINE_NO = 'line_no'
STRING_BODY = 'string_body'
STRING_ERROR = 'string_error'

# Constants
EOF = chr(255)
ZERO_CHAR = chr(0)
MAX_STR_CONST = 1024

ERROR_TOKEN = 'ERROR'
STRING_CONST = 'STR_CONST'

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
R_EOL = re.compile('(\n\r|\r\n|\n)')
R_BOOLEAN = re.compile('(t[r|R][u|U][e|E])|(f[a|A][l|L][s|S][e|E])')
R_INTEGER = re.compile('[0-9]+')
R_WHITE_SPACE = re.compile('[ \f\t\v]+')
R_ANY_CHAR = re.compile('.')

IDENTIFIER = '[A-Za-z0-9_]*'
R_OBJECT_ID = re.compile('[a-z]' + IDENTIFIER)
R_TYPE_ID = re.compile('[A-Z]' + IDENTIFIER)

# Globals
# Graph builder
builder = GraphBuilder('COOL program')

# Lexing result
result = ''


# Out token to result
def out_token(line_no, token, data=''):
    global result

    if token in (ERROR_TOKEN, STRING_CONST):
        data = data.replace("\\", "\\\\")
        data = data.replace("\n", r"\n").replace("\t", r"\t").replace("\b", r"\b").\
               replace("\f", r"\f").replace('"', '\\"').replace('\r', '\\015').replace('\033', '\\033').\
               replace('\01', '\\001').replace('\02', '\\002').replace('\03', '\\003').replace('\04', '\\004').\
               replace('\00', '\\000').replace('\22', '\\022').replace('\13', '\\013')

        data = '"' + data + '"'

    result += '#%s %s %s\n' % (line_no, token, data) if data else '#%s %s\n' % (line_no, token)


# Universal line number incrementer
def inc_line_no(line_no, inc=1):
    return {ParsingProcess.UPDATE_CONTEXT: {LINE_NO: line_no + inc}}


# The lexing graph
def build_graph():
    global builder
    statement = builder.loop_rel(True).select('Statement').current

    # Operators
    builder[statement].parse_rel(TOKEN_DICT.keys(), ignore_case=True).\
        act('Operator', lambda line_no, last_parsed: out_token(line_no, TOKEN_DICT[last_parsed.upper()]))

    builder[statement].parse_rel(SINGLE_CHAR_OP).\
        act('Single Char Operator', lambda line_no, last_parsed: out_token(line_no, '\'' + last_parsed + '\''))

    # Integers
    builder[statement].parse_rel(R_INTEGER).\
        act('Integer', lambda line_no, last_parsed: out_token(line_no, 'INT_CONST', last_parsed))

    # Booleans
    builder[statement].parse_rel(R_BOOLEAN).\
        act('Boolean', lambda line_no, last_parsed: out_token(line_no, 'BOOL_CONST', last_parsed.lower()))

    # Object ID
    builder[statement].parse_rel(R_OBJECT_ID).\
        act('Object ID', lambda line_no, last_parsed: out_token(line_no, 'OBJECTID', last_parsed))

    # Type ID
    builder[statement].parse_rel(R_TYPE_ID).\
        act('Object ID', lambda line_no, last_parsed: out_token(line_no, 'TYPEID', last_parsed))

    # New line: increment the counter
    builder[statement].parse_rel(R_EOL).\
        act('New Line', inc_line_no)

    # Skipping white space
    builder[statement].parse_rel(R_WHITE_SPACE)

    # Complex notions
    add_inline_comment(statement)
    add_multiline_comment(statement)
    add_strings(statement)

    # Errors
    builder[statement].parse_rel('*)').\
        act('Unmatched multi-line', lambda line_no: out_token(line_no, ERROR_TOKEN, 'Unmatched *)'))

    builder[statement].parse_rel(R_ANY_CHAR).default().\
        act('Unexpected character', lambda line_no, last_parsed: out_token(line_no, ERROR_TOKEN, last_parsed))

    # Stopping
    builder[statement].parse_rel(EOF, ParsingProcess.OK)


# One-line comment notion
def add_inline_comment(statement):
    builder[statement].parse_rel('--').complex('Inline comment')
    inline_comment_chars = builder.loop_rel(True).select('Inline comment chars').current

    builder[inline_comment_chars].parse_rel([R_EOL, EOF], ParsingProcess.BREAK).check_only()  # No need to parse here, just done
    builder[inline_comment_chars].parse_rel(R_ANY_CHAR).default()  # Skip the chars


# Multi-line comment notion
def add_multiline_comment(statement):
    builder[statement].parse_rel('(*').complex('Multi-line comment')
    multiline_comment_body = builder.loop_rel(True).select('Multi-line comment body').current

    builder[multiline_comment_body].parse_rel(R_EOL, inc_line_no)
    builder[multiline_comment_body].parse_rel(EOF).check_only().\
        act('EOF in comment', lambda line_no: [out_token(line_no, ERROR_TOKEN, 'EOF in comment'), ParsingProcess.BREAK])

    builder[multiline_comment_body].parse_rel('(*', statement.owner.notion('Multi-line comment'))  # Nested comment
    builder[multiline_comment_body].parse_rel('*)', ParsingProcess.BREAK)

    builder[multiline_comment_body].parse_rel(R_ANY_CHAR).default()  # Consuming chars (gulp!)


# Strings
# Adding character to the string
def add_to_string(last_parsed, string_body, string_error):
    if not string_body:
        string_body = ''
    else:
        if len(string_body) == MAX_STR_CONST:
            return {ParsingProcess.ADD_CONTEXT: {STRING_ERROR: 'overflow'}} if not string_error else None

    return {ParsingProcess.UPDATE_CONTEXT: {STRING_BODY: string_body + last_parsed}}


# Out the string and clean-up
def out_string(line_no, string_body, string_error):
    if string_error == 'unescaped_eol':
        out_token(line_no + 1, ERROR_TOKEN, 'Unterminated string constant')  # +1 here is for compatibility purposes
    elif string_error == 'null_char':
        out_token(line_no, ERROR_TOKEN, 'String contains null character.')
    elif string_error == 'null_char_esc':
        out_token(line_no, ERROR_TOKEN, 'String contains escaped null character.')
    elif string_error == 'overflow':
        out_token(line_no, ERROR_TOKEN, 'String constant too long')
    elif string_error == 'eof':
        out_token(line_no, ERROR_TOKEN, 'EOF in string constant')
    else:
        out_token(line_no, STRING_CONST, string_body or '')

    return {ParsingProcess.DELETE_CONTEXT: [STRING_BODY, STRING_ERROR]}


# String notion itself
def add_strings(statement):
    string = builder[statement].parse_rel('"').complex('String').current
    string_chars = builder.loop_rel(True).select('String chars').current
    builder[string].next_rel().act('Out string', out_string)

    # 0 character error
    builder[string_chars].parse_rel(ZERO_CHAR).\
        act('Null character error', lambda: {ParsingProcess.ADD_CONTEXT: {STRING_ERROR: 'null_char'}})

    # If EOL matched stop the string with error or just break
    builder[string_chars].parse_rel(R_EOL).check_only().\
        act('EOL', lambda: [{ParsingProcess.ADD_CONTEXT: {STRING_ERROR: 'unescaped_eol'}}, ParsingProcess.BREAK])

    # Stop if EOF
    builder[string_chars].parse_rel(EOF).check_only().\
        act('EOF error', lambda: [{ParsingProcess.ADD_CONTEXT: {STRING_ERROR: 'eof'}}, ParsingProcess.BREAK])

    # Escapes
    escapes = builder[string_chars].parse_rel('\\').select('Escapes').current

    builder[escapes].parse_rel(R_EOL,
                  lambda string_body, string_error: tupled(add_to_string('\n', string_body, string_error), inc_line_no))

    builder[escapes].parse_rel('n', lambda string_body, string_error: add_to_string('\n', string_body, string_error))
    builder[escapes].parse_rel('t', lambda string_body, string_error: add_to_string('\t', string_body, string_error))
    builder[escapes].parse_rel('b', lambda string_body, string_error: add_to_string('\b', string_body, string_error))
    builder[escapes].parse_rel('f', lambda string_body, string_error: add_to_string('\f', string_body, string_error))

    builder[escapes].parse_rel(ZERO_CHAR).\
        act('Escaped null character error',
            lambda line_no: {ParsingProcess.ADD_CONTEXT: {STRING_ERROR: 'null_char_esc'}})

    builder[escapes].parse_rel(R_ANY_CHAR, add_to_string)

    # Finishing the string
    builder[string_chars].parse_rel('"', ParsingProcess.BREAK)

    # Just a good char
    builder[string_chars].parse_rel(R_ANY_CHAR, add_to_string).default()


build_graph()


def get_content(filename):
    with open(filename) as f:
        return f.read()


def lex_file(filename):
    return lex(get_content(filename), filename)


def lex(content, filename):
    global result
    result = ''

    content += EOF
    parser = ParsingProcess()

    out = parser(builder.graph, text=content, line_no=1)
    if out != parser.OK:
        raise SyntaxError('Could not lex %s: %s at %s' % (filename, out, parser.current))

    return result


def main():
    if len(sys.argv) >= 2:
        print lex_file(sys.argv[1])
    else:
        print "Usage: " + sys.argv[0] + " filename"


if __name__ == "__main__":
    main()

