# Universal Translator base classes
# (c) krvss 2011-2012

import types

# Base class for all communicable objects
class Abstract(object):
    def __init__(self):
        self.callbacks = []

    def parse(self, message, context = None):
        return None

    def call(self, callback, forget = False):
        if forget and callback in self.callbacks:
            self.callbacks.remove(callback)
        else:
            if callback and callable(callback.parse):
                self.callbacks.append(callback)

    def _notify(self, message, context = None):
        for callee in self.callbacks:
            if callable(callee.parse):
                callee.parse(message, context)


# Class for simple replies
class Reply(object):
    def __init__(self, result = False, length = 0):
        self.result = result
        self.length = length

    def is_error(self):
        return self.result == False


# Notion is an abstract with name
class Notion(Abstract):
    def __init__(self, name):
        super(Abstract, self).__init__()
        self.name = unicode(name)

    def parse(self, message, context = None):
        return Reply()


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
        self._disconnect(self.subject, "subject")
        self._subject = value
        self._connect(value, "subject")

    @property
    def object(self):
        return self._object

    @object.setter
    def object(self, value):
        self._disconnect(self.object, "object")
        self._object = value
        self._connect(value,  "object")


# Value notion is a name-value abstract
class ValueNotion(Notion):
    def __init__(self, name, value = None):
        super(ValueNotion, self).__init__(name)
        self.value = value

    def parse(self, message, context = None):
        if context and self in context:
            # Spawining a new if there is something for us
            value = context[self]
            del context[self]
            context["result"] = ValueNotion(self.name, value)

            return Reply(True)

        return Reply()


# Complex notion is a notion that relates to other notions
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
        return Reply(result=self.subject)


# Conditional relation is a condition to go further if message starts with sequence
CONDITIONAL_RELATION = 2

class ConditionalRelation(Relation):
    def __init__(self, subject, object, checker):
        super(ConditionalRelation, self).__init__(subject, object)
        self.checker = checker

    def get_type(self):
        return CONDITIONAL_RELATION

    def parse(self, message, context = None):
        if callable(self.checker):
            result, length = self.checker(message)

            if result:
                if context and self.object:
                    context[self.object] = result

                return Reply(result=self.object, length = length)

        return Reply()


# Case of conditional: presence of char sequence
class CharSequenceConditionalRelation(ConditionalRelation):
    def __init__(self, subject, object, checker):
        super(CharSequenceConditionalRelation, self).__init__(subject, object, checker)

    def parse(self, message, Context = None):
        length = len(self.checker) if message.lower().startswith(self.checker) else 0

        if length > 0:
            return Reply(result=self.object, length = length)

        return Reply()


# Base process class
class Process(Abstract):

    def get_next(self, abstract, message, context):
        raise NotImplementedError()

    def parse(self, message, context = None):

        abstract = context.get("start") if context else None

        while abstract:
             abstract, message = self.get_next(abstract, message, context)

        return Reply(message)


# Parser process
class ParserProcess(Process):
    def get_next(self, abstract, message, context):
        if not abstract:
            return None, message

        if not isinstance(abstract, Abstract):
            return None, message

        if hasattr(abstract, "name"):
            print "Current name %s" % abstract.name

        reply = abstract.parse(message, context)

        if reply.is_error(): # TODO: rollbacks etc
            if context:
                context["error"] = abstract
            return None, message # TODO: return error somehow

        if reply.result:
            if type(reply.result) is types.ListType: # TODO check modes or result
                length = -1
                bestReply = None

                for a in reply.result:
                    r = a.parse(message, context)

                    if r.result and r.length > length:
                        bestReply = r
                        length = r.length

                if bestReply:
                    reply = bestReply
                else:
                    return None, message

            abstract = reply.result

        if reply.length > 0:
            message = message[reply.length:]

        print "Next abstract %s, message %s" % (abstract, message)

        return abstract, message

