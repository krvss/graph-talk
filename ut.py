# Universal Translator base classes
# (c) krvss 2011-2012

# Base class for all communicable objects
class Abstract(object):

    # The way to send the abstract a message
    def parse(self, *message, **context):
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


# Relation is a connection between one or more abstracts: subject -> object
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
            old_value.parse('unrelate', **{'from': self, target: old_value})

        setattr(self, '_' + target, value)

        # Connect new one
        if isinstance(value, Abstract):
            value.parse('relate', **{'from': self, target: value})

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

    def parse(self, *message, **context):
        return self.value


# Function notion is notion that can callback custom function
class FunctionNotion(Notion):
    def __init__(self, name, function):
        super(FunctionNotion, self).__init__(name)
        self.function = function if callable(function) else None

    def parse(self, *message, **context):
        return self.function(self, *message, **context) if callable(self.function) else None


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

    def parse(self, *message, **context):
        reply = super(ComplexNotion, self).parse(*message, **context)

        if not reply:
            if message:
                # This abstract knows only Relate and Unrelate messages
                if message[0] == 'relate':
                    if context.get('subject') == self:
                        self._relate(context.get('from'))
                        return True

                elif message[0] == 'unrelate':
                    if context.get('subject') == self:
                        self._unrelate(context.get('from'))
                        return True

             # Returning copy of relation list by default, not using a list if there is only one
            if self._relations:
                return self._relations[0] if len(self._relations) == 1 else list(self._relations)


# Next relation is just a simple sequence relation
class NextRelation(Relation):
    def parse(self, *message, **context):
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


# Conditional relation is a condition to go further if text starts with sequence
class ConditionalRelation(Relation):
    def __init__(self, subject, object, checker):
        super(ConditionalRelation, self).__init__(subject, object)
        self.checker = checker

    def parse(self, *message, **context):
        if self.checker:
            length = result = None

            if callable(self.checker):
                result, length = self.checker(self, *message, **context)
            elif 'text' in context:
                length = len(self.checker) if context['text'].startswith(self.checker) else 0

                if length > 0:
                    result = self.checker

            if result:
                reply = {'move': length}
                if self.object:
                    reply['add_context'] = {'condition': result}

                return [reply, self.object]

        return 'error'


# TODO: update for latest parse spec
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

# Base process class, does parsing in step-by-step manner, moving from one abstract to another
class Process(Abstract):
    def __init__(self):
        super(Process, self).__init__()

        self._queue = []
        self._callback = None

    def callback(self, abstract):
        if abstract and callable(abstract.parse):
            self._callback = abstract
        else:
            self._callback = None

    def event_call(self, info):
        if self.current != self._callback and self._callback: # We do not need infinite asking loops
            reply = self._callback.parse(info, **{'from': self, 'message': self.message, 'context' :self.context})

            if reply: # No need to store empty replies
                self._to_que(False, current = self._callback, reply = reply)

                return True

        return False

    def _to_que(self, update, **dict):
        top = {'message': self.message, 'context': self.context,
               'current' : self.current, 'reply': self.reply}
        top.update(dict)

        if not update:
            self._queue.append(top)
        else:
            self._queue[-1].update(top)

    def _que_top_get(self, field):
        return self._queue[-1].get(field) if self._queue else None

    def _pull_command(self, command):
        data = None

        if isinstance(self.reply, dict) and command in self.reply:
            data = self.reply[command]
            del self.reply[command]

        elif command == self.reply:
            self._to_que(True, reply = None)
            data = command

        elif command in self.message:
            self.message.remove(command)
            data = command

        return data

    # Single parse iteration
    def parse_step(self):
        if self._pull_command('new'):
            if not self.event_call('new'):
                del self._queue[:-1] # Removing previous elements from queue

        # Start from message if no replies left
        if not self.reply and self.message and isinstance(self.message[0], Abstract):
            self._to_que(True, current = self.message[0], reply = self.message[0])
            del self.message[0]

        elif self._pull_command('stop'):
            if not self.event_call('stop'):
                return 'stopped'    # Just stop at once where we are if callback does not care

        elif self._pull_command('skip'):
            if not self.event_call('skip'):
                del self._queue[-2:] # Removing current and previous elements from queue

        # Done with message, now work with replies
        if not self.reply:
            if self._queue and len(self._queue) > 1:
                self._queue.pop() # Let's move on

                self.event_call('que_pop')
            else:
                return 'ok' # We're done if nothing in the queue
        else:
            if isinstance(self.reply, Abstract):
                self._to_que(True, current = self.reply,
                                   reply = self.reply.parse(*self.message, **self.context))

                self.event_call('next')

            elif isinstance(self.reply, list):
                first = self.reply.pop(0) # First one is ready to be processed
                self._to_que(False, reply = first)

                self.event_call('que_push')

            else:
                if not self.event_call('next_unknown'): # If there where a response on unknown we have to check it
                    return 'unknown'

    def parse(self, *message, **context):
        if message or context:
            update = len(self._queue) == 1 and not self.message and not self.reply
            self._to_que(update, message = list(message), context = context,
                                current = None, reply = None)

        while True:
            result = self.parse_step()

            if result:
                break

        return {'result': result}

    @property
    def message(self):
        m = self._que_top_get('message')
        return m if None != m else []

    @property
    def context(self):
        ctx = self._que_top_get('context')
        return ctx if None != ctx else {}

    @property
    def current(self):
        return self._que_top_get('current')

    @property
    def reply(self):
        return self._que_top_get('reply')


class ContextProcess(Process):

    def parse_step(self):
        result = super(ContextProcess, self).parse_step()

        if not result:
            return

        # TODO: invalid command arguments test
        if result == 'unknown':
            # Adding
            command = self._pull_command('add_context')
            if command and isinstance(command, dict):
                for k, w in command.items():
                    if not k in self.context:
                        self.context[k] = w

                self.event_call('added_context')
                return None

            # Updating
            command = self._pull_command('update_context')
            if command and isinstance(command, dict):
                self.context.update(command)

                self.event_call('updated_context')
                return None

            # Deleting
            command = self._pull_command('delete_context')
            if command:
                if isinstance(command, list):
                    for k in command:
                        if k in self.context:
                            del self.context[k]
                elif command in self.context:
                    del self.context[command]

                self.event_call('updated_context')
                return None

        return result


# Text parsing process supports error and move commands for text processing
class TextParsingProcess(ContextProcess):
    def __init__(self):
        super(TextParsingProcess, self).__init__()
        self._parsed_length = 0 # Init the length

    def parse_step(self):
        result = super(TextParsingProcess, self).parse_step()

        if not result:
            return

        if result == 'unknown':
            # Add errors to context
            error = self._pull_command('error')
            if error:
                self.errors[self.current or self] = error

                self.event_call('command_error')
                return None

            # Skip the parsed part of text in context
            move = self._pull_command('move')
            if move and 'text' in self.context:
                self.context['text'] = self.context['text'][move:]
                self._parsed_length += move

                self.event_call('command_move')
                return None

        return result

    def parse(self,  *message, **context):
        if 'new' in message:
            if self.errors:
                self.errors.clear() # Clean errors on start
            self._parsed_length = 0

        result = super(TextParsingProcess, self).parse(*message, **context)

        result['length'] = self._parsed_length

        if self.errors:
            result['result'] = 'error'

        return result

    @property
    def errors(self):
        if not 'errors' in self.context:
            self.context['errors'] = {}
        return self.context['errors']


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

