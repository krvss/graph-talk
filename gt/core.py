"""
.. module:: gt.core
   :platform: Unix, Windows
   :synopsis: Graph-talk core classes

.. moduleauthor:: Stas Kravets (krvss) <stas.kravets@gmail.com>

"""

from inspect import getargspec
from operator import attrgetter

from gt.utils import *


class Abstract(object):
    """
    Base class for communicative objects.
    """
    def __call__(self, *message, **context):
        """
        Main method for sending messages to the object.

        :param message:  list of arbitrary items to be processed one by one.
        :param context:  key-value description of the message processing context.

        :returns: None for no reaction, False if there is an error, any positive value otherwise.
        """
        raise NotImplementedError('Method not implemented')


class Access(Abstract):
    """
    Access provides :class:`Abstract`-style wrapper to access non-Abstract objects. Each instance has
    :attr:`Access.mode` to describe the access mode (execute or just return the object as is) and
    :attr:`Access.spec` to keep the additional information like function arguments specification, etc.

    .. note:: When comparing Access instance with other objects, from Access side, the wrapped value will be used.
        It means Access(1) will be equal with 1.
    """
    #: Callable object mode.
    CALL = 'call'
    #: The callable object is :class:`Abstract`.
    ABSTRACT = 'abstract'
    #: The callable object is function.
    FUNCTION = 'function'
    #: The object is a non-callable (e.g. primitive) value (both mode and spec).
    VALUE = 'value'
    #: Unknown mode and spec.
    OTHER = 'other'

    CACHE_ATTR = '__access__'
    CACHEABLE = frozenset([CALL, FUNCTION])

    def __init__(self, value):
        """
        Creates the new Access instance to wrap the value.

        :param value: any object to wrap.
        """
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
        Inits type information, setting the call proxy method, mode, and spec. Overwrite to support custom types.

        Sets the read-only properties:
            - :attr:`Access.mode`: :attr:`Access.CALL` for abstracts, :attr:`Access.FUNCTION` for
              functions and :attr:`Access.VALUE` for primitives;
            - :attr:`Access.spec`:  :attr:`Access.ABSTRACT` for abstracts, :obj:`inspect.ArgSpec`
              for functions, :attr:`Access.OTHER` for primitives;
            - :attr:`Access.value`: the object itself.
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
        """
        Proxy method to emulate the 'call' to the object (execute the function, return the value, etc).
        """
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

    #: Wrapped object.
    value = property(attrgetter('_value'))

    #: Access mode (the object is callable or not).
    mode = property(attrgetter('_mode'))

    #: Access spec (call specification, e.g. function argument specification).
    spec = property(attrgetter('_spec'))

    @staticmethod
    def get_access(obj, cache=False):
        """
        Gets the Access to the specified object, caches the access instance within the object, if possible.

        :param obj:     object to wrap into the Access.
        :param cache:   cache the access instance inside the object if True.
        :type cache:    bool.
        :returns:       new Access instance to access the object like an Abstract.
        :rtype:         Access.
        """
        if hasattr(obj, Access.CACHE_ATTR):
            access = getattr(obj, Access.CACHE_ATTR)
        else:
            access = Access(obj)

            if cache and access._mode in Access.CACHEABLE:
                setattr(obj, Access.CACHE_ATTR, access)

        return access


class Condition(Access):
    """
    Condition is used to check the possibility of the message handling in the specified context. It's
    :meth:`Condition.check` method returns the tuple of (rank, check_result). If the rank is less than 0
    it means the condition is not satisfied. The rank shows how relevant this condition is.

    The check result is used mostly for regular expressions to analyze its actual match result. Note that
    :meth:`Condition.check` method is assigned dynamically basing on the condition object type.
    """
    #: Number access spec.
    NUMBER = 'number'
    #: List access spec.
    LIST = 'list'
    #: Dictionary access spec.
    DICT = 'dict'
    #: String access spec.
    STRING = 'string'
    #: Regular expression access spec.
    REGEX = 'regex'
    #: Boolean access spec.
    BOOLEAN = 'bool'

    #: Returned if check was not passed.
    NO_CHECK = -1, None

    def __init__(self, value, *tags, **options):
        """
        Creates the new Condition.

        :param value:  value to be checked (object, function, regex, string, boolean, list).
        :param tags:   list of tags for this Condition to be active.
        :param options:
            - ignore_case (bool.): False by default, ignore case of string conditions or not.
            - search (bool.): False by default, perform the search or match regexes and strings when checking.
        """
        #: Set of tags to be considered active (read-only)
        self.tags = frozenset(tags)

        self._options = options
        self._ignore_case = options.get('ignore_case', False)
        self._search = options.get('search', False)

        self.check, self._conditions = self.check_compare, tuple([self])
        super(Condition, self).__init__(value)

    def setup(self):
        """
        Sets the additional :attr:`Access.spec` info: :attr:`Condition.NUMBER`, :attr:`Condition.STRING`,
        :attr:`Condition.LIST`, :attr:`Condition.REGEX`, :attr:`Condition.DICT`, :attr:`Condition.BOOLEAN`.

        Sets :meth:`Condition.check` to the appropriate checking function depending on the value type.
        """
        super(Condition, self).setup()

        if self._mode == self.FUNCTION:
            self.check = self.check_function

        elif is_number(self._value):
            self._spec = self.NUMBER

        elif is_list(self._value):
            self._spec, self.check = self.LIST, self.check_list
            self._conditions = tuple([Condition(c, *list(self.tags), **self._options ) for c in self._value])

        elif is_string(self._value):
            self._spec, self.check = self.STRING, self.check_string_search if self._search else self.check_string_match
            self._value_len = len(self._value)

            if self._ignore_case:
                self._value = self._value.upper()

        elif is_regex(self._value):
            self._spec, self.check = self.REGEX, self.check_regex_search if self._search else self.check_regex_match

        elif isinstance(self._value, dict):
            self._spec = self.DICT

        elif type(self._value) == bool:
            self._spec, self.check = self.BOOLEAN, self.check_boolean

    def check(self, message, context):
        """
        Checks the possibility of handling the message in the specified context.
        Returns the tuple of (rank, check_result) where rank shows the relevance of the condition.
        If less than 0 it means condition is not satisfied and completely irrelevant. Zero rank is mostly used for
        logical conditions (True/False) that cannot be measured numerically.
        Check result keeps the result of functional (user-defined, regular expression) check.

        .. note:: the default implementation returns :attr:`Condition.NO_CHECK` and should be overwritten in
         :meth:`Condition.setup` method.

        :param message:     message to check.
        :type message:      List.
        :param context:     checking context.
        :type context:      Dict.
        :returns:           Tuple of (rank, check_result) or just rank value.
        """
        return self.NO_CHECK

    def check_function(self, message, context):
        check = self._call(message, context)

        # Do we work with (rank, check) format?
        if get_len(check) == 2:
            return check
        elif check:
            return 0 if check is True else check, check
        else:
            return self.NO_CHECK

    def check_regex_match(self, message, context):
        check = self._value.match(message[0]) if message else None

        if check:
            rank = check.end() - check.start()  # Match length is the rank
            check = check.group(0)
        else:
            rank = - 1

        return rank, check

    def check_regex_search(self, message, context):
        check = self._value.search(message[0]) if message else None

        if check:
            rank = check.end()  # Whole length is the rank
            check = check.group(0)
        else:
            rank = - 1

        return rank, check

    def check_string_match(self, message, context):
        try:
            message0 = message[0][:self._value_len]

            if self._ignore_case:
                message0 = message0.upper()

            if message0 == self._value:
                return self._value_len, self._value

        except (TypeError, IndexError):
            pass

        return self.NO_CHECK

    def check_string_search(self, message, context):
        message0 = str(message[0])

        if self._ignore_case:
            message0 = message0.upper()

        pos = message0.find(self._value)
        if pos >= 0:
            return self._value_len + pos, self._value

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
        """
        Returns the list of inner conditions.
        """
        return self._conditions


class TrueCondition(Condition):
    """
    Condition that is always satisfied.
    """
    def __init__(self):
        super(TrueCondition, self).__init__(id(self))
        self.check = lambda message, context: (0, True)


TRUE_CONDITION = TrueCondition()


class Event(Access):
    """
    Event contains the user object (value or function) to be called if the :class:`Condition` was satisfied.
    It provides :attr:`Event.pre` and :attr:`Event.post` properties to assign functions to be executed before
    and after the user object call.
    """
    #: Object call result context parameter.
    RESULT = 'result'

    def __init__(self, value):
        """
        Wraps in :class:`Access` the value to be called.
        """
        super(Event, self).__init__(value)
        #: Pre-event, Event class instance.
        self.pre_event = None
        #: Post-event, Event class instance.
        self.post_event = None

    def run(self, message, context):
        """
        Does the Access call to the event object with the message and context.
        If :attr:`Event.pre` event is specified it will be called first. If its result is non-negative the object
        will not be called at all.
        If :attr:`Event.post` event is specified it will be called after the object and
        the context will contain the object call result in :attr:`Event.RESULT` context parameter. If its result
        is non-negative, it will be returned instead of object call result.

        :param message:     message to send to the event.
        :type message:      list.
        :param context:     running context.
        :type context:      dict.

        :returns:           tuple of (call result, :attr:`Access.value`).
        :rtype:             tuple.
        """
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
        """
        Sets/gets the pre-event object. Use pre_event attribute to assign an :class:`Event` instance directly.
        """
        return self.pre_event.value if self.pre_event else None

    @pre.setter
    def pre(self, value):
        self.pre_event = Event(value) if value is not None else None

    @property
    def post(self):
        """
        Sets/gets the post-event object. Use post_event attribute to assign an :class:`Event` instance directly.
        """
        return self.post_event.value if self.post_event else None

    @post.setter
    def post(self, value):
        self.post_event = Event(value) if value is not None else None


class Handler(Abstract):
    """
    Handler is used for routing of messages to handling functions called events (:class:`Event`) basing on the
    specified condition (:class:`Condition`). Each condition has a corresponding event. When handling a message,
    Handler class searches for the condition that has the highest rank and calls :attr:`Handler.unknown_event`
    if nothing found.

    The condition could be limited to be active only if its set of tags (:attr:`Condition.tags`) is a subset
    of the Handler set of tags. List of active conditions and events is in :attr:`Handler.active_events` property.
    """
    #: Answer context parameter, if equal to :attr:`Handler.RANK` the condition rank will be included in the answer.
    ANSWER = 'answer'
    #: Sender context parameter. When the event is called, contains the reference to the top-level handler.
    SENDER = 'sender'
    #: Condition context parameter. When the event is called, contains the check result.
    CONDITION = 'condition'
    #: Event context parameter. When the pre/post/event is called, contains the reference to the event function.
    EVENT = 'event'
    #: Rank context parameter. When the event is called, contains the check rank.
    RANK = 'rank'

    #: Returned by :meth:`Handler.handle` if no handler found.
    NO_HANDLE = (False, -1, None)

    def __init__(self):
        Access.get_access(self, True)

        self._tags = set()
        self._events = []
        #: Tuple of events which are eligible for the current tags (read-only).
        self.active_events = tuple()
        #: Event to be executed when no handler found for the message.
        self.unknown_event = None

    def on_access(self, condition_access, event_access):
        """
        Adds the Condition and Event instances pair.

        :param condition_access:    condition to be checked.
        :type condition_access:     Condition.
        :param event_access:        event to be executed if the condition is satisfied.
        :type event_access:         Event.
        """
        if (condition_access, event_access) not in self._events:
            self._events.append((condition_access, event_access))

            self.update_events()

    def on(self, condition, event, *tags):
        """
        Adds the condition - event pair.

        :param condition:    condition for the event (function, abstract, value).
        :param event:        function, abstract, or value to be called if condition is satisfied.
        :param tags:         list of tags to bind the condition to the handler's state.
        """
        self.on_access(Condition(condition, *tags), Event(event))

    def on_any(self, event):
        """
        Adds the event that will be triggered on any message.

        :param event:   function, abstract or value to be called.
        """
        self.on_access(TRUE_CONDITION, Event(event))

    def off(self, condition, event):
        """
        Removes the condition - event pair.

        :param condition:   condition to be removed (no matter Condition type or not)
        :param event:       event to be removed (no matter Event type or not).
        """
        if (condition, event) in self._events:
            self._events.remove((condition, event))

            self.update_events()

    def off_any(self, event):
        """
        Removes the event that will be triggered on any message.

        :param event:   event to be removed.
        """
        self.off(TRUE_CONDITION, event)

    def off_condition(self, condition):
        """
        Removes all events for the condition.

        :param condition:   condition to be removed.
        """
        self._events = list(filter(lambda e: not (e[0] == condition), self._events))

        self.update_events()

    def off_event(self, event):
        """
        Removes all occurrences of the event.

        :param event:   event to be removed.
        """
        self._events = list(filter(lambda e: not (e[1] == event), self._events))

        self.update_events()

    def get_events(self, condition=None):
        """
        Gets the events for the specified condition. If the condition is not specified returns the list of events
        that trigger on any message.

        :param condition:   condition to get the events.
        :returns:           list of events found.
        :rtype:             list.
        """
        if condition:
            return [e[1] for e in self._events if has_first(e, condition)]
        else:
            return [e[1] for e in self._events if e[0] == TRUE_CONDITION]

    def clear_events(self):
        """
        Removes all conditions and events.
        """
        del self._events[:]
        self.active_events = tuple()

    def update_tags(self):
        """
        Called by :meth:`Handler.update_events` to get the set of tags describing the current state.

        :returns:   set of tags describing the current state.
        :rtype:     set.
        """
        return self._tags

    def update_events(self):
        """
        Called by :meth:`Handler.update` when the list of active events needs to be updated
        (for example, after the new event was added or tags were changed).
        """
        self.active_events = tuple(filter(lambda e: e[0].tags.issubset(self._tags), self._events))

    def update(self):
        """
        Update is called manually or by handler itself when something is changed. If the tag set returned by
        :meth:`Handler.update_tags` is different from :attr:`Handler.tags`, :meth:`Handler.update_events`
        will be called to re-populate the list of active events.
        """
        new_tags = self.update_tags()

        if new_tags != self._tags:
            self.tags = new_tags

            self.update_events()

    def handle(self, message, context):
        """
        Checks the list of condition-event pairs to find the condition with the highest rank for the message and
        context and then executes the corresponding event.

        :param message:     list of message parts.
        :type message:      list.
        :param context:     message handling context.
        :type context:      dict.
        :returns:           Tuple of (event_result, condition_rank, event_found). If no condition was found, rank
         is equal to -1 (:attr:`Handler.NO_HANDLE` will be returned if not overridden by :attr:`Handler.unknown_event`).
        :rtype:             tuple.
        """
        check, rank, event_found = self.NO_HANDLE

        if not self.SENDER in context:
            context[self.SENDER] = self

        # Searching for the best event
        for condition_access, event_access in self.active_events:
            # Condition check, if no condition the result is true with zero rank
            c_rank, c_check = condition_access.check(message, context)

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
        Answers on the incoming message. Calls :meth:`Handler.handle` method and returns the first element from
        its reply. If the context parameter :attr:`Handler.ANSWER` is equal to :attr:`Handler.RANK` - returns the
        rank is well.

        :param message:     message items.
        :param context:     message context.
        :returns:           handling result or tuple of (handling_result, condition_rank).
        """
        answer_mode = context.pop(self.ANSWER, None)  # Applicable only for a top level
        result = self.handle(message, context)

        if answer_mode == self.RANK:
            return result[0], result[1]

        return result[0]  # No need to know the details

    @property
    def tags(self):
        """
        Sets/gets the set of the current tags. Does not call :meth:`Handler.update`.
        """
        return self._tags

    @tags.setter
    def tags(self, value):
        self._tags = frozenset(value)

    @property
    def events(self):
        """
        Gets the list of all conditions and events regardless of the current tags.
        """
        return self._events


class Element(Handler):
    """
    Element is a part of a complex system (e.g. graph). It has an owner and could be passed in forward and backward
    directions by some process.
    """
    #: Default prefix for property change notifications.
    SET_PREFIX = 'set'
    #: Notifications separator
    SEP = '_'

    #: Owner context parameter
    OWNER = 'owner'
    #: Name context parameter for notifications.
    NAME = 'name'
    #: Old value context parameter for notifications (e.g. keeps the old owner when changing it).
    OLD_VALUE = 'old-value'
    #: New value context parameter for notifications.
    NEW_VALUE = 'new-value'

    def __init__(self, owner=None):
        """
        Creates the Element, attaching it to the owner, if specified.

        :param owner:   graph to own this element.
        :type owner:    Graph.
        """
        super(Element, self).__init__()

        self._owner = None
        #: The graph this element belongs to.
        self.owner = owner

    def is_forward(self, message):
        """
        Checks the message about passing the element in a forward direction.

        :param message:     message to be checked
        :type message:      list.
        :returns:           forward or not.
        :rtype:             bool.
        """
        return message and message[0] in Process.FORWARD

    def can_go_forward(self, *message, **context):
        """
        Passing forward condition.
        """
        return self.is_forward(message)

    def on_forward(self, event):
        """
        Adds the event to be called when this element is passed in a forward direction.

        :param event:   user function to be called, will be wrapped in :class:`Event`.
        """
        self.on(self.can_go_forward, event)

    def off_forward(self):
        """
        Removes the forward condition and event.
        """
        self.off_condition(self.can_go_forward)

    def is_backward(self, message):
        """
        Checks is the message about passing the element in a backward direction.

        :param message:     message to be checked
        :type message:      list.
        :returns:           backward or not.
        :rtype:             bool.
        """
        return message and message[0] in Process.BACKWARD

    def can_go_backward(self, *message, **context):
        """
        Passing backward condition.
        """
        return self.is_backward(message)

    def on_backward(self, event):
        """
        Adds the event to be called when this element is passed in a backward direction.

        :param event: user function to be called.
        """
        self.on(self.can_go_backward, event)

    def off_backward(self):
        """
        Removes the backward condition and event.
        """
        self.off_condition(self.can_go_backward)

    @staticmethod
    def add_prefix(msg, prefix):
        """
        Adds the prefix to the message, used when generating a notification about property change (e.g. owner).
        If the prefix is already in place does nothing.

        :param msg:     message with the property name.
        :type msg:      str.
        :param prefix:  prefix to add.
        :type prefix:   str.
        """
        event_name = msg

        if not msg.startswith(prefix):
            event_name = Element.SEP.join([prefix, event_name])

        return event_name

    def change_property(self, name, value):
        """
        Sets the property to the new value with the notification, if needed. For example, when setting the owner, old
        and new owners will be notified about the change with the message generated with :meth:`Element.add_prefix`
        method.

        :param name:    property name.
        :type name:     str.
        :param value:   property value.
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
        """
        Sets/gets the owner using :meth:`Element.change_property` method.
        """
        return self._owner

    @owner.setter
    def owner(self, value):
        self.change_property('owner', value)


class Notion(Element):
    """
    Notion is an element with name. Represent the graph vertex.
    """
    def __init__(self, name, owner=None):
        """
        Creates the new Notion with the specified name.

        :param name:    notion name.
        :type name:     str.
        :param owner:   notion's owner.
        :type owner:    Graph.
        """
        super(Notion, self).__init__(owner)
        self._name, self.name = None, name

    def __str__(self):
        return '"%s"' % self.name

    def __repr__(self):
        rep = '<%s(%s' % (get_object_name(self.__class__), self.__str__())

        if self.owner:
            rep += ', %s' % self.owner

        return rep + ')>'

    @property
    def name(self):
        """
        Sets/gets the notion name using :meth:`Element.change_property` method.
        """
        return self._name

    @name.setter
    def name(self, value):
        self.change_property(self.NAME, value)


class ActionNotion(Notion):
    """
    Action notion is a notion that executes the user function when passed forward.
    """
    def __init__(self, name, action, owner=None):
        """
        Creates the new ActionNotion with the specified name and action.

        :param name:    notion name.
        :param action:  action, any object to be wrapped in :class:`Event`.
        :param owner:   notion's owner.
        :type owner:    Graph.
        """
        super(ActionNotion, self).__init__(name, owner)
        self.on_forward(action)

    @property
    def action(self):
        """
        Sets/gets the user function to be triggered using :meth:`Element.on_forward` method.
        """
        value = self.get_events(self.can_go_forward)
        return value[0] if value else None

    @action.setter
    def action(self, value):
        self.off_forward()
        self.on_forward(value)


class Relation(Element):
    """
    Relation is a connection between two notions, directed from the subject to object. Represents the graph arc.
    """
    #: Subject context parameter, used in change subject notifications.
    SUBJECT = 'subject'
    #: Object context parameter, used in change object notifications.
    OBJECT = 'object'

    def __init__(self, subj, obj, owner=None):
        """
        Creates the new Relation between subj and obj.

        :param subj:    source notion.
        :type subj:     ComplexNotion.
        :param obj:     target notion.
        :type obj:      Notion.
        :param owner:   relation's owner.
        :type owner:    Graph.
        """
        super(Relation, self).__init__(owner)
        self._object = self._subject = None
        self.subject, self.object = subj, obj

    @property
    def subject(self):
        """
        Sets/gets the subject using :meth:`Element.change_property` method.
        """
        return self._subject

    @subject.setter
    def subject(self, value):
        self.change_property(self.SUBJECT, value)

    @property
    def object(self):
        """
        Sets/gets the object using :meth:`Element.change_property` method.
        """
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
    Complex notion is a notion that contains other notions via relations. To add a relation just set its subject to
    the corresponding ComplexNotion.
    """
    def __init__(self, name, owner=None):
        super(ComplexNotion, self).__init__(name, owner)

        self._relations = []

        self.on(self.add_prefix(Relation.SUBJECT, self.SET_PREFIX), self.do_relation)
        self.on_forward(self.do_forward)

    def do_relation(self, *message, **context):
        """
        Subject change event, updates references if a sub-notion was connected/disconnected.

        :returns: True if subject's change was successful.
        :rtype: bool.
        """
        relation = context.get(self.SENDER)

        if context[self.OLD_VALUE] == self and relation in self._relations:
            self._relations.remove(relation)
            return True

        elif context[self.NEW_VALUE] == self and relation not in self._relations:
            self._relations.append(relation)
            return True

    def do_forward(self, *message, **context):
        """
        Forward message event.

        :returns: the list of relations or just single relation if the relations list length == 1
        """
        if self._relations:
            return self._relations[0] if len(self._relations) == 1 else tuple(self.relations)

    def remove_all(self):
        """
        Disconnects all relations.
        """
        while self._relations:
            self._relations[0].subject = None

    @property
    def relations(self):
        """
        Gets the list of relations (read-only).
        """
        return self._relations


class NextRelation(Relation):
    """
    Next relation returns its :attr:`Relation.object` to the forward message if the specified condition was satisfied.
    If the condition is not set, :class:`TrueCondition` is used.
    """
    def __init__(self, subj, obj, condition=None, owner=None, **options):
        """
        Creates the new NextRelation with the specified condition.

        :param subj:        subject.
        :type subj:         ComplexNotion.
        :param obj:         object.
        :type obj:          Notion.
        :param condition:   condition value, will be wrapped in :class:`Condition`.
        :param owner:       owner.
        :type owner:        Graph.
        :param options:     Condition options, like in :meth:`Condition.__init__`. When setting the new condition,
          options will be reapplied.
        """
        super(NextRelation, self).__init__(subj, obj, owner)
        self.options = options

        if condition:
            self.set_condition(condition)
        else:
            #: Passing condition, a :class:`Condition` class instance. Default value is :class:`TrueCondition`.
            self.condition_access = TRUE_CONDITION

        self.on(self.can_pass, self.do_next)

    def can_pass(self, *message, **context):
        """
        Forward message condition, will call :meth:`NextRelation.check_condition` if the message is a forward one.
        """
        if self.is_forward(message):  # We use 0 rank to make condition prevail other forward command
            return self.check_condition(message, context)

    def check_condition(self, message, context):
        """
        Returns the result of condition's :meth:`Condition.check` call.
        """
        return self.condition_access.check(message, context)

    def do_next(self, *message, **context):
        """
        Next event.

        :returns: :attr:`Relation.object`.
        :rtype: Notion.
        """
        return self.object

    def set_condition(self, value):
        """
        Sets the new condition, wrapping the value in the :class:`Condition`.

        :param value: new condition value.
        """
        self.condition_access = Condition(value, **self.options)

    @property
    def condition(self):
        """
        Sets/gets the value of the current condition. Note that it does NOT return a
        :class:`Condition` instance. Use :attr:`NextRelation.condition_access` for direct access instead.
        """
        return self.condition_access.value

    @condition.setter
    def condition(self, value):
        self.set_condition(value)


class ActionRelation(Relation):
    """
    Action relation executes the user function when passed forward.
    """
    def __init__(self, subj, obj, action, owner=None):
        """
        Creates the new ActionRelation.

        :param subj:    subject.
        :type subj:     ComplexNotion.
        :param obj:     object.
        :type obj:      Notion.
        :param action:  action value, will be wrapped in :class:`Access`.
        :param owner:   owner.
        :type owner:    Graph.
        """
        super(ActionRelation, self).__init__(subj, obj, owner)
        #: Passing action, a :class:`Access` class instance.
        self.action_access = Access(action)

        self.on_forward(self.do_act)

    def do_act(self, *message, **context):
        """
        Executes the action.

        :returns: If :attr:`ActionRelation.action` call result is not None and the object is not None too returns
          tuple (action_result, :attr:`Relation.object`). Otherwise returns action result OR :attr:`Relation.object`.
        """
        action_result = self.action_access(*message, **context)

        if action_result is not None and self.object is not None:
            return action_result, self.object
        else:
            return action_result if action_result is not None else self.object

    @property
    def action(self):
        """
        Sets/gets the action value, wrapping it in :class:`Access`. When called for reading, returns the
        :attr:`Access.value`. Use :attr:`ActionRelation.action_access` to access :class:`Access` class instance.
        """
        return self.action_access.value

    @action.setter
    def action(self, value):
        self.action_access = Access(value)


class Process(Handler):
    """
    Process goes from an :class:`Element` to element, asking what to do next with a :attr:`Process.query`.
    The answer from the :attr:`Process.current` element will be processing using :class:`Handler` methods.
    If the answer is a list, its items will be put to the queue and processed one by one. If the answer is another
    element, it will be the next current element to ask for directions.

    The processes are usually started with the start element and some context to be used in the dialog with
    the elements::

        p = Process()
        print(p(start_element, destination="Orion"))

    """
    #: New command. Clears the process internals when the process should be started from the scratch.
    NEW = 'new'
    #: Ok command. Stops the process with an "ok" result.
    OK = 'ok'
    #: Stop command. Stops the process with a "stop" result.
    STOP = 'stop'
    #: Query command (needs dict). Sets :attr:`Process.query` to the specified value.
    QUERY = 'query'

    #: Next element command.
    NEXT = 'next'
    #: Previous element command.
    PREVIOUS = 'previous'

    #: Non-empty current element tag; queue item field with the current element.
    CURRENT = 'current'
    #: Non-empty message tag; queue item field with the current message.
    MESSAGE = 'message'
    #: Empty message tag, shows that the current message is empty.
    EMPTY_MESSAGE = 'empty_' + MESSAGE

    #: Set of forward queries to identify the direction.
    FORWARD = set([NEXT])
    #: Set of backward queries to identify the direction.
    BACKWARD = set([PREVIOUS])

    STOP_CRITERIA = (OK, STOP, False)
    GO_CRITERIA = (None, True)

    def __init__(self):
        """
        Creates the new Process, sets the current query to :attr:`Process.NEXT`, initializes queue, events, and state.
        """
        super(Process, self).__init__()

        self._queue = NotifyList(self.update_fields)

        #: Process context.
        self.context = {}

        #: Current query. An initial value is :attr:`Process.NEXT`.
        self.query = self.NEXT

        #: Current message (read-only).
        self.message = None

        #: Current element (read-only).
        self.current = None

        self.new_queue_item({})
        self.setup_events()

    def new_queue_item(self, values):
        """
        Generates the new queue item (a dictionary) and adds it to the queue updated with values dictionary.

        :param values:  dictionary to update the queue item, should at least contain :attr:`Process.CURRENT` and
         :attr:`Process.MESSAGE`.
        :type values:   dict.
        :returns:       new queue item.
        :rtype:         dict.
        """
        item = NotifyDict(self.update_fields,
                          ((self.CURRENT, values.get(self.CURRENT)),
                           (self.MESSAGE, values.get(self.MESSAGE, NotifyList(self.update_message)))))

        self._queue.append(item)

        return item

    def to_queue(self, values):
        """
        Puts the new item to the queue or updates the empty one, if presents on the queue's top.
        Calls :meth:`Process.new_queue_item` to create the new item.

        :param values:  dictionary to update the queue item
        :type values:   dict.
        """
        if not self.message:
            self._queue[-1].update(values)  # No need to keep the empty one in the queue
        else:
            if not self.CURRENT in values:
                values[self.CURRENT] = self.current  # It is better to keep the current current

            self.new_queue_item(values)

    def set_message(self, message, insert=False):
        """
        Sets the current message or inserts in the front of current message if insert is True.

        :param message:     message items.
        :type message:      list.
        :param insert:      insert or replace the old message (False by default).
        :type insert:       bool.
        """
        message = NotifyList(self.update_message, [message] if not is_list(message) else message)

        if insert:
            message.extend(self.message)

        self._queue[-1][self.MESSAGE] = message

    def update_message(self):
        """
        Updates the :attr:`Process.message` property. This is a callback to be called by queue if its content changes.
        """
        self.message = self._queue[-1].get(self.MESSAGE)

    def update_fields(self):
        """
        Updates :attr:`Process.message` and :attr:`Process.current` properties. This is a callback to be called by
        queue if its content changes.
        """
        top = self._queue[-1]
        self.message = top.get(self.MESSAGE)
        self.current = top.get(self.CURRENT)

    def skip(self):
        """
        Removes the first item of the current :attr:`Process.message`. Useful when it is unknown and cannot be
        processed.
        """
        while not self.message and self._queue:  # Looking for the item to skip
            self.do_queue_pop()

        # It is ok if the message is empty to ignore skip
        if self.message:
            self.message.pop(0)

    # Events #
    def can_push_queue(self):
        """
        Queue push condition: if the first item of the :attr:`Process.message` is an Abstract or function,
        the process has to ask it about directions and handle the reply. To do this, a new queue item is created.
        """
        return Access.get_access(self.message[0], True).mode in Access.CACHEABLE

    def do_queue_push(self):
        """
        Queue push event: adds the new queue item with :attr:`Process.CURRENT` equals to the first
        :attr:`Process.message` item and :attr:`Process.MESSAGE` equals to :attr:`Process.QUERY` so
        the new current element will be asked with the current :attr:`Process.query`.
        """
        self.to_queue({self.CURRENT: self.message.pop(0),
                       self.MESSAGE: [self.QUERY]})  # Adding query command to start from asking

    def can_pop_queue(self):
        """
        Queue pop condition: when the current queue item is empty, we can remove it.
        """
        return len(self._queue) > 1

    def do_queue_pop(self):
        """
        Queue pop event: removes the first element from the queue.
        """
        self._queue.pop()

    def do_query(self):
        """
        Query event: sends the message the with the :attr:`Process.query` value to :attr:`Process.current` element .

        :return:    the answer of the element or True.
        """
        self.message.pop(0)

        # If abstract returns False/None, we just continue to the next one
        return getattr(self.current, Access.CACHE_ATTR)(self.query, **self.context) or True

    def can_clear_message(self, *message):
        """
        Cleanup condition: can we remove an empty message item.
        """
        return not message[0]

    def do_clear_message(self):
        """
        Cleanup event.
        """
        self.message.pop(0)

    def do_finish(self):
        """
        Finish event: returns the first message item with the finish value.

        :returns:   :attr:`Process.STOP` or :attr:`Process.OK` or a boolean value.
        """
        return self.message.pop(0)

    def update_tags(self):
        """
        Checks the current values of the :attr:`Process.message`, queue, :attr:`Process.current` and returns the
        set of tags for the current state. Override to add new tags, see :class:`Handler` for the details.
        """
        tags = set()

        if self.message:
            tags.add(self.MESSAGE)

            # Most wanted types
            if is_string(self.message[0]):
                tags.add(Condition.STRING)

            elif type(self.message[0]) == bool:
                tags.add(Condition.BOOLEAN)

            elif isinstance(self.message[0], dict):
                tags.add(Condition.DICT)

            else:
                tags.add(Condition.OTHER)

        else:
            tags.add(self.EMPTY_MESSAGE)

        if self.current:
            tags.add(self.CURRENT)

        return tags

    def setup_events(self):
        """
        Sets up the process events and state tags. Tags are:
            - :attr:`Condition.STRING`: first message item is a string.
            - :attr:`Condition.BOOLEAN`: first message item is a boolean.
            - :attr:`Condition.DICT`: first message item is a dictionary.
            - :attr:`Access.OTHER`: first message item has some other type.
            - :attr:`Process.CURRENT`: current element is not empty.
            - :attr:`Process.EMPTY_MESSAGE`: current message is empty.
            - :attr:`Process.MESSAGE`: current message is not empty (has items).
        """
        self.on((self.STOP, self.OK), self.do_finish, Condition.STRING)
        self.on((True, False), self.do_finish, Condition.BOOLEAN)

        self.on(self.QUERY, self.do_query, Condition.STRING, self.CURRENT)

        self.on(self.can_push_queue, self.do_queue_push, Condition.OTHER)
        self.on(self.can_pop_queue, self.do_queue_pop, self.EMPTY_MESSAGE)

        self.on(self.can_clear_message, self.do_clear_message, self.MESSAGE)

    def on_new(self, message, context):
        """
        New 'special' event: called when starting the handle loop and :attr:`Process.NEW` command is specified.
        This event has no conditions and is called by :meth:`Process.handle` directly.
        """
        message.pop(0)

        self.to_queue({self.MESSAGE: message, self.CURRENT: None})
        del self._queue[:-1]  # And kill the rest

        self.context = context

    def on_resume(self, message, context):
        """
        Resume 'special' event: called when resuming the stopped process.
        This event has no conditions and is called by :meth:`Process.handle` directly.
        """
        self.to_queue({self.MESSAGE: message})
        self.context.update(context)

    def handle(self, message, context):
        """
        In contrast with :meth:`Handler.handle`, process handle does not stop when the message is handled,
        but continues handling with the result of the previous call.
        """
        message = list(message)
        if has_first(message, self.NEW):  # Very special case
            self.on_new(message, context)
        else:
            self.on_resume(message, context)

        result = self.NO_HANDLE

        while self.message or len(self._queue) > 1:
            self.update()
            result = super(Process, self).handle(self.message, self.context)

            if result[0] in self.STOP_CRITERIA:
                break

            elif result[0] in self.GO_CRITERIA:
                continue  # No need to put it into the message

            self.set_message(result[0], True)

        return result


class SharedProcess(Process):
    """
    Shared process supports context modification commands to share data between elements using context parameters .::

        p = SharedProcess()
        p({SharedProcess.ADD_CONTEXT: {'key': 'skeleton'}})
    """
    #: Add context command (requires dict). Adds the specified parameter and value to the context, skips existing ones.
    ADD_CONTEXT = 'add_context'
    #: Update context command (requires dict). Updates the specified key(s) in the context.
    UPDATE_CONTEXT = 'update_context'
    #: Delete context command (requires key or key list). Deletes the specified keys(s) from the context.
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
        Add context condition: checks if there is a :attr:`SharedProcess.ADD_CONTEXT` command with data in the dictionary.
        """
        return isinstance(message[0].get(self.ADD_CONTEXT), dict)

    def do_add_context(self):
        """
        Add context event; adds parameters to the context, skipping existing ones.
        """
        add = self.message[0].pop(self.ADD_CONTEXT)

        for k, v in add.items():
            if not k in self.context:
                self.context_add(k, v)

    def can_update_context(self, *message):
        """
        Update context condition: checks if there is a :attr:`SharedProcess.UPDATE_CONTEXT` command with data in the
        dictionary.
        """
        return isinstance(message[0].get(self.UPDATE_CONTEXT), dict)

    def do_update_context(self):
        """
        Update context event: adds or replaces context parameters.
        """
        update = self.message[0].pop(self.UPDATE_CONTEXT)

        for k, v in update.items():
            self.context_set(k, v)

    def can_delete_context(self, *message):
        """
        Delete context condition: checks if there is a :attr:`SharedProcess.DELETE_CONTEXT` command.
        """
        return self.DELETE_CONTEXT in message[0]

    def do_delete_context(self):
        """
        Delete context event; deletes the single key or all the keys from the list.
        """
        delete = self.message[0].pop(self.DELETE_CONTEXT)

        if is_list(delete):
            for k in delete:
                if k in self.context:
                    self.context_delete(k)

        elif delete in self.context:
            self.context_delete(delete)

    def setup_events(self):
        """
        Sets up the events and state tags. All commands require :attr:`Condition.DICT`.
        """
        super(SharedProcess, self).setup_events()

        self.on(self.can_add_context, self.do_add_context, Condition.DICT)
        self.on(self.can_update_context, self.do_update_context, Condition.DICT)
        self.on(self.can_delete_context, self.do_delete_context, Condition.DICT)


class StackingProcess(SharedProcess):
    """
    Process that can save and restore the context. Useful for cases when the process needs to try various paths
    in a graph and then rollback to the state it had at the crossroads.

    To perform the rollback, the process records all change actions done via :class:`SharedProcess` commands
    and plays them back in "undo" command style. If no rollback is needed, the saved context can be discarded.
    """
    #: Push the current context to the undo stack.
    PUSH_CONTEXT = 'push_context'
    #: Restore the context from the top of the undo stack.
    POP_CONTEXT = 'pop_context'
    #: Discard the saved context at the top of the undo stack, keeping the changed context as is.
    FORGET_CONTEXT = 'forget_context'

    #: Non-empty undo stack tag.
    TRACKING = 'tracking'

    def __init__(self):
        super(StackingProcess, self).__init__()

        self._context_stack = []

    def run_tracking_operation(self, operation):
        if self._context_stack:
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
        """
        Push context event: start recording changes.
        """
        self.message.pop(0)
        self._context_stack.append(DictChangeGroup())

    def do_pop_context(self):
        """
        Pop context event: un-does changes from the top of the undo stack and removes the saved context.
        """
        self.message.pop(0)
        self._context_stack.pop().undo()

    def do_forget_context(self):
        """
        Forget context event: discard the top context from the undo stack.
        """
        self.message.pop(0)
        self._context_stack.pop()

    def update_tags(self):
        tags = super(StackingProcess, self).update_tags()

        if self._context_stack:
            tags.add(self.TRACKING)

        return tags

    def setup_events(self):
        """
        Sets up the events and state tags. All commands require :attr:`Condition.STRING`, pop and forget commands
        also require non-empty undo stack (:attr:`StackingProcess.TRACKING`).
        """
        super(StackingProcess, self).setup_events()

        self.on(self.PUSH_CONTEXT, self.do_push_context, Condition.STRING)
        self.on(self.POP_CONTEXT, self.do_pop_context, self.TRACKING, Condition.STRING)
        self.on(self.FORGET_CONTEXT, self.do_forget_context, self.TRACKING, Condition.STRING)

    def on_new(self, message, context):
        """
        Clears the undo stack if a new process started.
        """
        super(StackingProcess, self).on_new(message, context)
        del self._context_stack[:]


class StatefulProcess(StackingProcess):
    """
    Allows saving of private element data to the context. Only works for the
    :attr:`Process.current`::

        ActionNotion('Changed my mind', {StatefulProcess.SET_STATE: {'mind': 'New York'}})

    .. note:: Element state is a part of rollback process, but only at the top level,
     for example if the state is a dict its internals will not be restored.
    """
    #: The name of the context parameter to access the state.
    STATE = 'state'

    #: Set the state command (requires dict), applicable for the current process element.
    SET_STATE = 'set_state'
    #: Clear the state command, remove saved state from the context.
    CLEAR_STATE = 'clear_state'

    #: 'Has previously saved states' tag.
    HAS_STATES = 'has_states'

    def __init__(self):
        super(StatefulProcess, self).__init__()
        self.states = {}

    def has_states(self):
        return len(self.states) > 0

    def _add_current_state(self):
        self.context[self.STATE] = self.states.get(self.current, {})

    def _del_current_state(self):
        del self.context[self.STATE]

    def _set_state(self, abstract, state):
        if not abstract in self.states:
            self.run_tracking_operation(DictChangeOperation(self.states, DictChangeOperation.ADD, abstract, state))
        else:
            self.run_tracking_operation(DictChangeOperation(self.states, DictChangeOperation.SET, abstract, state))

    def _clear_state(self, abstract):
        if abstract in self.states:
            self.run_tracking_operation(DictChangeOperation(self.states, DictChangeOperation.DELETE, abstract))

    def do_query(self):
        """
        Query event: adds the current element's state as the :attr:`StatefulProcess.STATE`
        context parameter. At the end of this method the state is removed from the context to keep it private.
        """
        self._add_current_state()

        # Now the state contains the right state
        result = super(StatefulProcess, self).do_query()

        self._del_current_state()

        return result

    # Events #
    def can_set_state(self, *message):
        """
        Set state condition: checks for :attr:`StatefulProcess.SET_STATE` command in the message.
        """
        return self.SET_STATE in message[0]

    def do_set_state(self):
        """
        Set state event: saves the value of the command to the internal dictionary of states.
        """
        value = self.message[0].pop(self.SET_STATE)
        self._set_state(self.current, value)

    def do_clear_state(self):
        """
        Clear state condition: checks for :attr:`StatefulProcess.CLEAR_STATE`.
        """
        self.message.pop(0)
        self._clear_state(self.current)

    def update_tags(self):
        tags = super(StatefulProcess, self).update_tags()

        if self.has_states():
            tags.add(self.HAS_STATES)

        return tags

    def setup_events(self):
        """
        Sets up the events and state tags. Set command requires :attr:`Condition.DICT` and :attr:`Process.CURRENT`,
        clear command requires :attr:`Process.CURRENT`, :attr:`Condition.STRING` and previously saved states
        (:attr:`StatefulProcess.HAS_STATES` tag).
        """
        super(StatefulProcess, self).setup_events()

        self.on(self.can_set_state, self.do_set_state, self.CURRENT, Condition.DICT)
        self.on(self.CLEAR_STATE, self.do_clear_state, self.CURRENT, self.HAS_STATES, Condition.STRING)

    def on_new(self, message, context):
        """
        New event: clears the states if a new process started.
        """
        super(StatefulProcess, self).on_new(message, context)
        self.states.clear()


class ParsingProcess(StatefulProcess):
    """
    Takes the text as an input; sends it to the graph elements as a context parameter. If an element responds with
    :attr:`ParsingProcess.PROCEED`, cuts off a piece of specified length from the beginning of the text.

    Supports :attr:`ParsingProcess.ERROR` command to indicate a problem and possible stop of lookahead.
    Supports looping commands :attr:`ParsingProcess.BREAK` and :attr:`ParsingProcess.CONTINUE`; to change the direction
    back to forward uses :attr:`Process.NEXT`.
    """
    #: Proceed command (requires a dict with numeric positive value); goes with the length of the parsed text piece.
    PROCEED = 'proceed'
    #: Error command; stops the forward processing and changes the :attr:`Process.query` to this value.
    ERROR = 'error'
    #: Break command; stops the forward processing and changes the :attr:`Process.query` to this value.
    BREAK = 'break'
    #: Continue command; stops the forward processing and changes the :attr:`Process.query` to this value.
    CONTINUE = 'continue'

    #: Context parameter with the total length of the parsed text.
    PARSED_LENGTH = 'parsed_length'
    #: Context parameter with the current text.
    TEXT = 'text'
    #: Context parameter with the last parsed text piece.
    LAST_PARSED = 'last_parsed'

    def is_parsed(self):
        """
        Checks whether the text was completely and successfully parsed.

        :return: True if the process has a forward direction and there is no more text to parse.
        """
        return self.query == self.NEXT and not self.text

    def handle(self, message, context):
        """
        Calls the :meth:`Process.handle`.

        :returns: If the text was not fully parsed (see :meth:`ParsingProcess.is_parsed`), returns False;
         otherwise returns the result of the superclass handle call.
        """
        result = super(ParsingProcess, self).handle(message, context)

        return False if not self.is_parsed() and not result[0] == self.STOP else result[0], self.parsed_length, result[2]

    # Events #
    def can_proceed(self, *message):
        """
        Proceed condition: checks for :attr:`ParsingProcess.PROCEED` and the positive distance.
        """
        distance = message[0].get(self.PROCEED)
        return is_number(distance) and len(self.context.get(self.TEXT)) >= distance

    def do_proceed(self):
        """
        Proceed event: cuts off the beginning of the text, updates :attr:`ParsingProcess.TEXT`,
        :attr:`ParsingProcess.PARSED_LENGTH` and :attr:`ParsingProcess.LAST_PARSED` context parameters.
        """
        proceed = self.message[0].pop(self.PROCEED)
        last_parsed = self.context[self.TEXT][0:proceed]

        self.context_set(self.TEXT, self.context[self.TEXT][proceed:])
        self.context_set(self.PARSED_LENGTH, self.parsed_length + proceed)
        self.context_set(self.LAST_PARSED, last_parsed)

    def do_turn(self):
        """
        Turn event: sets :attr:`Process.query` to the value of :attr:`ParsingProcess.BREAK`,
        :attr:`ParsingProcess.CONTINUE`, :attr:`ParsingProcess.ERROR`, or :attr:`Process.NEXT`. Clears the current
        message.
        """
        new_query = self.message.pop(0)

        if new_query in self.BACKWARD:
            del self.message[:]

        self.query = new_query

    def setup_events(self):
        """
        Sets up the events and state tags. Direction-changing commands require :attr:`Condition.STRING` tag,
        :attr:`ParsingProcess.PROCEED` command requires :attr:`Condition.DICT` tag.
        """
        super(ParsingProcess, self).setup_events()

        self.on((self.NEXT, self.ERROR, self.BREAK, self.CONTINUE), self.do_turn, Condition.STRING)
        self.on(self.can_proceed, self.do_proceed, Condition.DICT)

    def on_new(self, message, context):
        """
        New event: sets the direction to :attr:`Process.NEXT`, :attr:`ParsingProcess.PARSED_LENGTH` to 0
        and :attr:`ParsingProcess.LAST_PARSED` to the empty string.
        """
        super(ParsingProcess, self).on_new(message, context)

        self.query = self.NEXT
        self.context_set(self.PARSED_LENGTH, 0)
        self.context_set(self.LAST_PARSED, '')

    @property
    def text(self):
        """
        Gets the current text.
        """
        return self.context.get(self.TEXT, '')

    @property
    def parsed_length(self):
        """
        Gets the total parsed text length.
        """
        return self.context.get(self.PARSED_LENGTH, 0)

    @property
    def last_parsed(self):
        """
        Gets the last parsed text piece.
        """
        return self.context.get(self.LAST_PARSED, '')


# Adding new backward commands
Process.BACKWARD = Process.BACKWARD | set([ParsingProcess.ERROR, ParsingProcess.BREAK, ParsingProcess.CONTINUE])


class ParsingRelation(NextRelation):
    """
    Parsing relation: should be passable in a forward direction (otherwise returns :attr:`ParsingProcess.ERROR`).
    If passed, consumes the amount of text equal to the rank using :attr:`ParsingProcess.PROCEED` command.
    """
    def __init__(self, subj, obj, condition=None, owner=None, **options):
        """
        New options in addition to :meth:`NextRelation.__init__`:

            - optional (bool.): do not return :attr:`ParsingProcess.ERROR` if the condition was not satisfied,
              False by default.
            - check_only (bool.): do not return :attr:`ParsingProcess.PROCEED` if the condition was satisfied,
              False by default.
        """
        super(ParsingRelation, self).__init__(subj, obj, condition, owner, **options)

        #: Do not return error if cannot be passed
        self.optional = options.get('optional', False)
        #: Do not consume text when passed.
        self.check_only = options.get('check_only', False)

        self.unknown_event = Event(self.on_error)

    def check_condition(self, message, context):
        """
        Checks the :attr:`NextRelation.condition` against the value of :attr:`ParsingProcess.TEXT` context parameter.
        """
        return self.condition_access.check(tupled(context.get(ParsingProcess.TEXT), message), context)

    def do_next(self, *message, **context):
        """
        Consume the parsed part of the text equal to rank.

        :returns:   Tuple ({:attr:`ParsingProcess.PROCEED`: condition_rank}, :attr:`Relation.object`) if
          :attr:`ParsingRelation.check_only` is False, just :attr:`Relation.object` otherwise.
        """
        next_result = super(ParsingRelation, self).do_next(*message, **context)
        rank = context.get(self.RANK)

        return ({ParsingProcess.PROCEED: rank}, next_result) if rank and not self.check_only else next_result

    def on_error(self, *message):
        """
        Unknown_message event.

        :returns:   :attr:`ParsingProcess.ERROR`
        :rtype:     str.
        """
        if not self.optional and self.is_forward(message):
            return ParsingProcess.ERROR


class SelectiveNotion(ComplexNotion):
    """
    Selective notion is a :class:`ComplexNotion` that consists of only one sub-notion. It resembles *"switch"*
    statement from programming languages like Java or C++. SelectiveNotion tries all its relations and uses the
    one with the highest rank and processed without errors. After each try, the context state will be restored to make
    sure all relations use the same context data. Like in the original switch statement it is possible to specify the
    :attr:`SelectiveNotion.default` relation to be used if nothing worked.
    """
    #: Cases state parameter, keeps the list of remaining cases for re-tries.
    CASES = 'cases'

    def __init__(self, name, owner=None):
        super(SelectiveNotion, self).__init__(name, owner)

        self.on(self.can_retry, self.do_retry)
        self.on(self.can_finish, self.do_finish)

        self._default = None

    def get_best_cases(self, message, context):
        """
        Searches for the relation with the highest rank for the specified message and context.

        :param message:     message items.
        :type message:      list.
        :param context:     message handling context.
        :type context:      dict.
        :returns:           the relation(s) with the highest rank or :attr:`SelectiveNotion.default` relation,
          if specified.
        :rtype: list.
        """
        context[self.ANSWER] = self.RANK

        cases = []
        max_len = -1
        for rel in self.relations:
            if rel == self._default:  # Not now
                continue

            result, length = rel(*message, **context)  # With the rank, please

            if result != ParsingProcess.ERROR and length >= 0:
                max_len = max(length, max_len)
                cases.append((result, length))

        best_cases = [result for result, length in cases if length == max_len]

        if not best_cases and self._default:  # Right time to use the default
            best_cases = [self._default]

        return best_cases

    def do_relation(self, *message, **context):
        """
        Subject change event: additional check for the default relation to have this notion as a subject.
        """
        super(SelectiveNotion, self).do_relation(*message, **context)

        if self._default and not self._default in self.relations:
            self.default = None

    # Events #
    def can_go_forward(self, *message, **context):
        """
        Forward condition: makes sure this is a first visit of this element (no state is stored in the context).
        Re-try event will be used otherwise.
        """
        if not context.get(StatefulProcess.STATE):  # If we've been here before we need to try something different
            return super(SelectiveNotion, self).can_go_forward(*message, **context)

    def do_forward(self, *message, **context):
        """
        Forward event: if this notion has only one relation, it just returns it without any checks; otherwise calls
        :meth:`SelectiveNotion.get_best_cases` to get the best relation(s) and returns the first one from the list.

        Other relations with the same rank will be saved to the state :attr:`SelectiveNotion.CASES`
        parameter for retries. Note that element saves the context state to the process stack using
        :attr:`StackingProcess.PUSH_CONTEXT` command if there is more than one case to try.
        """
        reply = super(SelectiveNotion, self).do_forward(*message, **context)

        if is_list(reply):
            cases = self.get_best_cases(message, context)

            if cases:
                case = cases.pop(0)

                if not cases:
                    reply = case
                else:
                    reply = tupled(StackingProcess.PUSH_CONTEXT,  # Keep the context if re-try will needed
                                   {StatefulProcess.SET_STATE: {self.CASES: cases}},  # Store what to try next
                                   case,  # Try first case
                                   self)  # And come back again
            else:
                return ParsingProcess.ERROR

        return reply

    def can_retry(self, *message, **context):
        """
        Retry condition: if the previous case did not work (:attr:`ParsingProcess.ERROR` in the message),
        let's try something else.
        """
        return context.get(StatefulProcess.STATE) and has_first(message, ParsingProcess.ERROR)

    def do_retry(self, **context):
        """
        Retry event: if there are other cases to try - let's do this, if not - clear the state and keep the error
        propagating to the top.
        """
        cases = context[StatefulProcess.STATE][self.CASES]

        if cases:
            case = cases.pop(0)  # Try another case, if any

            # Pop context and update state, then try another case and come back here
            return tupled(StackingProcess.POP_CONTEXT,  # Roll back to the initial context
                          {StatefulProcess.SET_STATE: {self.CASES: cases}},  # Update cases
                          StackingProcess.PUSH_CONTEXT,  # Save updated context
                          Process.NEXT,  # Go forward again
                          case,  # Try another case
                          self)  # Come back
        else:
            return self.do_finish()  # No more opportunities

    def can_finish(self, *message, **context):
        """
        Finish condition: there is a saved state and no error happened.
        """
        return context.get(StatefulProcess.STATE) and self.is_forward(message)

    def do_finish(self):
        """
        Finish event: forget the saved context using :class:`StackingProcess.FORGET_CONTEXT` command and
        clear the state using :attr:`StatefulProcess.CLEAR_STATE` command.
        """
        return [StackingProcess.FORGET_CONTEXT, StatefulProcess.CLEAR_STATE]

    @property
    def default(self):
        """
        Sets/gets the default relation. Only the relation with the subject equal to this element can be used as the
        default.
        """
        return self._default

    @default.setter
    def default(self, value):
        if self._default == value or (value and value.subject != self):
            return

        self._default = value


class LoopRelation(NextRelation):
    """
    Loop relation specifies the number of times the :attr:`Relation.object` notion should appear.
    Similar to "for" loops in programming languages. The number of times is specified as a condition, possible
    conditions are: numeric (n; m..n; m..; ..n), wildcards ("*", "?", "+"), True (infinite loop), and a user function.
    """
    #: Current iteration context parameter.
    ITERATION = 'i'
    WILDCARDS = frozenset(['*', '?', '+'])
    INFINITY = float('inf')

    def __init__(self, subj, obj, condition=None, owner=None):
        super(LoopRelation, self).__init__(subj, obj, condition, owner)

        # General loop
        self.on(self.can_start_general, self.do_start_general, Condition.VALUE)
        self.on(self.can_loop_general, self.do_loop_general, Condition.VALUE)
        self.on(self.can_error_general, self.do_error_general, Condition.VALUE)

        # Custom loop
        self.on(self.can_loop_custom, self.do_loop_custom, Condition.FUNCTION)
        self.on(ParsingProcess.ERROR, self.do_error_custom, Condition.FUNCTION)

        # Common events
        self.on(self.can_break, self.do_break)
        self.on(self.can_continue, self.do_continue)

    def check_condition(self, message, context):
        """
        Forward condition. In this class this condition works only for infinite loops.
        """
        return self.condition_access == TRUE_CONDITION  # Here we check only the simplest case

    def set_condition(self, value):
        """
        Sets the new condition. In addition to :meth:`NextRelation.set_condition` updates the events using
        :meth:`Handler.update_events` to keep only events which work for the specified loop condition type.

        :param value:   new condition value.
        """
        super(LoopRelation, self).set_condition(value)

        if self.is_general():
            self.tags = [Condition.VALUE]
        elif self.is_custom():
            self.tags = [Condition.FUNCTION]

        self.update_events()

    def is_wildcard(self):
        """
        Is a wildcard loop.
        """
        return self.condition in self.WILDCARDS

    def is_numeric(self):
        """
        Is a numeric loop.
        """
        if self.condition_access.spec == Condition.NUMBER:
            return True
        elif self.condition_access.spec == Condition.LIST and len(self.condition) == 2:
            return (self.condition[0] is None or self.condition_access.list[0].spec == Condition.NUMBER) \
                and (self.condition[1] is None or self.condition_access.list[1].spec == Condition.NUMBER)

    def is_infinite(self):
        """
        Is an infinite loop.
        """
        return self.condition is True

    def is_custom(self):
        """
        Is a custom loop: non-empty callable condition.
        """
        return self.condition_access.mode == Access.FUNCTION

    def is_flexible(self):
        """
        Is a flexible loop: the condition has no finite limit of repetitions, either lower or higher.
        """
        return (self.is_numeric() and self.condition_access.spec == Condition.LIST) or self.is_wildcard()

    def is_general(self):
        """
        Is a general type: numeric, wildcard or infinite, but not a custom.
        """
        return self.is_numeric() or self.is_wildcard() or self.is_infinite()

    def is_looping(self, context):
        """
        Checks if this loop is active now by presence of :attr:`LoopRelation.ITERATION` key in the element's state.

        :param context:     message handling context
        :type context:      dict.
        """
        return self.ITERATION in context.get(StatefulProcess.STATE)

    def get_bounds(self):
        """
        Gets the limits of the loop.

        :returns:   Tuple of (lower_bound, upper_bound). For loops with no lower bound (like ..n) it equals to 0,
         for loops with no upper bound it equals to infinity.
        :rtype:     tuple.
        """
        lower, upper = 0, self.INFINITY

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

    def get_next_iteration_reply(self, i=1):
        """
        Gets the next iteration reply: sets the state to the iteration number using :attr:`StatefulProcess.SET_STATE`
        command and saves the context if the loop is flexible using :attr:`StackingProcess.PUSH_CONTEXT` command.
        If the iteration number is higher than 1, discards the previous context state using
        :attr:`StackingProcess.FORGET_CONTEXT` command.

        :param i:   iteration number.
        :type i:    int.
        :returns:   list of commands: :attr:`StatefulProcess.SET_STATE` with :attr:`LoopRelation.ITERATION`
          equal to i, discarding and saving context commands if the loop :meth:`LoopRelation.is_flexible`.
        :rtype:     list.
        """
        reply = [{StatefulProcess.SET_STATE: {self.ITERATION: i}}]

        if self.is_flexible():
            if i != 1:
                reply.insert(0, StackingProcess.FORGET_CONTEXT)  # Forget the past

            reply += [StackingProcess.PUSH_CONTEXT]  # Save state if needed

        return reply + [self.object, self]  # Try and come back

    # Events #
    # General loop
    def can_start_general(self, *message, **context):
        """
        Forward condition for starting of general loops: checks for the first visit; loop event will be used otherwise.
        """
        return self.is_forward(message) and not self.is_looping(context)

    def do_start_general(self):
        """
        Forward event for starting of general loops; returns the first iteration using
        :meth:`LoopRelation.get_next_iteration_reply`.
        """
        return self.get_next_iteration_reply()

    def can_loop_general(self, *message, **context):
        """
        Loop condition for the general loops: makes sure there are no errors and iteration is more than 1.
        """
        return self.is_forward(message) and self.is_looping(context)

    def do_loop_general(self, **context):
        """
        Loop event for general loops: if the iteration number is within :meth:`LoopRelation.get_bounds`,
        increases it and repeats the loop. Stops the loop otherwise, clearing the state using
        :attr:`StatefulProcess.CLEAR_STATE` command and discards the saved context using
        :attr:`StackingProcess.FORGET_CONTEXT`, keeping it in the actual state.
        """
        i = context.get(StatefulProcess.STATE).get(self.ITERATION)

        if i < self.get_bounds()[1]:
            return self.get_next_iteration_reply(i + 1)
        else:
            reply = []

            if self.is_flexible():
                reply += [StackingProcess.FORGET_CONTEXT]

            return reply + [StatefulProcess.CLEAR_STATE]

    def can_error_general(self, *message, **context):
        """
        Error condition for the general loops (:attr:`ParsingProcess.ERROR` in the message).
        """
        return has_first(message, ParsingProcess.ERROR) and self.is_looping(context)

    def do_error_general(self, **context):
        """
        Error event for the general loops: if the loop condition is satisfied just clears the state using
        :attr:`StatefulProcess.CLEAR_STATE` command restores the context to the last good state using
        :attr:`StackingProcess.POP_CONTEXT` command and clears the error using :attr:`Process.NEXT`.
        If the number of repetitions is less than needed - discards the saved context using
        :attr:`StackingProcess.FORGET_CONTEXT` command clears the state and keeps the error.
        """
        i = context.get(StatefulProcess.STATE).get(self.ITERATION)
        lower, upper = self.get_bounds()

        reply = []

        if self.is_flexible():
            # Roll back to the previous good result
            if lower < i <= upper:
                reply += [Process.NEXT, StackingProcess.POP_CONTEXT]
            else:
                reply += [StackingProcess.FORGET_CONTEXT]

        return reply + [StatefulProcess.CLEAR_STATE]

    # Custom loop
    def can_loop_custom(self, *message):
        """
        Forward event for custom loops.
        """
        return self.is_forward(message)

    def do_loop_custom(self, *message, **context):
        """
        Loop event for custom loops. Calls the user function from :attr:`NextRelation.condition`,
        sending the value of the current iteration in the context parameter :attr:`LoopRelation.ITERATION`.
        The call result will be the new number of the iteration.
        If it is equal to 0, False, or None - stops the loop by clearing the state using
        :attr:`StatefulProcess.CLEAR_STATE` command.
        """
        i = self.condition_access(*message, **context)

        if i:
            return [{StatefulProcess.SET_STATE: {self.ITERATION: i}}, self.object, self]
        else:
            return False if not self.is_looping(context) else [StatefulProcess.CLEAR_STATE]

    def do_error_custom(self):
        """
        Error event for the custom loops: just clears the state using :attr:`StatefulProcess.CLEAR_STATE` command.
        """
        return StatefulProcess.CLEAR_STATE,

    # Common handling
    def can_break(self, *message, **context):
        """
        Break condition: checks for the message to be :attr:`ParsingProcess.BREAK` and the loop to be in progress
        using :meth:`LoopRelation.is_looping`.
        """
        return has_first(message, ParsingProcess.BREAK) and self.is_looping(context)

    def do_break(self):
        """
        Break event: changes the process direction to forward using :attr:`Process.NEXT` command,
        clears the loop state using :attr:`StatefulProcess.CLEAR_STATE` and the context state
        using :attr:`StackingProcess.FORGET_CONTEXT` if the loop :meth:`LoopRelation.is_flexible`.
        """
        reply = [Process.NEXT]

        if self.is_flexible():
            reply += [StackingProcess.FORGET_CONTEXT]

        return reply + [StatefulProcess.CLEAR_STATE]

    def can_continue(self, *message, **context):
        """
        Continue condition: checks for the message to be :attr:`ParsingProcess.CONTINUE` and the loop
        to be in progress using :meth:`LoopRelation.is_looping`.
        """
        return has_first(message, ParsingProcess.CONTINUE) and self.is_looping(context)

    def do_continue(self, *message, **context):
        """
        Continue event: changes the process direction to forward using :attr:`Process.NEXT`,
        starts the new iteration using :meth:`LoopRelation.do_loop_general` or :meth:`LoopRelation.do_loop_custom`
        depending on the loop type.
        """
        if self.is_general():
            return [Process.NEXT] + self.do_loop_general(**context)
        else:
            return [Process.NEXT] + self.do_loop_custom(*message, **context)


class Graph(Element):
    """
    Graph is a container for elements like Notions, Relations, and other Graphs. It allows easy search and processing
    of the elements.
    """

    def __init__(self, root=None, owner=None):
        """
        Creates the new Graph with the specified root notion and owner. The name of the graph is equal to the name of
        its root notion.

        :param root:    if of String type, Graph will create the new :class:`ComplexNotion` element with the
          corresponding name and owner to be used as a root. The root notion will be saved into the :attr:`Graph.root`
          property of the graph.
        :param owner:   owner of this graph.
        :type owner:    Graph.
        """
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

    def get_notion_search_rank(self, notion, criteria):
        """
        Gets the rank of the notion when searching by criteria. Used as a comparator for notions search.

        :param notion:      the notion to calculate the rank.
        :type notion:       Notion.
        :param criteria:    searching criteria: regex, string or user function.
        :returns:           similarity rank: match length for regex, length of the string if the string is equal
         to the notion's name, the result of user function call.
        :rtype:             int.
        """
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
        """
        Searches for the elements within the collection to find the ones with the highest rank according to
        the specified criteria.

        :param collection:  list of the elements of the same type (:class:`Notion` or :class:`Relation`).
        :type collection:   list.
        :param comparator:  comparison function.
        :param criteria:    search criteria.
        :returns:           elements with the highest rank.
        :rtype:             list.
        """
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
        """
        Finds the notions by the specified criteria. If more than 1 notion has the highest rank, the list will
        be returned. Calls :meth:`Graph.search_elements` with :meth:`Graph.get_notion_search_rank` as a comparator
        function.

        :param criteria:    user function, regex, or string to compare with the notion name. If not specified,
         all notions will be returned.
        :returns:           notions found.
        :rtype:             tuple.
        """
        return self.search_elements(self._notions, self.get_notion_search_rank, criteria) if criteria else \
            tuple(self._notions)

    def notion(self, criteria):
        """
        Finds a single notion by the criteria. Calls :meth:`Graph.notions` to get the list of notions than
        returns a first one.

        :param criteria:    search criteria.
        :returns:           notion found.
        :rtype:             Notion.
        """
        found = self.notions(criteria)

        return found[0] if found else None

    def get_relation_search_rank(self, relation, criteria):
        """
        Gets the rank of the relation when searching by criteria. Used as a comparator for relations search.

        :param relation:    the relation to calculate the rank.
        :type relation:     Relation.
        :param criteria:    searching criteria: a dictionary or user function. The dictionary contains
         :attr:`Relation.SUBJECT` or :attr:`Relation.OBJECT` keys to specify the notion which should be a subject
         or object for the relation.
        :returns:           similarity rank: the result of the user function call or -1 (no subject/object equals
         to criteria), 0 (subject or object is equal to criteria), 1 (both subject and object are equal).
        :rtype:             int.
        """
        if callable(criteria):
            return criteria(relation)
        else:
            if isinstance(criteria, dict):
                rank = -1

                if Relation.SUBJECT in criteria and relation.subject == criteria.get(Relation.SUBJECT):
                    rank += 1

                if Relation.OBJECT in criteria and relation.object == criteria.get(Relation.OBJECT):
                    rank += 1

                return rank

    def relations(self, criteria=None):
        """
        Finds the relations by the specified criteria. If more than 1 relation has the highest rank, the list will be
        returned. Calls :meth:`Graph.search_elements` with :meth:`Graph.get_relation_search_rank` as a
        comparator function.

        :param criteria:    user function or dictionary with target :attr:`Relation.SUBJECT` or :attr:`Relation.OBJECT`
         values. If not specified, all relations will be returned.
        :returns:           relations found.
        :rtype:             tuple.
        """
        return self.search_elements(self._relations, self.get_relation_search_rank, criteria) if criteria else \
            tuple(self._relations)

    def relation(self, criteria=None):
        """
        Finds a single relation by the criteria. Calls `Graph.relations` to get the list of relations than returns a
        first one.

        :param criteria:    search criteria.
        :returns:           relation found.
        :rtype:             Relation.
        """
        found = self.relations(criteria)

        return found[0] if found else None

    def do_element(self, **context):
        """
        Owner change event. This event appears when the element changes the owner. When received, the graph will add or
        remove the element from the corresponding list of notions or relations. If the root notion changes owner,
        the graph will set the :attr:`Graph.root` to None.
        """
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
        """
        Forward event. Returns :attr:`Graph.root` value.

        :returns:   root notion.
        :rtype:     Notion.
        """
        return self.root

    @property
    def root(self):
        """
        Setter/getter of the root notion. The new root should belong to the graph.
        """
        return self._root

    @root.setter
    def root(self, value):
        if (self._root == value) or (value and (value.owner != self or not isinstance(value, Notion))):
            raise ValueError('Invalid root %s' % value)

        self.change_property('root', value)

    def __str__(self):
        return '{"%s"}' % (self.root.name if self.root else '')

    def __repr__(self):
        rep = '{%s(%s' % (get_object_name(self.__class__), self.__str__())

        if self.owner:
            rep += ', %s' % self.owner

        return rep + ')}'

    @property
    def name(self):
        """
        Setter/getter of the graph name. The name of the graph is equal to the name of the :attr:`Graph.root` notion.
        """
        return self.root.name if self.root else None

    @name.setter
    def name(self, value):
        self.root.name = value


class GraphBuilder(object):
    """
    Graph builder helps to create :class:`Graph`. It uses chained operations to assemble the graph, connecting elements
    to each other, for example::

     builder.complex('complex').next_rel().notion('simple')

    The current element to attach the new one is stored in :attr:`GraphBuilder.current` property.
    """
    def __init__(self, graph=None):
        """
        Create the new GraphBuilder using specified graph.

        :param graph:   is of string type will be used to create the new graph.
        """
        if is_string(graph):
            graph = Graph(graph)

        #: Current graph
        self.graph = graph
        #: Current graph element to attach the new ones.
        self.current = graph.root if graph else None

    def attach(self, new):
        """
        Attaches the new element to the :attr:`GraphBuilder.current` depending on its type. If the new element is a
        :class:`Notion` and the current element is a :class:`Relation`, the new element becomes a
        :attr:`Relation.object` of the relation. If the new element is a relation, and the current
        element is a :class:`ComplexNotion`, the current element becomes a :attr:`Relation.subject` of the new relation.
        Set the current element to None to avoid this behavior.

        :param new:     the new element to attach and set as a current.
        :type new:      Element.
        :returns:       self.
        :rtype:         GraphBuilder.
        """
        if isinstance(new, Notion):
            if isinstance(self.current, Relation) and not self.current.object:
                self.current.object = new

        elif isinstance(new, Relation):
            if isinstance(self.current, ComplexNotion) and not new.subject:
                new.subject = self.current

        else:
            raise TypeError('Invalid element type for %s' % new)

        self.current = new

        return self

    def complex(self, name):
        """
        Attaches new :class:`ComplexNotion` with the specified name.

        :param name:    new complex notion name.
        :type name:     str.
        :returns:       self.
        :rtype:         GraphBuilder.
        """
        return self.attach(ComplexNotion(name, self.graph))

    def notion(self, name):
        """
        Attaches new :class:`Notion` with the specified name.

        :param name:    the new notion name.
        :type name:     str.
        :returns:       self.
        :rtype:         GraphBuilder.
        """
        return self.attach(Notion(name, self.graph))

    def act(self, name, action):
        """
        Attaches new :class:`ActionNotion` with the specified name and action.

        :param name:    the new notion name.
        :type name:     str.
        :param action:  the action to be passed to :meth:`ActionNotion.__init__`.
        :returns:       self.
        :rtype:         GraphBuilder.
        """
        return self.attach(ActionNotion(name, action, self.graph))

    def next_rel(self, condition=None, obj=None, **options):
        """
        Attaches new :class:`NextRelation` with the specified condition and object.

        :param condition:   the passing condition.
        :param obj:         the object of the new relation.
        :type obj:          Notion.
        :param options:     options to be passed to :meth:`NextRelation.__init__`.
        :returns:           self.
        :rtype:             GraphBuilder.
        """
        return self.attach(NextRelation(None, obj, condition, self.graph, **options))

    def act_rel(self, action, obj=None):
        """
        Attaches new :class:`ActionRelation` with the specified action and object.

        :param action:      the action value (user function, etc.).
        :param obj:         the object of the new relation.
        :type obj:          Notion.
        :returns:           self.
        :rtype:             GraphBuilder.
        """
        return self.attach(ActionRelation(None, obj, action, self.graph))

    def parse_rel(self, condition, obj=None, **options):
        """
        Attaches new :class:`ParsingRelation` with the specified condition and object.

        :param condition:   the passing condition.
        :param obj:         the object of the new relation.
        :type obj:          Notion.
        :param options:     options to be passed to :meth:`ParsingRelation.__init__`.
        :returns:           self.
        :rtype:             GraphBuilder.
        """
        rel = ParsingRelation(None, obj, condition, self.graph, **options)

        return self.attach(rel)

    def select(self, name):
        """
        Attaches new :class:`SelectiveNotion` with the specified name.

        :param name:        new selective notion name.
        :type name:         str.
        :returns:           self.
        :rtype:             GraphBuilder.
        """
        return self.attach(SelectiveNotion(name, self.graph))

    def default(self):
        """
        If the :attr:`GraphBuilder.current` element is a :class:`Relation` and its subject is a
        :class:`SelectiveNotion` instance, this relation will be set as a :attr:`SelectiveNotion.default`.

        :returns:   self.
        :rtype:     GraphBuilder.
        """
        if isinstance(self.current, Relation) and isinstance(self.current.subject, SelectiveNotion):
            self.current.subject.default = self.current
        else:
            raise TypeError('Cannot make %s the default' % self.current)

        return self

    def loop_rel(self, condition, obj=None):
        """
        Attaches new :class:`LoopRelation` with the specified condition and object.

        :param condition:   the iteration condition.
        :param obj:         the object of the new relation.
        :type obj:          Notion.
        :returns:           self.
        :rtype:             GraphBuilder.
        """
        return self.attach(LoopRelation(None, obj, condition, self.graph))

    def sub_graph(self, name):
        """
        Creates the new sub-graph with the specified name. If the current :attr:`GraphBuilder.graph` is None,
        the new graph will be used as a current. Otherwise the :attr:`GraphBuilder.current` element will be set to
        the :attr:`Graph.root` of the new graph.

        :returns:   self.
        :rtype:     GraphBuilder.
        """
        new = Graph(name, self.graph if self.graph else None)

        if not self.graph:
            self.graph = new
            self.current = self.graph.root
        else:
            self.attach(new.root)
            self.graph = new

        return self

    def pop(self):
        """
        Goes to the :attr:`Graph.root` element of the :attr:`Element.owner` of the :attr:`GraphBuilder.current`
        element's graph.

        :returns:   self.
        :rtype:     GraphBuilder.
        """
        if self.current and self.current.owner and self.current.owner.owner:
            self.graph = self.current.owner.owner
            self.current = self.graph.root
        else:
            raise IndexError('On the top already')

        return self

    def set_current(self, element):
        """
        Sets the element as a :attr:`GraphBuilder.current`, using its owner as a current :attr:`GraphBuilder.graph`.

        :param element:     new current element.
        :type element:      Element.
        :returns:           self.
        :rtype:             GraphBuilder.
        """
        if element != self.current:
            self.current = element

            if element and element.owner != self.graph:
                self.graph = element.owner

        return self

    def back(self):
        """
        If the :attr:`GraphBuilder.current` is a :class:`Notion`, searches for any :class:`Relation` that has it
        as a :attr:`Relation.object` and sets it as a current.
        If the current element is a Relation, sets its :attr:`Relation.subject` notion as a current.

        :returns:   self.
        :rtype:     GraphBuilder.
        """
        if isinstance(self.current, Notion):
            rel = self.graph.relations({Relation.OBJECT: self.current})
            if rel:
                return self.set_current(rel[0])
        else:
            return self.set_current(self.current.subject)

    def __getitem__(self, element):
        """
        :attr:`GraphBuilder.current` element helper.

        :param element: if of String type, sets the :attr:`GraphBuilder.current` element to the notion with this name,
         otherwise sets the specified element as a current.
        :returns:       self.
        :rtype:         GraphBuilder.
        """
        if is_string(element):
            element = self.graph.notion(element)

        return self.set_current(element)
