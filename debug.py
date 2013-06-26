# Universal Translator debug classes
# (c) krvss 2011-2013

from ut import Abstract


# Debugger/logger
class Analyzer(Abstract):
    events = []

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
                    self.default_debug(*message, **context)

            elif callable(event):
                result = event(*message, **context)

            if result:
                break

        return result

    def add_details(self):
        self.events.append(Analyzer.print_details)

    def add_queries(self):
        self.events.append(Analyzer.print_queries)

    def default_debug(self, *message, **context):
        pass

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
