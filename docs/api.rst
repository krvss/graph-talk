Graph-talk API
**************

.. automodule:: gt.core

Base Classes
============

.. autoclass:: Abstract
   :members: __call__

.. autoclass:: Access
    :show-inheritance:
    :members: __init__, __call__, setup,  get_access

.. autoclass:: Condition
    :show-inheritance:
    :members: __init__, setup, list

.. autoclass:: Event
    :show-inheritance:
    :members: __init__, run, pre, post

.. autoclass:: TrueCondition
    :show-inheritance:

.. autoclass:: Handler
    :show-inheritance:
    :members:
    :special-members: __call__

Graph Classes
=============

.. autoclass:: Element
    :show-inheritance:
    :special-members: __init__
    :members:

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
    :special-members: __init__
    :members:

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
    :special-members: __init__
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
