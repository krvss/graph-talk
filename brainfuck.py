import sys

from ut import *
import re

# TODO: optimization and white space

# Brainfuck virtual machine that runs language commands
class BFVM(object):
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


# Create the parsing/interpreting graph for the specified VM
def make_interpreter_graph(vm):
    simple_commands = dict((('+', vm.inc), ('-', vm.dec), ('.', vm.output), (',', vm.input),
                            ('>', vm.right), ('<', vm.left)))

    def add_simple_command(top, last_parsed):
        # Last_parsed works fine as the name of the notion
        NextRelation(top, ActionNotion(last_parsed, simple_commands[last_parsed], top.owner), owner=top.owner)

    def start_loop(top, top_stack, parsed_length):
        top_stack.append((top, parsed_length))
        new_top = ComplexNotion('Loop', top.owner)

        # Loop becomes the new top to add the simple commands
        LoopRelation(top, new_top, lambda: None if not vm.is_not_zero() else True)

        return {SharedProcess.UPDATE_CONTEXT: {'top': new_top}}

    def stop_loop(top_stack):
        if top_stack:
            return {SharedProcess.UPDATE_CONTEXT: {'top': top_stack.pop()[0]}}
        else:
            return Process.STOP

    # Building interpreter graph, Source is responsible for parsing and Program for execution
    b = GraphBuilder('Interpreter').next_rel().complex('Source').next_rel().complex('Commands')
    command_root = b.loop(lambda text: text).select('Command').current

    # Simple command parsing
    b.parse_rel(simple_commands.keys(), add_simple_command)

    # Loops
    b.at(command_root).parse_rel('[').act('Start loop', start_loop)
    b.at(command_root).parse_rel(']').act('Stop loop', stop_loop)

    # Invalid character error
    b.at(command_root).parse_rel(re.compile('.')).default().act('Bad character', Process.STOP)

    # The program itself
    program_root = b.at(b.graph.root).act_rel(
        lambda top_stack: None if not top_stack else Process.STOP).complex('Program').current

    return {'root': b.graph, 'top': program_root, 'top_stack': []}


def run(source, context):
    process = ParsingProcess()

    r = process(context['root'], text=source, **context)

    if r == Process.STOP:
        message = 'Parsing error'

        if isinstance(process.current, Relation):
            message = 'Start loop without end at position %s' % context['top_stack'][0][1]

        elif isinstance(process.current, Notion):
            if process.current.name == 'Bad character':
                message = 'Unknown char "%s" at position %s' % (process.last_parsed, process.parsed_length)

            elif process.current.name == 'Stop loop':
                message = 'End loop without start at position %s' % process.parsed_length

        return message


# Interprets specified string using buffer for testing
def interpret(source, test=None):
    vm = BFVM(test)

    result = run(source, make_interpreter_graph(vm))

    return result if not test else result or vm.out_buffer


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


def make_converter_graph():
    def add_with_tabs(s, code, tabs=0):
        code.append(" " * tabs * 4 + s)

    def start_loop(code, level):
        add_with_tabs('\nwhile mem[i]:', code, level)

        return {SharedProcess.UPDATE_CONTEXT: {'level': level + 1}}

    def stop_loop(code, level):
        add_with_tabs('\n', code, 0)

        if level:
            return {SharedProcess.UPDATE_CONTEXT: {'level': level - 1}}
        else:
            return Process.STOP

    # Building converter graph
    b = GraphBuilder('Interpreter').next_rel().complex('code').next_rel().complex('Commands')
    command_root = b.loop(lambda text: text).select('Command').current

    # Commands
    b.at(command_root).parse_rel(re.compile('\++')).act('+',
                    lambda level, code, last_parsed: add_with_tabs('mem[i] += %s' % len(last_parsed), code, level))

    b.at(command_root).parse_rel(re.compile('-+')).act('-',
                    lambda level, code, last_parsed: add_with_tabs('mem[i] -= %s' % len(last_parsed), code, level))

    b.at(command_root).parse_rel(re.compile('>+')).act('>',
                    lambda level, code, last_parsed: add_with_tabs('i += %s' % len(last_parsed), code, level))

    b.at(command_root).parse_rel(re.compile('<+')).act('>',
                    lambda level, code, last_parsed: add_with_tabs('i -= %s' % len(last_parsed), code, level))

    b.at(command_root).parse_rel('.').act('.',
                    lambda level, code: add_with_tabs('sys.stdout.write(chr(mem[i]))', code, level))

    b.at(command_root).parse_rel(',').act(',',
                    lambda level, code: add_with_tabs('mem[i] = ord(sys.stdin.read(1))', code, level))

    b.at(command_root).parse_rel('[').act('Start loop', start_loop)
    b.at(command_root).parse_rel(']').act('Stop loop', stop_loop)

    # Invalid character error
    b.at(command_root).parse_rel(re.compile('.')).default().act('Bad character', Process.STOP)
    
    # Initial source
    code = []
    code.append('import sys\n')
    code.append('i, mem = 0, bytearray(30000)\n')

    return {'root': b.graph, 'code': code, 'level': 0, }


def convert(source):
    context = make_converter_graph()

    result = run(source, context)

    if result is None:
        for line in context['code']:
            print line
    else:
        print result


def main():
    if len(sys.argv) >= 2:
        with open(sys.argv[1], 'r') as f:
            source = f.read()
            result = convert(source) if 'c' in sys.argv else interpret(source)

            if result:
                print result
    else:
        test_interpreter()
        print "Usage: " + sys.argv[0] + " filename [c]"

if __name__ == "__main__":
    main()
