Developer's Guide
=================
The base of the class hierarchy is :class:`.Abstract` class that does nothing except providing the :meth:`.Abstract.__call__` interface with 'message' and 'context' parameters::

    def __call__(self, *message, **context):
        raise NotImplementedError('Method not implemented')

The communication between objects should use only this method for message exchange::

    a = AbstractImpl()
    a('ultimate question', mode=42)

Message Handling
----------------

:class:`.Handler` class is a base class for condition-event based message processing. It contains the list of condition-event pairs and uses the :meth:`.Handler.handle` method to find the best condition for the message in a certain context and return the result of the event's call for that condition. The condition and event could be objects, values, or user functions.

To add a new condition-event pair, the Handler class provides an :meth:`.Handler.on` method::

    def on(self, condition, event, *tags)

For example::

    h = Handler()
    h.on('event', lambda: True)

    print h(‘event’)

    > True

    print h(‘tneve’)

    > False

An optional :attr:`.Handler.tags` parameter binds the condition to the state of the handler and will be described later.

When called, the 'on' method converts condition and event parameters to :class:`.Condition` and :class:`.Event` wrapper classes and puts the pair into the Handler event list.

Condition Class
---------------

Condition is processed based on its type – a string, regular expression, user function, etc. This is done by the :meth:`.Condition.setup` method of the :class:`.Condition` class, which sets up the correct :meth:`.Condition.check` function to analyze the message and compare it with the condition value. One may ask why in dynamic typed language, there is a need to worry about types. The reason is very simple: speed. It is too expensive to call non-applicable checks and/or use try blocks each time when looking for the best condition – using a type-specific comparison gives a very significant performance boost.

The default declaration of the user function to be used as a condition has the same form as the :meth:`.Abstract.__call__` method. When checking, it receives data from the :meth:`.Handler.handle` method. For example::

    user_condition = lambda *message, **context: return message and message[0] == "hi"

The result of the condition check is one or two values: check rank and check result. Check rank is a relevance indicator for the condition and the check result is actually the outcome of the check. For example, the check rank of "a+" regular expression for the message "aa" is 2 and the check result is "aa".

=================================   ====================================================
**Check result**                    **Meaning**
---------------------------------   ----------------------------------------------------
One numeric value                   Check rank, Check result will be equal to check rank
Two values: numeric and arbitrary   Check rank is first and Check result is second
One boolean value                   Rank = 0 if True, -1 if False, Check result = value
=================================   ====================================================

Logical checks have 0 rank by default. Check result is useful for the event and will be included in the context during the event's call. For example, if the condition returns True, the event context will contain ``{'rank': 0, 'condition': True}``.

If the condition did not work, it returns (-1, False) or :attr:`.Condition.NO_CHECK` value.

The condition has an ignore_case option, which is False by default. It affects only string conditions.

Let’s see how different types of conditions work, always for message[0].

+------------------------------+------------------------------------------------+-------------------------------------+
| Condition type               | Rank and result                                | Example                             |
+==============================+================================================+=====================================+
| Function                     || Should return the check rank or check rank    || ``lambda *m, **c: (1,"ok")``       |
|                              || with the check result                         || any message[0]                     |
|                              |                                                ||                                    |
|                              |                                                || rank = 1,                          |
|                              |                                                || check result = "ok"                |
+------------------------------+------------------------------------------------+-------------------------------------+
| Regular expression - match   || Length of the expression matched and match    || 'a+'                               |
|                              || result                                        || message[0] = "aa"                  |
|                              |                                                ||                                    |
|                              |                                                || rank = 2                           |
|                              |                                                || check result = "aa"                |
+------------------------------+------------------------------------------------+-------------------------------------+
| Regular expression - search  | Same as above, but using the search method     || "b+"                               |
|                              |                                                || message[0] = "agabb"               |
|                              |                                                ||                                    |
|                              |                                                || rank = 5                           |
|                              |                                                || check result = "bb"                |
+------------------------------+------------------------------------------------+-------------------------------------+
| String – match               || Length of the string if message[0] starts     || "stop"                             |
|                              || from the string and string itself as a result || message[0] = "stop"                |
|                              |                                                ||                                    |
|                              |                                                || rank = 4                           |
|                              |                                                || check result = "stop"              |
+------------------------------+------------------------------------------------+-------------------------------------+
| String – search              || Same as above, but using the find method of   || "run"                              |
|                              || string class                                  || message[0] = "now run"             |
|                              |                                                ||                                    |
|                              |                                                || rank = 7                           |
|                              |                                                || check result = "run"               |
+------------------------------+------------------------------------------------+-------------------------------------+
| Boolean value                | 0, True if message[0] equals value             || False                              |
|                              |                                                || message[0] = False                 |
|                              |                                                ||                                    |
|                              |                                                || rank = 0                           |
|                              |                                                || check result = False               |
+------------------------------+------------------------------------------------+-------------------------------------+
| List                         | Highest rank for each list item check          || ["1", "11"]                        |
|                              |                                                || message[0] = "11"                  |
|                              |                                                ||                                    |
|                              |                                                || rank = 2                           |
|                              |                                                || check result = "11"                |
+------------------------------+------------------------------------------------+-------------------------------------+
| Other value                  | 0 or value length if applicable, message[0] as || 8                                  |
|                              | the result                                     || message[0] = 8                     |
|                              |                                                ||                                    |
|                              |                                                || rank = 0                           |
|                              |                                                || check result = 8                   |
+------------------------------+------------------------------------------------+-------------------------------------+

For example::

    h = Handler()

    def show_me(*m, **c):
        print c

        return

    h.on(re.compile('a+'), show_me)

    h('aaa')

    > {'sender': <gt.core.Handler object at xxx>, 'condition': 'aaa', 'rank': 3, 'event': <function show_me at xxx>}

Here you see the context content for the event. It contains 'h' object as a sender of the message, passed condition, its rank, and show_me as a selected event. More information on events is below.

There is one more very important benefit from the wrapper classes called context mapping.









+------------------------------+------------------------------------------------+-------------------------------------+
|                              |                                                ||                                    |
|                              |                                                ||                                    |
|                              |                                                ||                                    |
|                              |                                                ||                                    |
|                              |                                                ||                                    |
+------------------------------+------------------------------------------------+-------------------------------------+
