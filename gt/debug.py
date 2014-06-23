# Graph-talk debug classes
# (c) Stas Kravets (krvss) 2011-2014

from core import Handler, Event

from collections import defaultdict

try:
    import pydevd
    _DEBUGGER = 'pydev'
except ImportError:
    _DEBUGGER = 'pdb'


class ProcessDebugger(Handler):
    """
    Process analyzer/debugger, sample usage: ProcessDebugger(process, True) to show the log
    """
    AT = 'at'
    REPLY = 'reply'
    LOG = 'log'

    def __init__(self, process=None, log=False):
        super(ProcessDebugger, self).__init__()
        self._points = defaultdict(dict)
        self._process = None

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

        for _, event in process.events:
            if event.value == process.do_queue_push:
                event.post = self.do_reply_at

            elif event.value == process.do_query:
                event.post = self.is_log

    def detach(self):
        if self._process:
            self._process.off_event(self)
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

    def do_reply_at(self, **context):
        process = context[self.SENDER]
        point = self._points.get(process.current)

        if not point:
            return

        if ProcessDebugger.REPLY in point:
            return self._points[process.current].get(self.REPLY)

    def is_log(self, **context):
        process = context[self.SENDER]
        point = self._points.get(process)

        if not point:
            return

        if self.LOG in point:
            query = process.text + ", " + process.query if hasattr(process, 'text') else process.query
            print "%s: '%s'? - '%s'" % (process.current, query, context.get(Event.RESULT))
