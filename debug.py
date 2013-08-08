# Universal Translator debug classes
# (c) krvss 2011-2013

from ut import Abstract


# Debugger/logger
class Analyzer(Abstract):
    events = []

    def __init__(self):
        self.debug = None

    def parse(self, *message, **context):
        process = context.get('from')
        result = False

        for event in self.events:
            if isinstance(event, dict):

                if 'filter' in event and message and not message[0].startswith(event['filter']):
                    continue

                if 'abstract' in event and process and process.current != event['abstract']:
                    continue

                result = event['call'](*message, **context) if 'call' in event else \
                    self.debug(*message, **context) if callable(self.debug) else None

            elif callable(event):
                result = event(*message, **context)

            if result:
                break

        return result

    def add_details(self):
        self.events.append(Analyzer.print_details)

    def add_queries(self, text = False):
        if not text:
            self.events.append(Analyzer.print_queries)
        else:
            self.events.append(Analyzer.print_queries_and_text)

    @staticmethod
    def print_details(*message, **context):
        process = context['from']

        log_str = '%s:' % message[0]
        properties = ', '.join([('%s: %s' % (p, getattr(process, p))) for p in process._queueing_properties()])

        print log_str + properties

        return None

    @staticmethod
    def print_queries(*message, **context):
        if message:
            if message[0].startswith('query_pre'):
                print '( %s )' % context['from'].current,
            elif message[0].startswith('result_pre'):
                print ''

    @staticmethod
    def print_queries_and_text(*message, **context):
        if message:
            if message[0].startswith('query_pre'):
                print '( %s : [%s] )' % (context['from'].current, context.get('context').get('text'))
            elif message[0].startswith('result_pre'):
                print ''
