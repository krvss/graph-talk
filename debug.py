# Universal Translator debug classes
# (c) krvss 2011-2013

from ut import Abstract, Handler
from utils import has_first, get_object_name

try:
    import pydevd
    _DEBUGGER = 'pydev'
except ImportError:
    _DEBUGGER = 'pdb'


class ProcessDebugger(Handler):
    AT = 'at'
    REPLY = 'reply'
    LOG = 'log'
    EVENT = 'event'

    def __init__(self):
        super(ProcessDebugger, self).__init__()
        self.points = []
        self.processes = {}

        self.on(self.is_at, self.do_reply_at)
        self.on(self.is_log, None)

    def attach(self, process):
        process.on_any(self)
        process_events = {self.AT: process.add_prefix(get_object_name(process.do_queue_push), process.POST_PREFIX),
                          self.LOG: process.add_prefix(process.QUERY, process.POST_PREFIX)}

        self.processes[process] = process_events

    def detach(self, process):
        process.off_all(self)
        # TODO points clear

    def find_point(self, process):
        for point in self.points:
            if point.get(self.AT) == process.current or point.get(self.LOG) == process:
                return point

    def get_process_point(self, context):
        #TODO: should we be so bound to self.XXXX or process.XXXX
        process = context.get(self.SENDER)
        if not process in self.processes:
            return None, None

        return process, self.find_point(process)

    def reply_at(self, abstract, reply):
        self.points.append({self.AT: abstract, self.REPLY: reply})

    def show_log(self, process):
        self.points.append({self.LOG: process})

    def is_at(self, *message, **context):
        process, point = self.get_process_point(context)
        if not point:
            return

        if self.REPLY in point:
            return has_first(message, self.processes[process].get(self.AT))

    def do_reply_at(self, *message, **context):
        process = context.get(self.SENDER)
        return self.find_point(process).get(self.REPLY)

    def is_log(self, *message, **context):
        process, point = self.get_process_point(context)
        if not point:
            return

        if self.LOG in point and has_first(message, self.processes[process].get(self.LOG)):
            print "%s: '%s'? - '%s'" % (process.current, process.query, context.get(process.RESULT))


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
                print '( %s )' % context['from'].current
            elif message[0].startswith('result_pre'):
                print ''

    @staticmethod
    def print_queries_and_text(*message, **context):
        if message:
            if message[0].startswith('query_pre'):
                print '( %s : [%s] )' % (context['from'].current, context.get('context').get('text'))
            elif message[0].startswith('result_pre'):
                print ''
