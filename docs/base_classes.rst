.. automodule:: gt.core

Base Classes
=========================

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