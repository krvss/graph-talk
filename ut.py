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
                    return Reply(list(self._relations))


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
        repeat = True
        restore = False

        if self.n and callable(self.n):
            repeat = self.n(self, context)

        elif context:
            counter = 1 if self.n else True

            if self in context:
                if "error" in context:
                    if not self.n:
                        repeat = False
                        restore = True
                    else:
                        return Reply()
                else:
                    if self.n:
                        i = context[self]
                        if i <= self.n:
                            counter = i + 1
                        else:
                            repeat = False

            if repeat:
                context[self] = counter

        if repeat:
            reply = Reply([self.object, self])
            reply.store = self
        else:
            reply = Reply(True)

            if context and self in context:
                del context[self]

            if restore:
                reply.restore = self

        return reply


# Base process class
class Process(Abstract):

    def get_next(self, abstract, message, context):
        raise NotImplementedError()

    def parse(self, message, context = None):
        if not context:
            context = {}
            abstract = None
        else:
            abstract = context.get("start")

        initial_length = len(message)

        while abstract: # TODO : stop when message empty?
            abstract, message, context = self.get_next(abstract, message, context)

        return Reply(not "error" in context, initial_length - len(message))


# Parser process
class ParserProcess(Process):
    def __init__(self):
        super(ParserProcess, self).__init__()

    def _get_context_info(self, context, name, default):
        if not self in context:
            context[self] = {}

        if not name in context[self]:
            context[self][name] = default
            return default
        else:
            return context[self][name]

    def _get_stack(self, context):
        return self._get_context_info(context, "stack", [])

    def _get_states(self, context):
        return self._get_context_info(context, "states", {})

    def _rollback(self, context):
        abstract = None

        if self._can_rollback(context):
            abstract = self._get_stack(context).pop()
            print "Rolled back to %s" % abstract

        return abstract

    def _can_rollback(self, context):
        return len(self._get_stack(context)) > 0

    def _add_to_stack(self, context, abstract):
        stack = self._get_stack(context)
        stack.append(abstract)

        print "Adding next %s to stack, stack size is %s" % (abstract, len(stack))

    def get_next(self, abstract, message, context): #TODO: remove prints or add callbacks

        # Check do we have where to go to
        if not abstract or not isinstance(abstract, Abstract):
            print "Not an abstract - %s, rolling back" % abstract

            return self._rollback(context), message, context
        else:
            print "Current abstract %s, message %s, context %s" % (abstract, message, context)

            reply = abstract.parse(message, context)

            if reply.is_error():
                context["error"] = abstract

                print "Error at %s, rolling back" % abstract

                return self._rollback(context), message, context

        if reply.result:
            if type(reply.result) is types.ListType:
                abstract = reply.result.pop(0) # First one is ready to be processed

                for r in reply.result:
                    self._add_to_stack(context, r)
            else:
                abstract = reply.result
        else:
            print "Nowhere to go at at %s, rolling back" % abstract
            return self._rollback(context), message, context

        if reply.length > 0:
            message = message[reply.length:]

        if hasattr(reply, "store"): # TODO: when to store - before or after result parsing
            self._get_states(context)[reply.store] = (message, dict(context))

        if hasattr(reply, "restore"):
            message, context = self._get_states(context)[reply.restore]
            #del self._get_states(context)[reply.store] TODO

        return abstract, message, context

