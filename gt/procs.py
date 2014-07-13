# Graph-talk processor classes
# (c) Stas Kravets (krvss) 2011-2014

from gt.core import *

class FileProcessor(Process):
    """
    File processor contains the graph and the parsing process to parse the file contents
    """
    FILENAME = 'filename'
    def __init__(self, name):
        super(FileProcessor, self).__init__()
        self.parser = ParsingProcess()
        self.builder = GraphBuilder(name)

        self.filename = None

        self.build_graph()

    def build_graph(self):
        pass

    def parser_call(self, message=None, context=None):
        """
        Call the parser with specified message and context; default values is graph root and self context
        """
        return self.parser(*(message or [self.builder.graph]), **(context or self.context))

    # Events #
    def on_file(self, *message):
        """
        Process the new file
        """
        self.filename = message[0].pop(self.FILENAME)
        message[0][self.parser.TEXT] = get_content(self.filename)

    def on_text(self, *message):
        self.context[self.parser.TEXT] = message[0].pop(self.parser.TEXT)

        return self.parser_call()

    def setup_events(self):
        super(FileProcessor, self).setup_events()

        self.on(lambda *message: self.FILENAME in message[0], self.on_file, Condition.DICT)
        self.on(lambda *message: self.parser.TEXT in message[0], self.on_text, Condition.DICT)

    def get_reply(self, result):
        """
        Pre-process the reply
        """
        return result

    def on_new(self, message, context):
        super(FileProcessor, self).on_new(message, context)
        self.parser(self.NEW)

        self.filename = None

    def handle(self, message, context):
        context.update(self.context)
        result = super(FileProcessor, self).handle(message, context)

        # Act as a proxy - if nothing found locally call parser's handle
        if result == self.NO_HANDLE:
            result = self.parser.handle(message, context)

        return self.get_reply(result[0]), result[1], result[2]
