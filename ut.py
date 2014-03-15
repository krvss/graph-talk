# Universal Translator base classes
# (c) krvss 2011-2014

from inspect import getargspec

from utils import *


# Base abstract class for all communicable objects
class Abstract(object):

    # Parse the message
    def parse(self, *message, **context):
        raise NotImplementedError('Method not implemented')

    # Make the answer
    def answer(self, *message, **context):
        return self.parse(*message, **context)

    # A singular way to call
    def __call__(self, *args, **kwargs):
        return self.answer(*args, **kwargs)


# Access caches type information to increase the execution speed
class Access(object):
    CALL = 'call'
    ABSTRACT = 'abstract'
    FUNCTION = 'function'
    VALUE = 'value'
    NUMBER = 'number'
    LIST = 'list'
    STRING = 'string'
    REGEX = 'regex'
    OTHER = 'other'

    def __init__(self, value, ignore_case=False):
        self._value = value
        self._mode, self._spec = self.OTHER, self.OTHER
        self._ignore_case = ignore_case

        self.setup()

    # Init the type information
    def setup(self):
        if isinstance(self._value, Abstract):
            self._mode, self._spec = self.CALL, self.ABSTRACT

        elif callable(self._value):
            self._mode, self._spec = self.FUNCTION, getargspec(self._value)

        else:
            self._mode = self.VALUE

            if is_number(self._value):
                self._spec = self.NUMBER

            elif is_list(self._value):
                self._spec = self.LIST

            elif is_string(self._value):
                self._spec = self.STRING

                if self._ignore_case:
                    self._value = self._value.upper()

            elif is_regex(self._value):
                self._spec = self.REGEX

    # Do the access with message and context
    def access(self, message, context):
        if self._spec == self.ABSTRACT:
            return self._value(*message, **context)

        elif self._mode == self.FUNCTION:
            if self._spec.varargs and not self._spec.keywords:
                return self.value(*message)

            elif self._spec.keywords and not self._spec.varargs:
                return self.value(**context)

            elif self._spec.varargs and self._spec.keywords:
                return self.value(*message, **context)

            elif not self._spec.varargs and not self._spec.keywords and not self._spec.args:
                return self.value()

            elif self._spec.args:
                i, args = len(self._spec.defaults) - 1 if self._spec.defaults else -1, {}
                for arg in reversed(self._spec.args):
                    if arg != 'self':
                        args[arg] = context[arg] if arg in context else self._spec.defaults[i] if i >= 0 else None
                        i -= 1

                return self._value(**args)

        return self._value

    @property
    def mode(self):
        return self._mode

    @property
    def spec(self):
        return self._spec

    @property
    def value(self):
        return self._value


# Condition is a kind of Access that checks the possibility of the access according to message and context
class Condition(Access):
    def __init__(self, value, ignore_case=False):
        super(Condition, self).__init__(value, ignore_case)

        if self.spec == self.LIST:
            self._condition_list = tuple([Access(c, ignore_case) for c in value])
        else:
            self._condition_list = self,

    def check(self, message, context):
        rank, check = -1, None

        for condition in self._condition_list:
            if condition.mode == self.FUNCTION:
                check = self.access(message, context)

                # Do we work with (rank, check) format?
                if get_len(check) == 2:
                    rank, check = check
                elif check:
                    rank = 0 if check is True else check

            elif condition.spec == self.REGEX:
                check = condition.value.match(message[0]) if message else None

                if check:
                    rank = check.end() - check.start()  # Match length is the rank

            elif condition.spec == self.STRING and message:
                message0 = str(message[0])

                if self._ignore_case:
                    message0 = message0.upper()

                if message0.startswith(condition.value):
                    rank, check = len(condition.value), condition.value

            elif has_first(message, condition.value):
                rank, check = max(get_len(condition.value), 0), condition.value

        if rank < 0:
            check = None  # Little cleanup

        return rank, check

    @property
    def list(self):
        return self._condition_list


# Handler dialect
ANSWER = 'answer'
SENDER = 'sender'
CONDITION = 'condition'
HANDLER = 'handler'
RANK = 'rank'

NO_PARSE = (False, -1, None)


# Handler is a class for the routing of messages to processing functions (handlers) basing on specified conditions
class Handler(Abstract):
    def __init__(self):
        self.handlers = []
        self.ignore_case = False

    # Adding the condition - handler pair
    def on(self, condition, handler):
        if (condition, handler) not in self.handlers:
            self.handlers.append((condition, handler))

    # Adding the handler, without condition it will trigger on any message
    def on_any(self, handler):
        if handler not in self.handlers:
            self.handlers.append(handler)

    # Removing the condition - handler pair
    def off(self, condition, handler):
        if (condition, handler) in self.handlers:
            self.handlers.remove((condition, handler))

    # Removing the handler
    def off_any(self, handler):
        if handler in self.handlers:
            self.handlers.remove(handler)

    # Removing all the handlers for the condition
    def off_condition(self, condition):
        self.handlers = filter(lambda h: not (is_list(h) and h[0] == condition), self.handlers)

    # Remove all occurrences of the handler
    def off_handler(self, handler):
        self.handlers = filter(lambda h: not ((is_list(h) and h[1] == handler) or h == handler), self.handlers)

    # Getting the handlers for the specified condition
    def get_handlers(self, condition=None):
        if condition:
            return [h[1] for h in self.handlers if has_first(h, condition)]
        else:
            return [h for h in self.handlers if not is_list(h)]

    # Smart call with a message and a context: feeds only the number of arguments the function is ready to accept
    def var_call_result(self, func, message, context):
        if isinstance(func, Abstract):
            return func(*message, **context)

        spec = get_args(func)

        if spec.varargs and not spec.keywords:
            return func(*message)

        elif spec.keywords and not spec.varargs:
            return func(**context)

        elif spec.varargs and spec.keywords:
            return func(*message, **context)

        elif not spec.varargs and not spec.keywords and not spec.args:
            return func()

        elif spec.args:
            i, args = len(spec.defaults) - 1 if spec.defaults else -1, {}
            for arg in reversed(spec.args):
                if arg != 'self':
                    args[arg] = context[arg] if arg in context else spec.defaults[i] if i >= 0 else None
                    i -= 1

            return func(**args)

    # Checking the condition to satisfy the message and context
    def can_handle(self, condition, message, context):
        rank, check = -1, None
        conditions = condition if is_list(condition) else [condition]

        for condition in conditions:
            if callable(condition):
                check = self.var_call_result(condition, message, context)

                # Do we work with (rank, check) format?
                if is_list(check) and len(check) == 2 and is_number(check[0]):
                    rank, check = check
                elif check:
                    rank = check if is_number(check) else 0  # If check result is numeric - this is a rank

            elif is_regex(condition):
                check = condition.match(message[0]) if message else None

                if check:
                    rank = check.end() - check.start()  # Match length is the rank

            elif is_string(condition) and message:
                message0 = str(message[0])

                if self.ignore_case:
                    message0 = message0.upper()
                    condition = condition.upper()

                if message0.startswith(condition):
                    rank, check = len(condition), condition

            elif has_first(message, condition):
                rank, check = max(get_len(condition), 0), condition

        if rank < 0:
            check = None  # Little cleanup

        return rank, check

    # Running the specified handler, returns result as result, rank, handler
    def run_handler(self, handler, message, context):
        result = self.var_call_result(handler, message, context) if callable(handler) else handler

        return result, handler

    # Calling handlers basing on condition, using ** to protect the context content
    def handle(self, *message, **context):
        check, rank, handler_found = NO_PARSE

        if not SENDER in context:
            context[SENDER] = self

        # Searching for the best handler
        for handler in self.handlers:
            handler_func = handler if not is_list(handler) else handler[1]

            # Avoiding recursive calls
            if context.get(HANDLER) == handler_func:
                continue

            # Condition check, if no condition the result is true with zero rank
            condition = self.can_handle(handler[0], message, context) if is_list(handler) else (0, True)

            if condition[0] <= rank:
                continue
            else:
                rank, check, handler_found = condition[0], condition[1], handler_func

        # Running the best handler
        if rank >= 0:
            if not HANDLER in context:
                context[HANDLER] = handler_found

            context.update({RANK: rank, CONDITION: check})

            # Call handler, add the condition result to the context
            result, handler_found = self.run_handler(handler_found, message, context)
        else:
            result = False

        return result, rank, handler_found

    # Parse means search for a handler
    def parse(self, *message, **context):
        return self.handle(*message, **context)

    # Answer depends on the context
    def answer(self, *message, **context):
        answer_mode = context.pop(ANSWER, None)  # Applicable only for a top level
        result = super(Handler, self).answer(*message, **context)

        if answer_mode == RANK:
            return result[0], result[1]

        return result[0]  # No need to know the details


# Talker dialect
PRE_PREFIX = 'pre'
POST_PREFIX = 'post'
RESULT = 'result'
UNKNOWN = 'unknown'

SEP = '_'
SILENT = (RESULT, UNKNOWN)


# Handler which uses pre and post handling notifications
class Talker(Handler):

    # Add prefix to the message
    @staticmethod
    def add_prefix(message, prefix):
        event_name = str(message[0] if is_list(message) else message)

        if not event_name.startswith(prefix):
            event_name = SEP.join([prefix, event_name])

        return tupled(event_name, message[1:]) if is_list(message) else event_name

    # Remove prefix from the message
    @staticmethod
    def remove_prefix(message, prefix=None):
        event_name = str(message[0] if message and is_list(message) else message)

        if not SEP in event_name or (prefix and not event_name.startswith(prefix + SEP)):
            return None

        return event_name.split(SEP, 1)[-1]

    # Should event go silent or not, useful to avoid recursions
    def is_silent(self, event_name):
        if not is_string(event_name):
            event_name = str(event_name)

        return event_name.startswith(PRE_PREFIX) or event_name.startswith(POST_PREFIX) \
            or event_name in SILENT

    # Runs the handler with pre and post notifications
    def run_handler(self, handler, message, context):
        event = message if (message and is_string(message[0])) else (get_object_name(handler), )
        silent = self.is_silent(event[0])

        if not silent:
            context[HANDLER] = handler

            # Pre-processing, adding prefix to event or handler name
            pre_result = self.handle(*self.add_prefix(event, PRE_PREFIX), **context)

            if pre_result[0]:
                return pre_result[0], pre_result[2]

        result = super(Talker, self).run_handler(handler, message, context)

        if not silent:
            context.update({RESULT: result[0], RANK: result[1]})

            # Post-processing, adding postfix and results
            post_result = self.handle(*self.add_prefix(event, POST_PREFIX), **context)

            if post_result[0]:
                return post_result[0], post_result[2]

        return result

    # Parse means search for a handler
    def parse(self, *message, **context):
        result = super(Talker, self).parse(*message, **context)

        # There is a way to override result and handle unknown message
        if result[0] is not False:
            context.update({RESULT: result[0], RANK: result[1], HANDLER: result[2]})
            after_result = super(Talker, self).parse(RESULT, *message, **context)

            if after_result[0]:
                result = after_result  # override has priority
        else:
            result = super(Talker, self).parse(UNKNOWN, *message, **context)

        return result


# Element dialect
NEXT = 'next'
PREVIOUS = 'previous'
OWNER = 'owner'

SET_PREFIX = 'set'
NAME = 'name'
OLD_VALUE = 'old-value'
NEW_VALUE = 'new-value'

FORWARD = [NEXT]
BACKWARD = [PREVIOUS]


# Element is a part of a bigger system
class Element(Talker):

    def __init__(self, owner=None):
        super(Element, self).__init__()
        self.on(self.can_set_property, self.do_set_property)

        self._owner, self.owner = None, owner

    def can_set_property(self, *message, **context):
        property_name = self.remove_prefix(message, SET_PREFIX)

        if property_name and hasattr(self, property_name) and \
                has_keys(context, OLD_VALUE, NEW_VALUE) and \
                getattr(self, property_name) != context.get(NEW_VALUE):

                return len(property_name), property_name  # To select the best property

    # Set the property to the new value
    def do_set_property(self, *message, **context):
        old_value = context.get(OLD_VALUE)

        if isinstance(old_value, Abstract):
            old_value(*message, **context)

        new_value = context.get(NEW_VALUE)

        setattr(self, '_%s' % context[CONDITION], new_value)

        if isinstance(new_value, Abstract):
            new_value(*message, **context)

        return True

    def change_property(self, name, value):
        # We change property via handler to allow notifications
        return self(self.add_prefix(name, SET_PREFIX),
                    **{NEW_VALUE: value, OLD_VALUE: getattr(self, name)})

    def can_go_forward(self, *message, **context):
        return self.can_handle(FORWARD, message, context)

    def can_go_backward(self, *message, **context):
        return self.can_handle(BACKWARD, message, context)

    def is_forward(self, message):
        return message and message[0] in FORWARD

    def is_backward(self, message):
        return message and message[0] in BACKWARD

    def on_forward(self, handler):
        self.on(self.can_go_forward, handler)

    def off_forward(self):
        self.off_condition(self.can_go_forward)

    def on_backward(self, handler):
        self.on(self.can_go_backward, handler)

    def off_backward(self):
        self.off_condition(self.can_go_backward)

    @property
    def owner(self):
        return self._owner

    @owner.setter
    def owner(self, value):
        self.change_property('owner', value)


# Notion is an element with name
class Notion(Element):
    def __init__(self, name, owner=None):
        super(Notion, self).__init__(owner)
        self._name, self.name = None, name

    def __str__(self):
        return '"%s"' % self.name

    def __repr__(self):
        return '<%s(%s, %s)>' % (get_object_name(self.__class__), self.__str__(), self.owner)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self.change_property(NAME, value)


# Action notion is a notion with specified forward handler
class ActionNotion(Notion):
    def __init__(self, name, action, owner=None):
        super(ActionNotion, self).__init__(name, owner)
        self.on_forward(action)

    @property
    def action(self):
        value = self.get_handlers(self.can_go_forward)
        return value[0] if value else None

    @action.setter
    def action(self, value):
        self.off_forward()
        self.on_forward(value)


# Relation dialect
SUBJECT = 'subject'
OBJECT = 'object'


# Relation is a connection between one or more elements: subject -> object
class Relation(Element):

    def __init__(self, subj, obj, owner=None):
        super(Relation, self).__init__(owner)
        self._object = self._subject = None
        self.subject, self.object = subj, obj

    @property
    def subject(self):
        return self._subject

    @subject.setter
    def subject(self, value):
        self.change_property(SUBJECT, value)

    @property
    def object(self):
        return self._object

    @object.setter
    def object(self, value):
        self.change_property(OBJECT, value)

    def __str__(self):
        return '<%s - %s>' % (self.subject, self.object)

    def __repr__(self):
        return self.__str__()


# Complex notion is a notion that relates with other notions (objects)
class ComplexNotion(Notion):
    def __init__(self, name, owner=None):
        super(ComplexNotion, self).__init__(name, owner)

        self._relations = []

        self.on(self.add_prefix(SUBJECT, SET_PREFIX), self.do_relation)
        self.on_forward(self.do_forward)

    def do_relation(self, *message, **context):
        relation = context.get(SENDER)

        if context[OLD_VALUE] == self and relation in self._relations:
            self._relations.remove(relation)
            return True

        elif context[NEW_VALUE] == self and relation not in self._relations:
            self._relations.append(relation)
            return True

    def do_forward(self, *message, **context):
        if self._relations:
            return self._relations[0] if len(self._relations) == 1 else tuple(self.relations)

    @property
    def relations(self):
        return self._relations


# Next relation checks for additional condition when relation traversed forward
class NextRelation(Relation):
    def __init__(self, subj, obj, condition=None, owner=None):
        super(NextRelation, self).__init__(subj, obj, owner)
        self.condition_access = Condition(condition, self.ignore_case)

        self.on(self.can_pass, self.next_handler)

    def check_condition(self, message, context):
        return self.condition_access.check(message, context)

    def can_pass(self, *message, **context):
        if self.is_forward(message):  # We use 0 rank to make condition prevail other forward command
            return True if not self.has_condition() else self.check_condition(message, context)

    def next_handler(self, *message, **context):
        return self.object

    def has_condition(self):
        return self.condition_access.value is not None

    @property
    def condition(self):
        return self.condition_access.value

    @condition.setter
    def condition(self, value):
        self.condition_access = Condition(value, self.ignore_case)


# Action relation performs an action and moves forward
class ActionRelation(Relation):
    def __init__(self, subj, obj, action, owner=None):
        super(ActionRelation, self).__init__(subj, obj, owner)
        self.action = action

        self.on_forward(self.act_next)

    def act_next(self, *message, **context):
        action_result = self.var_call_result(self.action, message, context) if callable(self.action) else self.action

        if action_result is not None and self.object is not None:
            return action_result, self.object
        else:
            return action_result if action_result is not None else self.object


# Process dialect
NEW = 'new'
OK = 'ok'
STOP = 'stop'
SKIP = 'skip'

CURRENT = 'current'
MESSAGE = 'message'
QUERY = 'query'


# Process is a walker from an abstract to abstract, asking them for the next one with a query
# It has the current abstract and the message to process; when new abstract appears,
# the new queue item with current and message is created
class Process(Talker):

    def __init__(self):
        super(Process, self).__init__()

        self._queue = []
        self.new_queue_item({})

        self.context = {}
        self.query = NEXT

        self.setup_handlers()

    # Generate the new queue item and add it to the queue updated with values
    def new_queue_item(self, values):
        item = {CURRENT: values.get(CURRENT) or None,
                MESSAGE: values.get(MESSAGE) or []}

        self._queue.append(item)

        return item

    # Put the new item in the queue, updating the empty one, if presents
    def to_queue(self, values):
        if not self.message:
            self.queue_top.update(values)  # No need to keep the empty one in the queue
        else:
            if not CURRENT in values:
                values[CURRENT] = self.current  # It is better to keep the current current

            self.new_queue_item(values)

    # Set the current message or inserts in the front of current message if insert = True
    def set_message(self, message, insert=False):

        if isinstance(message, tuple):
            message = list(message)
        elif not is_list(message):
            message = [message]

        if insert:
            message.extend(self.message)

        self.queue_top[MESSAGE] = message

    # Events #
    # New: cleaning up the queue
    def do_new(self):
        self.message.pop(0)
        del self._queue[:-1]

        self.queue_top[CURRENT] = None

    # Queue push: if the head of the message is an Abstract - we make the new queue item and get ready to query it
    def can_push_queue(self, *message):
        return self.message and (isinstance(message[0], Abstract) or callable(message[0]))

    def do_queue_push(self):
        self.to_queue({CURRENT: self.message.pop(0),
                       MESSAGE: [QUERY]})  # Adding query command to start from asking

    # Queue pop: when current queue item is empty we can remove it
    def can_pop_queue(self, *message):
        return len(self._queue) > 1 and not message

    def do_queue_pop(self):
        self._queue.pop()

    # Query: should we ask the query to the current current
    def can_query(self, *message):
        return self.current and has_first(message, QUERY)

    def do_query(self):
        self.message.pop(0)

        reply = self.current(self.query, **self.context) if isinstance(self.current, Abstract) \
            else self.var_call_result(self.current, self.message, self.context)  # TODO: check non-callable lists

        return reply or True  # if it is False/None, we just continue to the next one

    # Skip: remove current and the next item from the queue
    def do_skip(self):
        self.message.pop(0)  # Remove the command itself

        while not self.message and self._queue:  # Looking for the item to skip
            self.do_queue_pop()

        # It is ok if the message is empty to ignore skip
        if self.message:
            self.message.pop(0)

    # Cleanup: remove empty message item
    def can_clear_message(self, *message):
        if message:
            return not message[0]

    def do_clear_message(self):
        self.message.pop(0)

    def do_return(self):
        return self.message.pop(0)

    # Init handlers
    def setup_handlers(self):
        self.on(NEW, self.do_new)
        self.on(SKIP, self.do_skip)
        self.on((STOP, OK, True, False), self.do_return)

        self.on(self.can_query, self.do_query)
        self.on(self.can_push_queue, self.do_queue_push)
        self.on(self.can_pop_queue, self.do_queue_pop)
        self.on(self.can_clear_message, self.do_clear_message)

    # Start new parsing
    def start_parsing(self, new_message, new_context):
        if has_first(new_message, NEW):
            self.context = new_context
        else:
            self.context.update(new_context)

        self.to_queue({MESSAGE: list(new_message)})

    # Process' parse works in step-by-step manner, processing message and then popping the queue
    def parse(self, *message, **context):
        self.start_parsing(message, context)

        result = NO_PARSE

        while self.message or len(self._queue) > 1:
            result = super(Process, self).parse(*self.message, **self.context)

            if result[0] in (OK, STOP, False):
                break

            elif result[0] in (None, True):
                continue  # No need to put it into the message

            self.set_message(result[0], True)

        return result

    @property
    def queue_top(self):
        return self._queue[-1]

    @property
    def message(self):
        return self.queue_top.get(MESSAGE)

    @property
    def current(self):
        return self.queue_top.get(CURRENT)


# Shared context dialect
ADD_CONTEXT = 'add_context'
UPDATE_CONTEXT = 'update_context'
DELETE_CONTEXT = 'delete_context'


# Shared context process supports context modification commands
class SharedContextProcess(Process):

    def _context_add(self, key, value):
        self.context[key] = value

    def _context_set(self, key, value):
        self.context[key] = value

    def _context_delete(self, key):
        del self.context[key]

    # Events #
    # Do we have add context command
    def can_add_context(self, *message):
        return message and isinstance(message[0], dict) \
            and isinstance(message[0].get(ADD_CONTEXT), dict)  # TODO less isinstances

    # Adding items to context, do not replacing existing ones
    def do_add_context(self):
        add = self.message[0].pop(ADD_CONTEXT)

        for k, v in add.items():
            if not k in self.context:
                self._context_add(k, v)

    # Updating the context
    def can_update_context(self, *message):
        return message and isinstance(message[0], dict) \
            and isinstance(message[0].get(UPDATE_CONTEXT), dict)

    def do_update_context(self):
        update = self.message[0].pop(UPDATE_CONTEXT)

        for k, v in update.items():
            self._context_set(k, v)

    # Deleting items from the context
    def can_delete_context(self, *message):
        return message and isinstance(message[0], dict) \
            and DELETE_CONTEXT in message[0]

    def do_delete_context(self):
        delete = self.message[0].pop(DELETE_CONTEXT)

        if is_list(delete):
            for k in delete:
                if k in self.context:
                    self._context_delete(k)

        elif delete in self.context:
            self._context_delete(delete)

    def setup_handlers(self):
        super(SharedContextProcess, self).setup_handlers()

        self.on(self.can_add_context, self.do_add_context)
        self.on(self.can_update_context, self.do_update_context)
        self.on(self.can_delete_context, self.do_delete_context)


# StackingContextProcess dialect
PUSH_CONTEXT = 'push_context'
POP_CONTEXT = 'pop_context'
FORGET_CONTEXT = 'forget_context'


# Process that can save and restore context
# Useful for cases when process needs to try various paths in the graph
class StackingContextProcess(SharedContextProcess):

    def __init__(self):
        super(StackingContextProcess, self).__init__()

        self._context_stack = []

    def is_tracking(self):
        return len(self._context_stack) > 0

    # Clearing stack if new
    def do_new(self):
        super(StackingContextProcess, self).do_new()
        del self._context_stack[:]

    def run_tracking_operation(self, operation):
        if self.is_tracking():
            self._context_stack[-1].add(operation)
        else:
            operation.do()

    # Tracking changes in the context, if needed
    def _context_add(self, key, value):
        self.run_tracking_operation(DictChangeOperation(self.context, DictChangeOperation.ADD, key, value))

    def _context_set(self, key, value):
        self.run_tracking_operation(DictChangeOperation(self.context, DictChangeOperation.SET, key, value))

    def _context_delete(self, key):
        self.run_tracking_operation(DictChangeOperation(self.context, DictChangeOperation.DELETE, key))

    # Events #
    def do_push_context(self):
        self.message.pop(0)
        self._context_stack.append(DictChangeGroup())

    def can_pop_context(self, *message):
        return self.is_tracking() and has_first(message, POP_CONTEXT)

    def do_pop_context(self):
        self.message.pop(0)
        self._context_stack[-1].undo()
        self._context_stack.pop()

    def can_forget_context(self, *message):
        return self.is_tracking() and has_first(message, FORGET_CONTEXT)

    def do_forget_context(self):
        self.message.pop(0)
        self._context_stack.pop()

    def setup_handlers(self):
        super(StackingContextProcess, self).setup_handlers()

        self.on(PUSH_CONTEXT, self.do_push_context)
        self.on(self.can_pop_context, self.do_pop_context)
        self.on(self.can_forget_context, self.do_forget_context)


# StatefulProcess dialect
STATE = 'state'
SET_STATE = 'set_state'
CLEAR_STATE = 'clear_state'

NOTIFY = 'notify'
TO = 'to'
INFO = 'info'
NOTIFICATIONS = 'notifications'


# Process with support of abstract states and notifications between them
# Useful to preserve private a state of an abstract
class StatefulProcess(StackingContextProcess):

    def __init__(self):
        super(StatefulProcess, self).__init__()
        self.states = {}

    def _add_current_state(self):
        self.context[STATE] = self.states.get(self.current, {})

    def _del_current_state(self):
        del self.context[STATE]

    def _set_state(self, abstract, state):
        if not abstract in self.states:
            self.run_tracking_operation(DictChangeOperation(self.states, DictChangeOperation.ADD, abstract, state))
        else:
            self.run_tracking_operation(DictChangeOperation(self.states, DictChangeOperation.SET, abstract, state))

    def _clear_state(self, abstract):
        if abstract in self.states:
            self.run_tracking_operation(DictChangeOperation(self.states, DictChangeOperation.DELETE, abstract))

    # Clearing states if new
    def do_new(self):
        super(StatefulProcess, self).do_new()
        self.states.clear()

    def do_query(self):
        self._add_current_state()

        # Now the state contains the right state
        result = super(StatefulProcess, self).do_query()

        self._del_current_state()

        return result

    # Events #
    # Set state
    def can_set_state(self, *message):
        return self.current and message and isinstance(message[0], dict) and SET_STATE in message[0]

    def do_set_state(self):
        value = self.message[0].pop(SET_STATE)
        self._set_state(self.current, value)

    # Clear state
    def can_clear_state(self, *message):
        return self.current and message and has_first(message, CLEAR_STATE)

    def do_clear_state(self):
        self.message.pop(0)
        self._clear_state(self.current)

    # Notifications
    def can_notify(self, *message):
        return message and isinstance(message[0], dict) and isinstance(message[0].get(NOTIFY), dict) \
            and has_keys(message[0].get(NOTIFY), TO, INFO)

    def do_notify(self):
        notification = self.message[0].pop(NOTIFY)
        to = notification[TO]
        info = notification[INFO]

        if not to in self.states:
            self._set_state(to, {})

        operation = DictChangeOperation.ADD if not NOTIFICATIONS in self.states[to] \
            else DictChangeOperation.SET

        self.run_tracking_operation(DictChangeOperation(self.states[to], operation,
                                                        NOTIFICATIONS, info))

    def setup_handlers(self):
        super(StatefulProcess, self).setup_handlers()

        self.on(self.can_set_state, self.do_set_state)
        self.on(self.can_clear_state, self.do_clear_state)
        self.on(self.can_notify, self.do_notify)


# ParsingProcess dialect
ERROR = 'error'
PROCEED = 'proceed'
BREAK = 'break'
CONTINUE = 'continue'

PARSED_LENGTH = 'parsed_length'
TEXT = 'text'
LAST_PARSED = 'last_parsed'


# Parsing process supports error and move commands for text processing
class ParsingProcess(StatefulProcess):

    def do_new(self):
        super(ParsingProcess, self).do_new()
        self.query = NEXT
        self._context_set(PARSED_LENGTH, 0)
        self._context_set(LAST_PARSED, '')

    def is_parsed(self):
        return self.query == NEXT and not self.text

    def parse(self, *message, **context):
        result = super(ParsingProcess, self).parse(*message, **context)

        return False if not self.is_parsed() and not result[0] == STOP else result[0], self.parsed_length, result[2]

    # Events #
    # Proceed: part of the Text was parsed
    def can_proceed(self, *message):
        if not message or not isinstance(message[0], dict):
            return False

        distance = message[0].get(PROCEED)
        return is_number(distance) and len(self.context.get(TEXT)) >= distance

    def do_proceed(self):
        proceed = self.message[0].pop(PROCEED)
        last_parsed = self.context[TEXT][0:proceed]

        self._context_set(TEXT, self.context[TEXT][proceed:])
        self._context_set(PARSED_LENGTH, self.parsed_length + proceed)
        self._context_set(LAST_PARSED, last_parsed)

    # Next, Break, Error or Continue
    def do_turn(self):
        new_query = self.message.pop(0)

        if new_query in BACKWARD:
            del self.message[:]

        self.query = new_query

    def setup_handlers(self):
        super(ParsingProcess, self).setup_handlers()

        self.on((NEXT, ERROR, BREAK, CONTINUE), self.do_turn)
        self.on(self.can_proceed, self.do_proceed)

    @property
    def text(self):
        return self.context.get(TEXT, '')

    @property
    def parsed_length(self):
        return self.context.get(PARSED_LENGTH, 0)

    @property
    def last_parsed(self):
        return self.context.get(LAST_PARSED, '')


# Adding new backward commands
BACKWARD += [ERROR, BREAK, CONTINUE]


# Parsing relation: should be passable in forward direction (otherwise returns Error)
class ParsingRelation(NextRelation):
    def __init__(self, subj, obj, condition=None, owner=None):
        super(ParsingRelation, self).__init__(subj, obj, condition, owner)

        self.optional = False
        self.check_only = False

        self.on(UNKNOWN, self.on_error)

    # Here we check condition against the parsing text
    def check_condition(self, message, context):
        return self.condition_access.check(tupled(context.get(TEXT), message), context)

    def next_handler(self, *message, **context):
        next_result = super(ParsingRelation, self).next_handler(*message, **context)
        rank = context.get(RANK)

        return ({PROCEED: rank}, next_result) if rank and not self.check_only else next_result

    def on_error(self, *message, **context):
        if not self.optional and len(message) > 1 and message[1] in FORWARD:
            return ERROR


# SelectiveNotion dialect
CASES = 'cases'


# Selective notion: complex notion that can consist of one of its objects
# It tries all relations and uses the one without errors
class SelectiveNotion(ComplexNotion):

    def __init__(self, name, owner=None):
        super(SelectiveNotion, self).__init__(name, owner)

        self.on(self.can_retry, self.do_retry)
        self.on(self.can_finish, self.do_finish)

        self._default = None

    # Searching for the longest case, use default if none and it is specified
    def get_best_cases(self, message, context):
        context[ANSWER] = RANK

        cases = []
        max_len = -1
        for rel in self.relations:
            if rel == self.default:  # Not now
                continue

            result, length = rel(*message, **context)  # With the rank, please

            if result != ERROR and length >= 0:
                max_len = max(length, max_len)
                cases.append((rel, length))

        best_cases = [case for case, length in cases if length == max_len]

        if not best_cases and self.default:  # Right time to use the default
            best_cases = [self.default]

        return best_cases

    # Default should be the part of relations
    def do_relation(self, *message, **context):
        super(SelectiveNotion, self).do_relation(*message, **context)

        if self.default and not self.default in self.relations:
            self.default = None

    # Events #
    def can_go_forward(self, *message, **context):
        if not context.get(STATE):  # If we've been here before we need to try something different
            return super(SelectiveNotion, self).can_go_forward(*message, **context)

    def do_forward(self, *message, **context):
        reply = super(SelectiveNotion, self).do_forward(*message, **context)

        if is_list(reply):
            cases = self.get_best_cases(message, context)

            if cases:
                case = cases.pop(0)

                if not cases:
                    reply = case
                else:
                    reply = (PUSH_CONTEXT,  # Keep the context if re-try will needed
                             {SET_STATE: {CASES: cases}},  # Store what to try next
                             case,  # Try first case
                             self)  # And come back again
            else:
                return ERROR

        return reply

    def can_retry(self, *message, **context):
        return context.get(STATE) and has_first(message, ERROR)

    def do_retry(self, *message, **context):
        cases = context[STATE][CASES]

        if cases:
            case = cases.pop(0)  # Try another case, if any

            # Pop context and update state, then try another case and come back here
            return [POP_CONTEXT,  # Roll back to the initial context
                    {SET_STATE: {CASES: cases}},  # Update cases
                    PUSH_CONTEXT,  # Save updated context
                    NEXT,  # Go forward again
                    case,  # Try another case
                    self]  # Come back
        else:
            return self.do_finish(*message, **context)  # No more opportunities

    def can_finish(self, *message, **context):
        return context.get(STATE) and self.is_forward(message)

    def do_finish(self, *message, **context):
        return [FORGET_CONTEXT, CLEAR_STATE]

    @property
    def default(self):
        return self._default

    @default.setter
    def default(self, value):
        if self._default == value or (value and value.subject != self):
            return

        self._default = value


# LoopRelation dialect
ITERATION = 'i'
WILDCARDS = ('*', '?', '+')
INFINITY = float('inf')


# Loop relation specifies counts of the related object.
# Possible conditions are: numeric (n; m..n; m..; ..n), wildcards (*, ?, +), true (infinite loop), and iterator function
class LoopRelation(NextRelation):

    def __init__(self, subj, obj, condition=None, owner=None):
        super(LoopRelation, self).__init__(subj, obj, condition, owner)

        # General loop
        self.on(self.can_start_general, self.do_start_general)
        self.on(self.can_loop_general, self.do_loop_general)
        self.on(self.can_error_general, self.do_error_general)
        
        # Custom loop
        self.on(self.can_loop_custom, self.do_loop_custom)
        self.on(self.can_error_custom, self.do_error_custom)
        
        # Common events
        self.on(self.can_break, self.do_break)
        self.on(self.can_continue, self.do_continue)

    def check_condition(self, message, context):
        if not self.has_condition():  # Here we check only the simplest case
            return False

    # Is a wildcard loop
    def is_wildcard(self):
        return self.condition in WILDCARDS

    # Is a numeric loop
    def is_numeric(self):
        if self.condition_access.spec == Access.NUMBER:
            return True
        elif self.condition_access.spec == Access.LIST and len(self.condition) == 2:
            return (self.condition[0] is None or self.condition_access.list[0].spec == Access.NUMBER) \
                and (self.condition[1] is None or self.condition_access.list[1].spec == Access.NUMBER)

    # Infinite loop
    def is_infinite(self):
        return self.condition is True

    # Custom loop: not empty callable condition
    def is_custom(self):
        return self.condition_access.mode == Access.FUNCTION

    # Flexible condition has no finite bound, lower or higher
    def is_flexible(self):
        return (self.is_numeric() and self.condition_access.spec == Access.LIST) or self.is_wildcard()

    # Checking for the condition type
    def is_general(self):
        return self.is_numeric() or self.is_wildcard() or self.is_infinite()

    # Checking is we are in loop now
    def is_looping(self, context):
        return ITERATION in context.get(STATE)

    # Get the limits of the loop
    def get_bounds(self):
        lower, upper = 0, INFINITY

        if self.is_numeric():
            if self.condition_access.spec == Access.NUMBER:
                lower, upper = 1, self.condition
            else:
                if self.condition[0]:
                    lower = self.condition[0]
                if self.condition[1]:
                    upper = self.condition[1]

        elif self.is_wildcard():
            if self.condition == '+':
                lower = 1
            elif self.condition == '?':
                upper = 1

        elif self.is_infinite():
            lower = upper

        return lower, upper

    # Make the iteration reply
    def get_next_iteration_reply(self, i=1):
        reply = [{SET_STATE: {ITERATION: i}}]

        if self.is_flexible():
            if i != 1:
                reply.insert(0, FORGET_CONTEXT)  # Forget the past
            reply += [PUSH_CONTEXT]  # Save state if needed

        return reply + [self.object, self]  # Try and come back

    # Events #
    # General loop
    def can_start_general(self, *message, **context):
        return self.is_forward(message) and not self.is_looping(context) and self.is_general()

    def do_start_general(self, *message, **context):
        return self.get_next_iteration_reply()

    def can_loop_general(self, *message, **context):
        return self.is_forward(message) and self.is_looping(context) and self.is_general()

    def do_loop_general(self, *message, **context):
        i = context.get(STATE).get(ITERATION)

        if i < self.get_bounds()[1]:
            return self.get_next_iteration_reply(i + 1)
        else:
            reply = []

            if self.is_flexible():
                reply += [FORGET_CONTEXT]

            return reply + [CLEAR_STATE]

    def can_error_general(self, *message, **context):
        return has_first(message, ERROR) and self.is_looping(context) and self.is_general()

    def do_error_general(self, *message, **context):
        i = context.get(STATE).get(ITERATION)
        lower, upper = self.get_bounds()

        reply = []

        if self.is_flexible():
            # Roll back to the previous good result
            if lower < i <= upper:
                reply += [NEXT, POP_CONTEXT]
            else:
                reply += [FORGET_CONTEXT]

        return reply + [CLEAR_STATE]
    
    # Custom loop
    def can_loop_custom(self, *message, **context):
        return self.is_forward(message) and self.is_custom()

    def do_loop_custom(self, *message, **context):
        i = self.condition_access.access(message, context)

        if i:
            return {SET_STATE: {ITERATION: i}}, self.object, self
        else:
            return False if not self.is_looping(context) else CLEAR_STATE,

    def can_error_custom(self, *message, **context):
        return has_first(message, ERROR) and self.is_custom()

    def do_error_custom(self, *message, **context):
        return CLEAR_STATE,
    
    # Common handling
    def can_break(self, *message, **context):
        return has_first(message, BREAK) and self.is_looping(context)

    def do_break(self, *message, **context):
        reply = [NEXT]

        if self.is_flexible():
            reply += [FORGET_CONTEXT]

        return reply + [CLEAR_STATE]

    def can_continue(self, *message, **context):
        return has_first(message, CONTINUE) and self.is_looping(context)

    def do_continue(self, *message, **context):
        return [NEXT] + self.do_loop_general(*message, **context)


# Graph is a holder of Notions and Relation, it allows easy search and processing of them
class Graph(Element):
    def __init__(self, root=None, owner=None):
        super(Graph, self).__init__(owner)

        self._root = None
        self._notions = []
        self._relations = []

        self.on(self.add_prefix(OWNER, SET_PREFIX), self.do_element)
        self.on_forward(self.do_forward)

        if root:
            if is_string(root):
                root = ComplexNotion(root, self)

            self.root = root

    # Gets the rank of notion when searching by criteria
    def get_notion_search_rank(self, notion, criteria):
        if callable(criteria):
            return criteria(notion)
        else:
            if is_regex(criteria):
                match = criteria.match(notion.name)
                if match:
                    return match.end() - match.start()

            elif notion.name == criteria:
                return len(criteria)

        return -1

    def search_elements(self, collection, comparator, criteria):
        rank = -1
        found = []

        for element in collection:
            r = comparator(element, criteria)

            if r >= rank and r >= 0:
                if r > rank:
                    rank = r
                    del found[:]
                found.append(element)

        return found

    def notions(self, criteria=None):
        return self.search_elements(self._notions, self.get_notion_search_rank, criteria) if criteria else \
            tuple(self._notions)

    def notion(self, criteria):
        found = self.notions(criteria)

        return found[0] if found else None

    # Gets the rank of relation when searching by criteria
    def get_relation_search_rank(self, relation, criteria):
        if callable(criteria):
            return criteria(relation)
        else:
            if isinstance(criteria, dict):
                req, rel = [], []

                if SUBJECT in criteria:
                    req.append(criteria[SUBJECT])
                    rel.append(relation.subject)

                if OBJECT in criteria:
                    req.append(criteria[OBJECT])
                    rel.append(relation.object)

                return len(rel) if rel == req and rel else -1

    def relations(self, criteria=None):
        return self.search_elements(self._relations, self.get_relation_search_rank, criteria) if criteria else \
            tuple(self._relations)

    def relation(self, criteria=None):
        found = self.relations(criteria)

        return found[0] if found else None

    def do_element(self, *message, **context):
        element = context.get(SENDER)

        if isinstance(element, Notion) or isinstance(element, Graph):
            collection = self._notions
        elif isinstance(element, Relation):
            collection = self._relations
        else:
            return False

        if context[OLD_VALUE] == self and element in collection:
            collection.remove(element)

            if element == self.root:
                self.root = None

            return True

        elif context[NEW_VALUE] == self and element not in collection:
            collection.append(element)
            return True

    def do_forward(self, *message, **context):
        return self.root

    @property
    def root(self):
        return self._root

    @root.setter
    def root(self, value):
        if (self._root == value) or (value and (value.owner != self or not isinstance(value, Notion))):
            return

        self.change_property('root', value)

    def __str__(self):
        return '{"%s"}' % (self.root.name if self.root else '')

    def __repr__(self):
        return '{%s(%s, %s)}' % (get_object_name(self.__class__), self.__str__(), self.owner)

    @property
    def name(self):
        return self.root.name if self.root else None

    @name.setter
    def name(self, value):
        self.root.name = value

# TODO: test and exceptions if incorrect state
# Graph builder helps to create graph structures
class GraphBuilder(object):
    def __init__(self, graph=None):
        if is_string(graph):
            graph = Graph(graph)

        self.graph = graph
        self.current = graph.root if graph else None

    def attach(self, new):
        if isinstance(new, Notion):
            if isinstance(self.current, Relation) and not self.current.object:
                self.current.object = new

        elif isinstance(new, Relation):
            if isinstance(self.current, Notion) and not new.subject:
                new.subject = self.current

                if isinstance(self.current, ComplexNotion):
                    return self  # Do not update last, just connect

        self.current = new

        return self

    def complex(self, name):
        return self.attach(ComplexNotion(name, self.graph))

    def notion(self, name):
        return self.attach(Notion(name, self.graph))

    def next_rel(self, condition=None, obj=None, ignore_case=None):
        rel = NextRelation(self.current, obj, condition, self.graph)
        rel.ignore_case = ignore_case

        return self.attach(rel)

    def act_rel(self, action, obj=None):
        return self.attach(ActionRelation(self.current, obj, action, self.graph))

    def parse_rel(self, condition, obj=None, ignore_case=None, optional=None):
        rel = ParsingRelation(self.current, obj, condition, self.graph)
        rel.ignore_case, rel.optional = ignore_case, optional

        return self.attach(rel)

    def default(self):
        if isinstance(self.current, Relation) and isinstance(self.current.subject, SelectiveNotion):
            self.current.subject.default = self.current

        return self

    def check_only(self, value=True):
        if isinstance(self.current, ParsingRelation):
            self.current.check_only = value

        return self

    def loop(self, condition, obj=None):
        return self.attach(LoopRelation(self.current, obj, condition, self.graph))

    def select(self, name):
        return self.attach(SelectiveNotion(name, self.graph))

    def act(self, name, action):
        return self.attach(ActionNotion(name, action, self.graph))

    def graph(self, name):
        new = Graph(name, self.graph if self.graph else None)

        if not self.graph:
            self.graph = new
            self.current = self.graph.root
        else:
            self.attach(new.root)
            self.graph = new

        return self

    def at(self, element):
        if element != self.current:
            self.current = element

            if element and element.owner != self.graph:
                self.graph = element.owner

        return self

    # Go to the higher level of the current element
    def pop(self):
        if self.current and self.current.owner:
            self.graph = self.current.owner.owner
            self.current = self.graph.root

        return self
