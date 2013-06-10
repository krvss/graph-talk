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

CHAR_ANY = "."

INTEGER = "[0-9]+"
IDENTIFIER = "[A-Za-z0-9_]*"


# Functions
def inc_lineno(notion, *m, **c):
    if 'state' in c:
        c[c_line] += 1


def out(notion, *m, **c):
    if not 'state' in c:
        return

    o = ''

    if c[c_token]:
        o = '#' + str(c[c_line]) + " : " + c[c_token] + " "

    if c[c_data]:
        o += c[c_data]

    print o

# Root
root = ComplexNotion("COOL program")
normal = SelectiveNotion("Statement")
LoopRelation(root, normal)

# Out
print_out = FunctionNotion("Print out", out)

# Space
eol = FunctionNotion("eol", inc_lineno)
ConditionalRelation(normal, eol, re.compile(EOL))

ConditionalRelation(normal, None, re.compile(WHITE_SPACE))

# Identifiers and numbers
integer = ComplexNotion("Integer")
ConditionalRelation(normal, integer, re.compile(INTEGER))

FunctionRelation(integer, print_out,
                 lambda r, *m, **c: {"update_context": {c_token: "INT_CONST", c_data: c["passed_condition"]}})


identifier = ComplexNotion("id")
ConditionalRelation(normal, identifier, re.compile(IDENTIFIER))
FunctionRelation(identifier, print_out,
                 lambda r, *m, **c: {"update_context": {c_token: "OBJECTID", c_data: c["passed_condition"]}})

s = "   \r\n  \r\n 111 alfa_2 \n   34 \r"
c = {"text": s, c_data: None, c_token: None, c_line: 1}

p = TextParsingProcess()

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