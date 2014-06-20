# COOL lexer example for Graph-talk
# (c) krvss 2011-2014

import re

from core import *

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


class Eater(object):
    """
    Eater class finds the minimum position of the string in the text
    """
    def __init__(self, stops):
        self.stops = stops

    def eat(self, text):
        pos = text.find(EOF)  # End of file is a last position in any case

        for stop in self.stops:
            new_pos = -1

            if is_regex(stop):
                p = stop.search(text)
                if p:
                    new_pos = p.start()
            else:
                new_pos = text.find(stop)

            if 0 <= new_pos < pos:
                pos = new_pos

        return pos or True

    @staticmethod
    def get_eater(stops):
        if not is_list(stops):
            stops = [stops]

        return Eater(stops).eat


def inc_line_no(line_no, inc=1):
    """
    Universal line number incrementer
    """
    return {ParsingProcess.UPDATE_CONTEXT: {LINE_NO: line_no + inc}}


def add_to_string(last_parsed, string_body, string_error):
    """
    Adding parsed characters to the string body
    """
    if not string_body:
        string_body = ''
    else:
        l = len(string_body)

        if l + len(last_parsed) > MAX_STR_CONST:
            return {ParsingProcess.ADD_CONTEXT: {STRING_ERROR: 'overflow'}} if not string_error else None

    return {ParsingProcess.UPDATE_CONTEXT: {STRING_BODY: string_body + last_parsed}}


class CoolLexer(object):
    """
    Main lexer class
    """
    def __init__(self, content, filename=None):
        self.content, self.filename = content, filename
        self.result = ''

        self.builder = GraphBuilder('COOL program')
        self.build_graph()

        self.parser = ParsingProcess()

    def out_token(self, line_no, token, data=''):
        """
        Out token to result
        """
        if token in (ERROR_TOKEN, STRING_CONST):
            data = data.replace("\\", "\\\\")
            data = data.replace("\n", r"\n").replace("\t", r"\t").replace("\b", r"\b").\
                replace("\f", r"\f").replace('"', '\\"').replace('\r', '\\015').replace('\033', '\\033').\
                replace('\01', '\\001').replace('\02', '\\002').replace('\03', '\\003').replace('\04', '\\004').\
                replace('\00', '\\000').replace('\22', '\\022').replace('\13', '\\013')

            data = '"' + data + '"'

        self.result += '#%s %s %s\n' % (line_no, token, data) if data else '#%s %s\n' % (line_no, token)

    def build_graph(self):
        """
        Make the lexing graph
        """
        statement = self.builder.loop_rel(True).select('Statement').current

        # Operators
        self.builder[statement].parse_rel(TOKEN_DICT.keys(), ignore_case=True).\
            act('Operator', lambda line_no, last_parsed: self.out_token(line_no, TOKEN_DICT[last_parsed.upper()]))

        self.builder[statement].parse_rel(SINGLE_CHAR_OP).\
            act('Single Char Operator', lambda line_no, last_parsed: self.out_token(line_no, '\'' + last_parsed + '\''))

        # Integers
        self.builder[statement].parse_rel(R_INTEGER).\
            act('Integer', lambda line_no, last_parsed: self.out_token(line_no, 'INT_CONST', last_parsed))

        # Booleans
        self.builder[statement].parse_rel(R_BOOLEAN).\
            act('Boolean', lambda line_no, last_parsed: self.out_token(line_no, 'BOOL_CONST', last_parsed.lower()))

        # Object ID
        self.builder[statement].parse_rel(R_OBJECT_ID).\
            act('Object ID', lambda line_no, last_parsed: self.out_token(line_no, 'OBJECTID', last_parsed))

        # Type ID
        self.builder[statement].parse_rel(R_TYPE_ID).\
            act('Object ID', lambda line_no, last_parsed: self.out_token(line_no, 'TYPEID', last_parsed))

        # New line: increment the counter
        self.builder[statement].parse_rel(R_EOL, inc_line_no)

        # Skipping white space
        self.builder[statement].parse_rel(R_WHITE_SPACE)

        # Inline comments
        self.builder[statement].parse_rel('--').complex('Inline comment').parse_rel(Eater.get_eater(R_EOL))

        # Complex notions
        self.add_multiline_comment(statement)
        self.add_strings(statement)

        # Errors
        self.builder[statement].parse_rel('*)').\
            act('Unmatched multi-line', lambda line_no: self.out_token(line_no, ERROR_TOKEN, 'Unmatched *)'))

        self.builder[statement].parse_rel(R_ANY_CHAR).default().\
            act('Unexpected character', lambda line_no, last_parsed: self.out_token(line_no, ERROR_TOKEN, last_parsed))

        # Stopping
        self.builder[statement].parse_rel(EOF, ParsingProcess.OK)

    def add_multiline_comment(self, statement):
        """
        Multi-line comment notion
        """
        self.builder[statement].parse_rel('(*').complex('Multi-line comment')
        multiline_comment_body = self.builder.loop_rel(True).select('Multi-line comment body').current

        self.builder[multiline_comment_body].parse_rel(R_EOL, inc_line_no)
        self.builder[multiline_comment_body].parse_rel(EOF).check_only().\
            act('EOF in comment', lambda line_no: [self.out_token(line_no, ERROR_TOKEN, 'EOF in comment'),
                                                   ParsingProcess.BREAK])

        # Nested comment
        self.builder[multiline_comment_body].parse_rel('(*', statement.owner.notion('Multi-line comment'))
        self.builder[multiline_comment_body].parse_rel('*)', ParsingProcess.BREAK)

        # Consuming chars (gulp!) until something interesting pops up
        self.builder[multiline_comment_body].parse_rel(Eater.get_eater([R_EOL, '(*', '*)'])).default()

    def out_string(self, line_no, string_body, string_error):
        """
        Out the string and clean-up
        """
        if string_error == 'unescaped_eol':
            self.out_token(line_no + 1, ERROR_TOKEN, 'Unterminated string constant')  # +1 here is for compatibility
        elif string_error == 'null_char':
            self.out_token(line_no, ERROR_TOKEN, 'String contains null character.')
        elif string_error == 'null_char_esc':
            self.out_token(line_no, ERROR_TOKEN, 'String contains escaped null character.')
        elif string_error == 'overflow':
            self.out_token(line_no, ERROR_TOKEN, 'String constant too long')
        elif string_error == 'eof':
            self.out_token(line_no, ERROR_TOKEN, 'EOF in string constant')
        else:
            self.out_token(line_no, STRING_CONST, string_body or '')

        return {ParsingProcess.DELETE_CONTEXT: [STRING_BODY, STRING_ERROR]}

    def add_strings(self, statement):
        """
        String notion itself
        """
        string = self.builder[statement].parse_rel('"').complex('String').current
        string_chars = self.builder.loop_rel(True).select('String chars').current
        self.builder[string].next_rel().act('Out string', self.out_string)

        # 0 character error
        self.builder[string_chars].parse_rel(ZERO_CHAR).\
            act('Null character error', lambda: {ParsingProcess.ADD_CONTEXT: {STRING_ERROR: 'null_char'}})

        # If EOL matched stop the string with error or just break
        self.builder[string_chars].parse_rel(R_EOL).check_only().\
            act('EOL', lambda: [{ParsingProcess.ADD_CONTEXT: {STRING_ERROR: 'unescaped_eol'}}, ParsingProcess.BREAK])

        # Stop if EOF
        self.builder[string_chars].parse_rel(EOF).check_only().\
            act('EOF error', lambda: [{ParsingProcess.ADD_CONTEXT: {STRING_ERROR: 'eof'}}, ParsingProcess.BREAK])

        # Escapes
        escapes = self.builder[string_chars].parse_rel('\\').select('Escapes').current

        self.builder[escapes].parse_rel(R_EOL,
            lambda string_body, string_error: tupled(add_to_string('\n', string_body, string_error), inc_line_no))

        self.builder[escapes].\
            parse_rel('n', lambda string_body, string_error: add_to_string('\n', string_body, string_error))
        self.builder[escapes].\
            parse_rel('t', lambda string_body, string_error: add_to_string('\t', string_body, string_error))
        self.builder[escapes].\
            parse_rel('b', lambda string_body, string_error: add_to_string('\b', string_body, string_error))
        self.builder[escapes].\
            parse_rel('f', lambda string_body, string_error: add_to_string('\f', string_body, string_error))

        self.builder[escapes].parse_rel(ZERO_CHAR).\
            act('Escaped null character error',
                lambda line_no: {ParsingProcess.ADD_CONTEXT: {STRING_ERROR: 'null_char_esc'}})

        self.builder[escapes].parse_rel(R_ANY_CHAR, add_to_string)

        # Finishing the string
        self.builder[string_chars].parse_rel('"', ParsingProcess.BREAK)

        # Just a good chars
        self.builder[string_chars].parse_rel(Eater.get_eater([ZERO_CHAR, R_EOL, '\\', '"']), add_to_string).default()

    def lex(self):
        """
        Run lexing
        """
        self.result = ''
        out = self.parser(Process.NEW, self.builder.graph, text=self.content, line_no=1)

        if out != self.parser.OK:
            raise SyntaxError('Could not lex %s: %s at %s' % (self.filename, out, self.parser.current))

        return self.result


def get_content(filename):
    with open(filename) as f:
        return f.read()


def lex_file(filename):
    return lex(get_content(filename), filename)


def lex(content, filename):
    content += EOF
    lexer = CoolLexer(content, filename)

    #from debug import ProcessDebugger
    #ProcessDebugger(parser).show_log()

    return lexer.lex()


def main():
    import sys

    if len(sys.argv) >= 2:
        print lex_file(sys.argv[1])
    else:
        print "Usage: " + sys.argv[0] + " filename"


if __name__ == "__main__":
    main()
