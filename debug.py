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


# Process analyzer/debugger, sample usage: ProcessDebugger(process, True) to show the log
class ProcessDebugger(Handler):
    AT = 'at'
    REPLY = 'reply'
    LOG = 'log'
    EVENT = 'event'

    AT_EVENT = Process2.add_prefix(get_object_name(Process2.do_queue_push), Talker.POST_PREFIX)
    LOG_EVENT = Process2.add_prefix(Process2.QUERY, Talker.POST_PREFIX)

    def __init__(self, process=None, log=False):
        super(ProcessDebugger, self).__init__()
        self._points = defaultdict(dict)
        self._process = None

        self.on(self.is_at, self.do_reply_at)
        self.on(self.is_log, None)

        self.attach(process)

        if log:
            self.show_log()

    def attach(self, process):
        if self._process == process:
            return

        elif self._process:
            self.detach()

        if process:
            self._process = process

        process.on_any(self)

    def detach(self):
        if self._process:
            self._process.off_handler(self)
            self._process = None
        
    def clear_points(self):
        self._points.clear()

    def reply_at(self, abstract, reply):
        self._points[abstract] = {ProcessDebugger.REPLY: reply}

    def show_log(self):
        self._points[self._process] = {ProcessDebugger.LOG: True}

    def hide_log(self):
        if self._process in self._points:
            del self._points[self._process]

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

