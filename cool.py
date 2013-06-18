# Regex classes
from ut import *
import re

# Global parameters
c_line = "current_lineno"
c_token = "current_token"
c_data = "current_data"

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
WHITE_SPACE = r"[ \f\t\v]*"

ANY_CHAR = "."

INTEGER = "[0-9]+"
IDENTIFIER = "[A-Za-z0-9_]*"


# Functions
def inc_lineno(notion, *m, **c):
    if 'state' in c:
        return {'update_context': {c_line: c[c_line] + 1}}


def out(notion, *m, **c):
    if not 'state' in c:
        return

    o = ''

    if c[c_token]:
        o = '#' + str(c[c_line]) + " " + c[c_token] + " "

    if c[c_data]:
        o += c[c_data]

    print o

# General purpose notions

# Out
print_out = FunctionNotion("Print out", out)

# EOL
eol = FunctionNotion("EOL", inc_lineno)

# Any char: just consume the text
any_char = FunctionRelation("Any", None, re.compile(ANY_CHAR))

# Break: stop loop
stop_loop = ValueNotion("Break", "break")

# Inline comments

# Root
root = ComplexNotion("COOL program")
statement = SelectiveNotion("Statement")
LoopRelation(root, statement)

# Space
ConditionalRelation(statement, eol, re.compile(EOL))
ConditionalRelation(statement, None, re.compile(WHITE_SPACE))

# Identifiers and numbers
integer = ComplexNotion("Integer")
ConditionalRelation(statement, integer, re.compile(INTEGER))

FunctionRelation(integer, print_out,
                 lambda r, *m, **c: {"update_context": {c_token: "INT_CONST", c_data: c["passed_condition"]}})


identifier = ComplexNotion("id")
ConditionalRelation(statement, identifier, re.compile(IDENTIFIER))
FunctionRelation(identifier, print_out,
                 lambda r, *m, **c: {"update_context": {c_token: "OBJECTID", c_data: c["passed_condition"]}})

# Comments
inline_comment = ComplexNotion("Inline comment")
ConditionalRelation(statement, inline_comment, "--")

inline_comment_chars = SelectiveNotion("Inline comment characters")
LoopRelation(inline_comment, inline_comment_chars)

inline_comment_end = ComplexNotion("Inline comment end")
ConditionalRelation(inline_comment_chars, inline_comment_end, re.compile(EOL))

NextRelation(inline_comment_end, eol)
NextRelation(inline_comment_end, stop_loop)

ConditionalRelation(inline_comment_chars, None, re.compile(ANY_CHAR))

s = "   \r\n  \r\n 111 alfa_2 \n   34 \r 12 --13 \r\n 8"
c = {"text": s, c_data: None, c_token: None, c_line: 1}


from test import logger
#logger.logging = True

p = ParsingProcess()
p.callback = logger


r = p.parse(root, **c)

print r

exit()

"""
mycoolc:
#!/bin/csh -f
./lexer $* | ./parser $* | ./semant $* | ./cgen $*

compilers@compilers-vm:~/PA2$ ./lexer grading/escapedunprintables.cool
#name "grading/escapedunprintables.cool"
#1 STR_CONST "This is a tab:\t"
"""