Developer's Guide
*****************
The base of the class hierarchy is :class:`.Abstract` class that does nothing except providing the :meth:`.Abstract.__call__` interface with 'message' and 'context' parameters::

    def __call__(self, *message, **context):
        raise NotImplementedError('Method not implemented')

The communication between objects should use only this method for message exchange::

    a = AbstractImpl()
    a('ultimate question', mode=42)

Message Handling
================

:class:`.Handler` class is a base class for condition-event based message processing. It contains the list of condition-event pairs and uses the :meth:`.Handler.handle` method to find the best condition for the message in a certain context and return the result of the event's call for that condition. The condition and event could be objects, values, or user functions.

To add a new condition-event pair, the Handler class provides an :meth:`.Handler.on` method::

    def on(self, condition, event, *tags)

For example::

    h = Handler()
    h.on('event', lambda: True)

    print h('event')

    > True

    print h('tneve')

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

Let's see how different types of conditions work, always for message[0].

+------------------------------+-----------------------------------------------+-------------------------------------+
| Condition type               | Rank and result                               | Example                             |
+==============================+===============================================+=====================================+
| Function                     | Should return the check rank or check rank    || ``lambda *m, **c: (1,"ok")``       |
|                              | with the check result                         || any message[0]                     |
|                              |                                               ||                                    |
|                              |                                               || rank = 1,                          |
|                              |                                               || check result = "ok"                |
+------------------------------+-----------------------------------------------+-------------------------------------+
| Regular expression - match   | Length of the expression matched and match    || 'a+'                               |
|                              | result                                        || message[0] = "aa"                  |
|                              |                                               ||                                    |
|                              |                                               || rank = 2                           |
|                              |                                               || check result = "aa"                |
+------------------------------+-----------------------------------------------+-------------------------------------+
| Regular expression - search  | Same as above, but using the search method    || "b+"                               |
|                              |                                               || message[0] = "agabb"               |
|                              |                                               ||                                    |
|                              |                                               || rank = 5                           |
|                              |                                               || check result = "bb"                |
+------------------------------+-----------------------------------------------+-------------------------------------+
| String – match               | Length of the string if message[0] starts     || "stop"                             |
|                              | from the string and string itself as a result || message[0] = "stop"                |
|                              |                                               ||                                    |
|                              |                                               || rank = 4                           |
|                              |                                               || check result = "stop"              |
+------------------------------+-----------------------------------------------+-------------------------------------+
| String – search              | Same as above, but using the find method of   || "run"                              |
|                              | string class                                  || message[0] = "now run"             |
|                              |                                               ||                                    |
|                              |                                               || rank = 7                           |
|                              |                                               || check result = "run"               |
+------------------------------+-----------------------------------------------+-------------------------------------+
| Boolean value                | 0, True if message[0] equals value            || False                              |
|                              |                                               || message[0] = False                 |
|                              |                                               ||                                    |
|                              |                                               || rank = 0                           |
|                              |                                               || check result = False               |
+------------------------------+-----------------------------------------------+-------------------------------------+
| List                         | Highest rank for each list item check         || ["1", "11"]                        |
|                              |                                               || message[0] = "11"                  |
|                              |                                               ||                                    |
|                              |                                               || rank = 2                           |
|                              |                                               || check result = "11"                |
+------------------------------+-----------------------------------------------+-------------------------------------+
| Other value                  | 0 or value length if applicable, message[0]   || 8                                  |
|                              | as the result                                 || message[0] = 8                     |
|                              |                                               ||                                    |
|                              |                                               || rank = 0                           |
|                              |                                               || check result = 8                   |
+------------------------------+-----------------------------------------------+-------------------------------------+

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

Context mapping
---------------

If the condition function or event function always uses declarations like::

    def handler1(*message, **context)

the most frequent operation within such functions will be::

    if context.get('param', 'default'):
        ...

To save the developer's time, Graph-talk implements its so-called "context mapping" feature. If you need to analyze only certain values from the context, you just need to specify their names in the condition or event parameter list. So, the previous example will look like this::

    def handler1 (param='default')

If the context contains 'param' value, it will be used when calling the user function. The table below describes possible context mapping cases.

=================================   =========================================
**Function declaration**            **Call result**
---------------------------------   -----------------------------------------
``handler (*message)``	            Only the message parameter will be filled
``handler (**context)``	            Only the context parameter will be filled
``handler ()``	                    No parameters
``handler (a, b=1)``	            Corresponding parameters will be pulled from the context, default will be used if there is no such key
``handler (*message, **context)``   Default call, both parameters will be filled
non-callable value	                The value will be returned
=================================   =========================================

Usually, condition functions only accept the message to check for message[0] contents. For example, the show_me function in the previous example could be declared as::

    def show_me(**c)

The class that implements the context mapping is called :class:`.Access` and is used as a base class for :class:`.Condition` and :class:`.Event` classes. Access, in turn, is a child of the :class:`.Abstract` class.

Event Class
-----------
:class:`.Event` functions can declare any arguments or do not declare them at all. If the condition was satisfied, the condition check result will be included in the context of the event call::

    h = Handler()
    h.on("continue", do_continue)
    
    def do_continue(**context):
        ...

Event context will contain the following parameters with corresponding values:

#. :attr:`.Handler.RANK` = len("continue"), 8 in this case
#. :attr:`.Handler.CONDITION` = "continue"
#. :attr:`.Handler.EVENT` = do_continue
#. :attr:`.Handler.SENDER` = h

A special feature of Event class is :attr:`.Event.pre` and :attr:`.Event.post` properties, which can contain other events to be called before or after user function. If the pre- or post-event will return a non-empty result, this result will be used instead of the one returned by user function. For example::

    c = Condition(re.compile('a+'))
    e = Event(show_me)
    h.on_access(c, e)  # No need to wrap

    e.pre = 1

    print (h('a'))

    > 1

Pre and post properties accept any functions, which will be wrapped in the Event class and executed via the :meth:`.Event.run` method. If you want to use the Event instance as a pre/post-event, write it directly to :attr:`.Event.pre_event` or :attr:`.Event.post_event` field.

Note that if the post-event was specified, the :attr:`.Event.RESULT` context value for its call will contain the value returned by the user event function.

Handling step-by-step
---------------------

#. Define conditions and events for the handler instance using the arguments needed for checking the condition and running the event.
#. Add the condition and event via the :meth:`.Handler.on` method or via :meth:`.Handler.on_access` if you want to add :class:`.Condition` and :class:`.Event` instances.
#. :class:`.Handler` will try each condition against the incoming message and context to find the one with the highest rank. If several conditions return the same value, the first one will be used.
#. The event of the winning condition will be called, and its result will be returned from the handle method as a tuple (event_result, condition_rank, event_found).
#. If there is no condition found, the handle will return :attr:`.Handler.NO_HANDLE`. There is a way to handle all unknown messages: the Handler class provides the :attr:`.Handler.unknown_event` property, which will be called if no condition worked. Its result will be returned from the handle method.
#. By default, the __call__ method of Handler returns only the event_result value, no condition rank and so on.
#. If the :attr:`.Handler.ANSWER` context value was set to :attr:`.Handler.RANK`, __call__ would return (event_result, rank) tuple: ``a("ultimate question", mode=42, answer=Handler.RANK)``. This will be used by Selective notions.

Some examples (the code from the previous example was used) are the following::

    h.handle(['aa'], {})

    > (1, 2, 1)

    h.handle([], {})

    > (False, -1, None)

Tags
----
The :class:`.Handler` class provides a simple 'state-like' condition filter to avoid unnecessary checks. You can specify a set of tags for the condition in the :meth:`.Handler.on` method to reflect for which state it is applicable::

    h.on("move", do_move, "has_fuel", "has_direction")

The Handler instance has the set of current tags, which reflect its current state and :meth:`.Handler.update` method. Update does a very simple thing: it keeps in the condition-event pair list used by handle method only the conditions which tag set is a subset of the handler tag set.

First, update calls the :meth:`.Handler.update_tags` method. It returns the set of tags describing the current situation. If it is different from the existing set, update filters the list of active conditions and events.

If tags are {"has_fuel", "maps_loading"}, the "move" message will not be considered at all. If tags are {"has_fuel", "has_direction", "doors_closed"} – the "move" condition-event pair will be active.

For example::

    class UpdateTest(Handler):
        def __init__(self):
            super(UpdateTest, self).__init__()
            self.fixed_tags = set()

        def update_tags(self):
            return self.fixed_tags

    u = UpdateTest()

    u.on('move', Event(True), 'has_fuel', 'has_direction')

    print u('move')

    > False

    u.fixed_tags = {'has_fuel', 'maps_loading'}
    u.update()

    print u('move')

    > False

    u.fixed_tags = {'has_fuel', 'has_direction', 'doors_closed'}
    u.update()

    print u('move')

    > True

The :meth:`.Handler.update` method should be executed manually in appropriate cases. Use the :attr:`.Handler.tags` field to access the current tags.

Building and Walking the Graphs
===============================

The graph is a set of Notions and Relations. It has a root notion whose name is also the name of the graph. Both notions and relations have the same parent class: :class:`.Element`. The parent class of the :class:`.Element` class is the :class:`.Handler`.

Graph Element
-------------
As mentioned above, the process asks the element what to do next. That means sending the corresponding message to it. For the "forward" direction, the message is "next" (defined as :attr:`.Process.NEXT`); for the backward direction, the messages are "previous" (defined as :attr:`.Process.PREVIOUS`), "break" (defined as :attr:`.ParsingProcess.BREAK`), "continue" (defined as :attr:`.ParsingProcess.CONTINUE`), and "error" (defined as :attr:`.ParsingProcess.ERROR`).

The Element class uses the Handler's features to respond to process messages. It has two convenience methods: :meth:`.Element.on_forward` and :meth:`.Element.on_backward` to assign customized events to reply to the process.

As an example, :class:`.ActionNotion` uses the 'on_forward' event to specify the user function to be triggered when the process passes the notion.

Each Element belongs to a certain graph, which is set by the :attr:`.Element.owner` property. When the owner changes, Element sends the "set_owner" message to the old and new owners so they can update their internal references.

Walking the Graph
-----------------

Different elements respond differently to the :attr:`.Process.NEXT` process message.

Basic :class:`.Notion` is a leaf of the tree ("Object" in the figure below), so it does not return the next element. :class:`.ActionNotion` could trigger a user function to do something when reaching this notion.

.. figure::  images/concepts_rel.png

Basic :class:`.Relation` (an arrow in the figure above) does not reply to process messages – it just connects two elements together (subject and object). :class:`.NextRelation` replies with the :attr:`.Relation.object` to the :attr:`.Process.NEXT` message, thus providing a way to pass itself forward, from the top to the bottom of the graph. It also has the :attr:`.NextRelation.condition` to be checked before replying. If the condition is specified and False, the relation will not be passable. :class:`.ActionRelation` is similar to ActionNotion – it triggers a user function when passed.

:class:`.ComplexNotion` consists of other notions and implies the presence of all of them. It returns not just one relation but the whole "to-pass list." Some of those relations could lead to another complex notion. To support this, the process has a list of elements to visit, implemented as a queue.

.. figure::  images/guide_complex.png

For example, complex notion "A" contains "A1, A2, A3" notions; "A1" is a complex notion too and contains "A11, A12, A13" notions. The process receives ["A-A1", "A-A2", "A-A3"] list of relations from "A." When process visits "A1" and pops the first element, it receives ["A1-A11", "A1-A12", "A1-A13"]. The "to-pass" list will look like this: ["A1-A11", "A1-A12", "A1-A13", "A-A2", "A-A3"]. The process always works with the head of the queue; it takes commands/elements from it and puts back the replies from the elements.

:class:`.SelectiveNotion` is a kind of complex notion that finds the best relation to pass in the current context. It checks all of its sub-relations for the highest relevance rank and returns the best one to the process. Here, the trick is that several relations could return the same rank.

.. figure::  images/guide_selective.png

For example, selective notion "B" contains "B1, B2" notions via NextRelations without conditions. That means both "B-B1" and "B-B2" will have the same rank equal to zero. The final decision of which case is good is yet to be revealed somewhere later. So, the process needs to try both relations. If the first one fails, we will need to revert all changes to the initial state when we’ve made the decision to try "B-B1" and "B-B2". This is a general approach called lookahead. With lookahead, you try one case, and if it does not work, you try another one.

Lookahead and Error Handling
----------------------------
Each time the element makes a decision about how it should reply to the process, it considers only the message and the context. This is a very important assumption because if we ask the same thing in the same context, the result should be the same as well. Imagine that we took a wrong turn at the selective notion and several elements later found that we could not move further. What if the context had already changed? If we had had an original context state, we could have just returned to the initial point and could have tried another case (or cases)—pretty much like transactions work. This is how it works in Graph-talk, step by step:

#. The selective notion finds that there is more than one relation to try.
#. That means we need to keep the original context. This is done via a "push_context" (defined as :attr:`.StackingProcess.PUSH_CONTEXT`) message to the process. The process creates a restore point for the future and puts it to the stack.
#. Besides :attr:`.StackingProcess.PUSH_CONTEXT`, selective notion returns the first case (first relation) to try and the reference to itself to talk again later.
#. Process picks the first case and talks to it, moving forward while possible.
#. If an error is encountered (some element returned an :attr:`.ParsingProcess.ERROR` message), the process reverses its direction and starts to ask elements with not the :attr:`.Process.NEXT` but the :attr:`.ParsingProcess.ERROR` question. Elements stop to answer, and this question will finally go to the initial selective notion.
#. If the case worked fine, the process would go to selective notion as well, but without an error.
#. When selective notion is visited again with an error, it restores the context (via :attr:`.StackingProcess.POP_CONTEXT` command) and tries another case, changing the direction of the process to forward again (step 2).
#. If there was no error, selective notion just discards the stored context because it is not needed anymore (:attr:`.StackingProcess.FORGET_CONTEXT` command).

Lookahead looks a bit similar to the exception handling. The only difference is that the process does not really go back – it just changes its message. It starts asking "error" to each element in its "to-pass" list, starting from the current one until some element will handle it. If there were several nested selective notions, they would pop the saved contexts from the stack one by one. If no case worked, the "error" message would go to the higher level, and the process finishes.

If an element keeps and changes its state out of the context, it means its state cannot and will not be reverted. There is a way to store the state conveniently within the context – it will be described later.

Context and State
-----------------
The context could be used for information exchange between the elements. For example, an element may put there some data, which will be used by another element. To handle this, the following messages are used: "add_context" (defined as :attr:`.SharedProcess.ADD_CONTEXT`), "update_context" (defined as :attr:`.SharedProcess.UPDATE_CONTEXT`) and "delete_context" (defined as :attr:`.SharedProcess.DELETE_CONTEXT`). For example, an ActionRelation may say to the process, "add_context": {"warning": "under_construction"}, and another ActionRelation could use it in the handler via context mapping::

    def is_safe_road(warning):
        return None if warning else self.object

If there is a need to roll back during lookahead, all the changes in the context done through these commands will be reverted – just as the undo operation works.

If the element needs to keep in the context some private information that should not be shared but be a part of the rollback, there is a pair of commands to do this: "set_state" (defined as :attr:`.StatefulProcess.SET_STATE`) and "clear_state" (defined as :attr:`.StatefulProcess.CLEAR_STATE`). First, one will set the specified value as a state for the current element. When this element is visited, its state will be sent to it as part of the context in the :attr:`.StatefulProcess.STATE` value. No other element will see this state. If the state is not needed anymore, just clear it.

For example, the complete selective notion reply for lookahead looks like this, given that the "case" is the first relation to try, and "cases" is the list of all other relations with the same rank: ["push_context", {"set_state": {"cases": cases}}, case, self].

The state will be sent as part of the context, so context mapping could be used to handle it as well. Note that if the state is a complex value like a dictionary, its content will not be reverted. Only the top-level value will be rolled back. An example of how the state works for loops is below.

Looping
-------
Let's say that some complex notion should appear exactly N times. This is what :class:`.LoopRelation` does. It repeats its object according to the condition specified. Here are the supported conditions:

#. Integer N
#. Ranges M, N (from M to N); M, ... (at least M and more); ..., N (0 to N).
#. Wildcards: "*" (from 0 to an infinite number of times), "?" (0 or 1 time), "+" (more than one time)
#. User function
#. TRUE_CONDITION (infinite loop)

.. figure::  images/concepts_loop.png

Loop uses both state and lookahead. In the simplest case, it says to the process, "set my state to the number of iteration, then take the object, and come back to me after all." When the process comes back to the loop again (note – it still is a forward direction), it checks the iteration number; if it is within the bounds, it repeats the cycle with an iteration of + 1.

If there is a :meth:`.LoopRelation.is_flexible` (without an exact number of repetitions) condition used, like "*", it works in a bit of a different manner. We do not know how many times the Object should appear, so the loop says, "push the context, then go to the object, and come back to me." If there was no error – fine, at least one iteration worked. However, there may be more Objects, so we need to iterate again, now with a different context – the one we have now. The old context is discarded, and a new one is put to the stack. Reusing the transaction analogy, try several payments: if the first one works, update the balance, and try another one.

If an error occurs and conditions were satisfied, the loop restores the last-known good context and ends, changing the direction of the process to forward again. Otherwise, it clears the state and keeps the error propagating further.

Loops could handle :attr:`.ParsingProcess.CONTINUE` and :attr:`.ParsingProcess.BREAK` messages as most programming languages do. If the element says "break," the process changes its question from "next" to "break" and keeps going until it finds someone who can handle it. First, the loop consumes it and does the appropriate handling, stopping the iterations and clearing the state. It also changes the direction to forward.

Building the Graphs
-------------------
:class:`.GraphBuilder` is the class to construct graphs. It allows chained operations, so the building process looks like this::

    builder = GraphBuilder('New Graph')

    builder.next_rel().complex('initiate').next_rel().notion('remove breaks').back().back().next_rel().act('ignite', 1)

    print Process()(builder.graph)

    > 1

This is the graph: 

.. figure::  images/guide_builder.png

The builder has used the :attr:`.GraphBuilder.current` element to attach the result of the operation performed. The new builder will create an empty graph with the root notion under the specified name and use it as a current element. Adding the next relation will use the current notion element as a subject. Adding a new notion after the relation will attach it as an object to the current relation, and so on. Back operation will traverse the current element back depending on its type.

To access the graph itself, use the :attr:`.GraphBuilder.graph` property. The graph allows searching for the notions by name and relations by object and subject.

For example, to find all the notions with names that start from "i" in the graph above use ``builder.graph.notions(re.compile(‘i+’))``. You can pass user function to the search as well.

For example::

    print builder.graph.notions(re.compile('i*'))

    > [<ComplexNotion("initiate", {"New Graph"})>, <ActionNotion("ignite", {"New Graph"})>]

To find all relations with the same subject, use ``builder.graph.relations({Relation.SUBJECT: subject_value})``.

GraphBuilder allows setting the current element directly via the :meth:`.GraphBuilder.set_current` method to continue building from the certain place. Check its API description for other operations.
