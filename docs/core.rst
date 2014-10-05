Graph-talk Core API
*******************

.. automodule:: gt.core

Base Classes
============

.. autoclass:: Abstract
   :members: __call__

.. autoclass:: Access
    :show-inheritance:
    :members: __init__, __call__, setup,  get_access, CALL, ABSTRACT, FUNCTION, VALUE, OTHER, value, mode, spec

.. autoclass:: Condition
    :show-inheritance:
    :members:
    :special-members: __init__, NUMBER, LIST, DICT, STRING, REGEX, BOOLEAN, NO_CHECK

.. autoclass:: TrueCondition
    :show-inheritance:

.. autoclass:: Event
    :show-inheritance:
    :members:
    :special-members: __init__, RESULT

.. autoclass:: Handler
    :show-inheritance:
    :members:
    :special-members: __init__, unknown_event, active_events, __call__, ANSWER, SENDER, CONDITION, EVENT, RANK, NO_HANDLE

Graph Classes
=============

.. autoclass:: Element
    :show-inheritance:
    :members:
    :special-members: __init__, NEXT, PREVIOUS, OWNER, SET_PREFIX, NAME, OLD_VALUE, NEW_VALUE, SEP, FORWARD, BACKWARD

.. autoclass:: Notion
    :show-inheritance:
    :special-members: __init__
    :members:

.. autoclass:: ActionNotion
    :show-inheritance:
    :special-members: __init__
    :members:

.. autoclass:: ComplexNotion
    :show-inheritance:
    :special-members: __init__
    :members:

.. autoclass:: Relation
    :show-inheritance:
    :members:
    :special-members: __init__, SUBJECT, OBJECT

.. autoclass:: NextRelation
    :show-inheritance:
    :special-members: __init__
    :members:

.. autoclass:: ActionRelation
    :show-inheritance:
    :special-members: __init__
    :members:

.. autoclass:: ParsingRelation
    :show-inheritance:
    :special-members: __init__
    :members:

.. autoclass:: SelectiveNotion
    :show-inheritance:
    :special-members: __init__, CASES
    :members:

.. autoclass:: LoopRelation
    :show-inheritance:
    :special-members: __init__, ITERATION
    :members:

.. autoclass:: Graph
    :show-inheritance:
    :special-members: __init__
    :members:

.. autoclass:: GraphBuilder
    :show-inheritance:
    :special-members: __init__, __getitem__
    :members:

Process Classes
===============
.. autoclass:: Process
    :show-inheritance:
    :members: context, message, query, current, skip, can_push_queue, do_queue_push, can_pop_queue, do_queue_pop,
     do_query, setup_events, can_clear_message, do_clear_message, do_finish, update_tags, on_new, on_resume, handle,
     NEW, OK, STOP, QUERY, EMPTY_MESSAGE, CURRENT, MESSAGE

.. autoclass:: SharedProcess
    :show-inheritance:
    :members:
    :special-members: ADD_CONTEXT, UPDATE_CONTEXT, DELETE_CONTEXT

.. autoclass:: StackingProcess
    :show-inheritance:
    :members:
    :special-members: PUSH_CONTEXT, POP_CONTEXT, FORGET_CONTEXT, TRACKING

.. autoclass:: StatefulProcess
    :show-inheritance:
    :members:
    :special-members: STATE, SET_STATE, CLEAR_STATE, HAS_STATES

.. autoclass:: ParsingProcess
    :show-inheritance:
    :members:
    :special-members: ERROR, PROCEED, BREAK, CONTINUE
