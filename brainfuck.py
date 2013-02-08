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


#  Brainfuck language description
class Language:
    INC = '+'
    DEC = '-'
    NEXT = '>'
    PREV = '<'
    OUT = '.'
    IN = ','

    WHILE = '['
    END_WHILE = ']'

    @staticmethod
    def increment(memory, position):
        memory[position] = memory[position] + 1 if memory[position] < 256 else 0

    @staticmethod
    def decrement(memory, position):
        memory[position] = memory[position] - 1 if memory[position] > 0 else 255

    @staticmethod
    def next(memory, position):
        if position < len(memory) - 1:
            return position + 1

    @staticmethod
    def previous(memory, position):
        if position > 0:
            return position - 1

    @staticmethod
    def output(memory, position):
        cell = memory[position]
        out = '\'%s\'' % cell if cell < 10 else chr(cell)
        sys.stdout.write(out)

    @staticmethod
    def input(memory, position):
        memory[position] = ord(getch())

    @staticmethod
    def init():
        # TODO: set to 30000
        return {"memory": [0] * 30, "position" : 0}

    @staticmethod
    def get_command(id):
        if id == Language.INC:
            return Language.increment

        elif id == Language.DEC:
            return Language.decrement

        elif id == Language.NEXT:
            return Language.next

        elif id == Language.PREV:
            return Language.previous

        elif id == Language.OUT:
            return Language.output

        elif id == Language.IN:
            return Language.input


class BasicCommand(FunctionNotion):
    def __init__(self, command):
        super(BasicCommand, self).__init__('BasicCommand', self.run)
        self.command = command

    def run(self, *message, **context):
        if not 'memory' in context:
            return

        new_pos = self.command(context['memory'], context['position'])

        if new_pos is not None:
            return {'update_context': {'position' : new_pos}}


class LoopCommandRelation(LoopRelation):
    def __init__(self, subject, object):
        super(LoopCommandRelation, self).__init__(subject, object, self.check)

    def check(self, *message, **context):
        return context['memory'][context['position']] != 0


class CommandNotion(FunctionNotion):
    def __init__(self, name = 'CommandNotion'):
        super(CommandNotion, self).__init__(name, self.make)

    def get_top(self, context):
        return context['loops'][len(context['loops']) - 1][0] if context['loops'] else context['root']

    def make(self, *message, **context):
        if not 'state' in context:
            return

        lang_cmd = Language.get_command(context['state']['notifications']['condition'])

        NextRelation(self.get_top(context), BasicCommand(lang_cmd))


class LoopStartNotion(CommandNotion):
    def __init__(self, name = 'LoopStartNotion'):
        super(LoopStartNotion, self).__init__(name)

    def make(self, *message, **context):
        if not 'root' in context:
            return

        top = self.get_top(context)
        new_top = ComplexNotion('Loop')

        LoopCommandRelation(top, new_top)
        context['loops'].append((new_top, context['parsed_length'] - 1))


class LoopEndNotion(CommandNotion):
    def __init__(self, name = 'LoopEndNotion'):
        super(LoopEndNotion, self).__init__(name)

    def make(self, *message, **context):
        if not 'loops' in context:
            return

        if context['loops']:
            context['loops'].pop()

        else:
            return {'error': 'no_loops'}


def stopper(n, *m, **c):
    if 'text' in c:
        if len(c['text']) > 0:
            return {'error': 'unknown_command at %s' % c['parsed_length']}
        elif c['loops']:
            unclosed = [str(p[1]) for p in c['loops']]
            return {'error': 'unclosed_loops at %s' % ','.join(unclosed)}
        else:
            return 'stop'


class Parser(TextParsingProcess):
    def parse_source(self, source):
        context = {'text': source, 'root': ComplexNotion('root'), 'loops': []}

        return self.parse('new', self.get_graph(), **context)

    @staticmethod
    def get_graph():
        root = ComplexNotion('Brainfuck Program')

        command = SelectiveNotion('Command')

        LoopRelation(root, command)

        simple_cmd = CommandNotion()

        ConditionalRelation(command, LoopStartNotion(), Language.WHILE)

        ConditionalRelation(command, simple_cmd, Language.INC)
        ConditionalRelation(command, simple_cmd, Language.DEC)
        ConditionalRelation(command, simple_cmd, Language.PREV)
        ConditionalRelation(command, simple_cmd, Language.NEXT)
        ConditionalRelation(command, simple_cmd, Language.OUT)
        ConditionalRelation(command, simple_cmd, Language.IN)

        ConditionalRelation(command, LoopEndNotion(), Language.END_WHILE)

        NextRelation(command, FunctionNotion('Bad command', stopper))

        return root


def load(from_str):
    parser = Parser()
    r = parser.parse_source(from_str)

    if r == 'error':
        return r, parser.context['errors']
    else:
        return 'ok', parser.context['root']

def run(program):
    context = {}
    context.update(Language.init())

    runner = StatefulProcess()
    runner.parse(program, **context)


#s = ',>,<.>.'
#s = '++[.-]'

#s = '++++++++++[>+++++++>++++++++++>+++>+<<<<-]>++.>+.+++++++..+++.>++.<<+++++++++++++++.>.+++.------.--------.>+.>.')
#s = '++>++<[.->[.-]<]') 2,2,1,1
#s = '[.[[]'

s = '+++a'

result, out = load(s)

if result == 'ok':
    run(out)
else:
    print out