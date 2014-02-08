import sys
import os
import termios
import fcntl

from ut import *

from debug import ProcessDebugger

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


# Brainfuck virtual machine that runs language commands
class BFVM(object):  # TODO: to python with compressing
    def __init__(self, test=False):
        self.memory = bytearray(30000)
        self.position = 0

        self.test = test
        self.input_buffer = ''
        self.out_buffer = ''

    def inc(self):
        self.memory[self.position] = self.memory[self.position] + 1 \
            if self.memory[self.position] < 255 else 0

    def dec(self):
        self.memory[self.position] = self.memory[self.position] - 1 \
            if self.memory[self.position] > 0 else 255

    def left(self):
        if self.position > 0:
            self.position -= 1
            return True
        else:
            return False

        # TODO: overflow/underflow

    def right(self):
        if self.position < len(self.memory):
            self.position += 1
            return True
        else:
            return False

    def is_not_zero(self):
        return self.memory[self.position] != 0

    def input(self):
        if self.test and self.input_buffer:
            value = self.input_buffer[0]
            self.input_buffer = self.input_buffer[1:]
        else:
            value = getch()

        self.memory[self.position] = ord(value)

    def output(self):
        cell = self.memory[self.position]

        if self.test:
            self.out_buffer += chr(cell)
        else:
            # Printout in a friendly format
            out = '\'%s\'' % cell if cell < 10 else chr(cell)
            sys.stdout.write(out)


# Create the parsing/interpreting graph for the specified VM
def make_graph(vm):
    simple = dict((('+', vm.inc), ('-', vm.dec), ('.', vm.output), (',', vm.input), ('>', vm.right), ('<', vm.left)))

    def add_simple_command(top, last_parsed):
        NextRelation2(top, ActionNotion2(last_parsed, simple[last_parsed], top.owner), top.owner)

    def start_loop(top, stack):
        stack.append(top)
        new_top = ComplexNotion2('loop', top.owner)
        LoopRelation2(top, new_top, lambda: None if not vm.is_not_zero() else True)
        return {SharedContextProcess2.UPDATE_CONTEXT: {'top': new_top}}

    def stop_loop(stack):
        if stack:
            new_top = stack.pop()
            return {SharedContextProcess2.UPDATE_CONTEXT: {'top': new_top}}, ParsingProcess2.BREAK

    b = GraphBuilder('Interpreter').next().complex('Source').next().complex('Commands')
    b.loop(lambda text: text).select('Command')
    command_root = b.current

    b.at(b.graph.root).next().complex('Program')
    program_root = b.current

    # Simple parsing
    b.at(command_root).parse(simple.keys()).act('Simple command', add_simple_command)

    # Loops
    # TODO: add_at?
    b.at(command_root).parse('[').complex('Start Loop')
    loop_root = b.current

    b.at(loop_root).next().act('Init Loop', start_loop)
    NextRelation2(loop_root, b.graph.notion('Commands'))

    b.at(command_root).parse(']').act('Stop Loop', stop_loop)

    # TODO: error
    return {'root': b.graph, 'top': program_root, 'stack': []}


# Interpretes specified string using buffer for testing
def interprete(source, test=''):
    vm = BFVM(test)

    context = make_graph(vm)

    process = ParsingProcess2()
    #ProcessDebugger(process, True)

    print process.parse(context['root'], text=source, **context)
    pass


# Execution commands
class SimpleCommand(ActionNotion):
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
class ParseCommand(ActionNotion):
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

        NextRelation(command, ActionNotion('Stop', Parser.parse_stop))

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
        #print Parser.execute(f.read())
        #interprete('++>++<[.->[.-]<]')
        #interprete('+[-].')
        interprete(s)
        f.close()
    else:
        print "Usage: " + sys.argv[0] + " filename"

if __name__ == "__main__":
    main()
else:
    print Parser.execute(s)