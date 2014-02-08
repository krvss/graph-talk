# Universal Translator base classes
# (c) krvss 2011-2013

from inspect import getargspec, isfunction, ismethod
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


# Handler is a class for the routing of messages to processing functions (handlers) basing on specified conditions
class Handler(Abstract):
    ANSWER = 'answer'
    SENDER = 'sender'
    CONDITION = 'condition'
    HANDLER = 'handler'
    RANK = 'rank'

    NO_PARSE = (False, -1, None)

    def __init__(self):
        self.handlers = []

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

        spec = getargspec(func)
        v_count, k_count = 0, 0

        if spec.varargs:
            v_count = len(spec.varargs) if is_list(spec.varargs) else 1

        if spec.keywords:
            k_count = len(spec.keywords) if is_list(spec.keywords) else 1

        if v_count and not k_count:
            return func(*message)

        elif k_count and not v_count:
            return func(**context)

        elif v_count and k_count:
            return func(*message, **context)

        elif not v_count and not k_count and not spec.args:
            return func()

        elif spec.args:
            args = {}
            for arg in spec.args:
                if arg != 'self':
                    args[arg] = context[arg] if arg in context else None

            return func(**args)

    # Checking the condition to satisfy the message and context
    def can_handle(self, condition, message, context):
        rank, check = -1, None

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

        else:
            if not is_list(condition):
                condition = [condition]

            for c in condition:
                if is_string(c) and message:
                    if str(message[0]).startswith(c):
                        rank, check = len(c), c

                elif has_first(message, c):
                    rank, check = max(get_len(c), 0), c

        if rank < 0:
            check = None  # Little cleanup

        return rank, check

    # Running the specified handler, returns result as result, rank, handler
    def run_handler(self, handler, message, context):
        result = self.var_call_result(handler, message, context) if callable(handler) else handler

        return result, handler

    # Calling handlers basing on condition, using ** to protect the context content
    def handle(self, *message, **context):
        check, rank, handler_found = Handler.NO_PARSE

        if not Handler.SENDER in context:
            context[Handler.SENDER] = self

        # Searching for the best handler
        for handler in self.handlers:
            handler_func = handler if not is_list(handler) else handler[1]

            # Avoiding recursive calls
            if context.get(Handler.HANDLER) == handler_func:
                continue

            # Condition check, if no condition the result is true with zero rank
            condition = self.can_handle(handler[0], message, context) if is_list(handler) else (0, True)

            if condition[0] <= rank:
                continue
            else:
                rank, check, handler_found = condition[0], condition[1], handler_func

        # Running the best handler
        if rank >= 0:
            if not Handler.HANDLER in context:
                context[Handler.HANDLER] = handler_found

            context.update({Handler.RANK: rank, Handler.CONDITION: check})

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
        answer_mode = context.pop(Handler.ANSWER, None)  # Applicable only for a top level
        result = super(Handler, self).answer(*message, **context)

        if answer_mode == Handler.RANK:
            return result[0], result[1]

        return result[0]  # No need to know the details


# Handler which uses pre and post handling notifications
class Talker(Handler):
    PRE_PREFIX = 'pre'
    POST_PREFIX = 'post'
    RESULT = 'result'
    UNKNOWN = 'unknown'

    SEP = '_'
    SILENT = (RESULT, UNKNOWN)

    # Add prefix to the message
    @staticmethod
    def add_prefix(message, prefix):
        event = str(message[0] if is_list(message) else message)

        if not event.startswith(prefix):
            event = Talker.SEP.join([prefix, event])

        return tupled(event, message[1:]) if is_list(message) else event

    # Remove prefix from the message
    @staticmethod
    def remove_prefix(message, prefix=None):
        event = str(message[0] if message and is_list(message) else message)

        if not Talker.SEP in event or (prefix and not event.startswith(prefix + Talker.SEP)):
            return None

        return event.split(Talker.SEP, 1)[-1]

    # Should event go silent or not, useful to avoid recursions
    def is_silent(self, event):
        if not is_string(event):
            event = str(event)

        return event.startswith(Talker.PRE_PREFIX) or event.startswith(Talker.POST_PREFIX) \
            or event in Talker.SILENT

    # Runs the handler with pre and post notifications
    def run_handler(self, handler, message, context):
        event = message if (message and is_string(message[0])) else (get_object_name(handler), )
        silent = self.is_silent(event[0])

        if not silent:
            context[Handler.HANDLER] = handler

            # Pre-processing, adding prefix to event or handler name
            pre_result = self.handle(*self.add_prefix(event, Talker.PRE_PREFIX), **context)

            if pre_result[0]:
                return pre_result[0], pre_result[2]

        result = super(Talker, self).run_handler(handler, message, context)

        if not silent:
            context.update({Talker.RESULT: result[0], Handler.RANK: result[1]})

            # Post-processing, adding postfix and results
            post_result = self.handle(*self.add_prefix(event, Talker.POST_PREFIX), **context)

            if post_result[0]:
                return post_result[0], post_result[2]

        return result

    # Parse means search for a handler
    def parse(self, *message, **context):
        result = super(Talker, self).parse(*message, **context)

        # There is a way to override result and handle unknown message
        if result[0] is not False:
            context.update({Talker.RESULT: result[0], Handler.RANK: result[1], Handler.HANDLER: result[2]})
            after_result = super(Talker, self).parse(Talker.RESULT, *message, **context)

            if after_result[0]:
                result = after_result  # override has priority
        else:
            result = super(Talker, self).parse(Talker.UNKNOWN, *message, **context)

        return result


# Element is a part of a bigger system
class Element(Talker):
    NEXT = 'next'
    PREVIOUS = 'previous'
    OWNER = 'owner'

    SET_PREFIX = 'set'
    NAME = 'name'
    OLD_VALUE = 'old-value'
    NEW_VALUE = 'new-value'

    FORWARD = NEXT,
    BACKWARD = PREVIOUS,

    def __init__(self, owner=None):
        super(Element, self).__init__()
        self.on(self.can_set_property, self.do_set_property)

        self._owner, self.owner = None, owner

    def can_set_property(self, *message, **context):
        property_name = self.remove_prefix(message, Element.SET_PREFIX)

        if property_name and hasattr(self, property_name) and \
                has_keys(context, Element.OLD_VALUE, Element.NEW_VALUE) and \
                getattr(self, property_name) != context.get(Element.NEW_VALUE):

                return len(property_name), property_name  # To select the best property

    # Set the property to the new value
    def do_set_property(self, *message, **context):
        old_value = context.get(Element.OLD_VALUE)

        if isinstance(old_value, Abstract):
            old_value(*message, **context)

        new_value = context.get(Element.NEW_VALUE)

        setattr(self, '_%s' % context[Handler.CONDITION], new_value)

        if isinstance(new_value, Abstract):
            new_value(*message, **context)

        return True

    def change_property(self, name, value):
        # We change property via handler to allow notifications
        return self(self.add_prefix(name, Element.SET_PREFIX),
                    **{Element.NEW_VALUE: value, Element.OLD_VALUE: getattr(self, name)})

    def can_go_forward(self, *message, **context):
        return self.can_handle(Element.FORWARD, message, context)

    def can_go_backward(self, *message, **context):
        return self.can_handle(Element.BACKWARD, message, context)

    def is_forward(self, message):
        return message and message[0] in Element.FORWARD

    def is_backward(self, message):
        return message and message[0] in Element.BACKWARD

    def on_forward(self, handler):
        self.on(self.can_go_forward, handler)

    def off_forward(self):
        self.off_condition(self.can_go_forward)

    def on_backward(self, handler):
        self.on(self.can_go_backward, handler)

    def off_backward(self):
        self.off_condition(self.can_go_backward)

    @staticmethod
    def add_forward_command(command):
        if not command in Element.FORWARD:
            Element.FORWARD = Element.FORWARD + (command, )

    @staticmethod
    def remove_forward_command(command):
        Element.FORWARD = tuple(c for c in Element.FORWARD if c != command)

    @staticmethod
    def add_backward_command(command):
        if not command in Element.BACKWARD:
            Element.BACKWARD = Element.BACKWARD + (command, )

    @staticmethod
    def remove_backward_command(command):
        Element.BACKWARD = tuple(c for c in Element.BACKWARD if c != command)

    @property
    def owner(self):
        return self._owner

    @owner.setter
    def owner(self, value):
        self.change_property('owner', value)


# Notion is an element with name
class Notion2(Element):
    def __init__(self, name, owner=None):
        super(Notion2, self).__init__(owner)
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
        self.change_property(Element.NAME, value)


# Action notion is a notion with specified forward handler
class ActionNotion2(Notion2):
    def __init__(self, name, action, owner=None):
        super(ActionNotion2, self).__init__(name, owner)
        self.on_forward(action)

    @property
    def action(self):
        value = self.get_handlers(self.can_go_forward)
        return value[0] if value else None

    @action.setter
    def action(self, value):
        self.off_forward()
        self.on_forward(value)


# Relation is a connection between one or more elements: subject -> object
class Relation2(Element):
    SUBJECT = 'subject'
    OBJECT = 'object'

    def __init__(self, subj, obj, owner=None):
        super(Relation2, self).__init__(owner)
        self._object = self._subject = None
        self.subject, self.object = subj, obj

    @property
    def subject(self):
        return self._subject

    @subject.setter
    def subject(self, value):
        self.change_property(Relation2.SUBJECT, value)

    @property
    def object(self):
        return self._object

    @object.setter
    def object(self, value):
        self.change_property(Relation2.OBJECT, value)

    def __str__(self):
        return '<%s - %s>' % (self.subject, self.object)

    def __repr__(self):
        return self.__str__()


# Complex notion is a notion that relates with other notions (objects)
class ComplexNotion2(Notion2):
    def __init__(self, name, owner=None):
        super(ComplexNotion2, self).__init__(name, owner)

        self._relations = []

        self.on(self.add_prefix(Relation2.SUBJECT, Element.SET_PREFIX), self.do_relation)
        self.on_forward(self.do_forward)

    def do_relation(self, *message, **context):
        relation = context.get(Handler.SENDER)

        if context[Element.OLD_VALUE] == self and relation in self._relations:
            self._relations.remove(relation)
            return True

        elif context[Element.NEW_VALUE] == self and relation not in self._relations:
            self._relations.append(relation)
            return True

    def do_forward(self, *message, **context):
        if self._relations:
            return self._relations[0] if len(self._relations) == 1 else tuple(self.relations)

    @property
    def relations(self):
        return self._relations


# Next relation checks for additional condition when relation traversed forward
class NextRelation2(Relation2):
    def __init__(self, subj, obj, condition=None, owner=None):
        super(NextRelation2, self).__init__(subj, obj, owner)
        self.condition = condition

        self.on(self.can_pass, self.next_handler)

    def check_condition(self, message, context):
        return self.can_handle(self.condition, message, context)

    def can_pass(self, *message, **context):
        if self.is_forward(message):  # We use 0 rank to make condition prevail other forward command
            return True if self.condition is None else self.check_condition(message, context)

    def next_handler(self, *message, **context):
        return self.object


# Process is a walker from an abstract to abstract, asking them for the next one with a query
# It has the current abstract and the message to process; when new abstract appears,
# the new queue item with current and message is created
class Process2(Talker):
    NEW = 'new'
    OK = 'ok'
    STOP = 'stop'
    SKIP = 'skip'

    CURRENT = 'current'
    MESSAGE = 'message'
    QUERY = 'query'

    def __init__(self):
        super(Process2, self).__init__()

        self._queue = []
        self.new_queue_item({})

        self.context = {}
        self.query = Element.NEXT

        self.setup_handlers()

    # Generate the new queue item and add it to the queue updated with values
    def new_queue_item(self, values):
        item = {Process2.CURRENT: values.get(Process2.CURRENT) or None,
                Process2.MESSAGE: values.get(Process2.MESSAGE) or []}

        self._queue.append(item)

        return item

    # Put the new item in the queue, updating the empty one, if presents
    def to_queue(self, values):
        if not self.message:
            self.queue_top.update(values)  # No need to keep the empty one in the queue
        else:
            if not Process2.CURRENT in values:
                values[Process2.CURRENT] = self.current  # It is better to keep the current current

            self.new_queue_item(values)

    # Set the current message or inserts in the front of current message if insert = True
    def set_message(self, message, insert=False):

        if isinstance(message, tuple):
            message = list(message)
        elif not is_list(message):
            message = [message]

        if insert:
            message.extend(self.message)

        self.queue_top[Process2.MESSAGE] = message

    # Events #
    # New: cleaning up the queue
    def do_new(self):
        self.message.pop(0)
        del self._queue[:-1]

        self.queue_top[Process2.CURRENT] = None

    # Queue push: if the head of the message is an Abstract - we make the new queue item and get ready to query it
    def can_push_queue(self, *message):
        return self.message and isinstance(message[0], Abstract)

    def do_queue_push(self):
        self.to_queue({Process2.CURRENT: self.message.pop(0),
                       Process2.MESSAGE: [Process2.QUERY]})  # Adding query command to start from asking

    # Queue pop: when current queue item is empty we can remove it
    def can_pop_queue(self, *message):
        return len(self._queue) > 1 and not message

    def do_queue_pop(self):
        self._queue.pop()

    # Query: should we ask the query to the current current
    def can_query(self, *message):
        return self.current and has_first(message, Process2.QUERY)

    def do_query(self):
        self.message.pop(0)
        reply = self.current(self.query, **self.context)
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
            return ((is_list(message[0]) or isinstance(message[0], dict)) and not message[0]) or message[0] is None

    def do_clear_message(self):
        self.message.pop(0)

    # Init handlers
    def setup_handlers(self):
        self.on(Process2.NEW, self.do_new)
        self.on(Process2.SKIP, self.do_skip)

        self.on(self.can_query, self.do_query)
        self.on(self.can_push_queue, self.do_queue_push)
        self.on(self.can_pop_queue, self.do_queue_pop)
        self.on(self.can_clear_message, self.do_clear_message)

    # Start new parsing
    def start_parsing(self, new_message, new_context):
        if has_first(new_message, Process2.NEW):
            self.context = new_context
        else:
            self.context.update(new_context)

        self.to_queue({Process2.MESSAGE: list(new_message)})

    # Process' parse works in step-by-step manner, processing message and then popping the queue
    def parse(self, *message, **context):
        self.start_parsing(message, context)

        result = Handler.NO_PARSE

        while self.message or len(self._queue) > 1:
            result = super(Process2, self).parse(*self.message, **self.context)

            if result[0] in (Process2.OK, Process2.STOP, False):
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
        return self.queue_top.get(Process2.MESSAGE)

    @property
    def current(self):
        return self.queue_top.get(Process2.CURRENT)


# Shared context process supports context modification commands
class SharedContextProcess2(Process2):
    ADD_CONTEXT = 'add_context'
    UPDATE_CONTEXT = 'update_context'
    DELETE_CONTEXT = 'delete_context'

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
            and isinstance(message[0].get(SharedContextProcess2.ADD_CONTEXT), dict)

    # Adding items to context, do not replacing existing ones
    def do_add_context(self):
        add = self.message[0].pop(SharedContextProcess2.ADD_CONTEXT)

        for k, v in add.items():
            if not k in self.context:
                self._context_add(k, v)

    # Updating the context
    def can_update_context(self, *message):
        return message and isinstance(message[0], dict) \
            and isinstance(message[0].get(SharedContextProcess2.UPDATE_CONTEXT), dict)

    def do_update_context(self):
        update = self.message[0].pop(SharedContextProcess2.UPDATE_CONTEXT)

        for k, v in update.items():
            self._context_set(k, v)

    # Deleting items from the context
    def can_delete_context(self, *message):
        return message and isinstance(message[0], dict) \
            and SharedContextProcess2.DELETE_CONTEXT in message[0]

    def do_delete_context(self):
        delete = self.message[0].pop(SharedContextProcess2.DELETE_CONTEXT)

        if is_list(delete):
            for k in delete:
                if k in self.context:
                    self._context_delete(k)

        elif delete in self.context:
            self._context_delete(delete)

    def setup_handlers(self):
        super(SharedContextProcess2, self).setup_handlers()

        self.on(self.can_add_context, self.do_add_context)
        self.on(self.can_update_context, self.do_update_context)
        self.on(self.can_delete_context, self.do_delete_context)


# Process that can save and restore context
# Useful for cases when process needs to try various paths in the graph
class StackingContextProcess2(SharedContextProcess2):
    PUSH_CONTEXT = 'push_context'
    POP_CONTEXT = 'pop_context'
    FORGET_CONTEXT = 'forget_context'

    def __init__(self):
        super(StackingContextProcess2, self).__init__()

        self._context_stack = []

    def is_tracking(self):
        return len(self._context_stack) > 0

    # Clearing stack if new
    def do_new(self):
        super(StackingContextProcess2, self).do_new()
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
        return self.is_tracking() and has_first(message, StackingContextProcess2.POP_CONTEXT)

    def do_pop_context(self):
        self.message.pop(0)
        self._context_stack[-1].undo()
        self._context_stack.pop()

    def can_forget_context(self, *message):
        return self.is_tracking() and has_first(message, StackingContextProcess2.FORGET_CONTEXT)

    def do_forget_context(self):
        self.message.pop(0)
        self._context_stack.pop()

    def setup_handlers(self):
        super(StackingContextProcess2, self).setup_handlers()

        self.on(StackingContextProcess2.PUSH_CONTEXT, self.do_push_context)
        self.on(self.can_pop_context, self.do_pop_context)
        self.on(self.can_forget_context, self.do_forget_context)


# Process with support of abstract states and notifications between them
# Useful to preserve private a state of an abstract
class StatefulProcess2(StackingContextProcess2):
    STATE = 'state'
    SET_STATE = 'set_state'
    CLEAR_STATE = 'clear_state'

    NOTIFY = 'notify'
    TO = 'to'
    INFO = 'info'
    NOTIFICATIONS = 'notifications'

    def __init__(self):
        super(StatefulProcess2, self).__init__()
        self.states = {}

    def _add_current_state(self):
        self.context[StatefulProcess2.STATE] = self.states.get(self.current, {})

    def _del_current_state(self):
        del self.context[StatefulProcess2.STATE]

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
        super(StatefulProcess2, self).do_new()
        self.states.clear()

    def do_query(self):
        self._add_current_state()

        # Now the state contains the right state
        result = super(StatefulProcess2, self).do_query()

        self._del_current_state()

        return result

    # Events #
    # Set state
    def can_set_state(self, *message):
        return self.current and message and isinstance(message[0], dict) and StatefulProcess2.SET_STATE in message[0]

    def do_set_state(self):
        value = self.message[0].pop(StatefulProcess2.SET_STATE)
        self._set_state(self.current, value)

    # Clear state
    def can_clear_state(self, *message):
        return self.current and message and has_first(message, StatefulProcess2.CLEAR_STATE)

    def do_clear_state(self):
        self.message.pop(0)
        self._clear_state(self.current)

    # Notifications
    def can_notify(self, *message):
        return message and isinstance(message[0], dict) and isinstance(message[0].get(StatefulProcess2.NOTIFY), dict) \
            and has_keys(message[0].get(StatefulProcess2.NOTIFY), StatefulProcess2.TO, StatefulProcess2.INFO)

    def do_notify(self):
        notification = self.message[0].pop(StatefulProcess2.NOTIFY)
        to = notification[StatefulProcess2.TO]
        info = notification[StatefulProcess2.INFO]

        if not to in self.states:
            self._set_state(to, {})

        operation = DictChangeOperation.ADD if not StatefulProcess2.NOTIFICATIONS in self.states[to] \
            else DictChangeOperation.SET

        self.run_tracking_operation(DictChangeOperation(self.states[to], operation,
                                                        StatefulProcess2.NOTIFICATIONS, info))

    def setup_handlers(self):
        super(StatefulProcess2, self).setup_handlers()

        self.on(self.can_set_state, self.do_set_state)
        self.on(self.can_clear_state, self.do_clear_state)
        self.on(self.can_notify, self.do_notify)


# Parsing process supports error and move commands for text processing
class ParsingProcess2(StatefulProcess2):
    ERROR = 'error'
    PROCEED = 'proceed'
    BREAK = 'break'
    CONTINUE = 'continue'

    PARSED_LENGTH = 'parsed_length'
    TEXT = 'text'
    LAST_PARSED = 'last_parsed'

    def do_new(self):
        super(ParsingProcess2, self).do_new()
        self.query = Element.NEXT
        self._context_set(ParsingProcess2.PARSED_LENGTH, 0)
        self._context_set(ParsingProcess2.LAST_PARSED, '')

    def is_parsed(self):
        return self.query == Element.NEXT and not self.text

    def parse(self, *message, **context):
        result = super(ParsingProcess2, self).parse(*message, **context)

        return False if not self.is_parsed() else result[0], self.parsed_length, result[2]

    # Events #
    # Proceed: part of the Text was parsed
    def can_proceed(self, *message):
        if not message or not isinstance(message[0], dict):
            return False

        distance = message[0].get(ParsingProcess2.PROCEED)
        return is_number(distance) and len(self.context.get(ParsingProcess2.TEXT)) >= distance

    def do_proceed(self):
        proceed = self.message[0].pop(ParsingProcess2.PROCEED)
        last_parsed = self.context[ParsingProcess2.TEXT][0:proceed]

        self._context_set(ParsingProcess2.TEXT, self.context[ParsingProcess2.TEXT][proceed:])
        self._context_set(ParsingProcess2.PARSED_LENGTH, self.parsed_length + proceed)
        self._context_set(ParsingProcess2.LAST_PARSED, last_parsed)

    # Next, Break, Error or Continue
    def do_turn(self):
        new_query = self.message.pop(0)

        if new_query in Element.BACKWARD:
            del self.message[:]

        self.query = new_query

    def setup_handlers(self):
        super(ParsingProcess2, self).setup_handlers()

        self.on((Element.NEXT, ParsingProcess2.ERROR, ParsingProcess2.BREAK, ParsingProcess2.CONTINUE), self.do_turn)
        self.on(self.can_proceed, self.do_proceed)

    @property
    def text(self):
        return self.context.get(ParsingProcess2.TEXT, '')

    @property
    def parsed_length(self):
        return self.context.get(ParsingProcess2.PARSED_LENGTH, 0)

    @property
    def last_parsed(self):
        return self.context.get(ParsingProcess2.LAST_PARSED, '')


# Adding new backward commands
Element.add_backward_command(ParsingProcess2.ERROR)
Element.add_backward_command(ParsingProcess2.BREAK)
Element.add_backward_command(ParsingProcess2.CONTINUE)


# Parsing relation: should be passable in forward direction (otherwise returns Error)
class ParsingRelation(NextRelation2):
    def __init__(self, subj, obj, condition=None, owner=None):
        super(ParsingRelation, self).__init__(subj, obj, condition, owner)
        self.optional = False
        self.on(Talker.UNKNOWN, self.on_error)

    # Here we check condition against the parsing text
    def check_condition(self, message, context):
        return self.can_handle(self.condition, tupled(context.get(ParsingProcess2.TEXT), message), context)

    def next_handler(self, *message, **context):
        next_result = super(ParsingRelation, self).next_handler(*message, **context)
        rank = context.get(Handler.RANK)

        return ({ParsingProcess2.PROCEED: rank}, next_result) if rank else next_result

    def on_error(self, *message, **context):
        if not self.optional and len(message) > 1 and message[1] in Element.FORWARD:
            return ParsingProcess2.ERROR


# Selective notion: complex notion that can consist of one of its objects
# It tries all relations and uses the one without errors
class SelectiveNotion2(ComplexNotion2):
    CASES = 'cases'

    def __init__(self, name, owner=None):
        super(SelectiveNotion2, self).__init__(name, owner)

        self.on(self.can_retry, self.do_retry)
        self.on(self.can_finish, self.do_finish)

    # Searching for the longest case
    def get_best_cases(self, message, context):
        context[Handler.ANSWER] = Handler.RANK

        cases = []
        max_len = -1
        for rel in self.relations:
            result, length = rel(*message, **context)  # With the rank, please

            if result != ParsingProcess2.ERROR and length >= 0:
                max_len = max(length, max_len)
                cases.append((rel, length))

        return [case for case, length in cases if length == max_len]

    # Events #
    def can_go_forward(self, *message, **context):
        if not context.get(StatefulProcess2.STATE):  # If we've been here before we need to try something different
            return super(SelectiveNotion2, self).can_go_forward(*message, **context)

    def do_forward(self, *message, **context):
        reply = super(SelectiveNotion2, self).do_forward(*message, **context)

        if is_list(reply):
            cases = self.get_best_cases(message, context)

            if cases:
                case = cases.pop(0)

                if not cases:
                    reply = case
                else:
                    reply = (StackingContextProcess2.PUSH_CONTEXT,  # Keep the context if re-try will needed
                             {StatefulProcess2.SET_STATE: {SelectiveNotion2.CASES: cases}},  # Store what to try next
                             case,  # Try first case
                             self)  # And come back again
            else:
                return ParsingProcess2.ERROR

        return reply

    def can_retry(self, *message, **context):
        return context.get(StatefulProcess2.STATE) and has_first(message, ParsingProcess2.ERROR)

    def do_retry(self, *message, **context):
        cases = context[StatefulProcess2.STATE][SelectiveNotion2.CASES]

        if cases:
            case = cases.pop(0)  # Try another case, if any

            # Pop context and update state, then try another case and come back here
            return [StackingContextProcess2.POP_CONTEXT,  # Roll back to the initial context
                    {StatefulProcess2.SET_STATE: {SelectiveNotion2.CASES: cases}},  # Update cases
                    StackingContextProcess2.PUSH_CONTEXT,  # Save updated context
                    Element.NEXT,  # Go forward again
                    case,  # Try another case
                    self]  # Come back
        else:
            return self.do_finish(*message, **context)  # No more opportunities

    def can_finish(self, *message, **context):
        return context.get(StatefulProcess2.STATE) and self.is_forward(message)

    def do_finish(self, *message, **context):
        return [StatefulProcess2.FORGET_CONTEXT, StatefulProcess2.CLEAR_STATE]


# Loop relation specifies counts of the related object.
# Possible conditions are: numeric (n; m..n; m..; ..n), wildcards (*, ?, +), true (infinite loop), and iterator function
class LoopRelation2(NextRelation2):
    ITERATION = 'i'
    WILDCARDS = ('*', '?', '+')
    INFINITY = float('inf')

    def __init__(self, subj, obj, condition=None, owner=None):
        super(LoopRelation2, self).__init__(subj, obj, condition, owner)

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
        if not self.condition:  # Here we check only the simplest case
            return False

    # Is a wildcard loop
    def is_wildcard(self):
        return self.condition in LoopRelation2.WILDCARDS

    # Is a numeric loop
    def is_numeric(self):
        if is_number(self.condition):
            return True
        elif is_list(self.condition) and len(self.condition) == 2:
            return (self.condition[0] is None or is_number(self.condition[0])) \
                and (self.condition[1] is None or is_number(self.condition[1]))

    # Infinite loop
    def is_infinite(self):
        return self.condition is True

    # Custom loop: not empty callable condition
    def is_custom(self):
        return self.condition and callable(self.condition)

    # Flexible condition has no finite bound, lower or higher
    def is_flexible(self):
        return (self.is_numeric() and is_list(self.condition)) or self.is_wildcard()

    # Checking for the condition type
    def is_general(self):
        return self.is_numeric() or self.is_wildcard() or self.is_infinite()

    # Checking is we are in loop now
    def is_looping(self, context):
        return LoopRelation2.ITERATION in context.get(StatefulProcess2.STATE)

    # Get the limits of the loop
    def get_bounds(self):
        lower, upper = 0, LoopRelation2.INFINITY

        if self.is_numeric():
            if is_number(self.condition):
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
        reply = [{StatefulProcess2.SET_STATE: {LoopRelation2.ITERATION: i}}]

        if self.is_flexible():
            if i != 1:
                reply.insert(0, StatefulProcess2.FORGET_CONTEXT)  # Forget the past
            reply += [StackingContextProcess2.PUSH_CONTEXT]  # Save state if needed

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
        i = context.get(StatefulProcess2.STATE).get(LoopRelation2.ITERATION)

        if i < self.get_bounds()[1]:
            return self.get_next_iteration_reply(i + 1)
        else:
            reply = []

            if self.is_flexible():
                reply += [StatefulProcess2.FORGET_CONTEXT]

            return reply + [StatefulProcess2.CLEAR_STATE]

    def can_error_general(self, *message, **context):
        return has_first(message, ParsingProcess2.ERROR) and self.is_looping(context) and self.is_general()

    def do_error_general(self, *message, **context):
        i = context.get(StatefulProcess2.STATE).get(LoopRelation2.ITERATION)
        lower, upper = self.get_bounds()

        reply = []

        if self.is_flexible():
            # Roll back to the previous good result
            if lower < i <= upper:
                reply += [Element.NEXT, StatefulProcess2.POP_CONTEXT]
            else:
                reply += [StatefulProcess2.FORGET_CONTEXT]

        return reply + [StatefulProcess2.CLEAR_STATE]
    
    # Custom loop
    def can_loop_custom(self, *message, **context):
        return self.is_forward(message) and self.is_custom()

    def do_loop_custom(self, *message, **context):
        i = self.var_call_result(self.condition, message, context)

        if i:
            return {StatefulProcess2.SET_STATE: {LoopRelation2.ITERATION: i}}, self.object, self
        else:
            return False if not self.is_looping(context) else StatefulProcess2.CLEAR_STATE,

    def can_error_custom(self, *message, **context):
        return has_first(message, ParsingProcess2.ERROR) and self.is_custom()

    def do_error_custom(self, *message, **context):
        return StatefulProcess2.CLEAR_STATE,
    
    # Common handling
    def can_break(self, *message, **context):
        return has_first(message, ParsingProcess2.BREAK) and self.is_looping(context)

    def do_break(self, *message, **context):
        reply = [Element.NEXT]

        if self.is_flexible():
            reply += [StatefulProcess2.FORGET_CONTEXT]

        return reply + [StatefulProcess2.CLEAR_STATE]

    def can_continue(self, *message, **context):
        return has_first(message, ParsingProcess2.CONTINUE) and self.is_looping(context)

    def do_continue(self, *message, **context):
        return [Element.NEXT] + self.do_loop_general(*message, **context)


# Graph is a holder of Notions and Relation, it allows easy search and processing of them
class Graph(Element):
    def __init__(self, root=None, owner=None):
        super(Graph, self).__init__(owner)

        self._root = None
        self._notions = []
        self._relations = []

        self.on(self.add_prefix(Element.OWNER, Element.SET_PREFIX), self.do_element)
        self.on_forward(self.do_forward)

        if root:
            if is_string(root):
                root = ComplexNotion2(root, self)

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

                if Relation2.SUBJECT in criteria:
                    req.append(criteria[Relation2.SUBJECT])
                    rel.append(relation.subject)

                if Relation2.OBJECT in criteria:
                    req.append(criteria[Relation2.OBJECT])
                    rel.append(relation.object)

                return len(rel) if rel == req and rel else -1

    def relations(self, criteria=None):
        return self.search_elements(self._relations, self.get_relation_search_rank, criteria) if criteria else \
            tuple(self._relations)

    def relation(self, criteria=None):
        found = self.relations(criteria)

        return found[0] if found else None

    def do_element(self, *message, **context):
        element = context.get(Handler.SENDER)

        if isinstance(element, Notion2) or isinstance(element, Graph):
            collection = self._notions
        elif isinstance(element, Relation2):
            collection = self._relations
        else:
            return False

        if context[Element.OLD_VALUE] == self and element in collection:
            collection.remove(element)

            if element == self.root:
                self.root = None

            return True

        elif context[Element.NEW_VALUE] == self and element not in collection:
            collection.append(element)
            return True

    def do_forward(self, *message, **context):
        return self.root

    @property
    def root(self):
        return self._root

    @root.setter
    def root(self, value):
        if (self._root == value) or (value and (value.owner != self or not isinstance(value, Notion2))):
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


# Graph builder helps to create graph structures
class GraphBuilder(object):
    def __init__(self, graph=None):
        if is_string(graph):
            graph = Graph(graph)

        self.graph = graph
        self.current = graph.root if graph else None

    def attach(self, new):
        if isinstance(new, Notion2):
            if isinstance(self.current, Relation2) and not self.current.object:
                self.current.object = new

        elif isinstance(new, Relation2):
            if isinstance(self.current, Notion2) and not new.subject:
                new.subject = self.current

                if isinstance(self.current, ComplexNotion2):
                    return self  # Do not update last, just connect

        self.current = new

        return self

    def complex(self, name):
        return self.attach(ComplexNotion2(name, self.graph))

    def notion(self, name):
        return self.attach(Notion2(name, self.graph))

    def next(self, condition=None, obj=None):
        return self.attach(NextRelation2(self.current, obj, condition, self.graph))

    def parse(self, condition, obj=None):
        return self.attach(ParsingRelation(self.current, obj, condition, self.graph))

    def loop(self, condition, obj=None):
        return self.attach(LoopRelation2(self.current, obj, condition, self.graph))

    def select(self, name):
        return self.attach(SelectiveNotion2(name, self.graph))

    def act(self, name, action):
        return self.attach(ActionNotion2(name, action, self.graph))

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


### Borderline between new and old ###

# Notion is an abstract with name
class Notion(Abstract):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        if self.name:
            return '"%s"' % self.name

    def __repr__(self):
        return self.__str__()


# Relation is a connection between one or more abstracts: subject -> object
class Relation(Abstract):
    def __init__(self, subject, object):
        self._object = self._subject = None

        self.subject = subject
        self.object = object

    def connect(self, value, target):
        old_value = getattr(self, target)

        if old_value == value:
            return

        # Disconnect old one
        if isinstance(old_value, Abstract):
            old_value.parse('un_relate', **{'from': self})

        setattr(self, '_' + target, value)

        # Connect new one
        if isinstance(value, Abstract):
            value.parse('relate', **{'from': self})

    @property
    def subject(self):
        return self._subject

    @subject.setter
    def subject(self, value):
        self.connect(value, 'subject')

    @property
    def object(self):
        return self._object

    @object.setter
    def object(self, value):
        self.connect(value, 'object')

    def __str__(self):
        return '<%s - %s>' % (self.subject, self.object)

    def __repr__(self):
        return self.__str__()


# Action is a simple function/value keeper; it returns either function call result or value itself
# If copy is true a copy of result will be returned via copy() call
class Action(Abstract):
    def __init__(self, action, copy=False):
        self.action = action
        self.copy = copy

    def parse(self, *message, **context):
        result = self.action if not callable(self.action) else self.action(self, *message, **context)

        if self.copy and hasattr(result, 'copy'):
            result = result.copy()

        return result


# Action notion is a notion that calls for Action when next is queried
class ActionNotion(Notion, Action):
    def __init__(self, name, action, copy=False):
        Notion.__init__(self, name)
        Action.__init__(self, action, copy)

    def parse(self, *message, **context):
        if has_first(message, 'next'):
            return Action.parse(self, *message, **context)


# Complex notion is a notion that relates with other notions (objects)
class ComplexNotion(Notion):
    def __init__(self, name, relation=None):
        super(ComplexNotion, self).__init__(name)
        self._relations = []

        self.relate(relation)

    def relate(self, relation):
        if isinstance(relation, Relation) and relation.subject == self \
                and (relation not in self._relations):
            self._relations.append(relation)

    def un_relate(self, relation):
        if relation in self._relations:
            self._relations.remove(relation)

    def parse(self, *message, **context):
        reply = super(ComplexNotion, self).parse(*message, **context)

        if not reply:
            if message:
                # This abstract knows only Relate and Un relate messages
                if message[0] == 'relate':
                    self.relate(context.get('from'))
                    return True

                elif message[0] == 'un_relate':
                    self.un_relate(context.get('from'))
                    return True

                elif message[0] == 'next':
                     # Returning copy of relation list by default, not using a list if there is only one
                    if self._relations:
                        return self._relations[0] if len(self._relations) == 1 else list(self._relations)

    @property
    def relations(self):
        return list(self._relations)


# Next relation is just a simple sequence relation
class NextRelation(Relation):
    def parse(self, *message, **context):
        if has_first(message, 'next'):
            return self.object


# Action relation is a relation that uses Action when asked
class ActionRelation(NextRelation, Action):
    def __init__(self, subject, object, action, copy=False):
        NextRelation.__init__(self, subject, object)
        Action.__init__(self, action, copy)

    def parse(self, *message, **context):
        own_reply = super(ActionRelation, self).parse(*message, **context)
        act_reply = Action.parse(self, *message, **context)

        if own_reply and act_reply:
            return [act_reply, own_reply]
        else:
            return act_reply or own_reply


# Selective notion: complex notion that can consist of one of its objects
# It tries all relations and uses the one without errors
class SelectiveNotion(ComplexNotion):
    def parse(self, *message, **context):
        if context.get('state') and message:
            if context.get('errors'):
                cases = context['state']['cases']

                if cases and message[0] == 'next':
                    case = cases.pop(0)  # Try another case, if any

                    # Pop context and update state, then try another case and come back here
                    return ['pop_context', 'forget_context', {'set_state': {'cases': cases}}, 'push_context',
                            case, self]
                else:
                    return ['forget_context', 'clear_state', 'error']  # No more opportunities
            else:
                return ['forget_context', 'clear_state']  # Everything is ok, forget the past

        reply = super(SelectiveNotion, self).parse(*message, **context)

        if not isinstance(reply, list) or (not message or message[0] != 'next'):
            return reply

        # Searching for the longest case
        cases = {}
        max_key, max_len = None, 0
        for r in reply:
            length = r.parse('check', **context)

            if is_number(length):
                if length > max_len:
                    if max_key:
                        del cases[max_key]

                    max_key, max_len = r, length
                else:
                    continue
            else:
                length = None

            cases[r] = length

        if not cases:
            return 'error'  # No ways

        filtered = []
        for r in reply:
            if r in cases.keys():
                filtered.append(r)

        case = filtered.pop(0)

        if not filtered and cases[case] is not None:
            return case  # No need to try, just go
        else:
            return ['push_context', {'set_state': {'cases': filtered}},
                    case, self]  # Try first case


# Conditional relation is a condition to go further if text starts with sequence
# Optional flag defines should it return error if condition does not match or not
class ConditionalRelation(Relation):
    REGEX_TYPE_NAME = 'SRE_Pattern'

    def __init__(self, subject, object, checker, mode=None):
        super(ConditionalRelation, self).__init__(subject, object)
        self.checker = checker
        self.mode = mode

    # Return result and length of check
    def check(self, *message, **context):
        if self.checker:
            length = result = None

            if callable(self.checker):
                result, length = self.checker(self, *message, **context)

            elif 'text' in context:
                if type(self.checker).__name__ == ConditionalRelation.REGEX_TYPE_NAME:
                    m = self.checker.match(context['text'])

                    if m:
                        length = m.end()
                        result = m.group()
                    else:
                        length = 0

                else:
                    length = len(self.checker) if context['text'].startswith(self.checker) else 0

                    if length > 0:
                        result = self.checker

            return result, length

        else:
            return None, None

    def parse(self, *message, **context):
        result, length = self.check(*message, **context)

        if message:
            if message[0] == 'check':
                return length
            if message[0] != 'next':
                return

        if result:
            reply = {'move': length} if self.mode != 'test' else {}  # In test mode we do not consume input

            if self.object:  # Leave a message for the object to know what worked
                reply['update_context'] = {'passed_condition': result}

            return [reply, self.object]

        elif self.checker:
            return 'error' if self.mode is None else None


# Loop relation is a cycle that repeats object for specified or infinite number of times util error
class LoopRelation(Relation):
    def __init__(self, subject, object, n='*'):
        super(LoopRelation, self).__init__(subject, object)

        if isinstance(n, tuple):
            self.m = n[0]
            self.n = n[1] if len(n) > 1 else None
        else:
            self.n = n

    def is_ranged(self):
        return hasattr(self, 'm')

    def has_finite_n(self):
        return self.n is not True and (is_number(self.n) or self.n == '?')

    def has_rollback(self):
        return self.n == '*' or self.n == '+' or self.is_ranged()

    def parse(self, *message, **context):
        if (not has_first(message, 'next') and not has_first(message, 'break') and not has_first(message, 'continue')) \
                or (not self.n and not self.is_ranged()):
            return None

        repeat = True
        error = restore = False
        reply = []

        if callable(self.n):
            repeat = self.n(self, *message, **context)

            if repeat:
                iteration = repeat  # Storing for the future calls
                reply.append({'set_state': {'n': iteration}})

        elif context['state']:  # May be was here before
            iteration = context['state'].get('n')

            if context.get('errors') and self.n is not True:
                repeat = False

                if (self.n == '*' or self.n == '?') or (self.n == '+' and iteration > 1):
                    restore = True  # Number of iterations is arbitrary if no restriction, so we need to restore
                                    # last good context

                elif (self.n == '+' and iteration <= 1) or not self.is_ranged():
                    error = True  # '+' means more than 1 iterations and if there is no range we have a fixed count

                elif self.is_ranged():
                    if self.m is not None:
                        if iteration <= self.m:  # Less than lower limit
                            error = True
                        else:
                            restore = True

                    elif iteration < self.n:
                        restore = True
            else:
                if message[0] != 'next':
                    reply.append('next')

                if message[0] == 'break':  # Consider work done
                    repeat = False

                else:
                    if self.has_finite_n() and (self.n == '?' or iteration >= self.n):
                        repeat = False  # No more iterations

                    if repeat and self.has_rollback():
                        reply += ['forget_context', 'push_context']  # Prepare for the new iteration
                                                                     # apply last changes and start new tracking
                if repeat:
                    iteration += 1
                    reply.append({'set_state': {'n': iteration}})
        else:
            # A very first iteration - init the variable and store the context
            reply += [{'set_state': {'n': 1}}, 'push_context']

        if repeat:
            reply += [self.object, self]  # We need to come back after the object to think should we repeat or not
        else:
            if restore:
                reply.append('pop_context')  # If we need to restore we need to repair context

            if not callable(self.n):
                reply.append('forget_context')  # Nothing to forget in case of custom function

            reply.append('clear_state')  # No more repeats, clearing

            if error:
                reply.append('error')

        return reply


# Base process class, does parsing using list of event-condition-action items, moving from one abstract to another
class Process(Abstract):
    def __init__(self):
        super(Process, self).__init__()
        self.result = None

        self._queue = []
        self._callback = None

    # Ask callback regarding event happening
    def callback_event(self, info):
        if self.current != self._callback and self._callback:  # We do not need infinite asking loops
            reply = self._callback.parse(info, **{'from': self, 'message': self.message, 'context': self.context})

            if reply:  # No need to store empty replies
                self._to_queue(False, current=self._callback, reply=reply)

                return True

        return False

    def _run_event_func(self, event):
        # We need to check should we pass self to event trigger or not, no need to do if for lambdas
        return event(self) if not hasattr(event, '__self__') else event()

    # Run event if conditions are appropriate
    def run_event(self, event):
        # Event [1] is a condition checker
        can_run = self._run_event_func(event[1]) if event[1] else True
        result = None

        if can_run:
            # We need to check can we call event or not
            if not self.callback_event(event[0] + '_pre'):
                result = self._run_event_func(event[2])

                # Now we do a post-event call
                self.callback_event(event[0] + '_post')

        return can_run, result

    # Queue processing
    def _queueing_properties(self):
        return {'message': [], 'context': {}, 'current': None, 'reply': None}

    def _to_queue(self, update, **update_dict):
        top = dict([(p, getattr(self, p)) for p in self._queueing_properties().keys()])
        top.update(update_dict)

        if not update:
            self._queue.append(top)
        else:
            self._queue[-1].update(top)

    # Get the field from queue top (or lower), if no field or so default is returned
    def _queue_top_get(self, field, offset=-1):
        if self._queue and field in self._queue[offset]:
            return self._queue[offset].get(field)

        return self._queueing_properties().get(field)

    # Get command string from reply or message, remove it if pull is true
    def get_command(self, command, pull=False):
        data = None

        if isinstance(self.reply, dict) and command in self.reply:
            data = self.reply[command]

            if pull:
                del self.reply[command]

        elif command == self.reply:
            data = command

            if pull:
                self._to_queue(True, reply=None)

        elif command in self.message:
            data = command

            if pull:
                self.message.remove(command)

        elif self.message and isinstance(self.message[0], dict) and command in self.message[0]:
            data = self.message[0][command]

            if pull:
                del self.message[0][command]

        return data

    # Events
    def get_events(self):
        return [('new',  # Name
                 lambda self: self.get_command('new', True),  # Run condition
                 self.event_new  # Handler if condition is ok
                 ),
                ('pull_message',
                 lambda self: not self.reply and self.message and
                 isinstance(self.message[0], Abstract),
                 self.event_pull_message
                 ),
                ('stop',
                 lambda self: self.get_command('stop', True),
                 self.event_stop
                 ),
                ('skip',
                 lambda self: self.get_command('skip', True),
                 self.event_skip
                 ),
                ('do_queue_pop',
                 lambda self: not self.reply and len(self._queue) > 1,
                 self.event_pop
                 ),
                ('ok',
                 lambda self: not self.reply and len(self._queue) <= 1,
                 self.event_ok
                 ),
                ('query',
                 lambda self: isinstance(self.reply, Abstract),
                 self.event_query
                 ),
                ('queue_push',
                 lambda self: isinstance(self.reply, list) and len(self.reply) > 0,
                 self.event_push
                 )]

    def event_start(self):
        return None

    def event_new(self):
        if len(self._queue) > 1:
            self._queue_top_get('context', -2).clear()  # Old context should be gone

        del self._queue[:-1]  # Removing previous elements from queue

    def event_pull_message(self):
        self._to_queue(True, current=self.message[0], reply=self.message[0])
        del self.message[0]

    def event_stop(self):
        return 'stop'    # Just stop at once where we are if callback does not care

    def event_skip(self):
        del self._queue[-2:]  # Removing current and previous elements from queue

    def event_pop(self):
        self._queue.pop()  # Let's move on

    def event_push(self):
        # We update the queue if this is a last item
        self._to_queue(len(self.reply) == 1, reply=self.reply.pop(0))  # First one is ready to be processed

    def event_ok(self):
        return 'ok'  # We're done if nothing in the queue

    def get_query(self):
        return 'next'

    def event_query(self):
        self._to_queue(True, current=self.reply,
                       reply=self.reply.parse(self.get_query(), **self.context))

    def event_unknown(self):
        return 'unknown'

    def event_result(self):
        return self.result

    def parse(self, *message, **context):
        if message or context:
            # If there is only a last fake item in queue we can just update it
            update = len(self._queue) == 1 and not self.message and not self.reply
            self._to_queue(update,
                           message=list(message) if message else self.message,
                           context=context or self.context,
                           current=None, reply=None)

        events = self.get_events()
        self.result = self.run_event(('start', None, self.event_start))[1]

        while True:
            event_found = False

            for event in events:
                result = self.run_event(event)
                if result[0]:
                    event_found = True

                    if result[1]:
                        self.result = result[1]
                        break

            # If we are here we've entered an uncharted territory
            if not event_found:
                self.result = self.run_event(('unknown', None, self.event_unknown))[1]

            # If there was a reply we need to ask callback before stopping
            if self.result and self.run_event(('result', None, self.event_result))[1]:
                break

        return self.result

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, value):
        if not value or (value and callable(value.parse)) and self._callback != value:
            self._callback = value

    @property
    def message(self):
        return self._queue_top_get('message')

    @property
    def context(self):
        return self._queue_top_get('context')

    @property
    def current(self):
        return self._queue_top_get('current')

    @property
    def reply(self):
        return self._queue_top_get('reply')


# Shared context process supports context modification commands
class SharedContextProcess(Process):
    def get_events(self):
        return super(SharedContextProcess, self).get_events() + \
            [('add_context',
              lambda self: isinstance(self.get_command('add_context'), dict),
              self.event_add_context
              ),
             ('update_context',
              lambda self: isinstance(self.get_command('update_context'), dict),
              self.event_update_context
              ),
             ('delete_context',
              lambda self: self.get_command('delete_context'),
              self.event_delete_context
              )]

    def _context_add(self, key, value):
        self.context[key] = value

    def event_add_context(self):
        command = self.get_command('add_context', True)
        for k, v in command.items():
            if not k in self.context:
                self._context_add(k, v)

    def _context_set(self, key, value):
        self.context[key] = value

    def event_update_context(self):
        command = self.get_command('update_context', True)
        for k, v in command.items():
            self._context_set(k, v)

    def _context_delete(self, key):
        del self.context[key]

    def event_delete_context(self):
        command = self.get_command('delete_context', True)

        if isinstance(command, list):
            for k in command:
                if k in self.context:
                    self._context_delete(k)

        elif command in self.context:
            self._context_delete(command)


# Process that can save and restore context
# Useful for cases when process needs to try various paths in the graph
class StackingContextProcess(SharedContextProcess):
    def _queueing_properties(self):
        p = super(StackingContextProcess, self)._queueing_properties()
        p.update({'context_stack': []})

        return p

    def get_events(self):
        return super(StackingContextProcess, self).get_events() +\
            [('push_context',
              lambda self: self.get_command('push_context', True),
              self.event_push_context
              ),
             ('pop_context',
              lambda self: self.get_command('pop_context', True) and self.is_tracking(),
              self.event_pop_context
              ),
             ('forget_context',
              lambda self: self.get_command('forget_context', True) and self.is_tracking(),
              self.event_forget_context
              )]

    def event_new(self):
        super(StackingContextProcess, self).event_new()

        if self.context_stack:
            self._to_queue(True, context_stack=self._queueing_properties()['context_stack'])  # Clearing stack if new

    def is_tracking(self):
        return self.context_stack

    def _context_add(self, key, value):
        if not self.is_tracking():
            super(StackingContextProcess, self)._context_add(key, value)
        else:
            self.context_stack[-1].add(DictChangeOperation(self.context, DictChangeOperation.ADD, key, value))

    def _context_set(self, key, value):
        if not self.is_tracking():
            super(StackingContextProcess, self)._context_set(key, value)
        else:
            self.context_stack[-1].add(DictChangeOperation(self.context, DictChangeOperation.SET, key, value))

    def _context_delete(self, key):
        if not self.is_tracking():
            super(StackingContextProcess, self)._context_delete(key)
        else:
            self.context_stack[-1].add(DictChangeOperation(self.context, DictChangeOperation.DELETE, key))

    def event_push_context(self):
        self.context_stack.append(DictChangeGroup())

    def event_pop_context(self):
        self.context_stack[-1].undo()

    def event_forget_context(self):
        self.context_stack.pop()

    @property
    def context_stack(self):
        return self._queue_top_get('context_stack')


# Process with support of abstract states and notifications between them
# Useful to preserve private a state of an abstract
class StatefulProcess(StackingContextProcess):
    def _queueing_properties(self):
        p = super(StatefulProcess, self)._queueing_properties()
        p.update({'states': {}})

        return p

    def _add_current_state(self):
        # Self.reply is a new next, this is how the Process made
        self.context['state'] = self.states.get(self.reply) if self.reply in self.states else {}

    def _del_current_state(self):
        del self.context['state']

    def get_events(self):
        return super(StatefulProcess, self).get_events() + \
            [('set_state',
              lambda self: isinstance(self.get_command('set_state'), dict) and self.current,
              self.event_set_state
              ),
             ('clear_state',
              lambda self: self.current and self.get_command('clear_state', True),
              self.event_clear_state
              ),
             ('notify',
              lambda self: isinstance(self.get_command('notify'), dict) and
              isinstance(self.get_command('notify').get('to'), Abstract) and
              'data' in self.get_command('notify'),
              self.event_notify
              )]

    def event_new(self):
        super(StatefulProcess, self).event_new()

        if self.states:
            self._to_queue(True,  states=self._queueing_properties()['states'])  # Clearing states if new

    def event_query(self):
        self._add_current_state()
        # Now the state contains the right state
        super(StatefulProcess, self).event_query()
        self._del_current_state()

    def _set_state(self, abstract, state):
        if abstract in self.states:
            self.states[abstract].update(state)
        else:
            self.states[abstract] = state

    def event_set_state(self):
        self._set_state(self.current, self.get_command('set_state', True))

    def event_clear_state(self):
        if self.current in self.states:
            del self.states[self.current]

    def event_notify(self):
        msg = self.get_command('notify', True)
        recipient = msg['to']

        if not recipient in self.states:
            self._set_state(recipient, {})

        if not 'notifications' in self.states[recipient]:
            self.states[recipient]['notifications'] = {}

        self.states[recipient]['notifications'].update(msg['data'])

    @property
    def states(self):
        return self._queue_top_get('states')


# Parsing process supports error and move commands for text processing
class ParsingProcess(StatefulProcess):
    def get_query(self):
        q = self.states[self].get('query') if self in self.states else None
        return q or super(ParsingProcess, self).get_query()

    def get_events(self):
        return super(ParsingProcess, self).get_events() + \
            [('error',
              lambda self: self.get_command('error'),
              self.event_error
              ),
             ('move',
              lambda self: self.get_command('move') and 'text' in self.context,
              self.event_move
              ),
             ('break',
              lambda self: self.query == 'next' and self.get_command('break', True),
              self.event_break
              ),
             ('next',
              lambda self: self.query != 'next' and self.get_command('next', True),
              self.event_next
              ),
             ('continue',
              lambda self: self.query == 'next' and self.get_command('continue', True),
              self.event_continue
              )]

    def event_start(self):
        super(ParsingProcess, self).event_start()

        if not 'errors' in self.context:  # Add errors if they are not in context
            self._context_add('errors', {})

        if not 'parsed_length' in self.context:
            self._context_add('parsed_length', 0)

    def event_new(self):
        super(ParsingProcess, self).event_new()

        self._context_set('parsed_length', 0)

    def event_result(self):
        # If there are errors - result is always error
        if self.errors:
            self.result = 'error'

        # If not parsed text left this is an error
        if self.context.get('text') and not self.errors:
            self.errors[self] = 'underflow'
            self.result = 'error'

        return super(ParsingProcess, self).event_result()

    def event_error(self):
        error = self.get_command('error', True)
        key = self.current or self

        # Error is not just a value in context but a dict itself, so in case of tracking we need to be able to
        # revert its internal changes too
        if not self.is_tracking():
            self.errors[key] = error
        else:
            self.context_stack[-1].add(DictChangeOperation(self.errors, DictChangeOperation.SET, key, error))

    def event_move(self):
        move = self.get_command('move', True)

        self._context_set('text', self.context['text'][move:])
        self._context_set('parsed_length', self.parsed_length + move)

    def event_break(self):
        self._set_state(self, {'query': 'break'})
        self.event_pop()

    def event_next(self):
        self._set_state(self, {'query': None})

    def event_continue(self):
        self._set_state(self, {'query': 'continue'})
        self.event_pop()

    @property
    def errors(self):
        return self.context['errors'] if 'errors' in self.context else {}

    @property
    def parsed_length(self):
        return self.context['parsed_length'] if 'parsed_length' in self.context else 0

    @property
    def query(self):
        return self.get_query()
