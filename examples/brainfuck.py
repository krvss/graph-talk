# Brainfuck interpreter/converter example for Graph-talk
# (c) Stas Kravets (krvss) 2011-2014

import sys
import re

from gt.core import *


class BFVM(object):
    """
    Brainfuck virtual machine that runs language commands
    """
    def __init__(self, test=None):
        self.memory, self.position = bytearray(30000), 0
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
            value = sys.stdin.read(1)

        self.memory[self.position] = ord(value)

    def output(self):
        cell = self.memory[self.position]
        # Printout in a friendly format
        out = '(%s)' % cell if cell < 10 else chr(cell)

        if self.test:
            self.out_buffer += out
        else:
            sys.stdout.write(out)


def build_interpreter(vm):
    """
    Create the parsing/interpreting graph for the specified VM and set-up the environment
    """
    simple_commands = dict((('+', vm.inc), ('-', vm.dec), ('.', vm.output), (',', vm.input),
                            ('>', vm.right), ('<', vm.left)))

    def add_simple_command(top, last_parsed):
        # Last_parsed works fine as the name of the notion
        NextRelation(top, ActionNotion(last_parsed, simple_commands[last_parsed], top.owner), owner=top.owner)

    def start_loop(top, top_stack, parsed_length):
        # Push the current to to the stack to come back later, parsed length is needed for the error message
        top_stack.append((top, parsed_length))
        new_top = ComplexNotion('Loop', top.owner)

        # Loop becomes a new top to add simple commands; condition is to repeat while not zero in memort
        LoopRelation(top, new_top, lambda: None if not vm.is_not_zero() else True)

        return {ParsingProcess.UPDATE_CONTEXT: {'top': new_top}}

    def stop_loop(top_stack):
        if top_stack:
            return {ParsingProcess.UPDATE_CONTEXT: {'top': top_stack.pop()[0]}}
        else:
            return ParsingProcess.STOP  # Here we use very simple error processing, just stopping at certain element

    # Building interpreter graph, Source is responsible for parsing and Program for execution
    b = GraphBuilder('Interpreter').next_rel().complex('Source').next_rel().complex('Commands')

    # Root to add the available commands, looping while there is a text
    command_root = b.loop_rel(lambda text: text).select('Command').current

    # Simple command parsing
    b.parse_rel(simple_commands.keys(), add_simple_command)

    # Loops
    b[command_root].parse_rel('[').act('Start loop', start_loop)
    b[command_root].parse_rel(']').act('Stop loop', stop_loop)

    # Whitespace, just for convenience
    b[command_root].parse_rel(re.compile('\s+'))

    # Invalid character error
    b[command_root].parse_rel(re.compile('.')).default().act('Bad character', ParsingProcess.STOP)

    # The program itself, loop stack should be empty!
    program_root = b[b.graph.root].act_rel(
        lambda top_stack: None if not top_stack else ParsingProcess.STOP).complex('Program').current

    return {'root': b.graph, 'top': program_root, 'top_stack': []}


def run(source, env):
    """
    Execute the source program in the specified environment
    """
    process = ParsingProcess()

    r = process(env.pop('root'), text=source, **env)

    if r == process.STOP:
        message = 'Parsing error'

        if isinstance(process.current, Relation):
            message = 'Start loop without end at the position %s' % env['top_stack'][0][1]

        elif isinstance(process.current, Notion):
            if process.current.name == 'Bad character':
                message = 'Unknown char "%s" at the position %s' % (process.last_parsed, process.parsed_length)

            elif process.current.name == 'Stop loop':
                message = 'End loop without start at position %s' % process.parsed_length

        return message


def interpret(source, test=None):
    """
    Interprets specified string using buffer for testing
    """
    vm = BFVM(test)

    result = run(source, build_interpreter(vm))

    return result if not test else result or vm.out_buffer


def test_interpreter():
    """
    Self-test
    """
    result = interpret(',>, .<.', 'ab')
    assert result == 'ba'

    result = interpret('++ [.-]', True)
    assert result == '(2)(1)'

    result = interpret('++>  ++<\n[.->[.-]<]', True)
    assert result == '(2)(2)(1)(1)'

    result = interpret('[.[[]', True)
    assert result.startswith('Start loop') and result.endswith('1')

    result = interpret('+++a', True)
    assert result.startswith('Unknown char') and result.endswith('4')

    result = interpret('--]', True)
    assert result.startswith('End loop') and result.endswith('3')


def build_converter():
    """
    Create Brainfuck to Python converter graph
    """
    def add_with_tabs(s, src, tabs=0):
        src.append(" " * tabs * 4 + s)

    def start_loop(src, level):
        add_with_tabs('\nwhile mem[i]:', src, level)

        return {ParsingProcess.UPDATE_CONTEXT: {'level': level + 1}}

    def stop_loop(src, level):
        add_with_tabs('\n', src, 0)

        if level:
            return {ParsingProcess.UPDATE_CONTEXT: {'level': level - 1}}
        else:
            return ParsingProcess.STOP  # Error!

    b = GraphBuilder('Converter').next_rel().complex('Code').next_rel().complex('Commands')
    command_root = b.loop_rel(lambda text: text).select('Command').current

    # Commands, with compression
    b[command_root].parse_rel(re.compile('\++')).act('+',
                    lambda level, src, last_parsed: add_with_tabs('mem[i] += %s' % len(last_parsed), src, level))

    b[command_root].parse_rel(re.compile('-+')).act('-',
                    lambda level, src, last_parsed: add_with_tabs('mem[i] -= %s' % len(last_parsed), src, level))

    b[command_root].parse_rel(re.compile('>+')).act('>',
                    lambda level, src, last_parsed: add_with_tabs('i += %s' % len(last_parsed), src, level))

    b[command_root].parse_rel(re.compile('<+')).act('>',
                    lambda level, src, last_parsed: add_with_tabs('i -= %s' % len(last_parsed), src, level))

    b[command_root].parse_rel('.').act('.',
                    lambda level, src: add_with_tabs('sys.stdout.write(chr(mem[i]))', src, level))

    b[command_root].parse_rel(',').act(',',
                    lambda level, src: add_with_tabs('mem[i] = ord(sys.stdin.read(1))', src, level))

    b[command_root].parse_rel('[').act('Start loop', start_loop)
    b[command_root].parse_rel(']').act('Stop loop', stop_loop)

    # Invalid character error
    b[command_root].parse_rel(re.compile('.')).default().act('Bad character', ParsingProcess.STOP)

    return {'root': b.graph,
            'src': ['import sys\n', 'i, mem = 0, bytearray(30000)\n'],
            'level': 0, }


def convert(source):
    """
    Convert source on BF to Python
    """
    context = build_converter()

    result = run(source, context)

    if result is None:
        for line in context['src']:
            print line
    else:
        print result


def main():
    import sys

    if len(sys.argv) >= 2:
        with open(sys.argv[1], 'r') as f:
            source = f.read()
            result = convert(source) if '-c' in sys.argv else interpret(source)

            if result:
                print result
    else:
        test_interpreter()
        print "Usage: " + sys.argv[0] + " filename [-c]"

if __name__ == "__main__":
    main()
