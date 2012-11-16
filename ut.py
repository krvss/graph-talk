# Universal Translator base classes
# (c) krvss 2011-2012

# Base class for all communicable objects
class Abstract(object):

    # The way to ask the abstract a message
    def parse(self, *message, **kwmessage):
        return None


# Notion is an abstract with name
class Notion(Abstract):
    def __init__(self, name):
        super(Notion, self).__init__()
        self.name = name

    def __str__(self):
        if self.name:
            return '"%s"' % self.name

    def __repr__(self):
        return self.__str__()


# Relation is a connection between one or more abstracts
class Relation(Abstract):
    def __init__(self, subject, object):
        super(Relation, self).__init__()
        self._object = self._subject = None

        self.subject = subject
        self.object = object

    def _connect(self, value, target):
        old_value = getattr(self, target)

        if old_value == value:
            return

        # Disconnect old one
        if isinstance(old_value, Abstract):
            old_value.parse('unrelated', **{'from': self, target: old_value})

        setattr(self, '_' + target, value)

        # Connect new one
        if isinstance(value, Abstract):
            value.parse('related', **{'from': self, target: value})

    @property
    def subject(self):
        return self._subject

    @subject.setter
    def subject(self, value):
        self._connect(value, 'subject')

    @property
    def object(self):
        return self._object

    @object.setter
    def object(self, value):
        self._connect(value, 'object')

    def __str__(self):
        return '<%s - %s>' % (self.subject, self.object)

    def __repr__(self):
        return self.__str__()


# Value notion is notion that returns custom value
class ValueNotion(Notion):
    def __init__(self, name, value):
        super(ValueNotion, self).__init__(name)
        self.value = value

    def parse(self, *message, **kwmessage):
        return self.value


# Function notion is notion that can watch custom function
class FunctionNotion(Notion):
    def __init__(self, name, function):
        super(FunctionNotion, self).__init__(name)
        self.function = function if callable(function) else None

    def parse(self, *message, **kwmessage):
        return self.function(self, *message, **kwmessage) if callable(self.function) else None


# Complex notion is a notion that relates with other notions (objects)
class ComplexNotion(Notion):
    def __init__(self, name, relation = None):
        super(ComplexNotion, self).__init__(name)
        self._relations = []

        self._relate(relation)

    def _relate(self, relation):
        if relation and (relation not in self._relations):
            self._relations.append(relation)

    def _unrelate(self, relation):
        if relation and (relation in self._relations):
            self._relations.remove(relation)

    def parse(self, *message, **kwmessage):
        reply = super(ComplexNotion, self).parse(*message, **kwmessage)

        if not reply:
            if message:
                # This abstract knows only Relate and Unrelate messages
                if message[0] == 'related':
                    if kwmessage.get('subject') == self:
                        self._relate(kwmessage.get('from'))
                        return True

                elif message[0] == 'unrelated':
                    if kwmessage.get('subject') == self:
                        self._unrelate(kwmessage.get('from'))
                        return True

             # Returning relations by default, not using a list if there is only one
            if self._relations:
                return self._relations[0] if len(self._relations) == 1 else list(self._relations)


# Next relation is just a simple sequence relation
class NextRelation(Relation):
    def parse(self, *message, **kwmessage):
        return self.object


# TODO: update for latest parse spec
# Selective notion: complex notion that can consist of one of its objects
class SelectiveNotion(ComplexNotion):
    def __init__(self, name, relation = None):
        super(SelectiveNotion, self).__init__(name, relation)

    def parse(self, message, context = None):
        if context:
            if self in context:
                if 'error' in context:
                    cases = context[self]

                    if cases:
                        case = cases.pop(0) # Try another case

                        # Pop and update context, then try another case and come back here
                        return ['restore', {'update': {self: cases}}, 'store', case, self]
                    else:
                        return ['clear', 'error'] # Nowhere to go, stop

                else:
                    return 'clear' # Everything is ok, clear the past

        reply = super(SelectiveNotion, self).parse(message, context)

        if not reply or (reply and not type(reply) is types.ListType):
            return reply

        elif context:
            case = reply.pop(0)
            context[self] = reply # Store the cases

            return ['store', case, self] # Try first one

        return reply


# Conditional relation is a condition to go further if message starts with sequence
class ConditionalRelation(Relation):
    def __init__(self, subject, object, checker):
        super(ConditionalRelation, self).__init__(subject, object)
        self.checker = checker

    def parse(self, *message, **kwmessage):
        if self.checker:
            result = None

            if callable(self.checker):
                result, length = self.checker(self, *message, **kwmessage)
            elif message:
                length = len(self.checker) if message[0].startswith(self.checker) else 0

                if length > 0:
                    result = self.checker

            if result:
                # TODO: think how to exchange information between objects
                # TODO: may be 'sendmessage' can be used to exchange information between processes
                #if context and self.object: # May be this is something for the object
                #    context[self.object] = result

                return [{'move': length}, self.object]

        return 'error'


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
                if 'error' in context:
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
            reply = ['store', self.object, self] # Self is a new next to think should we repeat or not
        else:
            if restore:
                reply = ['restore', 'clear'] # Clean up after restore needed to remove self from context
            else:
                reply = ['clear'] # No need to restore, just clear self

            if error:
                reply.append('error')

        return reply

# ENDTODO: update for latest parse spec


# Base process class, does parsing in step-by-step manner, moving from one abstract to another
class Process(Abstract):
    def __init__(self):
        super(Process, self).__init__()
        self._queue = []

        self._watcher = None

    def watch(self, watcher):
        if watcher and callable(watcher.parse):
            self._watcher = watcher
        else:
            self._watcher = None

    def _notify_watcher(self, info):
        if self.current == self._watcher or not self._watcher:
            return None

        reply = self._watcher.parse(info, **{'from': self, 'message': self.message, 'kwmessage' :self.kwmessage})

        if reply: # No need to store empty replies
            self._to_que(self.message, self.kwmessage, self._watcher, reply)

    def _to_que(self, message, kwmessage, current, reply, update=False):
        if not update:
            self._queue.append({'current' : current, 'message': message, 'kwmessage': kwmessage, 'reply': reply})
        else :
            self._queue[-1].update({'current' : current, 'message': message, 'kwmessage': kwmessage, 'reply': reply})

    def _que_top_get(self, field):
        return self._queue[-1].get(field) if self._queue else None

    # Single parse iteration
    def parse_step(self):
        if 'start' in self.kwmessage:
            self._to_que(self.message, self.kwmessage, self.kwmessage['start'], self.kwmessage['start'], True)
            del self.kwmessage['start']

            del self._queue[:-1] # Clear the rest of queue - we are starting from scratch

        elif 'stop' in self.message:
            self._queue.pop()
            return 'stopped'

        elif 'skip' in self.message:
            del self._queue[-2:]

        if not self.reply:
            if self._queue:
                self._queue.pop() # Let's move on
            else:
                return 'ok' # We're done if nothing in the queue
        else:
            if isinstance(self.reply, Abstract):
                self._to_que(self.message, self.kwmessage, self.reply,
                             self.reply.parse(*self.message, **self.kwmessage), True)

                self._notify_watcher('next')
            else:
                self._notify_watcher('next_unknown')

                return 'unknown'

    def parse(self, *message, **kwmessage):
        if message or kwmessage:
            self._to_que(list(message), kwmessage, None, None)

        while True:
            result = self.parse_step()

            if result:
                break

        return {'result': result}

    @property
    def message(self):
        return self._que_top_get('message') or []

    @property
    def kwmessage(self):
        return self._que_top_get('kwmessage') or {}

    @property
    def current(self):
        return self._que_top_get('current')

    @property
    def reply(self):
        return self._que_top_get('reply')


# Process with support of list processing
class ListProcess(Process):

    def parse_step(self):
        result = super(ListProcess, self).parse_step()

        if not result:
            return # Nothing to do here

        # Got sequence?
        if result == 'unknown' and isinstance(self.reply, list):
            c = self.reply.pop(0) # First one is ready to be processed
            self._to_que(self.message, self.kwmessage, c, c)

            self._notify_watcher('stack_push')
            return

        return result


# Process with support of stop, continue and error commands
class ControlledProcess(ListProcess):
    def __init__(self):
        super(ControlledProcess, self).__init__()

        self._errors = {}

    def parse_step(self,  message, kwmessage):
        result = super(ControlledProcess, self).parse_step(message, kwmessage)

        if not result:
            return

        # Command parsing
        if result == 'unknown':
            # Error reply
            if (isinstance(self._reply, dict) and 'error' in self._reply) or self._reply == 'error':
                self._errors[self._current or self] = self._reply['error'] if isinstance(self._reply, dict) else self._reply
                self._reply = 'continue' # Keep going

                self._notify_watcher('command_error', message, kwmessage)

            # Continue command
            if self._reply == 'continue' or 'continue' in message:
                kwmessage['start'] = None # Go pop

                if 'continue' in message:
                    message.remove('continue') # Clean up

                self._notify_watcher('command_continue', message, kwmessage)

                result = None # And keep going

            # Stop reply
            elif self._reply == 'stop':
                result = 'stopped'

                self._notify_watcher('command_stopped', message, kwmessage)

        return result

    def parse(self, *message, **kwmessage):
        if 'start' in kwmessage and self._errors:
            self._errors = {} # Clean errors on start

        result = super(ControlledProcess, self).parse(*message, **kwmessage)

        if self._errors:
            result.update({'result': 'error', 'errors': self._errors})

        return result


# Text parsing process
class TextParsingProcess(ControlledProcess):
    def __init__(self):
        super(TextParsingProcess, self).__init__()

        self._start_length = 0

    def parse_step(self,  message, kwmessage):
        result = super(TextParsingProcess, self).parse_step(message, kwmessage)

        if not result:
            return

        # Command parsing
        if result == 'unknown':
            if isinstance(self._reply, dict):
                # Skip the parsed part
                if 'move' in self._reply:
                    message[0] = message[0][self._reply['move']:]
                    self._reply = 'continue'

                    result = None

                    self._notify_watcher('command_move', message, kwmessage)

                # Replace parsing text
                if 'text' in self._reply:
                    if not message:
                        message.insert(0, self._reply['text'])
                    else:
                        message[0] = self._reply['text']

                    self._start_length = len(message[0])
                    self._reply = 'continue'

                    result = None

                    self._notify_watcher('command_text', message, kwmessage)

        return result

    def parse(self,  *message, **kwmessage):
        self._start_length = len(message[0]) # Init the length

        result = super(TextParsingProcess, self).parse(*message, **kwmessage)

        result['length'] = self._start_length - len(result['message'][0])

        return result

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
        return self._get_context_info(context, 'message', None)

    def _set_message(self, context, message):
        self._get_context_info(context, 'message', None)

        context[self]['message'] = message

    def _get_current(self, context):
        return self._get_context_info(context, 'current', None)

    def _set_current(self, context, abstract):
        self._get_context_info(context, 'current', None)

        context[self]['current'] = abstract

    def _get_text(self, context):
        return context['text'] if 'text' in context else '' # TODO: should be within process context, here because of ctx copy problems

    def _set_text(self, context, text):
        context['text'] = text


    def parse(self, message, context = None):
        if not context:
            context = {}
        #
        #    abstract = None
        #else:
        #    abstract = context.get('start') #TODO we can use message for start

        initial_length = len(message)
        message = {'start': context.get('start'), 'text': message}

        
        self._set_message(context, message)
        #self._set_current(context, abstract)

        while self.get_next(context): #TODO refactor
            pass

        text = self._get_text(context)
        return {'result': not 'error' in context, 'length': initial_length - len(text)}


# Parser process
class ParserProcess(oProcess):
    def __init__(self):
        super(ParserProcess, self).__init__()

    def _get_stack(self, context):
        return self._get_context_info(context, 'stack', [])

    def _get_states(self, context):
        return self._get_context_info(context, 'states', {})

    def _get_error(self, context):
        if not 'error' in context:
            error = []
            context['error'] = error
        else:
            error = context['error']

        return error

    def _progress_notify(self, info, abstract, parsing_message = None, parsing_context = None):
        self._notify(info, {'abstract': abstract,
                            'message': parsing_message or '',
                            'text': self._get_text(parsing_context) if parsing_context else '',
                            'context': parsing_context or ''}) # TODO remove, add from instead, use message/abs from ctx

    def _rollback(self, context):
        abstract = None
        reply = None

        if self._can_rollback(context):
            abstract, reply = self._get_stack(context).pop(0)

            self._progress_notify('rolled_back', abstract)

        return abstract, reply

    def _can_rollback(self, context):
        return len(self._get_stack(context)) > 0

    def _add_to_stack(self, context, abstract, reply):
        stack = self._get_stack(context)
        stack.insert(0, (abstract, reply))

        self._progress_notify('added_to_stack', abstract)

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
                if name == 'start':
                    self._set_current(context, arg)
                    
                elif name == 'stop':
                    return False # Stop at once
                
                elif name == 'text':
                    text = arg
                    self._set_text(context, arg)

                elif name == 'move':

                    text = text[arg:]
                    self._set_text(context, text)

                elif name == 'error':
                    error = arg or abstract or self
                    self._get_error(context).append(error)

                    self._progress_notify('error_at', error)

                if abstract:
                # Commands processing with abstract
                    if name == 'restore':
                        old_context = self._get_states(context)[abstract]

                        context.clear() # Keeping context object intact
                        context.update(old_context)

                        if abstract in self._get_states(context):
                            del self._get_states(context)[abstract]

                        self._progress_notify('restored_for', abstract, text)

                    elif name == 'update':
                        context.update(arg)

                        self._progress_notify('updated_for', abstract, text)

                    elif name == 'store':
                        self._get_states(context)[abstract] = dict(context)

                        self._progress_notify('storing', abstract, text)

                    elif name == 'clear':
                        if abstract in self._get_states(context): # TODO: copy of restore part, combine or remove
                            del self._get_states(context)[abstract]

                        if arg != 'state':
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
            self._progress_notify('abstract_current', abstract, text, context)

            message = abstract.parse(text, context)

            self._set_message(context, message)

            if message:
                return True

        # If we are here we have no next from message and no new data, let's roll back
        self._progress_notify('rollback', abstract)

        if self._can_rollback(context):
            abstract, reply = self._rollback(context)
            self._set_message(context, reply)
            self._set_current(context, abstract)

            return True
        else:
            return False # Stopping

