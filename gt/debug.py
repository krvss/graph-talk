"""
.. module:: gt.debug
   :platform: Unix, Windows
   :synopsis: Graph-talk debug classes

.. moduleauthor:: Stas Kravets (krvss) <stas.kravets@gmail.com>

"""

from gt.core import Handler, Event

from collections import defaultdict


class ProcessDebugger(Handler):
    """
    Process analyzer/debugger, use to see the process logs or to emulate the reply from a certain element.
    """
    AT = 'at'
    REPLY = 'reply'
    LOG = 'log'

    def __init__(self, process=None, log=False):
        """
        Creates the new debugger.

        :param process: attach to the specified process.
        :type process: Process.
        :param log: start logging the process queries.
        :type log: bool.
        """
        super(ProcessDebugger, self).__init__()
        self._points = defaultdict(dict)
        self._process = None

        self.attach(process)

        if log:
            self.show_log()

    def attach(self, process):
        """
        Attaches the debugger to the specified process events.

        :param process: the process to attach.
        :type process: Process.
        """
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
        """
        Detaches the debugger from the process.
        """
        if self._process:
            self._process.off_event(self)
            self._process = None
        
    def clear_points(self):
        """
        Clears the reply and log hooks.
        """
        self._points.clear()

    def reply_at(self, abstract, reply):
        """
        Emulates the reply.

        :param abstract: element to emulate the reply.
        :type abstract: Abstract.
        :param reply: reply to return on the process' query.
        """
        self._points[abstract] = {ProcessDebugger.REPLY: reply}

    def show_log(self):
        """
        Adds the show log hook to the query event.
        """
        self._points[self._process] = {ProcessDebugger.LOG: True}

    def hide_log(self):
        """
        Removes the show log hook.
        """
        if self._process in self._points:
            del self._points[self._process]

    def do_reply_at(self, **context):
        """
        Reply event: returns the specified reply to the process.
        """
        process = context[self.SENDER]
        point = self._points.get(process.current)

        if not point:
            return

        if ProcessDebugger.REPLY in point:
            return self._points[process.current].get(self.REPLY)

    def is_log(self, **context):
        """
        Log event: prints the process' query and the element's reply on it.
        """
        process = context[self.SENDER]
        point = self._points.get(process)

        if not point:
            return

        if self.LOG in point:
            query = process.text + ', ' + process.query if hasattr(process, 'text') else process.query
            print("%s: '%s'? - '%s'" % (process.current, query, context.get(Event.RESULT)))
