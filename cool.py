# Regex classes
from ut import *
import re

# Global parameters
curr_lineno = 1
current_token = None
current_data = None

EOL = r"(\r\n|\n|\r){1}"
WHITE_SPACE	= r"[ \f\t\v]*"

CHAR_ANY = "."

INTEGER = "[0-9]+"
IDENTIFIER = "[A-Za-z0-9_]*"


def inc_lineno(notion, *m, **c):
    global curr_lineno

    if 'state' in c:
        curr_lineno += 1


def out(notion, *m, **c):
    if 'state' in c:
        print '#' + str(curr_lineno) + " : " + c['state']['notifications']['condition']

root = ComplexNotion("COOL program")
normal = SelectiveNotion("Normal mode")
LoopRelation(root, normal)


eol = FunctionNotion("eol", inc_lineno)
ConditionalRelation(normal, eol, re.compile(EOL))

ConditionalRelation(normal, None, re.compile(WHITE_SPACE))

int = FunctionNotion("int", out)
ConditionalRelation(normal, int, re.compile(INTEGER))

id = FunctionNotion("id", out) # TODO
ConditionalRelation(normal, id, re.compile(IDENTIFIER))


s = "   \r\n  \r\n 111 alfa_2 \n   34 \r"
c = {"text": s}

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