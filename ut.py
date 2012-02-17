# Universal Translator base classes
# (c) krvss 2011-2012

import types

# Base class for all communicable objects
class Abstract(object):
    def __init__(self):
        self._callbacks = []

    def parse(self, message, context = None):
        return None

    def call(self, callback, forget = False):
        if forget and callback in self._callbacks:
            self._callbacks.remove(callback)
        else:
            if callback and callable(callback.parse):
                self._callbacks.append(callback)

    def _notify(self, message, context = None):
        for callee in self._callbacks:
            if callable(callee.parse):
                callee.parse(message, context)


# Class for simple replies
class Reply(object):
    def __init__(self, result = False, length = 0):
        self.result = result
        self.length = length

    def is_error(self):
        return self.result == False

    def __str__(self):
        return "[%s:%s]" % (self.result, self.length)


# Notion is an abstract with name
class Notion(Abstract):
    def __init__(self, name):
        super(Abstract, self).__init__()
        self.name = unicode(name)

    def parse(self, message, context = None):
        return Reply()

    def __str__(self):
        if self.name:
            return "'%s'" % self.name


# Relation is a connection between 1 or more abstracts
class Relation(Abstract):
    def __init__(self, subject, object):
        super(Relation, self).__init__()
        self._subject = None
        self._object = None

        self.subject = subject
        self.object = object

    def get_type(self):
        raise NotImplementedError()

    def _disconnect(self, value, target):
        if value:
            self._notify("unrelating", {"relation": self, target: value})
            self.call(value, True)

    def _connect(self, value, target):
        if value:
            self.call(value)
            self._notify("relating", {"relation": self, target: value})

    @property
    def subject(self):
        return self._subject

    @subject.setter
    def subject(self, value):
        if value == self.subject:
            return

        self._disconnect(self.subject, "subject")
        self._subject = value
        self._connect(value, "subject")

    @property
    def object(self):
        return self._object

    @object.setter
    def object(self, value):
        if value == self.object:
            return

        self._disconnect(self.object, "object")
        self._object = value
        self._connect(value,  "object")

    def __str__(self):
        return "<%s - %s>" % (self.subject, self.object)


# Function notion is notion that can call custom function
class FunctionNotion(Notion):
    def __init__(self, name, function):
        super(FunctionNotion, self).__init__(name)
        self.function = function if callable(function) else None

    def parse(self, message, context = None):
        return Reply(self.function(self, context) if self.function else True)


# Complex notion is a notion that relates with other notions (objects)
class ComplexNotion(Notion):
    def __init__(self, name, relation = None):
        super(ComplexNotion, self).__init__(name)
        self._relations = []

        self._relate(relation)

    def _relate(self, relation):
        if relation and (relation not in self._relations):
            self._relations.append(relation)

            if relation.subject != self:
                relation.subject = self

    def _unrelate(self, relation):
        if relation and (relation in self._relations):
            self._relations.remove(relation)

            if relation.subject == self:
                relation.subject = None

    def parse(self, message, context = None):
        reply = super(ComplexNotion, self).parse(message)

        if reply.is_error():
            if message == "relating":
                if context.get("subject") == self:
                    self._relate(context["relation"])

            elif message == "unrelating":
                if context.get("subject") == self:
                    self._unrelate(context["relation"])

            else: # Returning relations by default
                if len(self._relations) == 1:
                    return Reply(self._relations[0])
                elif not self._relations:
                    return Reply()
                else:
                    return Reply(self._relations)


# Next relation is just a simple sequence relation
NEXT_RELATION = 1

class NextRelation(Relation):
    def __init__(self, subject, object):
        super(NextRelation, self).__init__(subject, object)

    def get_type(self):
        return NEXT_RELATION

    def parse(self, message, context = None):
        return Reply(result = self.object)


# Conditional relation is a condition to go further if message starts with sequence
CONDITIONAL_RELATION = 2

class ConditionalRelation(Relation):
    def __init__(self, subject, object, checker):
        super(ConditionalRelation, self).__init__(subject, object)
        self.checker = checker

    def get_type(self):
        return CONDITIONAL_RELATION

    def parse(self, message, context = None):
        if self.checker:
            result = None

            if callable(self.checker):
                result, length = self.checker(message)
            else:
                length = len(self.checker) if message.startswith(self.checker) else 0

                if length > 0:
                    result = self.checker

            if result:
                if context and self.object: # May be this is something for the object
                    context[self.object] = result

                return Reply(self.object, length)

        return Reply()


# Loop relation is a cycle that repeats object for specified or infinite number of times
LOOP_RELATION = 3

class LoopRelation(Relation):
    def __init__(self, subject, object, n = None):
        super(LoopRelation, self).__init__(subject, object)
        self.n = n

    def get_type(self):
        return LOOP_RELATION

    def parse(self, message, context = None):
        if context:
            counter = 1 if self.n else True

            if self in context:
                if "error" in context:
                    if not self.n:
                        del context[self]
                        return Reply(True) # It is ok if error and * loop
                    else:
                        return Reply()
                else:
                    if self.n:
                        i = context[self]
                        if i > self.n:
                            return Reply(True) # No more iterations
                        else:
                            counter = i + 1

            context[self] = counter

        reply = Reply(self.object)
        reply.loop = self

        return reply

# Process waypoint
class ProcessPoint(object):
    def __init__(self, abstract = None, message = None, context = None):
        super(ProcessPoint, self).__init__()

        self.abstract = abstract
        self.message = message
        self.context = context

    def has_error(self):
        return self.context and "error" in self.context

    def set_error(self, value):
        if not self.context:
            self.context = {}

        self.context["error"] = value

    def get_error(self):
        return self.context["error"] if self.has_error() else None

    def clear_error(self):
        if self.has_error():
            del self.context["error"]


# Base process class
class Process(Abstract):

    def get_next(self, process_point):
        raise NotImplementedError()

    def parse(self, message, context = None):
        if not context:
            context = {}
            abstract = None
        else:
            abstract = context.get("start")

        pp = ProcessPoint(abstract, message, context)

        while pp.abstract: # TODO : stop when message empty?
            pp = self.get_next(pp)

        return Reply(not "error" in context, len(message) - len(pp.message))


# Parser process
class ParserProcess(Process):
    def __init__(self):
        super(ParserProcess, self).__init__()

    def _get_stack(self, process_point):
        if not self in process_point.context:
            _stack = []
            process_point.context[self] = {"stack": _stack}
        else:
            _stack = process_point.context[self]["stack"]

        return _stack

    def _rollback(self, process_point):
        if self._can_rollback(process_point):
            old_process_point = self._get_stack(process_point).pop()

            if hasattr(old_process_point, "loop"):
                if process_point.has_error():
                    old_process_point.set_error(process_point.get_error()) # We need to keep error for the loop
                else:
                    old_process_point.message = process_point.message # Restoring context for the loop but keep message
            else: # Alternatives
                if not process_point.has_error():
                    process_point.abstract = True
                    old_process_point = process_point

            print "Rolled back to %s" % old_process_point.abstract

            return old_process_point
        else:
            process_point.abstract = None
            return process_point

    def _can_rollback(self, process_point):
        return len(self._get_stack(process_point)) > 0

    def _add_to_stack(self, process_point, reply):
        stack = self._get_stack(process_point)

        if hasattr(reply, "loop"):
            pp = ProcessPoint(reply.loop, process_point.message, process_point.context)

            pp.loop = reply.loop
            stack.append(pp)
            print "Adding loop %s to the stack, stack size is %s" % (pp.loop, len(stack))

        else:
            stack.append(ProcessPoint(reply.result, process_point.message, process_point.context))
            print "Adding alternative %s to stack, stack size is %s" %( reply.result, len(stack))

    def get_next(self, process_point): #TODO: remove prints or add callbacks

        # Check do we have where to go to
        if not process_point.abstract or not isinstance(process_point.abstract, Abstract):
            print "Not an abstract - %s, rolling back" % process_point.abstract if hasattr(process_point, "abstract")  \
                                                                              else process_point

            if self._can_rollback(process_point):
                return self._rollback(process_point)
            else:
                process_point.abstract = None
                return process_point
        else:
            print "Current abstract %s, message %s" % (process_point.abstract, process_point.message)

            reply = process_point.abstract.parse(process_point.message, process_point.context)

            if reply.is_error():
                process_point.set_error(process_point.abstract)

                print "Error at %s, rolling back" % process_point.get_error()

                return self._rollback(process_point)

            else:
                process_point.clear_error()

        if reply.result:
            if type(reply.result) is types.ListType: # TODO check modes or result

                length = -1
                bestReply = None # TODO: alternative
                alternatives = []

                for a in reply.result:
                    r = a.parse(process_point.message, process_point.context)

                    if r.result:
                        if r.length > length:
                            bestReply = r
                            length = r.length
                            alternatives = []
                        elif r.length == length:
                            if bestReply:
                                alternatives.append(bestReply)
                                bestReply = None

                            alternatives.append(r)

                if bestReply:
                    reply = bestReply
                    print "Best reply %s selected" % reply
                else:
                    if alternatives:
                        reply = alternatives.pop(0)
                        alternatives.reverse()

                        for a in alternatives:
                            self._add_to_stack(process_point, a)

                        print "First alternative %s selected" % reply
                    else:
                        print "No alternatives, trying to roll back"
                        process_point.set_error(process_point.abstract)
                        return self._rollback(process_point)

            process_point.abstract = reply.result
        else:
            return self._rollback(process_point)

        if reply.length > 0:
            process_point.message = process_point.message[reply.length:]

        if hasattr(reply, "loop"):
            self._add_to_stack(process_point, reply)

        return process_point

