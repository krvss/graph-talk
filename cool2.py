from ut import *
import re

# Shared variables
LINE_NO = 'line_no'

# Constants
EOF = chr(255)

# Regexes
INTEGER = "[0-9]+"
WHITE_SPACE = r"[ \f\t\v]*"
EOL = r"(\n\r|\r\n|\n){1}"

# Root -> Statement -> Boolean, Integer, Operator, Simple operator


def print_token(line_no, token, data=''):
    print '# %s %s %s' % (line_no, token, data)


def build_root():
    b = GraphBuilder('COOL program')
    statement = b.loop(True).selective('Statement').current

    # Integers
    b.parse_rel(re.compile(INTEGER)).act('Integer',
                                         lambda line_no, last_parsed: print_token(line_no, 'INT_CONST', last_parsed))

    # New line: increment the counter
    b.parse_rel(re.compile(EOL)).act('New Line', lambda line_no: {UPDATE_CONTEXT: {LINE_NO: line_no + 1}})

    # Skipping white space
    b.at(statement).parse_rel(re.compile(WHITE_SPACE))

    # Stopping
    b.at(statement).parse_rel(EOF, OK)

