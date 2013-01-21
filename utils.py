# Class to track dict changes: add, change and delete key
# Operations of the same type are not stacked, latter one replaces earlier of the same type
class DictChangeOperation(object):
    Operations = ('add', 'set', 'delete')
    ADD, SET, DELETE = Operations

    def __init__(self, type, key, value = None):

        if type not in self.Operations:
            raise ValueError(type)

        self._type, self._key = type, key
        self._value, self._old_value = value, None

    def do(self, target_dict):
        if self._type == self.SET and not self._key in target_dict:
            self._type = self.ADD # No old value, so it is rather add

        if self._type == self.ADD:
            target_dict[self._key] = self._value

        elif self._type == self.SET:
            self._old_value = target_dict[self._key]
            target_dict[self._key] = self._value

        else:
            self._old_value = target_dict[self._key]
            del target_dict[self._key]

    def undo(self, target_dict):
        if self._type == self.ADD:
            del target_dict[self._key]
        else:
            target_dict[self._key] = self._old_value

    def __hash__(self):
        return hash(self._type + str(self._key))

    def __eq__(self, other):
        return self._type == other._type and self._key == other._key

    def __str__(self):
        s = '%s %s' % (self._type, self._key)
        if self._type == self.ADD or self._type == self.SET:
            s += '=%s' % self._value

        if self._type == self.SET:
            s += '<-%s' %self._old_value

        return s

    def __repr__(self):
        return self.__str__()

    def store(self, ops_dict, do_target_dict = None):
        ops_dict[self.__hash__()] = self

        if do_target_dict:
            self.do(do_target_dict)

    @staticmethod
    def do_all(ops_dict, target_dict):
        for op in ops_dict.itervalues():
            op.do(target_dict)

    @staticmethod
    def undo_all(ops_dict, target_dict):
        for op in ops_dict.itervalues():
            op.undo(target_dict)
