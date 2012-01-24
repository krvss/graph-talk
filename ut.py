# Universal Translator base classes
# (c) krvss 2011-2012

# Base class for all communicable objects
class Abstract(object):
    def __init__(self):
        self.callbacks = []

    def parse(self, message):
        return None

    def call(self, callback, forget = False):
        if forget and callback in self.callbacks:
            self.callbacks.remove(callback)
        else:
            if callable(callback):
                self.callbacks.append(callback)

    def _notify(self, message):
        for callee in self.callbacks:
            callee(message)


# Class for simple replies
class Reply(object):
    def __init__(self, result = False, length = 0, context = None):
        self.result = result
        self.length = length
        self.context = context

    def is_error(self):
        return self.result == False


# Notion is an abstract with name
class Notion(Abstract):
    def __init__(self, name):
        super(Abstract, self).__init__()
        self.name = unicode(name)

    def parse(self, message):
        if message.lower().startswith("name"):
            return Reply(self.name, len("name"))

        return Reply()


# Relation is a connection between 1 or more abstracts
class Relation(Abstract):
    def __init__(self, subject, object):
        super(Relation, self).__init__()
        self.subject = subject
        self.object = object

    def get_type(self):
        raise NotImplementedError()


# Complex notion is a notion that relates to other notions
class ComplexNotion(Notion):
    def __init__(self, name, relation = None):
        super(ComplexNotion, self).__init__(name)
        self.relation = relation

    @property
    def relation(self):
        return self._relation

    @relation.setter
    def relation(self, value):
        self._relation = value

        if value:
            value.subject = self

    def parse(self, message):
        reply = self.parse(message)

        if reply.is_error():
            return self.relation.parse(message)


# Complex relation is a relation that consists of many other relations and selects best when parsing
COMPLEX_RELATION = 0

class ComplexRelation(Relation):
    def __init__(self, subject):
        super(ComplexRelation, self).__init__(subject, [])
        self._relations = []

    def get_type(self):
        return COMPLEX_RELATION

    def addRelation(self, relation):
        if not relation in self._relations:
            self._relations.append(relation)

            relation.subject = self.subject
            self.object.append(relation.object)

    def removeRelation(self, relation):
        if relation in self._relations:
            self._relations.remove(relation)
            self.object.remove(relation.object)

    def parse(self, message):
        length = -1
        bestReply = None

        for relation in self._relations:
            reply = relation.parse(message)

            if reply.result and reply.length > length:
                bestReply = reply

        return bestReply or Reply()


# Next relation is just a simple sequence relation
NEXT_RELATION = 1

class NextRelation(Relation):
    def __init__(self, subject, object):
        super(NextRelation, self).__init__(subject, object)

    def get_type(self):
        return NEXT_RELATION

    def parse(self, message):
        return Reply(result=self.subject)


# Conditional relation is a condition to go further if message starts with sequence
CONDITIONAL_RELATION = 2

class ConditionalRelation(Relation):
    def __init__(self, subject, object, checker):
        super(ConditionalRelation, self).__init__(subject, object)
        self.checker = checker

    def get_type(self):
        return CONDITIONAL_RELATION

    def parse(self, message):
        if callable(self.checker):
            result, length = self.checker(message)

            if result:
                return Reply(result=self.subject, length = length)

        return Reply()


# Case of conditional: presence of char sequence
class CharConditionalRelation(ConditionalRelation):
    def __init__(self, subject, object, checker):
        super(CharConditionalRelation, self).__init__(subject, object, checker)

    def parse(self, message):
        length = len(self.checker) if message.lower().startswith(self.checker) else 0

        if length > 0:
            return Reply(result=self.subject, length = length)

        return Reply()