"""
.. module:: gt.util
   :platform: Unix, Windows
   :synopsis: Graph-talk utility classes

.. moduleauthor:: Stas Kravets (krvss) <stas.kravets@gmail.com>

"""

import sys

if sys.version > '3':
    long = int
    basestring = str


class DictChangeOperation(object):
    """
    Class to track dict changes: add, change and delete key
    Operations of the same type are not stacked, latter one replaces earlier of the same type
    """
    Operations = ('add', 'set', 'delete')
    ADD, SET, DELETE = Operations

    def __init__(self, dict, type, key, value=None):
        self._dict, self._type, self._key = dict, type, key
        self._value, self._old_value = value, None

    def do(self):
        if self._type == self.SET and not self._key in self._dict:
            self._type = self.ADD  # No old value, so it is rather add

        if self._type == self.ADD:
            self._dict[self._key] = self._value

        elif self._type == self.SET:
            self._old_value = self._dict[self._key]
            self._dict[self._key] = self._value

        elif self._type == self.DELETE:
            self._old_value = self._dict[self._key]
            del self._dict[self._key]

        else:
            raise ValueError(type)

    def undo(self):
        if self._type == self.ADD:
            del self._dict[self._key]
        else:
            self._dict[self._key] = self._old_value

    def merge(self, other):
        if other._dict == self._dict and other._type == self._type == self.SET and other._key == self._key:
            self._value = other._value
            return True

        return False

    def __str__(self):
        s = '%s %s' % (self._type, self._key)
        if self._type == self.ADD or self._type == self.SET:
            s += '=%s' % self._value

        if self._type == self.SET:
            s += '<-%s' %self._old_value

        return s

    def __repr__(self):
        return self.__str__()


class DictChangeGroup(object):
    """
    Stack of dictionary changes for keeping of changes and mass operations
    """
    def __init__(self):
        self._stack = []

    def add(self, change, do=True):
        if not self._stack or not self._stack[-1].merge(change):
            self._stack.append(change)

        if do:
            change.do()

    def do(self):
        for c in self._stack:
            c.do()

    def undo(self):
        for c in self._stack.__reversed__():
            c.undo()


class NotifyDict(dict):
    """
    Dictionary wrapper to notify about updates
    """
    __slots__ = ['callback']

    def __init__(self, callback, iterable=None, **kwargs):
        self.callback = callback
        super(NotifyDict, self).__init__(iterable, **kwargs)

    def _wrap(method):

        def wrapper(self, *args, **kwargs):
            result = method(self, *args, **kwargs)
            self.callback()
            return result

        return wrapper

    __delitem__ = _wrap(dict.__delitem__)
    __setitem__ = _wrap(dict.__setitem__)

    clear = _wrap(dict.clear)
    pop = _wrap(dict.pop)
    popitem = _wrap(dict.popitem)
    setdefault = _wrap(dict.setdefault)
    update = _wrap(dict.update)


class NotifyList(list):
    """
    List wrapper to notify about updates
    """
    __slots__ = ['callback']

    def __init__(self, callback, iterable=None):
        self.callback = callback
        if iterable:
            super(NotifyList, self).__init__(iterable)
        else:
            super(NotifyList, self).__init__()

    def _wrap(method):

        def wrapper(self, *args, **kwargs):
            result = method(self, *args, **kwargs)
            self.callback()
            return result

        return wrapper

    __delitem__ = _wrap(list.__delitem__)
    __setitem__ = _wrap(list.__setitem__)

    if hasattr(list, '__delslice__'):
        __delslice__ = _wrap(list.__delslice__)
    if hasattr(list, '__setslice__'):
        __setslice__ = _wrap(list.__setslice__)

    __add__ = _wrap(list.__add__)
    __iadd__ = _wrap(list.__iadd__)
    __imul__ = _wrap(list.__imul__)
    __mul__ = _wrap(list.__mul__)

    append = _wrap(list.append)
    extend = _wrap(list.extend)
    insert = _wrap(list.insert)
    remove = _wrap(list.remove)
    reverse = _wrap(list.reverse)
    sort = _wrap(list.sort)
    pop = _wrap(list.pop)


# Utility functions #
def is_number(n):
    return type(n) in (int, long)


def is_list(l):
    return isinstance(l, list) or isinstance(l, tuple)


def is_regex(r):
    return type(r).__name__ == 'SRE_Pattern'


def is_string(s):
    return isinstance(s, basestring)


def has_first(l, value):
    return l and l[0] == value


def has_keys(dictionary, *keys):
    for key in keys:
        if not key in dictionary:
            return False

    return True


def get_len(o):
    l = -1
    try:
        l = len(o)
    finally:
        return l


def tupled(*args):
    res = ()
    for arg in args:
        res += tuple(arg) if is_list(arg) else (arg, )

    return res


def get_object_name(obj):
    return obj.__name__ if hasattr(obj, '__name__') else str(obj)


def get_content(filename):
    with open(filename) as f:
        return f.read()
