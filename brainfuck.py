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


# Brainfuck virtual machine that runs language commands
class BFVM(object):  # TODO: to python with compressing
    def __init__(self, test=None):
        self.memory = bytearray(30000)
        self.position = 0

        self.test = test
        if self.test:
            self.input_buffer = test
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

    def right(self):
        if self.position < len(self.memory) - 1:
            self.position += 1

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
        # Printout in a friendly format
        out = '(%s)' % cell if cell < 10 else chr(cell)

        if self.test:
            self.out_buffer += out
        else:
            sys.stdout.write(out)


# Create the parsing/interpreting graph for the specified VM
def make_graph(vm):
    simple_commands = dict((('+', vm.inc), ('-', vm.dec), ('.', vm.output), (',', vm.input),
                            ('>', vm.right), ('<', vm.left)))

    def add_simple_command(top, last_parsed):
        # Last_parsed works fine as the name of the notion
        NextRelation2(top, ActionNotion2(last_parsed, simple_commands[last_parsed], top.owner), top.owner)

    def start_loop(top, top_stack, parsed_length):
        top_stack.append((top, parsed_length))
        new_top = ComplexNotion2('Loop', top.owner)

        # Loop becomes the new top to add the simple commands
        LoopRelation2(top, new_top, lambda: None if not vm.is_not_zero() else True)

        return {UPDATE_CONTEXT: {'top': new_top}}

    def stop_loop(top_stack):
        if top_stack:
            return {UPDATE_CONTEXT: {'top': top_stack.pop()[0]}}
        else:
            return STOP

    # Building interpreter graph, Source is responsible for parsing and Program for execution
    b = GraphBuilder('Interpreter').next().complex('Source').next().complex('Commands')
    command_root = b.loop(lambda text: text).select('Command').current

    # Simple command parsing
    b.parse_rel(simple_commands.keys()).act('Simple command', add_simple_command)

    # Loops
    b.at(command_root).parse_rel('[').act('Start loop', start_loop)
    b.at(command_root).parse_rel(']').act('Stop loop', stop_loop)

    # Invalid character error
    b.at(command_root).parse_rel(
        lambda text: 1 if text[0] not in simple_commands else 0).act('Bad character', STOP)

    # The program itself
    program_root = b.at(b.graph.root).act_rel(
        lambda top_stack: None if not top_stack else STOP).complex('Program').current

    return {'root': b.graph, 'top': program_root, 'top_stack': []}


# Interprets specified string using buffer for testing
def interpret(source, test=None):
    vm = BFVM(test)

    context = make_graph(vm)

    process = ParsingProcess2()

    r = process(context['root'], text=source, **context)

    if r == STOP:
        message = 'Parsing error'

        if isinstance(process.current, Relation2):
            message = 'Start loop without end at position %s' % context['top_stack'][0][1]

        elif isinstance(process.current, Notion2):
            if process.current.name == 'Bad character':
                message = 'Unknown char "%s" at position %s' % (process.last_parsed, process.parsed_length)

            elif process.current.name == 'Stop loop':
                message = 'End loop without start at position %s' % process.parsed_length

        return message

    if test:
        return vm.out_buffer


# Self-test
def test_interpreter():
    result = interpret(',>,.<.', 'ab')
    assert result == 'ba'

    result = interpret('++[.-]', True)
    assert result == '(2)(1)'

    result = interpret('++>++<[.->[.-]<]', True)
    assert result == '(2)(2)(1)(1)'

    result = interpret('[.[[]', True)
    assert result.startswith('Start loop') and result.endswith('1')

    result = interpret('+++a', True)
    assert result.startswith('Unknown char') and result.endswith('4')

    result = interpret('--]', True)
    assert result.startswith('End loop') and result.endswith('3')


def main():
    if len(sys.argv) == 2:
        f = open(sys.argv[1], 'r')
        interpret(f.read())
        f.close()
    else:
        test_interpreter()
        print "Usage: " + sys.argv[0] + " filename"

if __name__ == "__main__":
    main()
