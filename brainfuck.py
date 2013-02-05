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
        sys.stdout.write(chr(memory[position]))

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

class CommandNotion(FunctionNotion):
    def __init__(self):
        super(CommandNotion, self).__init__('Command', self.run)

    def run(self, *message, **context):
        if not 'state' in context:
            return

        command = Language.get_command(context['state']['notifications']['condition'])
        new_pos = command(context['memory'], context['position'])

        if new_pos is not None:
            return {'update_context': {'position' : new_pos}}

def stopper(n, *m, **c):
    if 'text' in c:
        if len(c['text']) > 0:
            return 'error'
        else:
            return 'stop'


class Parser(TextParsingProcess):
    def parse_source(self, source):
        context = {'text': source}
        context.update(Language.init())

        return self.parse('new', self.get_graph(), **context)

    @staticmethod
    def get_graph():
        root = ComplexNotion('Brainfuck Program')

        command = SelectiveNotion('Command')

        LoopRelation(root, command)

        simple_cmd = CommandNotion()

        ConditionalRelation(command, simple_cmd, Language.INC)
        ConditionalRelation(command, simple_cmd, Language.DEC)
        ConditionalRelation(command, simple_cmd, Language.PREV)
        ConditionalRelation(command, simple_cmd, Language.NEXT)
        ConditionalRelation(command, simple_cmd, Language.OUT)
        ConditionalRelation(command, simple_cmd, Language.IN)

        NextRelation(command, FunctionNotion('Unknown command', stopper))

        return root


def load(from_str):
    from test import logger

    parser = Parser()
    parser.callback = logger
    #logger.logging = True

    r = parser.parse_source(from_str)

    pass


load(',>,<.>.')