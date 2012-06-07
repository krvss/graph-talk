# Universal Translator base classes
# (c) krvss 2011-2012

import types

# Base class for all communicable objects
class Abstract(object):
    def __init__(self):
        self._callbacks = []

    def parse(self, message, **context):
        return None

    def call(self, callback, forget = False):
        if forget and callback in self._callbacks:
            self._callbacks.remove(callback)
        else:
            if callback and callable(callback.parse):
                self._callbacks.append(callback)

    def _notify(self, message, **context):
        for callee in self._callbacks:
            if callable(callee.parse):
                callee.parse(message, **context)


# Notion is an abstract with name
class Notion(Abstract):
    def __init__(self, name):
        super(Abstract, self).__init__()
        self.name = name

    def parse(self, message, **context):
        return None

    def __str__(self):
        if self.name:
            return "'%s'" % self.name


# Relation is a connection between one or more abstracts
class Relation(Abstract):
    def __init__(self, subject, object):
        super(Relation, self).__init__()
        self._subject = None
        self._object = None

        self.subject = subject
        self.object = object

    def _connect(self, value, target):
        old_value = getattr(self, target)

        if old_value == value:
            return

        if old_value:
            self._notify("unrelating", **{"from": self, target: value})
            self.call(value, True)

        setattr(self, "_" + target, value)

        if value:
            self.call(value)
            self._notify("relating", **{"from": self, target: value})

    @property
    def subject(self):
        return self._subject

    @subject.setter
    def subject(self, value):
        self._connect(value, "subject")

    @property
    def object(self):
        return self._object

    @object.setter
    def object(self, value):
        self._connect(value, "object")

    def __str__(self):
        return "<%s - %s>" % (self.subject, self.object)


# Function notion is notion that can call custom function
class FunctionNotion(Notion):
    def __init__(self, name, function):
        super(FunctionNotion, self).__init__(name)
        self.function = function if callable(function) else None

    def parse(self, message, **context):
        return self.function(self, message, **context) if self.function else None


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

    def parse(self, message, **context):
        reply = super(ComplexNotion, self).parse(message, **context)

        if not reply:
            if message == "relating":
                if context.get("subject") == self:
                    self._relate(context.get("from"))

            elif message == "unrelating":
                if context.get("subject") == self:
                    self._unrelate(context.get("from"))

            else: # Returning relations by default
                if self._relations:
                    return self._relations[0] if len(self._relations) == 1 else list(self._relations)


# Next relation is just a simple sequence relation
class NextRelation(Relation):
    def __init__(self, subject, object):
        super(NextRelation, self).__init__(subject, object)

    def parse(self, message, **context):
        return self.object


# Selective notion: complex notion that can consist of one of its objects
class SelectiveNotion(ComplexNotion):
    def __init__(self, name, relation = None):
        super(SelectiveNotion, self).__init__(name, relation)

    def parse(self, message, context = None):
        if context:
            if self in context:
                if "error" in context:
                    cases = context[self]

                    if cases:
                        case = cases.pop(0) # Try another case

                        # Pop and update context, then try another case and come back here
                        return ["restore", {"update": {self: cases}}, "store", case, self]
                    else:
                        return ["clear", "error"] # Nowhere to go, stop

                else:
                    return "clear" # Everything is ok, clear the past

        reply = super(SelectiveNotion, self).parse(message, context)

        if not reply or (reply and not type(reply) is types.ListType):
            return reply

        elif context:
            case = reply.pop(0)
            context[self] = reply # Store the cases

            return ["store", case, self] # Try first one

        return reply


# Conditional relation is a condition to go further if message starts with sequence
class ConditionalRelation(Relation):
    def __init__(self, subject, object, checker):
        super(ConditionalRelation, self).__init__(subject, object)
        self.checker = checker

    def parse(self, message, context = None):
        if self.checker:
            result = None

            if callable(self.checker):
                result, length = self.checker(message, context)
            else:
                length = len(self.checker) if message.startswith(self.checker) else 0

                if length > 0:
                    result = self.checker

            if result:
                if context and self.object: # May be this is something for the object
                    context[self.object] = result

                return [{"move": length}, self.object]

        return "error"


# Loop relation is a cycle that repeats object for specified or infinite number of times
class LoopRelation(Relation):
    def __init__(self, subject, object, n = None):
        super(LoopRelation, self).__init__(subject, object)
        self.n = n

    def parse(self, message, context = None):
        repeat = True
        error = restore = False

        if self.n and callable(self.n):
            repeat = self.n(self, context)

        elif context:
            if self in context:
                if "error" in context:
                    repeat = False

                    if not self.n:
                        restore = True # Number of iterations is arbitrary if no restriction, we need to restore last good context
                    else:
                        error = True # Number is fixed so we have an error
                else:
                    if self.n:
                        i = context[self]

                        if i < self.n:
                            context[self] = i + 1
                        else:
                            repeat = False # No more iterations

            else:
                context[self] = 1 if self.n else True # Initializing the loop

        if repeat:
            reply = ["store", self.object, self] # Self is a new next to think should we repeat or not
        else:
            if restore:
                reply = ["restore", "clear"] # Clean up after restore needed to remove self from context
            else:
                reply = ["clear"] # No need to restore, just clear self

            if error:
                reply.append("error")

        return reply


# Base process class
class Process(Abstract):
    def notify_progress(self, info, current, message = None, reply = None):
        self._notify(message = info, context = {"current": current, "message": message, "reply": reply})

    def parse(self, message, **context):
        current = context.get("start")
        reply = context.get("reply") or current or message # TODO: think how to store the state

        while reply:
            if isinstance(reply, Abstract):
                current = reply
                reply = current.parse(message, **context)

                self.notify_progress("next", current, message, reply)
            else:
                self.notify_progress("next_stop", current, message, reply)
                break # Do not know what to do

        return {"reply": reply, "from": current}


# Process with support of list processing with stack
class StackedProcess(Process):
    def __init__(self):
        super(StackedProcess, self).__init__()

        self._stack = []

    def parse(self, message, **context):
        while True:
            r = super(StackedProcess, self).parse(message, **context)

            # If we are here - we stopped at unknown message
            reply = r["reply"]
            current = r["from"]

            # Got sequence?
            if type(reply) is types.ListType:
                self.notify_progress("stack_list", current, message, reply)

                if len(reply) >= 1:
                    c = reply.pop(0) # First one is ready to be processed

                    if reply: # No need to push empty list
                        self.notify_progress("stack_push", current, message, reply)

                        self._stack.append((current, reply))

                    context.update({"start": c}) # New current

                    continue
                else:
                    reply = None # New reply needed

            # If nothing to work with let's try to pop from stack
            if not reply:
                if self._stack:
                    self.notify_progress("stack_pop", current, message)

                    current, reply = self._stack.pop()
                    context.update({"start": current, "reply": reply})

                    self.notify_progress("stack_popped", current, message, reply)
                else:
                    self.notify_progress("stack_empty", current, message)

                    break
            else:
                self.notify_progress("stack_stop", current, message, reply)
                break # Do not know what to do

        return {"reply": reply, "from": current}


# Abstract state; together states represent a tree-like structure
class State(object):
    def __init__(self, abstract, data, previous):
        self.abstract = abstract
        self.data = data
        self.previous = previous
        self.next = []

    def clear_next(self):
        del self.next[:]


# Base process class
class oProcess(Abstract):

    def get_next(self, context):
        raise NotImplementedError()

    def _get_context_info(self, context, name, default):
        if not self in context:
            context[self] = {}

        if not name in context[self]:
            context[self][name] = default
            return default
        else:
            return context[self][name]

    def _get_message(self, context):
        return self._get_context_info(context, "message", None)

    def _set_message(self, context, message):
        self._get_context_info(context, "message", None)

        context[self]["message"] = message

    def _get_current(self, context):
        return self._get_context_info(context, "current", None)

    def _set_current(self, context, abstract):
        self._get_context_info(context, "current", None)

        context[self]["current"] = abstract

    def _get_text(self, context):
        return context["text"] if "text" in context else "" # TODO: should be within process context, here because of ctx copy problems

    def _set_text(self, context, text):
        context["text"] = text


    def parse(self, message, context = None):
        if not context:
            context = {}
        #
        #    abstract = None
        #else:
        #    abstract = context.get("start") #TODO we can use message for start

        initial_length = len(message)
        message = {"start": context.get("start"), "text": message}

        
        self._set_message(context, message)
        #self._set_current(context, abstract)

        while self.get_next(context): #TODO refactor
            pass

        text = self._get_text(context)
        return {"result": not "error" in context, "length": initial_length - len(text)}


# Parser process
class ParserProcess(oProcess):
    def __init__(self):
        super(ParserProcess, self).__init__()

    def _get_stack(self, context):
        return self._get_context_info(context, "stack", [])

    def _get_states(self, context):
        return self._get_context_info(context, "states", {})

    def _get_error(self, context):
        if not "error" in context:
            error = []
            context["error"] = error
        else:
            error = context["error"]

        return error

    def _progress_notify(self, info, abstract, parsing_message = None, parsing_context = None):
        self._notify(info, {"abstract": abstract,
                            "message": parsing_message or "",
                            "text": self._get_text(parsing_context) if parsing_context else "",
                            "context": parsing_context or ""}) # TODO remove, add from instead, use message/abs from ctx

    def _rollback(self, context):
        abstract = None
        reply = None

        if self._can_rollback(context):
            abstract, reply = self._get_stack(context).pop(0)

            self._progress_notify("rolled_back", abstract)

        return abstract, reply

    def _can_rollback(self, context):
        return len(self._get_stack(context)) > 0

    def _add_to_stack(self, context, abstract, reply):
        stack = self._get_stack(context)
        stack.insert(0, (abstract, reply))

        self._progress_notify("added_to_stack", abstract)

    def get_next(self, context):

        message = self._get_message(context)
        text = self._get_text(context)
        abstract = self._get_current(context)

        # Got sequence?
        if type(message) is types.ListType:
            if len(message) >= 1:
                m = message.pop(0) # First one is ready to be processed

                if message: # No need to push empty list
                    self._add_to_stack(context, abstract, message)

                message = m
            else:
                self._set_current(context, None)
                self._set_message(context, None)

                return True # Let's try to roll back

        # Got command?
        if isinstance(message, str):
            message = {message: None}

        # Commands where abstract is not needed
        if isinstance(message, dict):
            for name, arg in message.iteritems():
                if name == "start":
                    self._set_current(context, arg)
                    
                elif name == "stop":
                    return False # Stop at once
                
                elif name == "text":
                    text = arg
                    self._set_text(context, arg)

                elif name == "move":

                    text = text[arg:]
                    self._set_text(context, text)

                elif name == "error":
                    error = arg or abstract or self
                    self._get_error(context).append(error)

                    self._progress_notify("error_at", error)

                if abstract:
                # Commands processing with abstract
                    if name == "restore":
                        old_context = self._get_states(context)[abstract]

                        context.clear() # Keeping context object intact
                        context.update(old_context)

                        if abstract in self._get_states(context):
                            del self._get_states(context)[abstract]

                        self._progress_notify("restored_for", abstract, text)

                    elif name == "update":
                        context.update(arg)

                        self._progress_notify("updated_for", abstract, text)

                    elif name == "store":
                        self._get_states(context)[abstract] = dict(context)

                        self._progress_notify("storing", abstract, text)

                    elif name == "clear":
                        if abstract in self._get_states(context): # TODO: copy of restore part, combine or remove
                            del self._get_states(context)[abstract]

                        if arg != "state":
                            if abstract in context:
                                del context[abstract]

            # Message processing finished
            self._set_message(context, None)
            if abstract == self._get_current(context): # Abstract was not changed => rollback
                self._set_current(context, None)
            return True

        # We have a new next maybe?
        if isinstance(message, Abstract):
            self._set_current(context, message)
            self._set_message(context, None)

            return True

        # Asking!
        if not message and abstract:
            self._progress_notify("abstract_current", abstract, text, context)

            message = abstract.parse(text, context)

            self._set_message(context, message)

            if message:
                return True

        # If we are here we have no next from message and no new data, let's roll back
        self._progress_notify("rollback", abstract)

        if self._can_rollback(context):
            abstract, reply = self._rollback(context)
            self._set_message(context, reply)
            self._set_current(context, abstract)

            return True
        else:
            return False # Stopping


