# Regex classes
from ut import *
import re

# Global parameters
c_line = "current_lineno"
c_token = "current_token"
c_data = "current_data"

MAX_STR_CONST = 1025

TOKEN_TYPES = (
    ("CLASS", 258),
    ("ELSE", 259),
    ("FI", 260),
    ("IF", 261),
    ("IN", 262),
    ("INHERITS", 263),
    ("LET", 264),
    ("LOOP", 265),
    ("POOL", 266),
    ("THEN", 267),
    ("WHILE", 268),
    ("CASE", 269),
    ("ESAC", 270),
    ("OF", 271),
    ("DARROW", 272),
    ("NEW", 273),
    ("ISVOID", 274),
    ("STR_CONST", 275),
    ("INT_CONST", 276),
    ("BOOL_CONST", 277),
    ("TYPEID", 278),
    ("OBJECTID", 279),
    ("ASSIGN", 280),
    ("NOT", 281),
    ("LE", 282),
    ("ERROR", 283),
    ("LET_STMT", 285)
)

# Regexes
EOL = r"(\r\n|\n|\r){1}"
ESC_EOL = r"\\(\r\n|\n|\r){1}"
WHITE_SPACE = r"[ \f\t\v]*"

ANY_CHAR = "."
ZERO_CHAR = "^" #chr(0)

INTEGER = "[0-9]+"
IDENTIFIER = "[A-Za-z0-9_]*"

EOF = "$"#chr(255)

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

# EOF
ConditionalRelation(statement, eof, EOF)

# End of text - we do not always have EOF
ConditionalRelation(statement, eof, lambda n, *m, **c: (True, 1) if not c["text"] else (False, 0))

# Space
ConditionalRelation(statement, eol, re.compile(EOL))
ConditionalRelation(statement, None, re.compile(WHITE_SPACE))

# Identifiers and numbers
integer = ComplexNotion("Integer")
ConditionalRelation(statement, integer, re.compile(INTEGER))

ActionRelation(integer, print_out,
               lambda r, *m, **c: {"update_context": {c_token: "INT_CONST", c_data: c["passed_condition"]}})


identifier = ComplexNotion("id")
ConditionalRelation(statement, identifier, re.compile(IDENTIFIER))

ActionRelation(identifier, print_out,
               lambda r, *m, **c: {"update_context": {c_token: "OBJECTID", c_data: c["passed_condition"]}})

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

error_EOF_comment = ActionNotion("EOF in comment", {"error": "EOF in comment"})
ConditionalRelation(multiline_comment_chars, error_EOF_comment, EOF)  # Error

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
ConditionalRelation(string_chars, string_eof, EOF)

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
ConditionalRelation(string_esc, string_eof, EOF)

ConditionalRelation(string_esc, string_add_char, re.compile(ANY_CHAR))

# Finishing string
string_finished = ComplexNotion("String finished")
ConditionalRelation(string_chars, string_finished, '"')

string_token = ActionNotion("String token", {"update_context": {c_token: "STR_CONST"}}, True)
NextRelation(string_finished, string_token)

NextRelation(string_finished, print_out)
NextRelation(string_finished, stop_loop)

ConditionalRelation(string_chars, string_add_char, re.compile(ANY_CHAR))



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

s = '"sa" 11 "ass"  23'
s = r' "nnn\o" 11 "omg/n"'
s = '"t' + ZERO_CHAR + 'oo" 111'
s = '"aaa'+ZERO_CHAR + '\n 111'
s = '''"omg\nsuper"
222'''


s += EOF
end = ConditionalRelation(statement, None, EOF)  # Done!

c = {"text": s, c_data: None, c_token: None, c_line: 1}


from test import logger
logger.add_queries(True)
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