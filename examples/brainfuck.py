# Brainfuck interpreter/converter example for Graph-talk
# (c) Stas Kravets (krvss) 2011-2014

import sys
import re

from gt.core import *
from gt.procs import FileProcessor


class BFVM(object):
    """
    Brainfuck virtual machine that runs language commands
    """
    def __init__(self):
        self.memory, self.position = None, None
        self.test, self.input_buffer, self.out_buffer = None, None, None
        self.reset()

    def set_test(self, test):
        self.test = test

        if is_string(test):
            self.input_buffer = test

        self.out_buffer = ''

    def reset(self):
        self.position = 0
        self.memory = bytearray(30000)

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


class BFInterpreter(FileProcessor):
    """
    Brainfuck interpreter example, builds the program graph first and then executes it
    """
    TOP = 'top'
    TOP_STACK = 'top_stack'
    TEST = 'test'

    def __init__(self):
        self.vm = BFVM()
        super(BFInterpreter, self).__init__('Interpreter')

    def build_graph(self):
        """
        Create the parsing/interpreting graph for the specified VM and set-up the environment
        """
        simple_commands = dict((('+', self.vm.inc), ('-', self.vm.dec), ('.', self.vm.output), (',', self.vm.input),
                                ('>', self.vm.right), ('<', self.vm.left)))

        def add_simple_command(top, last_parsed):
            # Last_parsed works fine as the name of the notion
            NextRelation(top, ActionNotion(last_parsed, simple_commands[last_parsed], top.owner), owner=top.owner)

        def start_loop(top, top_stack, parsed_length):
            # Push the current to to the stack to come back later, parsed length is needed for the error message
            top_stack.append((top, parsed_length))
            new_top = ComplexNotion('Loop', top.owner)

            # Loop becomes a new top to add simple commands; condition is to repeat while not zero in memory
            LoopRelation(top, new_top, lambda: None if not self.vm.is_not_zero() else True)

            return {ParsingProcess.UPDATE_CONTEXT: {self.TOP: new_top}}

        def stop_loop(top_stack):
            if top_stack:
                return {ParsingProcess.UPDATE_CONTEXT: {self.TOP: top_stack.pop()[0]}}
            else:
                return ParsingProcess.STOP  # Here we use very simple error processing, just stopping at certain element

        # Building interpreter graph, Source is responsible for parsing and Program for execution
        self.builder.next_rel().complex('Source').next_rel().complex('Commands')

        # Root to add the available commands, looping while there is a text
        command_root = self.builder.loop_rel(lambda text: text).select('Command').current

        # Simple command parsing
        self.builder.parse_rel(simple_commands.keys(), add_simple_command)

        # Loops
        self.builder[command_root].parse_rel('[').act('Start loop', start_loop)
        self.builder[command_root].parse_rel(']').act('Stop loop', stop_loop)

        # Whitespace, just for convenience
        self.builder[command_root].parse_rel(re.compile('\s+'))

        # Invalid character error
        self.builder[command_root].parse_rel(re.compile('.')).default().act('Bad character', ParsingProcess.STOP)

        # The program itself, loop stack should be empty!
        self.context[self.TOP] = self.builder[self.builder.graph.root].act_rel(
            lambda top_stack: None if not top_stack else ParsingProcess.STOP).complex('Program').current

        self.context[self.TOP_STACK] = []

    def get_reply(self, result):
        if result == self.parser.STOP:
            message = 'Parsing error'

            if isinstance(self.parser.current, Relation):
                message = 'Start loop without end at the position %s' % self.context['top_stack'][0][1]

            elif isinstance(self.parser.current, Notion):
                if self.parser.current.name == 'Bad character':
                    message = 'Unknown char "%s" at the position %s' % (self.parser.last_parsed, self.parser.parsed_length)

                elif self.parser.current.name == 'Stop loop':
                    message = 'End loop without start at position %s' % self.parser.parsed_length

            return message

        elif self.vm.test:
            return self.vm.out_buffer

    def on_test(self, *message):
        self.vm.set_test(message[0].pop(self.TEST))

    def setup_events(self):
        super(BFInterpreter, self).setup_events()

        self.on(lambda *message: 1 if self.TEST in message[0] else -1, self.on_test, Condition.DICT)

    def on_new(self, message, context):
        super(BFInterpreter, self).on_new(message, context)

        context[self.TOP_STACK] = []
        self.vm.reset()

        self.builder.graph.notion('Program').remove_all()

    def self_test(self):
        """
        Self-test
        """
        result = self(Process.NEW, {'text':',>, .<.', 'test':'ab'})
        assert result == 'ba'

        result = self(Process.NEW, {'text':'++ [.-]', 'test': True})
        assert result == '(2)(1)'

        result = self(Process.NEW, {'text':'++>  ++<\n[.->[.-]<]', 'test': True})
        assert result == '(2)(2)(1)(1)'

        result = self(Process.NEW, {'text':'[.[[]', 'test': True})
        assert result.startswith('Start loop') and result.endswith('1')

        result = self(Process.NEW, {'text':'+++a', 'test': True})
        assert result.startswith('Unknown char') and result.endswith('4')

        result = self(Process.NEW, {'text':'--]', 'test': True})
        assert result.startswith('End loop') and result.endswith('3')


class BFConverter(FileProcessor):
    """
    Brainfuck to Python converter
    """
    SRC = 'src'
    LEVEL = 'level'

    DEFAULT = {SRC: ['import sys', 'i, mem = 0, bytearray(30000)\n'], LEVEL: 0}

    def __init__(self):
        super(BFConverter, self).__init__('Converter')

    def build_graph(self):
        """
        Create Brainfuck to Python converter graph
        """
        def add_with_tabs(s, src, tabs=0):
            src.append(" " * tabs * 4 + s)

        def start_loop(src, level):
            add_with_tabs('\nwhile mem[i]:', src, level)

            return {ParsingProcess.UPDATE_CONTEXT: {BFConverter.LEVEL: level + 1}}

        def stop_loop(src, level):
            add_with_tabs('\n', src, 0)

            if level:
                return {ParsingProcess.UPDATE_CONTEXT: {BFConverter.LEVEL: level - 1}}
            else:
                return ParsingProcess.STOP  # Error!

        self.builder.next_rel().complex('Code').next_rel().complex('Commands')
        command_root = self.builder.loop_rel(lambda text: text).select('Command').current

        # Commands, with compression
        self.builder[command_root].parse_rel(re.compile('\++')).act('+',
                                                                    lambda level, src, last_parsed: add_with_tabs(
                                                                        'mem[i] += %s' % len(last_parsed), src, level))

        self.builder[command_root].parse_rel(re.compile('-+')).act('-',
                                                                   lambda level, src, last_parsed: add_with_tabs(
                                                                       'mem[i] -= %s' % len(last_parsed), src, level))

        self.builder[command_root].parse_rel(re.compile('>+')).act('>',
                                                                   lambda level, src, last_parsed: add_with_tabs(
                                                                       'i += %s' % len(last_parsed), src, level))

        self.builder[command_root].parse_rel(re.compile('<+')).act('>',
                                                                   lambda level, src, last_parsed: add_with_tabs(
                                                                       'i -= %s' % len(last_parsed), src, level))

        self.builder[command_root].parse_rel('.').act('.',
                                                      lambda level, src: add_with_tabs('sys.stdout.write(chr(mem[i]))',
                                                                                       src, level))

        self.builder[command_root].parse_rel(',').act(',',
                                                      lambda level, src: add_with_tabs(
                                                          'mem[i] = ord(sys.stdin.read(1))', src, level))

        self.builder[command_root].parse_rel(re.compile('\s+'))

        self.builder[command_root].parse_rel('[').act('Start loop', start_loop)
        self.builder[command_root].parse_rel(']').act('Stop loop', stop_loop)

        # Invalid character error
        self.builder[command_root].parse_rel(re.compile('.')).default().act('Bad character', ParsingProcess.STOP)

        self.context.update(self.DEFAULT)

    def get_reply(self, result):
        if result is None:
            return '\n'.join(self.context[self.SRC])
        else:
            return 'print "Parsing error"'

    def on_new(self, message, context):
        super(BFConverter, self).on_new(message, context)

        context.update(self.DEFAULT)

    def self_test(self):
        from cStringIO import StringIO
        import tempfile

        backup = sys.stdout

        try:
            sys.stdout = StringIO()

            temp = tempfile.NamedTemporaryFile(delete=False)
            temp.write(self(Process.NEW, {self.FILENAME: 'hello.bf'}))
            temp.close()

            execfile(temp.name)
            out = sys.stdout.getvalue()

        finally:
            sys.stdout.close()
            sys.stdout = backup

        assert out.startswith('Hello World!')

def main():
    import sys

    interpreter = BFInterpreter()
    converter = BFConverter()

    if len(sys.argv) >= 2:
        dude = converter if '-c' in sys.argv else interpreter

        result = dude(interpreter.NEW, {interpreter.FILENAME: sys.argv[1]})

        if result:
            print result

    else:
        interpreter.self_test()
        converter.self_test()
        print "Usage: " + sys.argv[0] + " filename [-c]"

if __name__ == "__main__":
    main()
