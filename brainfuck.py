import sys
import os
import termios
import fcntl

from ut import *

# From http://love-python.blogspot.ru/2010/03/getch-in-python-get-single-character.html
def _getch():
    fd = sys.stdin.fileno()

    oldterm = termios.tcgetattr(fd)
    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)

    oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

    try:
        while 1:
            try:
                c = sys.stdin.read(1)
                break
            except IOError: pass
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
    return c


def getch():
    try:
        return _getch()
    except Exception:
        return sys.stdin.read(1)


# Execution commands
class SimpleCommand(FunctionNotion):
    INC = '+'
    DEC = '-'
    NEXT = '>'
    PREV = '<'
    OUT = '.'
    IN = ','

    def __init__(self, name):
        super(SimpleCommand, self).__init__(name, self.run)

    # Just select a proper command basing on name and execute it using memory and position
    def run(self, *message, **context):
        if not 'memory' in context:
            return

        memory = context['memory']
        position = context['position']

        if self.name == SimpleCommand.INC:
            memory[position] = memory[position] + 1 if memory[position] < 256 else 0

        elif self.name == SimpleCommand.DEC:
            memory[position] = memory[position] - 1 if memory[position] > 0 else 255

        elif self.name == SimpleCommand.NEXT:
            if position == len(memory) - 1:
                memory.append(0)

            return {'update_context': {'position': position + 1}}

        elif self.name == SimpleCommand.PREV:
            if position > 0:
                return {'update_context': {'position': position - 1}}
            else:
                return {'error': 'position underflow'}

        elif self.name == SimpleCommand.OUT:
            cell = memory[position]
            # Printout in a friendly format
            out = '\'%s\'' % cell if cell < 10 else chr(cell)

            sys.stdout.write(out)

        elif self.name == SimpleCommand.IN:
            memory[position] = ord(getch())


# Parser commands
class ParseCommand(FunctionNotion):
    def __init__(self, name):
        super(ParseCommand, self).__init__(name, self.make)

    def get_top(self, context):
        return context['loops'][len(context['loops']) - 1][0] if context['loops'] else context['root']

    def make(self, *message, **context):
        if not 'state' in context:
            return

        NextRelation(self.get_top(context), SimpleCommand(context['passed_condition']))


class ParseLoopStart(ParseCommand):
    def make(self, *message, **context):
        if not 'root' in context:
            return

        new_top = ComplexNotion('Loop')

        LoopRelation(self.get_top(context), new_top, lambda r, *m, **c: c['memory'][c['position']] != 0)
        context['loops'].append((new_top, context['parsed_length'] - 1))


class ParseLoopEnd(ParseCommand):
    def make(self, *message, **context):
        if not 'loops' in context:
            return

        if context['loops']:
            context['loops'].pop()
        else:
            return {'error': 'no_loops'}


# Language parser and interpreter
class Parser:
    @staticmethod
    def parse_stop(notion, *message, **context):
        if not 'text' in context:
            return

        if len(context['text']) > 0:
            return {'error': 'unknown_command "%s" at position %s' % (context['text'][0], context['parsed_length'])}

        elif context['loops']:
            unclosed = [str(p[1]) for p in context['loops']]
            return {'error': 'unclosed_loops at position %s' % ','.join(unclosed)}

        else:
            return 'stop'

    @staticmethod
    def get_graph():
        root = ComplexNotion('Brainfuck Program')
        command = SelectiveNotion('Command')
        LoopRelation(root, command)

        ConditionalRelation(command, ParseLoopStart('Loop start'), '[')
        ConditionalRelation(command, ParseLoopEnd('Loop end'), ']')

        simple_command = ParseCommand('Simple command')
        ConditionalRelation(command, simple_command, SimpleCommand.INC)
        ConditionalRelation(command, simple_command, SimpleCommand.DEC)
        ConditionalRelation(command, simple_command, SimpleCommand.PREV)
        ConditionalRelation(command, simple_command, SimpleCommand.NEXT)
        ConditionalRelation(command, simple_command, SimpleCommand.OUT)
        ConditionalRelation(command, simple_command, SimpleCommand.IN)

        NextRelation(command, FunctionNotion('Stop', Parser.parse_stop))

        return root

    @staticmethod
    def execute(from_str):
        process = ParsingProcess()

        root = ComplexNotion('root')
        context = {'text': from_str, 'root': root, 'loops': []}

        # Loading
        r = process.parse(Parser.get_graph(), **context)

        if r == 'error':
            return 'Parsing error(s): %s' % process.errors

        context = {'memory': [0] * len(from_str), 'position': 0}

        # Execution
        r = process.parse('new', root, **context)

        if r != 'ok':
            return 'Runtime error(s): %s ' % process.errors

        return 'ok'

# Tests

# Input and output 2 chars
s = ',>,<.>.'

# Simple loop
s = '++[.-]'

# Underflow error
s = '+<'

# Nested loops: print 2,2,1,1
s = '++>++<[.->[.-]<]'

# Loops level error
s = '[.[[]'

# Bad command error
s = '+++a'

# Hello, World!
s = '++++++++++[>+++++++>++++++++++>+++>+<<<<-]>++.>+.+++++++..+++.>++.<<+++++++++++++++.>.+++.------.--------.>+.>.'


def main():
    if len(sys.argv) == 2:
        f = open(sys.argv[1], "r")
        print Parser.execute(f.read())
        f.close()
    else:
        print "Usage: " + sys.argv[0] + " filename"

if __name__ == "__main__":
    main()
else:
    print Parser.execute(s)