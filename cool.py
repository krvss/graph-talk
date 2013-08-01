# Regex classes
from ut import *
import re

# Global parameters
c_line = "current_lineno"
c_token = "current_token"
c_data = "current_data"

MAX_STR_CONST = 1025

TOKEN_TYPES = (
    ("CLASS", "CLASS"),
    ("ELSE", "ELSE"),
    ("FI", "FI"),
    ("IF", "IF"),
    ("IN", "IN"),
    ("INHERITS", "INHERITS"),
    ("LET", "LET"),
    ("LOOP", "LOOP"),
    ("POOL", "POOL"),
    ("THEN", "THEN"),
    ("WHILE", "WHILE"),
    ("CASE", "CASE"),
    ("ESAC", "ESAC"),
    ("OF", "OF"),
    ("=>", "DARROW"),
    ("NEW", "NEW"),
    ("ISVOID", "ISVOID"),
    ("<-", "ASSIGN"),
    ("NOT", "NOT"),
    ("LE", "LE"),
    ("ERROR", "ERROR"),
    ("LET_STMT", "LET_STMT"),
    ("<=", "LE")
)

TOKEN_DICT = dict(TOKEN_TYPES)

SINGLE_CHAR_OP = ['@', '+', '-', '<', '{', '}', '.', ',', ':', ';', '(', ')', '=', '*', '/', '~']

# Regexes
EOL = r"(\r\n|\n|\r){1}"
ESC_EOL = r"\\(\r\n|\n|\r){1}"
WHITE_SPACE = r"[ \f\t\v]*"

ANY_CHAR = "."
ZERO_CHAR = chr(0)

INTEGER = "[0-9]+"
IDENTIFIER = "[A-Za-z0-9_]*"
TYPE_ID = "[A-Z]" + IDENTIFIER
OBJECT_ID = "[a-z]" + IDENTIFIER

EOF = chr(255)

ESC = "\\"


# Functions
def out(notion, *m, **c):
    o = ''

    if c_token in c:
        o = '#' + str(c[c_line]) + " " + c[c_token] + " "

    if c_data in c:
        o += c[c_data]

    if o:
        print o

    return {'update_context': {c_data: ''}}


def debug(a, *m, **c):
    pass


def string_add(n, *m, **c):
    return {'update_context': {c_data: (c[c_data] or "") + c["passed_condition"]}}


def is_0_char(n, *m, **c):
    if c["passed_condition"] == ZERO_CHAR:
        return True, 1

    return False, 0


def is_long_string(n, *m, **c):
    if c[c_data] and len(c[c_data]) >= MAX_STR_CONST:
        return True, 1

    return False, 0


def string_esc_convert(n, *m, **c):
    conv = "\\" + c["passed_condition"]

    return {"update_context": {"passed_condition": conv.decode('string_escape')}}


def is_operator(n, *m, **c):
    for k, v in TOKEN_DICT.iteritems():
        l = len(k)

        if len(c["text"]) >= l:
            o = c["text"][:l]
            if o.upper() == k:
                return v, l

    return False, 0


def is_single_operator(n, *m, **c):
    for op in SINGLE_CHAR_OP:
        if len(c["text"]) >= 1:
            if c["text"][0] == op:
                return "'" + op + "'", 1

    return False, 0


def is_boolean(n, *m, **c):
    if len(c["text"]) >= 4:
        if c["text"][0] == "t":
            if c["text"][1:4].upper() == "RUE":
                return "true", 4

        if c["text"][0] == "f" and len(c["text"]) >= 5:
            if c["text"][1:5].upper() == "ALSE":
                return "false", 5

    return False, 0


# General purpose notions

# Out
print_out = ActionNotion("Print out", out)

# EOL
eol = ActionNotion("EOL",
                   lambda n, *m, **c: {'update_context': {c_line: c[c_line] + 1}} if 'state' in c else None)

# EOF
eof = ActionNotion("EOF", "break")

# Break: stop loop
stop_loop = ActionNotion("Break", "break")

# Inline comments

# Root
root = ComplexNotion("COOL program")
statement = SelectiveNotion("Statement")
LoopRelation(root, statement, True)

# EOF - end of processing
ConditionalRelation(statement, eof, EOF)

# Space
ConditionalRelation(statement, eol, re.compile(EOL))
ConditionalRelation(statement, None, re.compile(WHITE_SPACE))

# Numbers
integer = ComplexNotion("Integer")
ConditionalRelation(statement, integer, re.compile(INTEGER))

ActionRelation(integer, print_out,
               lambda r, *m, **c: {"update_context": {c_token: "INT_CONST", c_data: c["passed_condition"]}})

# Operators
operator = ComplexNotion("Operator")
ConditionalRelation(statement, operator, is_operator)
ConditionalRelation(statement, operator, is_single_operator)

ActionRelation(operator, print_out,
               lambda r, *m, **c: {"update_context": {c_token: c["passed_condition"], c_data: ""}})

# Booleans
boolean = ComplexNotion("Boolean")
ConditionalRelation(statement, boolean, is_boolean)

ActionRelation(boolean, print_out,
               lambda r, *m, **c: {"update_context": {c_token: "BOOL_CONST", c_data: c["passed_condition"]}})

# IDs
obj_identifier = ComplexNotion("Object Identifier")
ConditionalRelation(statement, obj_identifier, re.compile(OBJECT_ID))

ActionRelation(obj_identifier, print_out,
               lambda r, *m, **c: {"update_context": {c_token: "OBJECTID", c_data: c["passed_condition"]}})

type_identifier = ComplexNotion("Type Identifier")
ConditionalRelation(statement, type_identifier, re.compile(TYPE_ID))

ActionRelation(type_identifier, print_out,
               lambda r, *m, **c: {"update_context": {c_token: "TYPEID", c_data: c["passed_condition"]}})

# Comments
# Inline
inline_comment = ComplexNotion("Inline comment")
ConditionalRelation(statement, inline_comment, "--")

inline_comment_chars = SelectiveNotion("Inline comment characters")  # Inline comment is a set of all chars except EOL
LoopRelation(inline_comment, inline_comment_chars)

inline_comment_end = ComplexNotion("Inline comment end")
ConditionalRelation(inline_comment_chars, inline_comment_end, re.compile(EOL))

NextRelation(inline_comment_end, eol)
NextRelation(inline_comment_end, stop_loop)

ConditionalRelation(inline_comment_chars, None, re.compile(ANY_CHAR))  # Just consume chars

# Multiline
error_unmatched_comment = ActionNotion("Unmatched multi-line", {"error": "Unmatched *)"})
ConditionalRelation(statement, error_unmatched_comment, "*)")  # Closing without opening

multiline_comment = ComplexNotion("Multiline comment")
ConditionalRelation(statement, multiline_comment, "(*")

multiline_comment_chars = SelectiveNotion("Multiline comment chars")
LoopRelation(multiline_comment, multiline_comment_chars, True)

error_EOF_comment = ActionNotion("EOF in comment", [{"error": "EOF in comment"}, "break"])
ConditionalRelation(multiline_comment_chars, error_EOF_comment, EOF, 'test')  # Error

ConditionalRelation(multiline_comment_chars, eol, re.compile(EOL))  # Increase line counter

ConditionalRelation(multiline_comment_chars, stop_loop, "*)", 'test')  # Going out

ConditionalRelation(multiline_comment_chars, multiline_comment, "(*")  # Going in again

ConditionalRelation(multiline_comment_chars, None, re.compile(ANY_CHAR))  # Just consume chars

ConditionalRelation(multiline_comment, None, '*)')

# Strings
string = ComplexNotion("String")
ConditionalRelation(statement, string, '"')

string_chars = SelectiveNotion("String chars")
LoopRelation(string, string_chars, True)

string_skip = ComplexNotion("Skip chars")
string_add_char = SelectiveNotion("String Add char")

# Null character test
string_null_char = ComplexNotion("String Null Char")
ConditionalRelation(string_add_char, string_null_char, is_0_char, 'test')

NextRelation(string_null_char, ActionNotion("String Null error", {"error": "String contains null character"}))
NextRelation(string_null_char, string_skip)

# Too long test
string_too_long = ComplexNotion("String Too Long")
ConditionalRelation(string_add_char, string_too_long, is_long_string, 'test')

NextRelation(string_too_long, ActionNotion("String Too Long error", {"error": "String constant too long"}))
NextRelation(string_too_long, string_skip)

# Adding chars
string_add_to_string = ActionNotion("String Add to string", string_add)
NextRelation(string_add_char, string_add_to_string)

# Skip mode
string_skip_chars = SelectiveNotion("String skip chars")
LoopRelation(string_skip, string_skip_chars, True)

string_skip_eol = ComplexNotion("String skip EOL")
ConditionalRelation(string_skip_chars, string_skip_eol, re.compile(EOL))

NextRelation(string_skip_eol, eol)
NextRelation(string_skip_eol, stop_loop)

ConditionalRelation(string_skip_chars, eol, re.compile(ESC_EOL))

ConditionalRelation(string_skip_chars, stop_loop, '"')

ConditionalRelation(string_skip_chars, None, re.compile(ANY_CHAR))

NextRelation(string_skip, stop_loop)

# Errors
string_eol = ComplexNotion("String EOL")
ConditionalRelation(string_chars, string_eol, re.compile(EOL))

NextRelation(string_eol, eol)

string_eol_error = ActionNotion("String EOL error", [{"error": "Unterminated string constant"}, "break"])

NextRelation(string_eol, string_eol_error)

string_eof = ActionNotion("String EOF error", [{"error": "EOF in string constant"}, "break"])
ConditionalRelation(string_chars, string_eof, EOF, 'test')

# Escapes
string_esc = SelectiveNotion("String Escape")
ConditionalRelation(string_chars, string_esc, ESC)

string_add_esc = ComplexNotion("String Escape add")

string_convert_esc = ActionNotion("String Convert Escape", string_esc_convert)
NextRelation(string_add_esc, string_convert_esc)
NextRelation(string_add_esc, string_add_char)

ConditionalRelation(string_esc, string_add_esc, "n")
ConditionalRelation(string_esc, string_add_esc, "t")
ConditionalRelation(string_esc, string_add_esc, "b")
ConditionalRelation(string_esc, string_add_esc, "f")

string_esc_eol = ComplexNotion("String ESC EOL")

NextRelation(string_esc_eol, ActionNotion("Add EOL", {"update_context": {"passed_condition": "\n"}}))
NextRelation(string_esc_eol, string_add_char)
NextRelation(string_esc_eol, eol)

ConditionalRelation(string_esc, string_esc_eol, re.compile(EOL))
ConditionalRelation(string_esc, string_eof, EOF, 'test')

ConditionalRelation(string_esc, string_add_char, re.compile(ANY_CHAR))

# Finishing string
string_finished = ComplexNotion("String finished")
ConditionalRelation(string_chars, string_finished, '"')

string_token = ActionNotion("String token", {"update_context": {c_token: "STR_CONST"}}, True)
NextRelation(string_finished, string_token)

NextRelation(string_finished, print_out)
NextRelation(string_finished, stop_loop)

ConditionalRelation(string_chars, string_add_char, re.compile(ANY_CHAR))

# ERROR
error = ComplexNotion("Error")
ConditionalRelation(statement, error, re.compile(ANY_CHAR))

ActionRelation(error, print_out,
               lambda r, *m, **c: {"update_context": {c_token: "ERROR", c_data: c["passed_condition"]},
                                   "error": c["passed_condition"]})


# Test
s1 = """

111 alfa_2
34
12 --13
8
"""

s = """(*(*
*)*)
111(*
&&&*)
222"""

#s = "*)"
s = 'thEn NeW 11 aa + - @ => <= tRuE fAlSe FALSE True T_T Tt aB1 >>> <<< -> ' + ZERO_CHAR

s = r'''
"aaa'''
s = "(*"

s = '"sa" 11 "ass"  23'
s = r' "nnn\o" 11 "omg/n"'
s = '"t' + ZERO_CHAR + 'oo" 111'

s = '''"omg\nsuper"
222'''

s = '"aaa'+ZERO_CHAR + '\n 111'

s += EOF
end = ConditionalRelation(statement, None, EOF)  # Done!

c = {"text": s, c_data: None, c_token: None, c_line: 1}


from test import logger
#logger.add_queries(True)
logger.debug = debug

logger.events.append({"abstract": string_add_char})

p = ParsingProcess()
p.callback = logger


r = p.parse(root, **c)

print r

if r != "ok":
    print p.errors

exit()

"""
mycoolc:
#!/bin/csh -f
./lexer $* | ./parser $* | ./semant $* | ./cgen $*

compilers@compilers-vm:~/PA2$ ./lexer grading/escapedunprintables.cool
#name "grading/escapedunprintables.cool"
#1 STR_CONST "This is a tab:\t"
"""