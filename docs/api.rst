Graph-talk API
**************

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

.. autoclass:: Event
    :show-inheritance:
    :members:
    :special-members: __init__, RESULT

.. autoclass:: TrueCondition
    :show-inheritance:

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
    :special-members: __init__
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
    :special-members: __init__
    :members:
