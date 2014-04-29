# Universal Translator base classes
# (c) krvss 2011-2014

from inspect import getargspec
from operator import attrgetter

from utils import *

# TODO remove
logging = False
import time
def set_logging(value):
    global logging
    logging = value


class Abstract(object):
    """
    Base abstract class for all communicable objects
    """
    def __call__(self, *message, **context):
        raise NotImplementedError('Method not implemented')


class Access(Abstract):
    """
    Access provides abstract-like access to any object
    """
    CALL = 'call'
    ABSTRACT = 'abstract'
    FUNCTION = 'function'
    VALUE = 'value'
    OTHER = 'other'

    CACHE_ATTR = '__access__'
    CACHEABLE = (CALL, FUNCTION)

    def __init__(self, value):
        self._value = value
        self._mode, self._spec = self.OTHER, self.OTHER
        self._call = self.call_direct

        self.setup()

    def __eq__(self, other):
        if isinstance(other, Access):
            return other._value == self._value

        return other == self._value

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return '%s, %s: %s' % (self._mode, self._spec, self._value)

    def setup(self):
        """
        Init type information
        """
        if isinstance(self._value, Abstract):
            self._mode, self._spec = self.CALL, self.ABSTRACT

        elif callable(self._value):
            self._mode, self._spec = self.FUNCTION, getargspec(self._value)

            if self._spec.varargs and not self._spec.keywords:
                self._call = self.call_args

            elif self._spec.keywords and not self._spec.varargs:
                self._call = self.call_kwargs

            elif self._spec.varargs and self._spec.keywords:
                return  # default call_direct is good here

            elif not self._spec.varargs and not self._spec.keywords and not self._spec.args:
                self._call = self.call_noargs

            elif self._spec.args:
                self._defaults_len = len(self._spec.defaults) - 1 if self._spec.defaults else -1
                self._reversed_args = list(reversed(self._spec.args))

                self._call = self.call_general

        else:
            self._mode = self.VALUE
            self._call = self.call_value

    def __call__(self, *message, **context):
        return self._call(message, context)

    def call_direct(self, message, context):
        return self._value(*message, **context)

    def call_args(self, message, context):
        return self._value(*message)

    def call_kwargs(self, message, context):
        return self._value(**context)

    def call_noargs(self, message, context):
        return self._value()

    def call_general(self, message, context):
        i, args = self._defaults_len, {}
        for arg in self._reversed_args:
            if arg != 'self':
                args[arg] = context[arg] if arg in context else self._spec.defaults[i] if i >= 0 else None
                i -= 1

        return self._value(**args)

    def call_value(self, message, context):
        return self._value

    value = property(attrgetter('_value'))
    mode = property(attrgetter('_mode'))
    spec = property(attrgetter('_spec'))

    @staticmethod
    def get_access(obj, cache=False):
        if hasattr(obj, Access.CACHE_ATTR):
            access = getattr(obj, Access.CACHE_ATTR)
        else:
            access = Access(obj)

            if cache and access._mode in Access.CACHEABLE:
                setattr(obj, Access.CACHE_ATTR, access)

        return access


class Condition(Access):
    """
    Condition is an Access that checks the possibility of the access according to the message and context
    """
    NUMBER = 'number'
    LIST = 'list'
    DICT = 'dict'
    STRING = 'string'
    REGEX = 'regex'
    BOOLEAN = 'bool'

    NO_CHECK = -1, None

    def __init__(self, value, ignore_case=False):
        self._ignore_case = ignore_case
        self.check, self._conditions = self.check_compare, tuple([self])
        super(Condition, self).__init__(value)

    def setup(self):
        """
        Setting additional mode info
        """
        super(Condition, self).setup()

        if self._mode == self.FUNCTION:
            self.check = self.check_function

        elif is_number(self._value):
            self._spec = self.NUMBER

        elif is_list(self._value):
            self._spec, self.check = self.LIST, self.check_list
            self._conditions = tuple([Condition(c, self._ignore_case) for c in self._value])

        elif is_string(self._value):
            self._spec, self.check = self.STRING, self.check_string

            if self._ignore_case:
                self._value = self._value.upper()

        elif is_regex(self._value):
            self._spec, self.check = self.REGEX, self.check_regex

        elif isinstance(self._value, dict):
            self._spec = self.DICT

        elif self._value is True or self._value is False:
            self._spec, self.check = self.BOOLEAN, self.check_boolean

    def check(self, message, context):
        raise TypeError('Undefined check for %s' % self.__str__())

    def check_function(self, message, context):
        check = self._call(message, context)

        # Do we work with (rank, check) format?
        if get_len(check) == 2:
            return check
        elif check:
            return 0 if check is True else check, check
        else:
            return self.NO_CHECK

    def check_regex(self, message, context):
        check = self._value.match(message[0]) if message else None

        if check:
            rank = check.end() - check.start()  # Match length is the rank
            check = check.group(0)
        else:
            rank = - 1

        return rank, check

    def check_string(self, message, context):
        try:
            message0 = message[0][:len(self._value)]

            if self._ignore_case:
                message0 = message0.upper()

            if message0 == self._value:
                return len(self._value), self._value

        except (TypeError, IndexError):
            pass

        return self.NO_CHECK

    def check_boolean(self, message, context):
        if message and message[0] is self._value:
            return 0, self._value
        else:
            return self.NO_CHECK

    def check_compare(self, message, context):
        if has_first(message, self._value):
            return max(get_len(self._value), 0), self._value
        else:
            return self.NO_CHECK

    def check_list(self, message, context):
        rank, check = self.NO_CHECK

        for condition in self._conditions:
            c_rank, c_check = condition.check(message, context)

            if c_rank > rank:
                rank, check = c_rank, c_check

        return rank, check

    @property
    def list(self):
        return self._conditions


# Condition that is always satisfied
class TrueCondition(Condition):
    def __init__(self):
        super(TrueCondition, self).__init__(id(self))
        self.check = lambda message, context: (0, True)


TRUE_CONDITION = TrueCondition()


class Event(Access):
    """
    Event is an Access that allows to attach Pre and Post custom functions before and after access
    """
    RESULT = 'result'

    def __init__(self, value):
        super(Event, self).__init__(value)
        self.pre_event, self.post_event = None, None

    def run(self, message, context):
        if self.pre_event:
            pre_result = self.pre_event.run(message, context)

            if pre_result[0] is not None:
                return pre_result

        result = self._call(message, context)

        if self.post_event:
            context[self.RESULT] = result
            post_result = self.post_event.run(message, context)

            if post_result[0] is not None:
                return post_result

        return result, self._value

    @property
    def pre(self):
        return self.pre_event.value if self.pre_event else None

    @pre.setter
    def pre(self, value):
        self.pre_event = Event(value) if value is not None else None

    @property
    def post(self):
        return self.post_event.value if self.post_event else None

    @post.setter
    def post(self, value):
        self.post_event = Event(value) if value is not None else None


class Handler(Abstract):
    """
    Handler is a class for the routing of messages to processing functions (events) basing on specified conditions
    """
    ANSWER = 'answer'
    SENDER = 'sender'
    CONDITION = 'condition'
    EVENT = 'event'
    RANK = 'rank'

    NO_HANDLE = (False, -1, None)

    def __init__(self):
        Access.get_access(self, True)

        self.events = []
        self.unknown_event = None

    def on_access(self, condition_access, event_access):
        """
        Adding the accesses
        """
        if (condition_access, event_access) not in self.events:
            self.events.append((condition_access, event_access))

    def on(self, condition, event):
        """
        Adding the condition - event pair
        """
        self.on_access(Condition(condition), Event(event))

    def on_any(self, event):
        """
        Adding the event, without condition it will trigger on any message
        """
        self.on_access(TRUE_CONDITION, Event(event))

    def off(self, condition, event):
        """
        Removing the condition - event pair
        """
        if (condition, event) in self.events:
            self.events.remove((condition, event))

    def off_any(self, event):
        """
        Removing the event
        """
        self.off(TRUE_CONDITION, event)

    def off_condition(self, condition):
        """
        Removing all the events for the condition
        """
        self.events = filter(lambda e: not (e[0] == condition), self.events)

    def off_event(self, event):
        """
        Remove all occurrences of the event
        """
        self.events = filter(lambda e: not (e[1] == event), self.events)

    def get_events(self, condition=None):
        """
        Getting the events for the specified condition
        """
        if condition:
            return [e[1] for e in self.events if has_first(e, condition)]
        else:
            return [e[1] for e in self.events if e[0] == TRUE_CONDITION]

    def handle(self, message, context):  # TODO check **'s, generalize
        """
        Calling events basing on condition
        """
        global logging
        if logging:
            print "%s.handle of %s, events %s" % (type(self), message, len(self.events))

        check, rank, event_found = self.NO_HANDLE

        if not self.SENDER in context:
            context[self.SENDER] = self

        # Searching for the best event
        for condition_access, event_access in self.events:
            if logging:
                t1 = time.time()

            # Condition check, if no condition the result is true with zero rank
            c_rank, c_check = condition_access.check(message, context)

            if logging:
                print "trying %s, spent %s" % (condition_access.value, time.time() - t1)

            if c_rank > rank:
                rank, check, event_found = c_rank, c_check, event_access

        # Running the best event
        if rank >= 0:
            context.update({self.RANK: rank, self.CONDITION: check, self.EVENT: event_found.value})

            # Call event, add the condition result to the context
            result, event_found = event_found.run(message, context)
        else:
            result = False

            # There is a way to handle unknown message
            if self.unknown_event:
                return self.unknown_event.run(message, context)

        return result, rank, event_found

    def __call__(self, *message, **context):
        """
        Answer depends on the context
        """
        answer_mode = context.pop(self.ANSWER, None)  # Applicable only for a top level
        result = self.handle(message, context)

        if answer_mode == self.RANK:
            return result[0], result[1]

        return result[0]  # No need to know the details


class Element(Handler):
    """
    Element is a part of a complex system (e.g. graph)
    """
    NEXT = 'next'
    PREVIOUS = 'previous'

    OWNER = 'owner'
    SET_PREFIX = 'set'
    NAME = 'name'
    OLD_VALUE = 'old-value'
    NEW_VALUE = 'new-value'

    SEP = '_'

    FORWARD = [NEXT]
    BACKWARD = [PREVIOUS]

    def __init__(self, owner=None):
        super(Element, self).__init__()

        self._owner, self.owner = None, owner

    def is_forward(self, message):
        return message and message[0] in self.FORWARD

    def can_go_forward(self, *message, **context):
        return self.is_forward(message)

    def on_forward(self, event):
        self.on(self.can_go_forward, event)

    def off_forward(self):
        self.off_condition(self.can_go_forward)

    def is_backward(self, message):
        return message and message[0] in self.BACKWARD

    def can_go_backward(self, *message, **context):
        return self.is_backward(message)

    def on_backward(self, event):
        self.on(self.can_go_backward, event)

    def off_backward(self):
        self.off_condition(self.can_go_backward)

    @staticmethod
    def add_prefix(msg, prefix):
        """
        Add prefix to the message
        """
        event_name = msg

        if not msg.startswith(prefix):
            event_name = Element.SEP.join([prefix, event_name])

        return event_name

    def change_property(self, name, value):
        """
        Set the property to the new value with notification, if needed
        """
        old_value = getattr(self, name)
        if old_value == value:
            return

        set_message, context = self.add_prefix(name, self.SET_PREFIX), \
                               {self.NEW_VALUE: value, self.OLD_VALUE: old_value, self.SENDER: self}

        if old_value and Access.get_access(old_value, True).spec == Access.ABSTRACT:
            old_value(set_message, **context)

        setattr(self, '_%s' % name, value)

        if value and Access.get_access(value, True).spec == Access.ABSTRACT:
            value(set_message,  **context)

        return True

    @property
    def owner(self):
        return self._owner

    @owner.setter
    def owner(self, value):
        self.change_property('owner', value)


class Notion(Element):
    """
    Notion is an element with name
    """
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
        self.change_property(self.NAME, value)


class ActionNotion(Notion):
    """
    Action notion is a notion with specified forward handler
    """
    def __init__(self, name, action, owner=None):
        super(ActionNotion, self).__init__(name, owner)
        self.on_forward(action)

    @property
    def action(self):
        value = self.get_events(self.can_go_forward)
        return value[0] if value else None

    @action.setter
    def action(self, value):
        self.off_forward()
        self.on_forward(value)


class Relation(Element):
    """
    Relation is a connection between one or more elements: subject -> object
    """
    SUBJECT = 'subject'
    OBJECT = 'object'

    def __init__(self, subj, obj, owner=None):
        super(Relation, self).__init__(owner)
        self._object = self._subject = None
        self.subject, self.object = subj, obj

    @property
    def subject(self):
        return self._subject

    @subject.setter
    def subject(self, value):
        self.change_property(self.SUBJECT, value)

    @property
    def object(self):
        return self._object

    @object.setter
    def object(self, value):
        self.change_property(self.OBJECT, value)

    def __str__(self):
        return '<%s - %s>' % (self.subject, self.object)

    def __repr__(self):
        return self.__str__()


class ComplexNotion(Notion):
    """
    Complex notion is a notion that relates with other notions (objects)
    """
    def __init__(self, name, owner=None):
        super(ComplexNotion, self).__init__(name, owner)

        self._relations = []

        self.on(self.add_prefix(Relation.SUBJECT, self.SET_PREFIX), self.do_relation)
        self.on_forward(self.do_forward)

    def do_relation(self, *message, **context):
        relation = context.get(self.SENDER)

        if context[self.OLD_VALUE] == self and relation in self._relations:
            self._relations.remove(relation)
            return True

        elif context[self.NEW_VALUE] == self and relation not in self._relations:
            self._relations.append(relation)
            return True

    def do_forward(self, *message, **context):
        if self._relations:
            return self._relations[0] if len(self._relations) == 1 else tuple(self.relations)

    @property
    def relations(self):
        return self._relations


class NextRelation(Relation):
    """
    Next relation checks for additional condition when relation passed forward
    """
    def __init__(self, subj, obj, condition=None, ignore_case=False, owner=None):
        super(NextRelation, self).__init__(subj, obj, owner)
        self.ignore_case = ignore_case
        self.condition_access = Condition(condition, ignore_case) if condition else TRUE_CONDITION

        self.on(self.can_pass, self.next_handler)

    def check_condition(self, message, context):
        return self.condition_access.check(message, context)

    def can_pass(self, *message, **context):
        if self.is_forward(message):  # We use 0 rank to make condition prevail other forward command
            return self.check_condition(message, context)

    def next_handler(self, *message, **context):
        return self.object

    @property
    def condition(self):
        return self.condition_access.value

    @condition.setter
    def condition(self, value):
        self.condition_access = Condition(value, self.ignore_case)


class ActionRelation(Relation):
    """
    Action relation performs an action and moves forward
    """
    def __init__(self, subj, obj, action, owner=None):
        super(ActionRelation, self).__init__(subj, obj, owner)
        self._action_access = Access(action)

        self.on_forward(self.do_act)

    def do_act(self, *message, **context):
        action_result = self._action_access(*message, **context)

        if action_result is not None and self.object is not None:
            return action_result, self.object
        else:
            return action_result if action_result is not None else self.object

    @property
    def action(self):
        return self._action_access.value

    @action.setter
    def action(self, value):
        self._action_access = Access(value)


class Process(Handler):
    """
    Process is a walker from an abstract to abstract, asking them for the next one with a query
    It has the current abstract and the message to process; when new abstract appears,
    the new queue item with current and message is created
    """
    NEW = 'new'
    OK = 'ok'
    STOP = 'stop'
    SKIP = 'skip'

    CURRENT = 'current'
    MESSAGE = 'message'
    QUERY = 'query'

    def __init__(self):
        super(Process, self).__init__()

        self._queue, self.context = [], {}
        self.new_queue_item({})

        self.query = Element.NEXT

        self.setup_handlers()

    def new_queue_item(self, values):
        """
        Generate the new queue item and add it to the queue updated with values
        """
        item = {self.CURRENT: values.get(self.CURRENT),
                self.MESSAGE: values.get(self.MESSAGE, [])}

        self._queue.append(item)

        return item

    def to_queue(self, values):
        """
        Put the new item in the queue, updating the empty one, if presents
        """
        if not self.message:
            self.queue_top.update(values)  # No need to keep the empty one in the queue
        else:
            if not self.CURRENT in values:
                values[self.CURRENT] = self.current  # It is better to keep the current current

            self.new_queue_item(values)

    def set_message(self, message, insert=False):
        """
        Set the current message or inserts in the front of current message if insert = True
        """
        message = [message] if not is_list(message) else list(message)  # TODO: all is_XXX check

        if insert:
            message.extend(self.message)

        self.queue_top[self.MESSAGE] = message

    # Events #
    def do_new(self):
        """
        New: cleaning up the queue
        """
        self.message.pop(0)
        del self._queue[:-1]

        self.queue_top[self.CURRENT] = None

    def can_push_queue(self):
        """
        Queue push: if the head of the message is an Abstract - we make the new queue item and get ready to query it
        """
        if self.message:
            return Access.get_access(self.message[0], True).mode in (Access.CALL, Access.FUNCTION)

    def do_queue_push(self):
        self.to_queue({self.CURRENT: self.message.pop(0),
                       self.MESSAGE: [self.QUERY]})  # Adding query command to start from asking

    def can_pop_queue(self, *message):
        """
        Queue pop: when current queue item is empty we can remove it
        """
        return len(self._queue) > 1 and not message

    def do_queue_pop(self):
        self._queue.pop()

    def can_query(self, *message):
        """
        Query: should we ask the query to the current current
        """
        return self.current and has_first(message, self.QUERY)

    def do_query(self):
        self.message.pop(0)

        # If abstract returns False/None, we just continue to the next one
        return getattr(self.current, Access.CACHE_ATTR)(self.query, **self.context) or True

    def do_skip(self):
        """
        Skip: remove current and the next item from the queue
        """
        self.message.pop(0)  # Remove the command itself

        while not self.message and self._queue:  # Looking for the item to skip
            self.do_queue_pop()

        # It is ok if the message is empty to ignore skip
        if self.message:
            self.message.pop(0)

    def can_clear_message(self, *message):
        """
        Cleanup: remove empty message item
        """
        if message:
            return not message[0]

    def do_clear_message(self):
        self.message.pop(0)

    def do_finish(self):
        return self.message.pop(0)

    def setup_handlers(self):
        """
        Init handlers
        """
        self.on(self.NEW, self.do_new)
        self.on(self.SKIP, self.do_skip)
        self.on((self.STOP, self.OK, True, False), self.do_finish)

        self.on(self.can_query, self.do_query)
        self.on(self.can_push_queue, self.do_queue_push)
        self.on(self.can_pop_queue, self.do_queue_pop)
        self.on(self.can_clear_message, self.do_clear_message)

    def on_start(self, new_message, new_context):
        """
        Start new process
        """
        if has_first(new_message, self.NEW):
            self.context = new_context
        else:
            self.context.update(new_context)

        self.to_queue({self.MESSAGE: list(new_message)})

    def handle(self, message, context):
        """
        Process' handle works in step-by-step manner, processing message and then popping the queue
        """
        self.on_start(message, context)

        result = self.NO_HANDLE

        while self.message or len(self._queue) > 1:
            result = super(Process, self).handle(self.message, self.context)

            if result[0] in (self.OK, self.STOP, False):
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
        return self.queue_top.get(self.MESSAGE)

    @property
    def current(self):
        return self.queue_top.get(self.CURRENT)


class SharedProcess(Process):
    """
    Shared process supports context modification commands
    """
    ADD_CONTEXT = 'add_context'
    UPDATE_CONTEXT = 'update_context'
    DELETE_CONTEXT = 'delete_context'

    def context_add(self, key, value):
        self.context[key] = value

    def context_set(self, key, value):
        self.context[key] = value

    def context_delete(self, key):
        del self.context[key]

    # Events #
    def can_add_context(self, *message):
        """
        Do we have add context command
        """
        return message and isinstance(message[0], dict) \
            and isinstance(message[0].get(self.ADD_CONTEXT), dict)  # TODO less isinstances

    def do_add_context(self):
        """
        Adding items to context, do not replacing existing ones
        """
        add = self.message[0].pop(self.ADD_CONTEXT)

        for k, v in add.items():
            if not k in self.context:
                self.context_add(k, v)

    def can_update_context(self, *message):
        """
        Updating the context
        """
        return message and isinstance(message[0], dict) \
            and isinstance(message[0].get(self.UPDATE_CONTEXT), dict)

    def do_update_context(self):
        update = self.message[0].pop(self.UPDATE_CONTEXT)

        for k, v in update.items():
            self.context_set(k, v)

    def can_delete_context(self, *message):
        """
        Deleting items from the context
        """
        return message and isinstance(message[0], dict) \
            and self.DELETE_CONTEXT in message[0]

    def do_delete_context(self):
        delete = self.message[0].pop(self.DELETE_CONTEXT)

        if is_list(delete):
            for k in delete:
                if k in self.context:
                    self.context_delete(k)

        elif delete in self.context:
            self.context_delete(delete)

    def setup_handlers(self):
        super(SharedProcess, self).setup_handlers()

        self.on(self.can_add_context, self.do_add_context)
        self.on(self.can_update_context, self.do_update_context)
        self.on(self.can_delete_context, self.do_delete_context)


# StackingContextProcess dialect
PUSH_CONTEXT = 'push_context'
POP_CONTEXT = 'pop_context'
FORGET_CONTEXT = 'forget_context'


# Process that can save and restore context
# Useful for cases when process needs to try various paths in the graph
class StackingContextProcess(SharedProcess):

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
    def context_add(self, key, value):
        self.run_tracking_operation(DictChangeOperation(self.context, DictChangeOperation.ADD, key, value))

    def context_set(self, key, value):
        self.run_tracking_operation(DictChangeOperation(self.context, DictChangeOperation.SET, key, value))

    def context_delete(self, key):
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
        return self.current and message and isinstance(message[0], dict) \
            and SET_STATE in message[0]

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
        self.query = Element.NEXT
        self.context_set(PARSED_LENGTH, 0)
        self.context_set(LAST_PARSED, '')

    def is_parsed(self):
        return self.query == Element.NEXT and not self.text

    def handle(self, message, context):
        result = super(ParsingProcess, self).handle(message, context)

        return False if not self.is_parsed() and not result[0] == self.STOP else result[0], self.parsed_length, result[2]

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

        self.context_set(TEXT, self.context[TEXT][proceed:])
        self.context_set(PARSED_LENGTH, self.parsed_length + proceed)
        self.context_set(LAST_PARSED, last_parsed)

    # Next, Break, Error or Continue
    def do_turn(self):
        new_query = self.message.pop(0)

        if new_query in Element.BACKWARD:
            del self.message[:]

        self.query = new_query

    def setup_handlers(self):
        super(ParsingProcess, self).setup_handlers()

        self.on((Element.NEXT, ERROR, BREAK, CONTINUE), self.do_turn)
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
Element.BACKWARD += [ERROR, BREAK, CONTINUE]


# Parsing relation: should be passable in forward direction (otherwise returns Error)
class ParsingRelation(NextRelation):
    def __init__(self, subj, obj, condition=None, ignore_case=False, owner=None):
        super(ParsingRelation, self).__init__(subj, obj, condition, ignore_case, owner)

        self.optional = False
        self.check_only = False

        self.unknown_event = Event(self.on_error)

    # Here we check condition against the parsing text
    def check_condition(self, message, context):
        return self.condition_access.check(tupled(context.get(TEXT), message), context)

    def next_handler(self, *message, **context):
        next_result = super(ParsingRelation, self).next_handler(*message, **context)
        rank = context.get(self.RANK)

        return ({PROCEED: rank}, next_result) if rank and not self.check_only else next_result

    def on_error(self, *message, **context):
        if not self.optional and self.is_forward(message):
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
        context[self.ANSWER] = self.RANK

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
                    self.NEXT,  # Go forward again
                    case,  # Try another case
                    self]  # Come back
        else:
            return self.do_finish()  # No more opportunities

    def can_finish(self, *message, **context):
        return context.get(STATE) and self.is_forward(message)

    def do_finish(self):
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
        if not self.condition_access == TRUE_CONDITION:  # Here we check only the simplest case
            return False

    # Is a wildcard loop
    def is_wildcard(self):
        return self.condition in WILDCARDS

    # Is a numeric loop
    def is_numeric(self):
        if self.condition_access.spec == Condition.NUMBER:
            return True
        elif self.condition_access.spec == Condition.LIST and len(self.condition) == 2:
            return (self.condition[0] is None or self.condition_access.list[0].spec == Condition.NUMBER) \
                and (self.condition[1] is None or self.condition_access.list[1].spec == Condition.NUMBER)

    # Infinite loop
    def is_infinite(self):
        return self.condition is True

    # Custom loop: not empty callable condition
    def is_custom(self):
        return self.condition_access.mode == Access.FUNCTION

    # Flexible condition has no finite bound, lower or higher
    def is_flexible(self):
        return (self.is_numeric() and self.condition_access.spec == Condition.LIST) or self.is_wildcard()

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
            if self.condition_access.spec == Condition.NUMBER:
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

    def do_start_general(self):
        return self.get_next_iteration_reply()

    def can_loop_general(self, *message, **context):
        return self.is_forward(message) and self.is_looping(context) and self.is_general()

    def do_loop_general(self, **context):
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

    def do_error_general(self, **context):
        i = context.get(STATE).get(ITERATION)
        lower, upper = self.get_bounds()

        reply = []

        if self.is_flexible():
            # Roll back to the previous good result
            if lower < i <= upper:
                reply += [self.NEXT, POP_CONTEXT]
            else:
                reply += [FORGET_CONTEXT]

        return reply + [CLEAR_STATE]
    
    # Custom loop
    def can_loop_custom(self, *message):
        return self.is_forward(message) and self.is_custom()

    def do_loop_custom(self, *message, **context):
        i = self.condition_access(*message, **context)

        if i:
            return {SET_STATE: {ITERATION: i}}, self.object, self
        else:
            return False if not self.is_looping(context) else CLEAR_STATE,

    def can_error_custom(self, *message):
        return has_first(message, ERROR) and self.is_custom()

    def do_error_custom(self):
        return CLEAR_STATE,
    
    # Common handling
    def can_break(self, *message, **context):
        return has_first(message, BREAK) and self.is_looping(context)

    def do_break(self):
        reply = [self.NEXT]

        if self.is_flexible():
            reply += [FORGET_CONTEXT]

        return reply + [CLEAR_STATE]

    def can_continue(self, *message, **context):
        return has_first(message, CONTINUE) and self.is_looping(context)

    def do_continue(self, **context):
        return [self.NEXT] + self.do_loop_general(**context)


# Graph is a holder of Notions and Relation, it allows easy search and processing of them
class Graph(Element):
    def __init__(self, root=None, owner=None):
        super(Graph, self).__init__(owner)

        self._root = None
        self._notions = []
        self._relations = []

        self.on(self.add_prefix(self.OWNER, self.SET_PREFIX), self.do_element)
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

                if Relation.SUBJECT in criteria:
                    req.append(criteria[Relation.SUBJECT])
                    rel.append(relation.subject)

                if Relation.OBJECT in criteria:
                    req.append(criteria[Relation.OBJECT])
                    rel.append(relation.object)

                return len(rel) if rel == req and rel else -1

    def relations(self, criteria=None):
        return self.search_elements(self._relations, self.get_relation_search_rank, criteria) if criteria else \
            tuple(self._relations)

    def relation(self, criteria=None):
        found = self.relations(criteria)

        return found[0] if found else None

    def do_element(self, **context):
        element = context.get(self.SENDER)

        if isinstance(element, Notion) or isinstance(element, Graph):
            collection = self._notions
        elif isinstance(element, Relation):
            collection = self._relations
        else:
            return False

        if context[self.OLD_VALUE] == self and element in collection:
            collection.remove(element)

            if element == self.root:
                self.root = None

            return True

        elif context[self.NEW_VALUE] == self and element not in collection:
            collection.append(element)
            return True

    def do_forward(self):
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
        rel = NextRelation(self.current, obj, condition, ignore_case, self.graph)

        return self.attach(rel)

    def act_rel(self, action, obj=None):
        return self.attach(ActionRelation(self.current, obj, action, self.graph))

    def parse_rel(self, condition, obj=None, ignore_case=None, optional=None):
        rel = ParsingRelation(self.current, obj, condition, ignore_case, self.graph)
        rel.optional = optional

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
