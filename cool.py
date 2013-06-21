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

EOF = chr(0)

# Functions
def inc_lineno(notion, *m, **c):
    if 'state' in c:
        return {'update_context': {c_line: c[c_line] + 1}}


def out(notion, *m, **c):
    o = ''

    if c_token in c:
        o = '#' + str(c[c_line]) + " " + c[c_token] + " "

    if c_data in c:
        o += c[c_data]

    if o:
        print o


# General purpose notions

# Out
print_out = FunctionNotion("Print out", out)

# EOL
eol = FunctionNotion("EOL", inc_lineno)

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

# TODO: think about valuerelation etc - no need to use lambda if only return needed
FunctionRelation(integer, print_out,
                 lambda r, *m, **c: {"update_context": {c_token: "INT_CONST", c_data: c["passed_condition"]}})


identifier = ComplexNotion("id")
ConditionalRelation(statement, identifier, re.compile(IDENTIFIER))

FunctionRelation(identifier, print_out,
                 lambda r, *m, **c: {"update_context": {c_token: "OBJECTID", c_data: c["passed_condition"]}})

# Comments
# Inline
inline_comment = ComplexNotion("Inline comment")
ConditionalRelation(statement, inline_comment, "--")

inline_comment_chars = SelectiveNotion("Inline comment characters")  # Inline comment is a set of chars except EOL
LoopRelation(inline_comment, inline_comment_chars)

inline_comment_end = ComplexNotion("Inline comment end")
ConditionalRelation(inline_comment_chars, inline_comment_end, re.compile(EOL))

NextRelation(inline_comment_end, eol)
NextRelation(inline_comment_end, stop_loop)

ConditionalRelation(inline_comment_chars, None, re.compile(ANY_CHAR))  # Just consume chars

# Multiline
multiline_comment = ComplexNotion("Multiline comment")
ConditionalRelation(statement, multiline_comment, "(*")  # TODO: attach function to each abstract?

ConditionalRelation(multiline_comment, eol, re.compile(EOL), True)

error_unmatched_comment = FunctionNotion("Unmatched multi-line", {"error": "Unmatched *)"})
ConditionalRelation(multiline_comment, error_unmatched_comment, EOF, True)

mm = ConditionalRelation(multiline_comment, multiline_comment, "(*", True)
ConditionalRelation(multiline_comment, None, "*)")


def deb(*m, **c): # TODO: make a default
    pass

# Test
s1 = """

111 alfa_2
34
12 --13
8
"""

s = """(*(**)*)"""

s += EOF
ConditionalRelation(statement, None, EOF)  # Done!

c = {"text": s, c_data: None, c_token: None, c_line: 1}


from test import logger
#logger.add_queries()

logger.events.append({"filter": "query_post", "abstract": mm, "call": deb})

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