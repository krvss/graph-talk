import sys
import os
import termios
import fcntl

#import cProfile

from ut import *
import re

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
    simple_commands = dict((('+', vm.inc), ('-', vm.dec), ('.', vm.output), (',', vm.input),
                            ('>', vm.right), ('<', vm.left)))

    def add_simple_command(top, last_parsed):
        # Last_parsed works fine as the name of the notion
        NextRelation2(top, ActionNotion2(last_parsed, simple_commands[last_parsed], top.owner), top.owner)

    def start_loop(top, top_stack):
        top_stack.append(top)
        new_top = ComplexNotion2('Loop', top.owner)
        # Loop becomes new top to add the commands
        LoopRelation2(top, new_top, lambda: None if not vm.is_not_zero() else True)

        return {SharedContextProcess2.UPDATE_CONTEXT: {'top': new_top}}

    def stop_loop(top_stack):
        if top_stack:
            return {SharedContextProcess2.UPDATE_CONTEXT: {'top': top_stack.pop()}}, ParsingProcess2.BREAK
        else:
            return Process2.STOP

    # Building interpreter graph, Source is responsible for parsing and Program for execution
    b = GraphBuilder('Interpreter').next().complex('Source').next().complex('Commands')
    command_root = b.loop(lambda text: text).select('Command').current

    # Simple command parsing
    b.parse(simple_commands.keys()).act('Simple command', add_simple_command)

    # Loops
    b.at(command_root).parse('[').complex('Start Loop').act_rel(start_loop, b.graph.notion('Commands'))
    b.at(command_root).parse(']').act('Stop Loop', stop_loop)

    # Errors (only one actually)
    b.at(command_root).parse(re.compile('.')).act('Bad character', Process2.STOP)

    # The program itself
    # TODO moar errors
    program_root = b.at(b.graph.root).next().complex('Program').current

    return {'root': b.graph, 'top': program_root, 'top_stack': []}


# Interpretes specified string using buffer for testing
def interprete(source, test=False):
    vm = BFVM(test)

    context = make_graph(vm)

    process = ParsingProcess2()
    #ProcessDebugger(process, True)

    r = process(context['root'], text=source, **context)

    if r == Process2.STOP:
        if process.current.name == 'Bad character':
            print 'Unknown char "%s" at position %s' % (process.last_parsed, process.parsed_length)



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
        #cProfile.run('interprete(s)', sort=0)
        #interprete(s)
        interprete(s)
        f.close()
    else:
        print "Usage: " + sys.argv[0] + " filename"

if __name__ == "__main__":
    main()
else:
    print Parser.execute(s)