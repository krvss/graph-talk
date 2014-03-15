import unittest

from debug import *

import re


# Test functions
def state_v_starter(**context):
    if STATE in context and 'v' in context[STATE]:
        return {SET_STATE: {'v': context[STATE]['v'] + 1}}
    else:
        return {SET_STATE: {'v': 1}}


def state_v_checker(**context):
    if STATE in context and 'v' in context[STATE]:
        return STOP
    else:
        return OK  # Others' state is not visible


def common_state_acc(**context):
    if 'acc' in context:
        return {UPDATE_CONTEXT: {'acc': context['acc'] + 1}}
    else:
        return {ADD_CONTEXT: {'acc': 1}}


def has_notification(**context):
    if STATE in context and NOTIFICATIONS in context[STATE]:
        return context[STATE][NOTIFICATIONS]['note']
    else:
        return False


def check_test_result(test_case, process, current, length):
    test_case.assertNotIn(current, process.states)
    test_case.assertFalse(process._context_stack)
    test_case.assertEqual(process.current, current)
    test_case.assertEqual(process.parsed_length, length)


def check_loop_result(test, process, loop, counter):
    check_test_result(test, process, loop, counter)

    if counter > 0:
        test.assertEqual(process.context['acc'], counter)
    else:
        test.assertNotIn('acc', process.context)


class TestCalls(Abstract):
    def __init__(self):
        self.last_message = None
        self.last_context = None

    def return_false(self):
        return False

    def return_true(self):
        return True

    def parse(self, *message, **context):
        self.last_message = message
        self.last_context = context

        return True


class UtTests(unittest.TestCase):

    def test_1_abstract(self):
        with self.assertRaises(NotImplementedError):
            Abstract().parse()

        abstract = TestCalls()
        self.assertEqual(abstract.parse(), abstract())

        # Access test
        # Function
        access = Access(lambda l: l)
        self.assertEqual(access.mode, Access.FUNCTION)
        self.assertIsInstance(access.spec, ArgSpec)

        # Abstract
        access = Access(abstract)
        self.assertEqual(access.mode, Access.CALL)
        self.assertEquals(access.spec, Access.ABSTRACT)

        # Number
        access = Access(1)
        self.assertEqual(access.mode, Access.VALUE)
        self.assertEquals(access.spec, Access.NUMBER)

        # List
        access = Access([1])
        self.assertEqual(access.mode, Access.VALUE)
        self.assertEquals(access.spec, Access.LIST)

        # List - 2
        access = Access((1, 2))
        self.assertEqual(access.mode, Access.VALUE)
        self.assertEquals(access.spec, Access.LIST)

        # String
        s = 'string'
        access = Access(s)
        self.assertEqual(access.mode, Access.VALUE)
        self.assertEquals(access.spec, Access.STRING)
        self.assertEqual(access.value, s)

        access = Access(s, True)
        self.assertEqual(access.mode, Access.VALUE)
        self.assertEquals(access.spec, Access.STRING)
        self.assertEqual(access.value, s.upper())

        # Regex
        access = Access(re.compile('.'))
        self.assertEqual(access.mode, Access.VALUE)
        self.assertEquals(access.spec, Access.REGEX)

        # Other
        access = Access(object())
        self.assertEqual(access.mode, Access.VALUE)
        self.assertEquals(access.spec, Access.OTHER)

        # Access and Get
        self.assertEqual(Access(lambda: 1).access([], {}), 1)
        self.assertEqual(Access(lambda *m: m[0]).access([2], {}), 2)
        self.assertEqual(Access(lambda *m, **c: c[m[0]]).access(['3'], {'3': 3}), 3)
        self.assertEqual(Access(lambda **c: c['4']).access(['4'], {'4': 4}), 4)
        self.assertEqual(Access(lambda a, b: a + b).access(['5'], {'a': 2, 'b': 3, 'c': 4}), 5)
        self.assertEqual(Access(lambda a, b=1: a + b).access(['6'], {'a': 3}), 4)
        self.assertEqual(Access(abstract.return_true).access(['7'], {'a': 4}), True)

        # Conditions
        tc = TestCalls()

        cant_handle = (-1, None)
        condition1 = Condition(lambda *m: m[0] == 1)
        condition2 = Condition(lambda *m, **c: (m[0], len(c)))
        condition3 = Condition(lambda: 4)
        condition4 = Condition(tc.return_true)
        condition5 = Condition(tc.return_false)

        self.assertEquals(condition1.check([1], {}), (0, True))
        self.assertEquals(condition1.check([2], {}), cant_handle)

        self.assertEquals(condition2.check([3], {'1': 1}), (3, 1))
        self.assertEquals(condition3.check([], {}), (4, 4))

        self.assertEquals(condition4.check([], {}), (0, True))
        self.assertEquals(condition5.check([], {}), cant_handle)

        condition_r = Condition(re.compile('a+'))

        self.assertEquals(condition_r.check(['a'], {})[0], 1)
        self.assertEquals(condition_r.check(['ab'], {})[0], 1)
        self.assertEquals(condition_r.check(['b'], {}), cant_handle)

        condition_s = Condition('aa')
        self.assertEquals(condition_s.check(['aa'], {}), (2, 'aa'))
        self.assertEquals(condition_s.check(['aaa'], {}), (2, 'aa'))
        self.assertEquals(condition_s.check(['b'], {}), cant_handle)

        condition_l = Condition(('aa', 'bb'))
        self.assertEquals(condition_l.check(['bb'], {}), (2, 'bb'))
        self.assertEquals(condition_l.check(['c'], {}), cant_handle)
        self.assertEqual(condition_l.value, ('aa', 'bb'))
        self.assertEqual(condition_l.list[0].spec, Access.STRING)
        self.assertEqual(condition_l.list[1].value, condition_l.value[1])

        condition_l = Condition(('a', 'bb'), True)
        self.assertEquals(condition_l.check(['bB'], {}), (2, 'BB'))
        self.assertEquals(condition_l.check(['aa'], {}), (1, 'A'))

        condition_r = Condition((re.compile('a+'), re.compile('aa'), 'aa'))
        self.assertEquals(condition_r.check(['aa'], {}), (2, 'aa'))

        condition_n = Condition(1)
        self.assertEquals(condition_n.check([1], {}), (0, 1))
        self.assertEquals(condition_n.check([0], {}), cant_handle)

        condition = Condition(lambda: (1, 2, 3))
        self.assertEquals(condition.check([], {}), ((1, 2, 3), (1, 2, 3)))

        # Access
        access = Access(tc.return_false)
        self.assertEquals(access.access([], {}), False)

        access = Access(lambda: True)
        self.assertTrue(access.access([], {}))

        access = Access((1, 2))
        self.assertEqual(access.access([], {}), (1, 2))

        access = Access(1)
        self.assertEquals(access.access([], {}), 1)

        access = Access(tc)
        self.assertTrue(access.access([], {}))

    def test_2_handler(self):
        h = Handler()

        handler1 = lambda: True
        handler2 = True

        # Generic 'on'
        h.on('event', handler1)

        self.assertIn(('event', handler1), h.handlers)

        # Cannot add duplicates
        h.on('event', handler1)

        self.assertEqual(len(h.handlers), 1)

        # Can add non-callable
        h.on('1', 1)
        self.assertEqual(h.get_handlers('1'), [1])

        # On any
        h.on_any(handler1)

        self.assertEqual(len(h.handlers), 3)
        self.assertIn(handler1, h.handlers)

        # No duplicates on on_any too
        h.on_any(handler1)

        self.assertEqual(len(h.handlers), 3)

        # Generic off
        h.off('event', handler1)

        self.assertNotIn(('event', handler1), h.handlers)

        # Off-any
        h.on('event', handler1)
        h.off_any(handler1)

        self.assertNotIn(handler1, h.handlers)
        self.assertIn(('event', handler1), h.handlers)

        # Off-conditon
        h.on('cond', 1)
        h.on('cond', 2)
        h.on('cond2', 2)

        h.off_condition('cond')

        self.assertFalse(h.get_handlers('cond'))
        self.assertEqual(h.get_handlers('cond2'), [2])

        h.off_condition('cond2')
        self.assertFalse(h.get_handlers('cond'))

        # Off-handler
        h.on_any(handler1)

        h.off_handler(handler1)
        h.off_handler(1)
        self.assertEqual(len(h.handlers), 0)

        # Get handlers
        h.on('event', handler1)
        h.on('event', handler2)

        h.on_any(handler2)

        self.assertEqual(h.get_handlers('event'), [handler1, handler2])
        self.assertEqual(h.get_handlers(), [handler2])

        # Smart calls
        self.assertEqual(h.var_call_result(lambda: 1, [], {}), 1)
        self.assertEqual(h.var_call_result(lambda *m: m[0], [2], {}), 2)
        self.assertEqual(h.var_call_result(lambda *m, **c: c[m[0]], ['3'], {'3': 3}), 3)
        self.assertEqual(h.var_call_result(lambda **c: c['4'], ['4'], {'4': 4}), 4)
        self.assertEqual(h.var_call_result(lambda a, b: a + b, ['5'], {'a': 2, 'b': 3, 'c': 4}), 5)
        self.assertEqual(h.var_call_result(lambda a, b=1: a + b, ['6'], {'a': 3}), 4)

        # Conditions
        condition1 = lambda *m: m[0] == 1
        condition2 = lambda *m, **c: (m[0], len(c))
        condition3 = lambda: 4

        tc = TestCalls()

        cant_handle = (-1, None)

        self.assertEquals(h.can_handle(condition1, [1], {}), (0, True))
        self.assertEquals(h.can_handle(condition1, [2], {}), cant_handle)

        self.assertEquals(h.can_handle(condition2, [3], {'1': 1}), (3, 1))
        self.assertEquals(h.can_handle(condition3, [], {}), (4, 4))

        self.assertEquals(h.can_handle(tc.return_true, [], {}), (0, True))
        self.assertEquals(h.can_handle(tc.return_false, [], {}), cant_handle)

        condition_r = re.compile('a+')

        self.assertEquals(h.can_handle(condition_r, ['a'], {})[0], 1)
        self.assertEquals(h.can_handle(condition_r, ['ab'], {})[0], 1)
        self.assertEquals(h.can_handle(condition_r, ['b'], {}), cant_handle)

        self.assertEquals(h.can_handle('aa', ['aa'], {}), (2, 'aa'))
        self.assertEquals(h.can_handle('aa', ['aaa'], {}), (2, 'aa'))
        self.assertEquals(h.can_handle('b', ['aa'], {}), cant_handle)

        self.assertEquals(h.can_handle(('aa', 'bb'), ['bb'], {}), (2, 'bb'))
        self.assertEquals(h.can_handle(('aa', 'bb'), ['c'], {}), cant_handle)

        h.ignore_case = True
        self.assertEquals(h.can_handle(('aa', 'bb'), ['bB'], {}), (2, 'BB'))
        self.assertEquals(h.can_handle(('A', 'bb'), ['aa'], {}), (1, 'A'))
        h.ignore_case = False

        condition_r_2 = re.compile('aa')
        self.assertEquals(h.can_handle((condition_r, condition_r_2, 'aa'), ['aa'], {}), (2, 'aa'))

        self.assertEquals(h.can_handle(1, [1], {}), (0, 1))
        self.assertEquals(h.can_handle(1, [0], {}), cant_handle)

        self.assertEquals(h.can_handle(lambda: (1, 2, 3), [], {}), (0, (1, 2, 3)))

        # Run handler
        self.assertEquals(h.run_handler(tc.return_false, [], {}), (False, tc.return_false))
        self.assertTrue(h.run_handler(handler1, [], {})[0])
        self.assertEqual(h.run_handler((1, 2), [], {}), ((1, 2), (1, 2)))
        self.assertEquals(h.run_handler(1, [], {}), (1, 1))

        # Handle itself
        # Longest wins
        del h.handlers[:]
        h.on('event', handler1)
        h.on('event1', handler2)
        r = h.handle('event')

        self.assertTrue(r[0])
        self.assertEqual(r[1], len('event'))
        self.assertEqual(r[2], handler1)

        r = h.handle('event1')

        self.assertTrue(r[0])
        self.assertEqual(r[1], len('event1'))
        self.assertEqual(r[2], handler2)

        self.assertFalse(h('eve'))

        # Any event - no-condition wins
        handler3 = lambda *m, **c: 'handler3'
        h.on_any(handler3)

        r = h.handle('even')
        self.assertEqual(r[0], 'handler3')
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2], handler3)

        # Specific event beats 'any' handler
        r = h.handle('event')
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], len('event'))
        self.assertEqual(r[2], handler1)

        # For any events first default wins
        h.on_any(tc.return_true)

        r = h.handle('even')
        self.assertEqual(r[0], 'handler3')
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2], handler3)

        # Call parameters check
        # Sender
        handler4 = lambda **c: c[SENDER]
        h.on(SENDER, handler4)

        r = h.handle(SENDER)
        self.assertEquals(r, (h, len(SENDER), handler4))

        r = h.handle(SENDER, **{SENDER: 'test'})
        self.assertEquals(r, ('test', len(SENDER), handler4))

        # Condition & rank
        handler5 = lambda **c: (c[RANK], c[CONDITION])

        h.on(CONDITION, handler5)

        r = h.handle(CONDITION)
        self.assertEquals(r, ((len(CONDITION), CONDITION), len(CONDITION), handler5))

        # Answer check
        r = h('event', **{ANSWER: RANK})
        self.assertEquals(r, (True, len('event')))

    def test_3_talker(self):
        t = Talker()
        tc = TestCalls()

        # Names
        self.assertEqual(t.add_prefix('event', '1'), SEP.join(['1', 'event']))
        self.assertEqual(get_object_name(t.add_prefix), 'add_prefix')
        self.assertEqual(t.add_prefix(['event', 1], POST_PREFIX), ('post_event', 1))
        self.assertEqual(t.add_prefix('post_event', POST_PREFIX), 'post_event')
        self.assertEqual(t.add_prefix(['post_event'], POST_PREFIX), ('post_event', ))

        self.assertEqual(t.remove_prefix('e', 'p'), None)
        self.assertEqual(t.remove_prefix('p_e_v', 'p'), 'e_v')
        self.assertEqual(t.remove_prefix(['p_e']), 'e')

        # Silent
        self.assertTrue(t.is_silent(PRE_PREFIX))
        self.assertTrue(t.is_silent(POST_PREFIX))
        for s in SILENT:
            self.assertTrue(t.is_silent(s))

        self.assertFalse(t.is_silent('loud'))
        self.assertFalse(t.is_silent(1))

        # Handling
        handler1 = 'handler1'

        # Stopping before return
        t.on('event', tc.return_true)
        t.on('pre_event', handler1)

        r = t.handle('event')
        self.assertEqual(r[0], 'handler1')
        self.assertEqual(r[1], len('event'))
        self.assertEqual(r[2], handler1)

        # Empty message - checking handler name
        t.on(lambda *m: len(m) == 0, tc.return_true)
        t.on('pre_return_true', handler1)

        r = t.handle()
        self.assertEqual(r[0], 'handler1')
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2], handler1)

        t.off('pre_return_true', handler1)

        r = t.handle()
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2], tc.return_true)

        # Non-callable handler - checking name
        t.on(1, 1)
        t.on('pre_1', 2)

        r = t.handle(1)
        self.assertEqual(r[0], 2)
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2], 2)

        t.off_handler(2)
        r = t.handle(1)
        self.assertEqual(r[0], 1)
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2], 1)

        # Overriding result
        t.off('pre_event', handler1)

        handler2 = lambda **c: 'handler2' if (c.get(RESULT) and c.get(RANK) == len('post_event')
                                                       and c.get(HANDLER) == tc.return_true) else None
        t.on('post_event', handler2)

        r = t.handle('event')
        self.assertEqual(r[0], 'handler2')
        self.assertEqual(r[1], len('event'))
        self.assertEqual(r[2], handler2)

        # Now clean run
        t.off('post_event', handler2)

        r = t.handle('event')
        self.assertTrue(r[0])
        self.assertEqual(r[1], len('event'))
        self.assertEqual(r[2], tc.return_true)

        # Recursion test
        t.on('r', lambda **c: c[SENDER].handle('r', **c))
        self.assertTrue(t.handle('r'))

        # Result test
        t.on('pre_result', 'handler3')  # Will not be called
        t.on(RESULT, 'handler4')
        self.assertEqual(t('event'), 'handler4')

        t.on(UNKNOWN, handler1)
        self.assertEqual(t('strange'), 'handler1')

    def test_4_element(self):
        e = Element()
        tc = TestCalls()

        # Can change property or not
        self.assertFalse(e.can_set_property('x'))
        self.assertFalse(e.can_set_property('set_owner'))
        self.assertFalse(e.can_set_property('set_owner', **{OLD_VALUE: '1'}))
        self.assertFalse(e.can_set_property('set_owner', **{OLD_VALUE: '1', NEW_VALUE: None}))

        self.assertTrue(e.can_set_property('set_owner', **{OLD_VALUE: '1', NEW_VALUE: '2'}))

        # Preventing the change
        e.on('pre_set_owner', tc.return_true)
        e.owner = tc
        self.assertIsNone(e.owner)

        # Allowing the change and verifying data
        e.off_handler(tc.return_true)
        e.owner = tc

        self.assertEqual(e.owner, tc)
        self.assertEqual(tc.last_message, ('set_owner', ))
        self.assertEqual(tc.last_context[CONDITION], 'owner')
        self.assertEqual(tc.last_context[HANDLER], e.do_set_property)
        self.assertEqual(tc.last_context[OLD_VALUE], None)
        self.assertEqual(tc.last_context[NEW_VALUE], tc)
        self.assertEqual(tc.last_context[SENDER], e)

        # Allowing the change to non-abstract
        self.assertTrue(e.change_property('owner', 1))
        self.assertFalse(e.change_property('owner', 1))

        self.assertEqual(e.owner, 1)

        # Move test
        # Forward
        handler1 = lambda *m: m[0] if m[0] in FORWARD else None

        e.on_forward(handler1)

        self.assertEqual(e(NEXT), NEXT)

        e.off_forward()

        self.assertTrue(e(NEXT) is False)

        self.assertFalse(e.is_forward(None))
        self.assertTrue(e.is_forward([NEXT]))
        self.assertFalse(e.is_forward([]))

        # Backward
        handler2 = lambda *m: m[0] if m[0] in BACKWARD else None
        e.on_backward(handler2)

        self.assertEqual(e(PREVIOUS), PREVIOUS)

        e.off_backward()

        self.assertTrue(e(PREVIOUS) is False)

        self.assertFalse(e.is_backward(None))
        self.assertTrue(e.is_backward([PREVIOUS]))
        self.assertFalse(e.is_backward([]))

    def test_5_objects(self):
        # Notions test
        n1 = Notion('n1')
        n2 = Notion('n2')
        n1.owner = n2

        self.assertEqual(n1.name, 'n1')
        self.assertEqual(n1.__str__(), '"' + n1.name + '"')
        self.assertEqual(n1.__repr__(), '<' + get_object_name(n1.__class__) + '("' + n1.name + '", "' + n2.name + '")>')
        self.assertEqual(n1.owner, n2)

        n1.owner = None

        # Relations test
        r1 = Relation(n1, n2)

        # Generic relation test
        self.assertEqual(r1.subject, n1)
        self.assertEqual(r1.object, n2)

        self.assertEqual(r1.__str__(), '<"n1" - "n2">')
        self.assertEqual(r1.__str__(), r1.__repr__())

        # Complex notion test
        cn = ComplexNotion('cn')
        r1.subject = cn

        # If relation is only one ComplexNotion should return it, not a list
        self.assertEqual(cn(NEXT), r1)

        r2 = Relation(n2, n1)
        r2.subject = cn

        # If there is more than 1 relation ComplexNotion should return the list
        self.assertEqual(cn(NEXT), (r1, r2))

        r2.subject = n2
        self.assertEqual(len(cn.relations), 1)

        # Trying direct calls to relate
        r3 = Relation(n1, n2)
        self.assertFalse(cn.do_relation(**{OLD_VALUE: None, SENDER: r3, NEW_VALUE: None}))
        self.assertFalse(cn.do_relation(**{OLD_VALUE: cn, SENDER: r3, NEW_VALUE: None}))

        self.assertTrue(cn.do_relation(**{OLD_VALUE: None, SENDER: r3, NEW_VALUE: cn}))
        self.assertFalse(cn.do_relation(**{OLD_VALUE: None, SENDER: r3, NEW_VALUE: cn}))
        self.assertTrue(cn.do_relation(**{OLD_VALUE: cn, SENDER: r3, NEW_VALUE: None}))

        # Unrelating
        cn2 = ComplexNotion('cn2')
        r1.subject = cn2

        self.assertEqual(r1.subject, cn2)
        self.assertNotIn(r1, cn.relations)
        self.assertIn(r1, cn2.relations)

        # Next test
        nr = NextRelation(n1, n2)
        self.assertEqual(nr(NEXT), n2)

        nr.condition = lambda **c: 'event' in c
        nr.object = [1]
        self.assertListEqual(nr(NEXT, event=1), nr.object)

        self.assertTrue(nr(event=1) is False)
        self.assertTrue(nr(NEXT) is False)

        # Action notion test
        na = ActionNotion('action', 'action')
        self.assertEquals(na(NEXT), na.name)
        self.assertEqual(na.action, na.name)

        na.action = 2
        self.assertEquals(na(NEXT), 2)

        na.off_forward()
        self.assertIsNone(na.action)

        # Action relation test
        ar = ActionRelation('subj', 'obj', lambda: True)

        self.assertEqual(ar(NEXT), (True, ar.object))
        ar.action = None

        self.assertEqual(ar(NEXT), ar.object)

        ar.action = 3

        self.assertEqual(ar(NEXT), (3, ar.object))

        ar.object = None

        self.assertEqual(ar(NEXT), 3)

    def test_6_process(self):
        process = Process()

        # Testing the default
        n = Notion('N')

        process.context = {'preserved': True}
        r = process(n, test='process_default')

        self.assertTrue(r)
        self.assertEquals(process.current, n)
        self.assertEquals(len(process._queue), 1)
        self.assertFalse(process.message)
        self.assertTrue(process.context.get('preserved'))

        # Testing the unknown
        strange = 'strange'
        n.on_forward(strange)

        r = process(NEW, n, test='process_unknown')
        self.assertTrue(r is False)
        self.assertEquals(process.current, n)
        self.assertEquals(len(process._queue), 1)
        self.assertTrue(process.message[0], strange)
        self.assertNotIn('preserved', process.context)

        # We really stuck
        r = process(test='process_unknown_2')
        self.assertTrue(r is False)
        self.assertEquals(process.current, n)
        self.assertEquals(len(process._queue), 1)
        self.assertTrue(process.message[0], strange)

        # Now we are good
        r = process(NEW, test='process_new')
        self.assertTrue(r is None)
        self.assertEquals(process.current, None)
        self.assertEquals(len(process._queue), 1)
        self.assertFalse(process.message)

        # Testing the correct processing of list replies
        cn = ComplexNotion('CN')
        n1 = Notion('N1')
        n2 = ActionNotion('N2', [True, STOP])

        NextRelation(cn, n1)
        NextRelation(cn, n2)

        # The route: CN returns [n1, n2], n1 returns none, n2 returns 'stop'
        r = process(NEW, cn, test='process_list')
        self.assertEqual(r, STOP)
        self.assertEquals(process.current, n2)
        self.assertEquals(len(process._queue), 1)
        self.assertFalse(process.message)

        # Skip test
        r = process(NEW, strange)
        self.assertTrue(r is False)
        self.assertIsNone(process.current)
        self.assertEquals(process.message[0], strange)
        self.assertEquals(len(process._queue), 1)

        r = process(NEW, SKIP, strange)
        self.assertTrue(r is None)
        self.assertIsNone(process.current)
        self.assertFalse(process.message)
        self.assertEquals(len(process._queue), 1)

        # Non-abstract returns
        n2.action = lambda: lambda: n1

        r = process(n2)
        self.assertTrue(r)
        self.assertEqual(process.current, n1)

    def test_7_debug(self):
        root = ComplexNotion('here')
        a = ComplexNotion('a')

        NextRelation(root, a)

        # Simple debugger test: reply with unknown message at the abstract
        process = Process()
        debugger = ProcessDebugger(process)

        unk = 'oh noes!'
        debugger.reply_at(a, unk)

        r = process(root, test='test_debugging')

        self.assertTrue(r is False)
        self.assertEqual(process.message[0], unk)
        self.assertEquals(process.current, a)
        self.assertEqual(len(process._queue), 1)

        # Now let's test skipping the unknowns by the debugger
        debugger.clear_points()

        b = Notion('b')
        b.on(QUERY, unk)
        NextRelation(a, b)

        c = ActionNotion('c', STOP)
        NextRelation(a, c)

        debugger.on(UNKNOWN, SKIP)

        r = process(NEW, root, test='test_skipping')
        self.assertEqual(r, STOP)
        self.assertEqual(process.current, c)
        self.assertEqual(len(process._queue), 1)

    def test_8_queue(self):
        # Stack test: root -> (a, e); a -> (b, c, d)
        root = ComplexNotion('root')
        a = ComplexNotion('a')

        NextRelation(root, a)

        b = Notion('b')
        c = ActionNotion('c', [])  # Test of empty array

        unk = 'unk'

        d = ActionNotion('d', unk)  # Stop here

        NextRelation(a, b)
        NextRelation(a, c)
        NextRelation(a, d)

        e = ActionNotion('e', unk)  # And stop here too

        NextRelation(root, e)

        process = Process()

        r = process(root, test='test_queue')

        self.assertEqual(process.current, d)
        self.assertTrue(r is False)
        self.assertEqual(len(process._queue), 2)
        self.assertEqual(process.message[0], unk)

        r = process(SKIP, test='test_skip_1')  # Make process pop from stack

        self.assertEqual(process.current, e)
        self.assertTrue(r is False)
        self.assertEqual(len(process._queue), 1)
        self.assertEqual(process.message[0], unk)

        r = process(SKIP, test='test_skip_2')  # Trying empty stack

        self.assertEqual(process.current, e)  # Nowhere to go
        self.assertTrue(r is None)
        self.assertEqual(len(process._queue), 1)
        self.assertFalse(process.message)

        # Trying list message
        process(e, b)
        r = process(SKIP)
        self.assertTrue(r)
        self.assertEqual(process.current, b)
        self.assertEqual(len(process._queue), 1)
        self.assertFalse(process.message)

    def test_9_context(self):
        # Verify correctness of adding
        # Root -> (a, b)
        root = ComplexNotion('root')
        a = Notion('a')

        ctx_key = 'ctx'
        l = lambda: {ADD_CONTEXT: {ctx_key: True}}
        a.on_forward(l)

        b = ActionNotion('b', lambda **c: STOP if ctx_key in c else OK)

        NextRelation(root, a)
        NextRelation(root, b)

        process = SharedContextProcess()

        r = process(root, test='test_context_add_1')
        self.assertEqual(r, STOP)
        self.assertIn(ctx_key, process.context)
        self.assertEqual(process.current, b)

        # Testing the order of execution/update and keeping of source values in context if adding
        process.context[ctx_key] = 1
        r = process(NEW, {ADD_CONTEXT: {'from': 'me'}}, root, test='test_context_add_2')

        self.assertEqual(r, STOP)
        self.assertEqual(1, process.context[ctx_key])
        self.assertEqual('me', process.context['from'])
        self.assertEqual(process.current, b)

        # Verify updating
        a.off_handler(l)
        l = lambda: {UPDATE_CONTEXT: {ctx_key: 'new'}}
        a.on_forward(l)

        process.context[ctx_key] = 2

        r = process(NEW, root, test='test_context_update')
        self.assertEqual(r, STOP)
        self.assertEqual('new', process.context[ctx_key])
        self.assertEqual(process.current, b)

        # Verify deleting & mass deleting
        a.off_handler(l)
        l = lambda: {DELETE_CONTEXT: ctx_key}
        a.on_forward(l)

        r = process(NEW, root, test='test_context_del')
        self.assertEqual(r, OK)
        self.assertNotIn(ctx_key, process.context)
        self.assertEqual(process.current, b)

        a.off_handler(l)
        l = lambda: {DELETE_CONTEXT: ['more', 'more2']}
        a.on_forward(l)

        r = process(NEW, root, test='test_context_del', more=False)
        self.assertEqual(r, OK)
        self.assertNotIn('more', process.context)
        self.assertEqual(process.current, b)

        # See what's happening if command argument is incorrect
        a.off_handler(l)
        a.on_forward(ADD_CONTEXT)

        r = process(NEW, root, test='test_context_bad')
        self.assertTrue(r is False)
        self.assertEqual(process.current, a)

    def test_a_dict_tracking(self):
        d = {'a': 1, 'c': 12}
        ops = DictChangeGroup()

        d2 = {'a': 1}

        a1 = DictChangeOperation(d, DictChangeOperation.ADD, 'b', 2)
        ops.add(a1, False)

        ops.add(DictChangeOperation(d, DictChangeOperation.SET, 'b', 4), False)

        a2 = DictChangeOperation(d, DictChangeOperation.SET, 'b', 3)
        ops.add(a2, False)

        a3 = DictChangeOperation(d2, DictChangeOperation.ADD, 'b', 3)
        ops.add(a3, False)

        s1 = DictChangeOperation(d, DictChangeOperation.SET, 'a', 0)
        ops.add(s1, False)

        ops.add(DictChangeOperation(d, DictChangeOperation.DELETE, 'c'), False)

        ops.do()

        self.assertEqual(d['b'], 3)
        self.assertEqual(d2['b'], 3)
        self.assertEqual(d['a'], 0)
        self.assertNotIn('c', d)

        ops.undo()

        self.assertEqual(d['a'], 1)
        self.assertEqual(d['c'], 12)
        self.assertNotIn('b', d)

        self.assertEqual(len(d), 2)

        self.assertEqual(str(a1), '%s %s=%s' % (DictChangeOperation.ADD,  a1._key, a1._value))
        self.assertEqual(repr(s1), '%s %s=%s<-%s' % (DictChangeOperation.SET,  s1._key, s1._value, s1._old_value))

        with self.assertRaises(ValueError):
            DictChangeOperation('fail', 1, 2)

    def test_b_stacking_context(self):
        # Testing without tracking
        root = ComplexNotion('root')

        NextRelation(root, ActionNotion('change_context',
                                          {ADD_CONTEXT: {'inject': 'ninja'}}))

        NextRelation(root, ActionNotion('change_context2',
                                          {UPDATE_CONTEXT: {'inject': 'revenge of ninja'}}))

        NextRelation(root, ActionNotion('del_context', {DELETE_CONTEXT: 'inject'}))

        p = ActionNotion('pop_context', POP_CONTEXT)
        NextRelation(root, p)

        process = StackingContextProcess()

        r = process(root, test='test_stacking_1')

        self.assertTrue(r is False)
        self.assertEqual(process.current, p)
        self.assertNotIn('inject', process.context)

        # Now tracking is on!
        root = ComplexNotion('root')

        NextRelation(root, ActionNotion('push_context', PUSH_CONTEXT))

        NextRelation(root, ActionNotion('change_context',
                                          {ADD_CONTEXT: {'terminator': '2'}}))

        NextRelation(root, ActionNotion('delete_context',
                                          {DELETE_CONTEXT: 'terminator'}))

        NextRelation(root, ActionNotion('change_context2',
                                          {UPDATE_CONTEXT: {'alien': 'omnomnom'}}))

        NextRelation(root, ActionNotion('check_context', lambda **c: None if 'alien' in c else 'Ripley!'))

        NextRelation(root, ActionNotion('push_context2', PUSH_CONTEXT))

        NextRelation(root, ActionNotion('change_context3',
                                          {UPDATE_CONTEXT: {'test': 'predator'}}))

        NextRelation(root, ActionNotion('forget_context', FORGET_CONTEXT))

        pop = ActionNotion('pop_context', POP_CONTEXT)
        NextRelation(root, pop)

        r = process(NEW, root, test='test_stacking_2')

        self.assertTrue(r is None)
        self.assertEqual(process.current, pop)
        self.assertNotIn('alien', process.context)
        self.assertNotIn('terminator', process.context)
        self.assertEqual('predator', process.context['test'])  # Lasts because context changes were forgotten
        self.assertFalse(process._context_stack)

    def test_c_states(self):
        # Root -> (inc, inc, 'state_check')
        root = ComplexNotion('root')

        inc = ActionNotion('+1', state_v_starter)

        NextRelation(root, inc)
        NextRelation(root, inc)

        check = ActionNotion('state_check', state_v_checker)
        NextRelation(root, check)

        process = StatefulProcess()
        r = process(root, test='test_states_1')

        self.assertEqual(r, OK)
        self.assertEqual(process.current, check)
        self.assertEqual(process.states[inc]['v'], 2)

        # Checking clearing of states when new
        r = process(NEW, root, test='test_states_2')
        self.assertEqual(r, OK)
        self.assertEqual(process.states[inc]['v'], 2)
        self.assertEqual(process.current, check)

        # Manual clearing of states
        inc.action = CLEAR_STATE
        r = process(root, test='test_states_3')

        self.assertEqual(r, OK)
        self.assertFalse(process.states)
        self.assertEqual(process.current, check)

        # Notifications
        while root.relations:
            root.relations[0].subject = None

        t = ActionNotion('terminator', has_notification)
        NextRelation(root, t)

        notification = {NOTIFY: {TO: t, INFO: {'note': OK}}}

        r = process(NEW, dict(notification), root, test='test_states_4')

        self.assertEqual(r, OK)
        self.assertEqual(process.current, t)

        # Test states and the stacking context
        private = {'private': {'super_private': 'traveling'}}
        t.action = lambda **c: {SET_STATE: private} if not 'private' in c[STATE] else \
                                   {SET_STATE: {'private': {'super_private': 'home', 'more': 'none'}}}

        t2 = ActionNotion('terminator2', (PUSH_CONTEXT, ))
        NextRelation(root, t2)

        NextRelation(root, t)

        t3 = ActionNotion('terminator2', (POP_CONTEXT, ))
        NextRelation(root, t3)

        r = process(NEW, root, test='test_states_5')

        self.assertTrue(r is None)
        self.assertEqual(process.states.get(t), private)
        self.assertNotIn('more', process.states.get(t)['private'])

        # Test notifications and the stacking context
        root.relations[0].subject = None
        t.action = {NOTIFY: {TO: t, INFO: {'note': False}}}

        r = process(NEW, dict(notification), root, test='test_states_5')

        self.assertTrue(r is None)
        self.assertEqual(process.states[t][NOTIFICATIONS],
                         notification[NOTIFY][INFO])

    def test_d_parsing(self):
        # Proceed test
        root = ComplexNotion('root')
        mover = ActionNotion('move', lambda: {PROCEED: 2})
        NextRelation(root, mover)

        process = ParsingProcess()
        # Good (text fully parsed)
        r = process(root, **{TEXT: 'go', 'test': 'test_parsing_1', ANSWER: RANK})

        self.assertTrue(r[0] is None)
        self.assertEqual(r[1], 2)
        self.assertEqual(r[1], process.parsed_length)
        self.assertEqual('go', process.last_parsed)

        # Bad (incomplete parsing)
        r = process(NEW, root, **{TEXT: 'gogo', 'test': 'test_parsing_2'})

        self.assertTrue(r is False)
        self.assertEqual(process.parsed_length, 2)
        self.assertEqual(process.text, 'go')
        self.assertEqual('go', process.last_parsed)

        # State check - nothing changed if POP
        r = process(NEW, PUSH_CONTEXT, root, POP_CONTEXT,
                    **{TEXT: 'go', 'test': 'test_parsing_3'})

        self.assertTrue(r is False)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.text, 'go')
        self.assertFalse(process.last_parsed)

        # Changing of query
        r = process(NEW, NEXT, BREAK, STOP)

        self.assertFalse(r)
        self.assertEqual(process.query, BREAK)

        r = process(NEW, CONTINUE, STOP)

        self.assertFalse(r)
        self.assertEqual(process.query, CONTINUE)

        r = process(NEW, ERROR, STOP)

        self.assertFalse(r)
        self.assertEqual(process.query, ERROR)

        r = process(NEW, STOP, **{TEXT: 1})
        self.assertEqual(r, STOP)

    def test_e_conditions(self):
        # Simple positive condition test root -a-> d for 'a'
        root = ComplexNotion('root')

        action = ActionNotion('passed', lambda **c: c.get(LAST_PARSED, ERROR))

        parsing = ParsingRelation(root, action, 'a')

        r = parsing(NEXT, **{TEXT: 'a', 'test': 'conditions_1'})

        self.assertEqual(r[0].get(PROCEED), 1)
        self.assertEqual(r[1], action)

        self.assertEqual(parsing(NEXT), ERROR)
        self.assertTrue(parsing(BREAK) is None)

        # Using in process
        process = ParsingProcess()

        r = process(root, **{TEXT: 'a', 'test': 'conditions_2'})

        self.assertEqual(process.parsed_length, 1)
        self.assertTrue(r is False)
        self.assertEqual(process.current, action)

        # Simple negative condition test root -a-> a for 'n'
        r = process(NEW, root, **{TEXT: 'n', 'test': 'conditions_3'})

        self.assertTrue(r is False)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, parsing)

        # Simple positive condition test root -function-> None for 'a'
        parsing.condition = lambda **c: 1 if c.get(TEXT, '').startswith('a') else -1
        parsing.object = None

        r = process(NEW, root, **{TEXT: 'a', 'test': 'conditions_4'})

        self.assertEqual(process.parsed_length, 1)
        self.assertTrue(r is None)
        self.assertEqual(process.current, parsing)

        r = process(NEW, root, **{TEXT: 'b', 'test': 'conditions_5'})

        self.assertTrue(r is False)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, parsing)

        # Optional check
        parsing.optional = True
        r = process(NEW, root, **{TEXT: '', 'test': 'conditions_6'})

        self.assertTrue(r is not False)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, parsing)

        # Regex check
        parsing.optional = False
        parsing.condition = re.compile(r'(\s)*')

        r = process(NEW, root, **{TEXT: '     ', 'test': 'conditions_7'})

        self.assertTrue(r is None)
        self.assertEqual(process.parsed_length, 5)
        self.assertEqual(process.current, parsing)

        # Underflow check
        r = process(NEW, root, **{TEXT: ' z', 'test': 'conditions_8'})

        self.assertTrue(r is False)
        self.assertEqual(process.parsed_length, 1)
        self.assertEqual(process.current, parsing)

        # Zero checker test
        parsing.condition = None
        parsing.object = 1
        self.assertEqual(parsing(NEXT), 1)

        # Check only test
        parsing.condition = 'x'
        parsing.check_only = True
        parsing.optional = False

        r = process(NEW, root, **{TEXT: 'x', 'test': 'conditions_9'})

        self.assertTrue(r is False)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, parsing)

        parsing.check_only = False

        r = process(NEW, root, **{TEXT: 'x', 'test': 'conditions_10'})

        self.assertEqual(r, 1)
        self.assertEqual(process.parsed_length, 1)
        self.assertEqual(process.current, parsing)

    def test_f_complex(self):
        # Complex notion test: root -> ab -> (a , b) with empty message
        root = ComplexNotion('root')
        ab = ComplexNotion('ab')
        NextRelation(root, ab)

        a = ActionNotion('a', common_state_acc)
        r1 = NextRelation(ab, a)

        b = ActionNotion('b', common_state_acc)
        r2 = NextRelation(ab, b)

        process = ParsingProcess()

        r = process(root, test='test_complex_1')

        self.assertTrue(r is None)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, b)
        self.assertEqual(process.context['acc'], 2)

        # Complex notion negative test: root -> ab -> ( (-a-> a) , (-b-> b) ) for 'a'
        r1.subject = None
        r2.subject = None

        ParsingRelation(ab, a, 'a')
        r2 = ParsingRelation(ab, b, 'b')

        r = process(NEW, root, **{TEXT: 'a', 'test': 'test_complex_2', 'acc': 0})

        self.assertTrue(r is False)
        self.assertEqual(process.parsed_length, 1)
        self.assertEqual(process.last_parsed, 'a')
        self.assertEqual(process.context['acc'], 1)
        self.assertNotIn(b, process.states)
        self.assertEqual(process.current, r2)  # Finished at error

        # Nested complex notion test: root -> ab -> ( (-a-> a) , (-b-> b)  -> c -> (d, e), f) for 'abf'
        c = ComplexNotion('c')
        NextRelation(ab, c)

        d = ActionNotion('d', common_state_acc)
        NextRelation(c, d)

        e = ActionNotion('e', common_state_acc)
        NextRelation(c, e)

        f = ActionNotion('f', True)
        ParsingRelation(ab, f, 'f')

        r = process(NEW, root, **{TEXT: 'abf', 'test': 'test_complex_3', 'acc': 0})

        self.assertEqual(r, True)
        self.assertEqual(process.parsed_length, 3)
        self.assertEqual(process.current, f)
        self.assertEqual(process.last_parsed, 'f')
        self.assertEqual(process.context['acc'], 4)

    def test_g_selective(self):
        process = ParsingProcess()

        # Simple selective test: root -a-> a, -b-> b for 'b'
        root = SelectiveNotion('root')
        a = ActionNotion('a', common_state_acc)

        c1 = ParsingRelation(root, a, 'a')

        b = ActionNotion('b', common_state_acc)
        c2 = ParsingRelation(root, b, 'b')

        r = process(root, **{TEXT: 'b', 'test': 'test_selective_1'})

        self.assertEqual(process.last_parsed, 'b')
        self.assertTrue(r is None)
        self.assertEqual(process.query, NEXT)
        check_test_result(self, process, b, 1)

        # Alternative negative test: same tree, message 'xx'
        r = process(NEW, root, **{TEXT: 'xx', 'test': 'test_selective_2'})

        self.assertTrue(r is False)
        self.assertEqual(process.query, ERROR)  # No case found
        check_test_result(self, process, root, 0)

        # Default test
        default = ParsingRelation(root, None, re.compile('.'))
        root.default = default

        r = root(NEXT, **{TEXT: 'x'})

        self.assertEqual(r, default)

        default.subject = None

        self.assertIsNone(root.default)

        root.default = default

        self.assertIsNone(root.default)

        r = root(NEXT, **{TEXT: 'x'})

        self.assertEqual(r, ERROR)

        default.subject = root

        r = root(NEXT, **{TEXT: 'a'})
        self.assertEqual(r[0], PUSH_CONTEXT)

        default.subject = None

        # Alternative test: root ->( a1 -> (-a-> a, -b->b) ), a2 -> (-aa->aa), -bb->bb ) ) for 'aa'
        c1.subject = None
        c2.subject = None

        a1 = ComplexNotion('a1')
        NextRelation(root, a1)

        a = ComplexNotion('a')
        a1a = ParsingRelation(a1, a, 'a')

        b = ActionNotion('b', common_state_acc)
        ParsingRelation(a, b, 'b')

        a2 = ComplexNotion('a2')
        na2 = NextRelation(root, a2)

        aa = ActionNotion('aa', common_state_acc)
        caa = ParsingRelation(a2, aa, 'aa')

        bb = ActionNotion('bb', common_state_acc)
        nbb = NextRelation(root, bb)

        r = process(NEW, root, **{TEXT: 'aa', 'test': 'test_selective_3'})

        self.assertEqual(process.context['acc'], 1)
        self.assertTrue(r is None)
        check_test_result(self, process, root, 2)

        # Longest regex/selection
        # Alternative test: root ->( a1 -> (-a-> a, -b->b) ), -a-> a2 -> (-c->aa), -a+->bb ) ) for 'aaaa'
        na2.subject = None
        na2.object = None
        ParsingRelation(root, a2, 'a')
        caa.condition = 'c'

        nbb.subject = None
        nbb.object = None
        ParsingRelation(root, bb, re.compile("(a)+"))

        s = ActionNotion('stop', ERROR)
        ParsingRelation(root, s, 'a')

        r = process(NEW, root, **{TEXT: 'aaaa', 'test': 'test_selective_4'})

        self.assertEqual(process.last_parsed, 'aaaa')
        self.assertTrue(r is None)
        check_test_result(self, process, bb, 4)

        # Negative test: just wrong text input
        r = process(NEW, root, **{TEXT: 'x', 'test': 'test_selective_5'})

        self.assertTrue(r is False)
        self.assertEqual(process.query, ERROR)
        self.assertEqual(process.last_parsed, '')
        check_test_result(self, process, a1a, 0)

        # Error test: 1 good case, but turns out to be invalid
        while root.relations:
            root.relations[0].subject = None

        breaker = ActionNotion('breaker', ERROR)
        c1 = ParsingRelation(root, breaker, 'a')
        NextRelation(root, ActionNotion('adder', common_state_acc))

        r = process(NEW, root, **{TEXT: 'a', 'test': 'test_selective_6'})

        self.assertTrue(r is False)
        self.assertEqual(process.query, ERROR)
        check_test_result(self, process, breaker, 1)

        # Error test 2: 2 good cases, both invalid
        c2.subject = root
        c2.object = breaker
        c2.condition = 'a'

        r = process(NEW, root, **{TEXT: 'a', 'test': 'test_selective_7'})

        self.assertTrue(r is False)
        self.assertEqual(process.query, ERROR)
        check_test_result(self, process, root, 1)

        c2.subject = None

        # No error, 1 good relation so there are no returns
        breaker.action = OK  # In this case Selective will not offer new cases

        r = process(NEW, root, ** {TEXT: 'a', 'test': 'test_selective_8'})

        self.assertTrue(r, OK)
        check_test_result(self, process, breaker, 1)

        # Testing non-parsing relations
        breaker.action = ERROR
        c1.subject = None
        NextRelation(root, breaker)

        r = process(NEW, root, **{TEXT: '', 'test': 'test_selective_9'})

        self.assertTrue(r is None)
        self.assertEqual(process.context['acc'], 1)
        check_test_result(self, process, root, 0)

    def test_h_loop(self):
        # Simple loop test: root -5!-> aa -a-> a for 'aaaaa'
        root = ComplexNotion('root')
        aa = ComplexNotion('aa')

        l = LoopRelation(root, aa, 5)

        self.assertTrue(l.is_numeric())
        self.assertTrue(l.is_general())
        self.assertFalse(l.is_flexible())

        a = ActionNotion('acc', common_state_acc)
        ParsingRelation(aa, a, 'a')

        process = ParsingProcess()

        r = process(root, **{TEXT: 'aaaaa', 'test': 'test_loop_basic'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 5)

        # Negative loop test: root -5!-> aa -a-> a for 'aaaa'
        r = process(NEW, root, **{TEXT: 'aaaa', 'test': 'test_loop_neg'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 4)

        # n=0 test
        l.condition = 0
        r = process(NEW, root, **{TEXT: '', 'test': 'test_loop_n=0'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 0)

        # Numeric ranges test
        l.condition = (2, 4)

        self.assertTrue(l.is_numeric())
        self.assertTrue(l.is_flexible())

        r = process(NEW, root, **{TEXT: 'aaa', 'test': 'test_loop_m..n'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 3)

        r = process(NEW, root, **{TEXT: 'a', 'test': 'test_loop_m..n_2'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 1)

        r = process(NEW, root, **{TEXT: 'aaaa', 'test': 'test_loop_m..n_3'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 4)

        r = process(NEW, root, **{TEXT: 'aaaaa', 'test': 'test_loop_m..n_neg'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 4)

        # Numeric flexibles test
        # No minimum
        l.condition = (None, 2)

        self.assertTrue(l.is_numeric())
        self.assertTrue(l.is_flexible())

        r = process(NEW, root, **{TEXT: '', 'test': 'test_loop_none..n'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 0)

        r = process(NEW, root, **{TEXT: 'aa', 'test': 'test_loop_none..n_2'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 2)

        r = process(NEW, root, **{TEXT: 'aaa', 'test': 'test_loop_none..n_3'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 2)

        # No maximum
        l.condition = 3, None

        self.assertTrue(l.is_numeric())
        self.assertTrue(l.is_flexible())

        r = process(NEW, root, **{TEXT: 'aa', 'test': 'test_loop_m..none_neg'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 2)

        r = process(NEW, root, **{TEXT: 'aaa', 'test': 'test_loop_m..none'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 3)

        r = process(NEW, root, **{TEXT: 'aaaa', 'test': 'test_loop_m..none_2'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 4)

        # Loop test for arbitrary count root -*!-> a's -a-> a for 'aaaa'
        l.condition = '*'

        self.assertTrue(l.is_wildcard())
        self.assertTrue(l.is_flexible())

        r = process(NEW, root, **{TEXT: 'aaaa', 'test': 'test_loop_*'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 4)

        # Loop test for >1 count root -+!-> a's -a-> a for 'aaaa'
        l.condition = '+'

        self.assertTrue(l.is_wildcard())
        self.assertTrue(l.is_flexible())

        r = process(NEW, root, **{TEXT: 'aaaa', 'test': 'test_loop_+'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 4)

        # Loop negative test for >1 count root -+!-> a's -a-> a for 'b'
        r = process(NEW, root, **{TEXT: 'b', 'test': 'test_loop_+_neg'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 0)

        # Loop test for ? count root -?-> a's -a-> a for 'a'
        l.condition = '?'

        self.assertTrue(l.is_wildcard())
        self.assertTrue(l.is_flexible())

        r = process(NEW, root, **{TEXT: 'a', 'test': 'test_loop_?'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 1)

        # Loop test for ? count root -?-> a's -a-> a for ''
        r = process(NEW, root, **{TEXT: '', 'test': 'test_loop_?_2'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 0)

        r = process(NEW, root, **{TEXT: 'aa', 'test': 'test_loop_?_2'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 1)

        # Loop test for endless count root -*!-> a's -a-> a for some number of a's
        l.condition = True

        self.assertFalse(l.is_wildcard())
        self.assertFalse(l.is_numeric())
        self.assertTrue(l.is_infinite())

        r = process(NEW, root, **{TEXT: 'aaaaa', 'test': 'test_loop_true_n'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 5)

        # Loop test for external function: root -function!-> a's -a-> a for 'aaaa'
        l.condition = lambda state: 5 if not 'i' in state else state['i'] - 1

        self.assertFalse(l.is_general())
        self.assertFalse(l.is_flexible())
        self.assertTrue(l.is_custom())

        r = process(NEW, root, **{TEXT: 'aaaaa', 'test': 'test_loop_ext_func'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 5)  # External functions stops at 5

        # Error in the custom loop
        r = process(NEW, root, **{TEXT: 'aaaa', 'test': 'test_loop_ext_func_neg'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 4)

        # Error in custom loop start
        l.condition = lambda: False
        r = process(NEW, root, **{TEXT: 'a', 'test': 'test_loop_ext_func_neg_2'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 0)

        # Nested loops
        # Positive test: root -2!-> a2 -2!-> a's -a-> a for 'aaaa'
        l.condition = 2

        aaa = ComplexNotion('aaa')
        l.subject = aaa

        l2 = LoopRelation(root, aaa, 2)

        r = process(NEW, root, **{TEXT: 'aaaa', 'test': 'test_loop_nested'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l2, 4)

        # Nested loops negative test: root -2!-> a2 -2!-> a's -a-> a for 'aaab'
        r = process(NEW, root, **{TEXT: 'aaab', 'test': 'test_loop_nested_neg'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l2, 3)

        # Break test: root -2!-> a's (-a-> a, -!->)
        l2.subject = None

        l.condition = (2, None)
        l.subject = root

        b = ActionNotion('b', state_v_starter)
        NextRelation(aa, b)

        c = ActionNotion('c', common_state_acc)
        p = ParsingRelation(root, c, 'c')

        # Try without break first
        a.action = common_state_acc

        r = process(NEW, root, **{TEXT: 'ac', 'test': 'test_loop_break_neg'})

        self.assertTrue(r is False)
        self.assertEqual(process.query, ERROR)
        self.assertEqual(process.states[b]['v'], 1)
        check_loop_result(self, process, p, 1)

        a.action = lambda **c: [common_state_acc(**c), BREAK]

        r = process(NEW, root, **{TEXT: 'ac', 'test': 'test_loop_break'})

        self.assertTrue(r is None)
        self.assertEqual(process.query, NEXT)
        self.assertNotIn(b, process.states)
        check_loop_result(self, process, c, 2)

        # Continue test
        l.condition = 2
        a.action = common_state_acc
        p.subject = None

        r = process(NEW, root, **{TEXT: 'aa', 'test': 'test_loop_continue_neg'})

        self.assertTrue(r is None)
        self.assertEqual(process.states[b]['v'], 2)
        self.assertEqual(process.query, NEXT)
        check_loop_result(self, process, l, 2)

        a.action = lambda **c: [common_state_acc(**c), CONTINUE]

        r = process(NEW, root, **{TEXT: 'aa', 'test': 'test_loop_continue'})

        self.assertTrue(r is None)
        self.assertEqual(process.query, NEXT)
        self.assertNotIn(b, process.states)
        check_loop_result(self, process, l, 2)

    def test_g_graph(self):
        graph = Graph()

        # Adding test
        root = ComplexNotion('root', graph)
        self.assertEqual((root, ), graph.notions())

        rave = ComplexNotion('rave')
        rave.owner = graph

        self.assertEqual((root, rave), graph.notions())

        # Removing test
        rave.owner = None

        self.assertEqual((root, ), graph.notions())

        # Adding test 2
        rel = NextRelation(root, rave, None, graph)

        self.assertEqual((rel,), graph.relations())

        # Removing test 2
        rel.owner = None

        self.assertEqual((), graph.relations())

        self.assertFalse(graph.do_element(graph.add_prefix(OWNER, SET_PREFIX), **{SENDER: self}))

        # Root
        graph.root = rel

        self.assertIsNone(graph.root)

        rave.owner = None
        graph.root = rave

        self.assertIsNone(graph.root)

        graph.root = root

        self.assertEqual(root, graph.root)

        root.owner = None

        self.assertIsNone(graph.root)

        # Search - Notions
        lock = Notion('lock', graph)

        r = re.compile('r')

        self.assertFalse(graph.notions(r))

        root.owner = graph
        rave.owner = graph

        ns = graph.notions(r)
        self.assertListEqual(ns, [root, rave])
        self.assertEqual(graph.notion(r), ns[0])

        self.assertListEqual([graph.notion('lock')], [lock])
        self.assertEqual(graph.notion(lambda notion: notion == rave), rave)

        # Search - Relations
        rel.owner = graph
        rel2 = NextRelation(rave, lock, None, graph)

        self.assertEqual(graph.relations(), (rel, rel2))
        self.assertEqual(graph.relation(), rel)

        rel3 = NextRelation(root, None, None, graph)

        self.assertListEqual(graph.relations({SUBJECT: root}), [rel, rel3])
        self.assertListEqual(graph.relations({OBJECT: rave}), [rel])
        self.assertListEqual(graph.relations({SUBJECT: rave, OBJECT: lock}), [rel2])
        self.assertListEqual(graph.relations(lambda r: r == rel3), [rel3])

        # Name, Str, and Next
        self.assertEqual(graph.__str__(), '{""}')

        graph.root = root
        self.assertEqual(graph(NEXT), root)

        graph.name = 'graph'
        self.assertEqual(root.name, graph.name)
        self.assertEqual(graph.__str__(), '{"%s"}' % root.name)

        sub_graph = Graph('sub', graph)
        self.assertEqual(sub_graph.name, 'sub')

        self.assertEqual(sub_graph.__repr__(), '{%s(%s, %s)}' % (get_object_name(sub_graph.__class__),
                                                                 sub_graph.__str__(), graph))

        self.assertEqual(graph.notion('sub'), sub_graph)

    def test_z_special(self):
        # Complex loop test: root -(*)-> sequence [-(a)-> a's -> a, -(b)-> b's -> b]
        root = ComplexNotion('root')
        sequence = ComplexNotion('sequence')

        l = LoopRelation(root, sequence, 3)

        a_seq = ComplexNotion('a\'s')
        l_a = LoopRelation(sequence, a_seq, '*')

        a = ActionNotion('a', common_state_acc)
        ParsingRelation(a_seq, a, 'a')

        b_seq = ComplexNotion('b\'s')
        l_b = LoopRelation(sequence, b_seq, '*')
        b = ActionNotion('b', state_v_starter)

        ParsingRelation(b_seq, b, 'b')

        process = ParsingProcess()

        r = process(root, text='bbaabaaa', test='special_test_1')

        self.assertTrue(r is None)
        self.assertEqual(process.parsed_length, 8)
        self.assertEqual(process.states[b]['v'], 3)
        self.assertEqual(process.context['acc'], 5)

        self.assertNotIn(l, process.states)
        self.assertNotIn(l_a, process.states)
        self.assertNotIn(l_b, process.states)

        self.assertFalse(process._context_stack)
        self.assertEqual(process.current, l)


def test():
    suite = unittest.TestLoader().loadTestsFromTestCase(UtTests)
    #suite = unittest.TestLoader().loadTestsFromName('test.UtTests.test_special')
    unittest.TextTestRunner(verbosity=2).run(suite)
