# Universal Translator debug classes
# (c) krvss 2011-2013

from collections import defaultdict

from ut import Abstract, Handler, Process2, Talker
from utils import has_first, get_object_name

try:
    import pydevd
    _DEBUGGER = 'pydev'
except ImportError:
    _DEBUGGER = 'pdb'

#TODO: remove analyzer, make logger more friendly

class ProcessDebugger(Handler):
    AT = 'at'
    REPLY = 'reply'
    LOG = 'log'
    EVENT = 'event'

    AT_EVENT = Process2.add_prefix(get_object_name(Process2.do_queue_push), Talker.POST_PREFIX)
    LOG_EVENT = Process2.add_prefix(Process2.QUERY, Talker.POST_PREFIX)

    def __init__(self, process=None):
        super(ProcessDebugger, self).__init__()
        self._points = defaultdict(dict)

        self.on(self.is_at, self.do_reply_at)
        self.on(self.is_log, None)

        if process:
            self.attach(process)

    def attach(self, process):
        process.on_any(self)

    def detach(self, process):
        process.off_handler(self)
        
    def clear_points(self):
        self._points.clear()

    def reply_at(self, abstract, reply):
        self._points[abstract] = {ProcessDebugger.REPLY: reply}

    def show_log(self, process):
        self._points[process] = {ProcessDebugger.LOG: True}

    def is_at(self, *message, **context):
        process = context[Handler.SENDER]
        point = self._points.get(process.current)

        if not point:
            return

        if ProcessDebugger.REPLY in point:
            return has_first(message, ProcessDebugger.AT_EVENT)

    def do_reply_at(self, *message, **context):
        process = context.get(self.SENDER)
        return self._points[process.current].get(self.REPLY)

    def is_log(self, *message, **context):
        process = context[Handler.SENDER]
        point = self._points.get(process)

        if not point:
            return

        if self.LOG in point and has_first(message, ProcessDebugger.LOG_EVENT):
            query = process.text + ", " + process.query if hasattr(process, 'text') else process.query
            print "%s: '%s'? - '%s'" % (process.current, query, context.get(process.RESULT))


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
