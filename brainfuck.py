from ut import *

# Language description
class Language:
    INC = '+'
    DEC = '-'
    NEXT = '>'
    PREV = '<'
    OUT = '.'
    IN = ','

    @staticmethod
    def increment(memory, position):
        inc = memory[position] + 1
        memory[position] = inc if inc < 255 else 0

    @staticmethod
    def decrement(memory, position):
        dec = memory[position] - 1
        memory[position] = dec if dec >= 0 else 255

    @staticmethod
    def get_command(id):
        if id == Language.INC:
            return Language.increment
        elif id == Language.DEC:
            return Language.decrement


class CommandNotion(FunctionNotion):
    def __init__(self, command):
        super(CommandNotion, self).__init__('Command', self.run)
        self.cmd = Language.get_command(command)

    def run(self, *message, **context):
        if not 'memory' in context:
            return

        memory = context['memory']
        position = context['position']

        new_pos = self.cmd(memory, position)

        if new_pos:
            return {'update_context': {'position' : new_pos}}


class ParserCommand(FunctionNotion):
    def __init__(self):
        super(ParserCommand, self).__init__('Parser Command', self.make_command)

    def make_command(self, *message, **context):
        if not 'state' in context:
            return

        command = context['state']['notifications']['condition']

        reply = {}

        root = context.get('program_root')

        if not root:
            root = ComplexNotion('Program')
            reply['add_context'] = {'program_root': root}

        Relation(root, CommandNotion(command))

        return reply


def stopper(n, *m, **c):
    if 'text' in c:
        if len(c['text']) > 0:
            return 'error'
        else:
            return 'stop'


class Parser(TextParsingProcess):
    def parse_source(self, source):
        return self.parse('new', self.get_graph(), text=source)

    @staticmethod
    def get_graph():
        root = ComplexNotion('Brainfuck Program')

        command = SelectiveNotion('Command')

        LoopRelation(root, command)

        simple_cmd = ParserCommand()

        ConditionalRelation(command, simple_cmd, Language.INC)
        ConditionalRelation(command, simple_cmd, Language.DEC)
        NextRelation(command, FunctionNotion('Unknown command', stopper))

        return root


def load(from_str):
    from test import logger

    parser = Parser()
    parser.callback = logger
    logger.logging = True

    r = parser.parse_source(from_str)

    if r == 'ok':
        return parser.context['program_root']
