"""
.. module:: tests.test
   :platform: Unix, Windows
   :synopsis: Graph-talk unit tests

.. moduleauthor:: Stas Kravets (krvss) <stas.kravets@gmail.com>

"""

import unittest
from inspect import ArgSpec
import os

from gt.debug import *
from gt.export import *


# Test functions
def state_v_starter(**context):
    if StatefulProcess.STATE in context and 'v' in context[StatefulProcess.STATE]:
        return {StatefulProcess.SET_STATE: {'v': context[StatefulProcess.STATE]['v'] + 1}}
    else:
        return {StatefulProcess.SET_STATE: {'v': 1}}


def state_v_checker(**context):
    if StatefulProcess.STATE in context and 'v' in context[StatefulProcess.STATE]:
        return Process.STOP
    else:
        return Process.OK  # Others' state is not visible


def common_state_acc(**context):
    if 'acc' in context:
        return {SharedProcess.UPDATE_CONTEXT: {'acc': context['acc'] + 1}}
    else:
        return {SharedProcess.ADD_CONTEXT: {'acc': 1}}


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

    def __call__(self, *message, **context):
        self.last_message = message
        self.last_context = context

        return True


class UtTests(unittest.TestCase):

    def test_1_abstract(self):
        with self.assertRaises(NotImplementedError):
            Abstract().__call__()

        abstract = TestCalls()
        self.assertEqual(abstract.__call__(), abstract())

    def test_2_accesses(self):
        abstract = TestCalls()

        # Access test
        # Function
        access = Access(lambda l: l)
        self.assertEqual(access.mode, Access.FUNCTION)
        self.assertIsInstance(access.spec, ArgSpec)

        # Abstract
        access = Access(abstract)
        self.assertEqual(access.mode, Access.CALL)
        self.assertEquals(access.spec, Access.ABSTRACT)

        # Value
        access = Access(1)
        self.assertEqual(access.mode, Access.VALUE)

        # Access and Get
        self.assertEqual(Access(lambda: 1)(), 1)
        self.assertEqual(Access(lambda *m: m[0])(2), 2)
        self.assertEqual(Access(lambda *m, **c: c[m[0]])('3', **{'3': 3}), 3)
        self.assertEqual(Access(lambda **c: c['4'])('4', **{'4': 4}), 4)
        self.assertEqual(Access(lambda a, b: a + b)('5', a=2, b=3, c=4), 5)
        self.assertEqual(Access(lambda a, b=1: a + b)('6', a=3), 4)
        self.assertEqual(Access(abstract.return_true)('7', a=4), True)
        self.assertEqual(Access(abstract)(), True)

        self.assertEqual(access.__repr__(), '%s, %s: %s' % (access.mode, access.spec, access.value))

        # Conditions
        condition = Condition(1)
        self.assertEqual(condition.mode, Condition.VALUE)
        self.assertEquals(condition.spec, Condition.NUMBER)

        # List
        condition = Condition([1])
        self.assertEqual(condition.mode, Condition.VALUE)
        self.assertEquals(condition.spec, Condition.LIST)

        # List - 2
        condition = Condition((1, 2))
        self.assertEqual(condition.mode, Condition.VALUE)
        self.assertEquals(condition.spec, Condition.LIST)

        # String
        s = 'string'
        condition = Condition(s)
        self.assertEqual(condition.mode, Condition.VALUE)
        self.assertEquals(condition.spec, Condition.STRING)
        self.assertEqual(condition.value, s)

        condition = Condition(s)
        self.assertEqual(condition.mode, Condition.VALUE)
        self.assertEquals(condition.spec, Condition.STRING)

        # Regex
        condition = Condition(re.compile('.'))
        self.assertEqual(condition.mode, Condition.VALUE)
        self.assertEquals(condition.spec, Condition.REGEX)

        # Other
        condition = Condition(object())
        self.assertEqual(condition.mode, Condition.VALUE)
        self.assertEquals(condition.spec, Condition.OTHER)

        tc = TestCalls()

        condition1 = Condition(lambda *m: m[0] == 1)
        condition2 = Condition(lambda *m, **c: (m[0], len(c)))
        condition3 = Condition(lambda: 4)
        condition4 = Condition(tc.return_true)
        condition5 = Condition(tc.return_false)

        self.assertEquals(condition1.check([1], {}), (0, True))
        self.assertEquals(condition1.check([2], {}), Condition.NO_CHECK)

        self.assertEquals(condition2.check([3], {'1': 1}), (3, 1))
        self.assertEquals(condition3.check([], {}), (4, 4))

        self.assertEquals(condition4.check([], {}), (0, True))
        self.assertEquals(condition5.check([], {}), Condition.NO_CHECK)

        condition_r = Condition(re.compile('a+'))

        self.assertEquals(condition_r.check(['a'], {})[0], 1)
        self.assertEquals(condition_r.check(['ab'], {})[0], 1)
        self.assertEquals(condition_r.check(['b'], {}), Condition.NO_CHECK)

        condition_s = Condition('aa')
        self.assertEquals(condition_s.check(['aa'], {}), (2, 'aa'))
        self.assertEquals(condition_s.check(['aaa'], {}), (2, 'aa'))
        self.assertEquals(condition_s.check(['b'], {}), Condition.NO_CHECK)

        condition_s = Condition('x', search=True)
        self.assertEquals(condition_s.check(['aax'], {}), (3, 'x'))
        self.assertEquals(condition_s.check(['b'], {}), Condition.NO_CHECK)

        condition_s = Condition('y', search=True, ignore_case=True)
        self.assertEquals(condition_s.check(['YY'], {}), (1, 'Y'))
        self.assertEquals(condition_s.check([(None, 3)], {}), Condition.NO_CHECK)

        condition_l = Condition(('aa', 'bb'))
        self.assertEquals(condition_l.check(['bb'], {}), (2, 'bb'))
        self.assertEquals(condition_l.check(['c'], {}), Condition.NO_CHECK)
        self.assertEqual(condition_l.value, ('aa', 'bb'))
        self.assertEqual(condition_l.list[0].spec, Condition.STRING)
        self.assertEqual(condition_l.list[1].value, condition_l.value[1])

        condition_l = Condition(('a', 'bb'), 42, ignore_case=True)
        self.assertEquals(condition_l.check(['bB'], {}), (2, 'BB'))
        self.assertEquals(condition_l.check(['aa'], {}), (1, 'A'))
        self.assertEqual(condition_l.tags, condition_l._conditions[0].tags)
        self.assertEqual(condition_l._options, condition_l._conditions[0]._options)

        condition_r = Condition((re.compile('a+'), re.compile('aa'), 'aa'))
        self.assertEquals(condition_r.check(['aa'], {}), (2, 'aa'))

        condition_r = Condition(re.compile('b+'), search=True)
        self.assertEquals(condition_r.check(['agabb'], {}), (5, 'bb'))

        self.assertEquals(condition_r.check(['nope'], {}), Condition.NO_CHECK)

        condition_n = Condition(1)
        self.assertEquals(condition_n.check([1], {}), (0, 1))
        self.assertEquals(condition_n.check([0], {}), Condition.NO_CHECK)

        condition = Condition(lambda: (1, 2, 3))
        self.assertEquals(condition.check([], {}), ((1, 2, 3), (1, 2, 3)))

        condition = Condition({})
        self.assertEqual(condition.spec, condition.DICT)

        self.assertEquals(TrueCondition().check('Yey', 'cheers!'), (0, True))

        # Access
        access = Access(tc.return_false)
        self.assertEquals(access(), False)

        access = Access(lambda: True)
        self.assertTrue(access())

        access = Access((1, 2))
        self.assertEqual(access(), (1, 2))

        access = Access(1)
        self.assertEquals(access(), 1)

        access = Access(tc)
        self.assertTrue(access())

        # Events
        e = Event(1)
        self.assertEqual(e.run([], {}), (1, 1))
        self.assertEqual(e.pre, None)
        self.assertEqual(e.post, None)

        e.pre = 0
        self.assertEqual(e.run([], {}), (0, 0))

        e.pre = None
        self.assertEqual(e.run([], {}), (1, 1))

        e.post = lambda **c: c[Event.RESULT]
        self.assertEqual(e.run([], {}), (1, e.post))

        e.post = None
        self.assertEqual(e.run([], {}), (1, 1))

    def test_3_handler(self):
        h = Handler()

        handler1 = lambda: True
        handler2 = True

        # Generic 'on'
        h.on('event', handler1)

        self.assertIn(('event', handler1), h.events)

        # Cannot add duplicates
        h.on('event', handler1)

        self.assertEqual(len(h.events), 1)

        # Can add non-callable
        h.on('1', 1)
        self.assertEqual(h.get_events('1'), [1])

        # On any
        h.on_any(handler1)

        self.assertEqual(len(h.events), 3)
        self.assertIn((TRUE_CONDITION, handler1), h.events)

        # No duplicates on on_any too
        h.on_any(handler1)

        self.assertEqual(len(h.events), 3)

        # Generic off
        h.off('event', handler1)

        self.assertNotIn(('event', handler1), h.events)

        # Off-any
        h.on('event', handler1)
        h.off_any(handler1)

        self.assertNotIn(handler1, h.events)
        self.assertIn(('event', handler1), h.events)

        # Off-conditon
        h.on('cond', 1)
        h.on('cond', 2)
        h.on('cond2', 2)

        h.off_condition('cond')

        self.assertFalse(h.get_events('cond'))
        self.assertEqual(h.get_events('cond2'), [2])

        h.off_condition('cond2')
        self.assertFalse(h.get_events('cond'))

        # Off-handler
        h.on_any(handler1)

        h.off_event(handler1)
        h.off_event(1)
        self.assertEqual(len(h.events), 0)

        # Get handlers
        h.on('event', handler1)
        h.on('event', handler2)

        h.on_any(handler2)

        self.assertEqual(h.get_events('event'), [handler1, handler2])
        self.assertEqual(h.get_events(), [handler2])

        # Handle itself
        # Longest wins
        h.clear_events()
        h.on('event', handler1)
        h.on('event1', handler2)
        r = h.handle(['event'], {})

        self.assertTrue(r[0])
        self.assertEqual(r[1], len('event'))
        self.assertEqual(r[2], handler1)

        r = h.handle(['event1'], {})

        self.assertTrue(r[0])
        self.assertEqual(r[1], len('event1'))
        self.assertEqual(r[2], handler2)

        self.assertFalse(h('eve'))

        # Any event - no-condition wins
        handler3 = lambda *m, **c: 'handler3'
        h.on_any(handler3)

        r = h.handle(['even'], {})
        self.assertEqual(r[0], 'handler3')
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2], handler3)

        # Specific event beats 'any' handler
        r = h.handle(['event'], {})
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], len('event'))
        self.assertEqual(r[2], handler1)

        # For any events first default wins
        tc = TestCalls()
        h.on_any(tc.return_true)

        r = h.handle(['even'], {})
        self.assertEqual(r[0], 'handler3')
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2], handler3)

        # Call parameters check
        # Sender
        handler4 = lambda **c: c[Handler.SENDER]
        h.on(Handler.SENDER, handler4)

        r = h.handle([Handler.SENDER], {})
        self.assertEquals(r, (h, len(Handler.SENDER), handler4))

        r = h.handle([Handler.SENDER], {Handler.SENDER: 'test'})
        self.assertEquals(r, ('test', len(Handler.SENDER), handler4))

        # Condition & rank
        handler5 = lambda **c: (c[Handler.RANK], c[Handler.CONDITION])

        h.on(Handler.CONDITION, handler5)

        r = h.handle([Handler.CONDITION], {})
        self.assertEquals(r, ((len(Handler.CONDITION), Handler.CONDITION), len(Handler.CONDITION), handler5))

        # Answer check
        r = h('event', **{Handler.ANSWER: Handler.RANK})
        self.assertEquals(r, (True, len('event')))

        # Unknown check
        handler1 = 'handler1'
        h.clear_events()

        h.unknown_event = Event(handler1)
        self.assertEqual(h('strange'), handler1)

        # Tags check
        class UpdateTest(Handler):
            def __init__(self):
                super(UpdateTest, self).__init__()
                self.fixed_tags = set()

            def update_tags(self):
                return self.fixed_tags

        u = UpdateTest()

        u.on('go', Event(True), 'case1', 'case2')

        self.assertEqual(u('go'), False)

        u.fixed_tags = {'case1'}
        u.update()

        self.assertEqual(u('go'), False)
        self.assertEqual(u.tags, {'case1'})

        u.fixed_tags = {'case1', 'case2'}
        u.update()

        self.assertEqual(u('go'), True)

        u.fixed_tags = set()
        u.update()

        self.assertEqual(u('go'), False)

    def test_4_element(self):
        e = Element()
        tc = TestCalls()
        e.owner = tc

        self.assertEqual(e.owner, tc)

        # Allowing the change to non-abstract
        self.assertTrue(e.change_property('owner', 1))
        self.assertFalse(e.change_property('owner', 1))

        self.assertEqual(e.owner, 1)

        # Move test
        # Forward
        event1 = lambda *m: m[0] if m[0] in Process.FORWARD else None

        e.on_forward(event1)

        self.assertEqual(e(Process.NEXT), Process.NEXT)

        e.off_forward()

        self.assertTrue(e(Process.NEXT) is False)

        self.assertFalse(e.is_forward(None))
        self.assertTrue(e.is_forward([Process.NEXT]))
        self.assertFalse(e.is_forward([]))

        # Backward
        event2 = lambda *m: m[0] if m[0] in Process.BACKWARD else None
        e.on_backward(event2)

        self.assertEqual(e(Process.PREVIOUS), Process.PREVIOUS)

        e.off_backward()

        self.assertTrue(e(Process.PREVIOUS) is False)

        self.assertFalse(e.is_backward(None))
        self.assertTrue(e.is_backward([Process.PREVIOUS]))
        self.assertFalse(e.is_backward([]))

        # Visit
        event3 = lambda *m: m[0] if m[0] in VisitorProcess.VISIT else None
        e.on_visit(event3)

        self.assertEqual(e(VisitorProcess.VISIT), VisitorProcess.VISIT)

        e.off_visit()

        self.assertTrue(e(VisitorProcess.VISIT) is False)

    def test_5_objects(self):
        # Notions test
        n1 = Notion('n1')
        n2 = Notion('n2')
        n2.owner = 1
        n1.owner = n2

        self.assertEqual(n1.name, 'n1')
        self.assertEqual(n1.__str__(), '"' + n1.name + '"')
        self.assertEqual(n1.__repr__(), '<' + get_object_name(n1.__class__) + '("' + n1.name + '", "' + n2.name + '")>')
        self.assertEqual(n1.owner, n2)
        self.assertEqual(n2.owner, 1)

        n1.owner = None
        self.assertEqual(n2.owner, 1)
        self.assertEqual(n1.__repr__(), '<' + get_object_name(n1.__class__) + '("' + n1.name + '")>')

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
        self.assertEqual(cn(Process.NEXT), r1)

        r2 = Relation(n2, n1)
        r2.subject = cn

        # If there is more than 1 relation ComplexNotion should return the list
        self.assertEqual(cn(Process.NEXT), (r1, r2))

        r2.subject = n2
        self.assertEqual(len(cn.relations), 1)

        # Trying direct calls to relate
        r3 = Relation(n1, n2)
        self.assertFalse(cn.do_relation(**{Element.OLD_VALUE: None, Handler.SENDER: r3, Element.NEW_VALUE: None}))
        self.assertFalse(cn.do_relation(**{Element.OLD_VALUE: cn, Handler.SENDER: r3, Element.NEW_VALUE: None}))

        self.assertTrue(cn.do_relation(**{Element.OLD_VALUE: None, Handler.SENDER: r3, Element.NEW_VALUE: cn}))
        self.assertFalse(cn.do_relation(**{Element.OLD_VALUE: None, Handler.SENDER: r3, Element.NEW_VALUE: cn}))
        self.assertTrue(cn.do_relation(**{Element.OLD_VALUE: cn, Handler.SENDER: r3, Element.NEW_VALUE: None}))

        # Unrelating
        cn2 = ComplexNotion('cn2')
        r1.subject = cn2

        self.assertEqual(r1.subject, cn2)
        self.assertNotIn(r1, cn.relations)
        self.assertIn(r1, cn2.relations)

        cn2.remove_all()
        self.assertIsNone(r1.subject)
        self.assertFalse(cn2.relations)

        # Next test
        nr = NextRelation(n1, n2)
        self.assertEqual(nr(Process.NEXT), n2)

        nr.condition = lambda **c: 'event' in c
        nr.object = [1]
        self.assertListEqual(nr(Process.NEXT, event=1), nr.object)

        self.assertTrue(nr(event=1) is False)
        self.assertTrue(nr(Process.NEXT) is False)

        # Action notion test
        na = ActionNotion('action', 'action')
        self.assertEquals(na(Process.NEXT), na.name)
        self.assertEqual(na.action, na.name)

        na.action = 2
        self.assertEquals(na(Process.NEXT), 2)

        na.off_forward()
        self.assertIsNone(na.action)

        # Action relation test
        ar = ActionRelation('subj', 'obj', True)

        self.assertEqual(ar(Process.NEXT), (True, ar.object))
        ar.action = None

        self.assertEqual(ar(Process.NEXT), ar.object)

        ar.action = 3

        self.assertEqual(ar(Process.NEXT), (3, ar.object))

        ar.object = None

        self.assertEqual(ar(Process.NEXT), 3)

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

        r = process(process.NEW, n, test='process_unknown')
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
        r = process(process.NEW, test='process_new')
        self.assertTrue(r is False)
        self.assertEquals(process.current, None)
        self.assertEquals(len(process._queue), 1)
        self.assertFalse(process.message)

        # Testing the correct processing of list replies
        cn = ComplexNotion('CN')
        n1 = Notion('N1')
        n2 = ActionNotion('N2', [True, process.STOP])

        NextRelation(cn, n1)
        rel = NextRelation(cn, n2)

        # The route: CN returns [n1, n2], n1 returns none, n2 returns 'stop'
        r = process(process.NEW, cn, test='process_list')
        self.assertEqual(r, process.STOP)
        self.assertEquals(process.current, n2)
        self.assertEquals(len(process._queue), 1)
        self.assertFalse(process.message)

        # Skip test
        r = process(process.NEW, strange)
        self.assertTrue(r is False)
        self.assertIsNone(process.current)
        self.assertEquals(process.message[0], strange)
        self.assertEquals(len(process._queue), 1)

        n2.action = process.skip
        r = process(process.NEW, n2, strange)
        self.assertTrue(r)
        self.assertIsNone(process.current)
        self.assertFalse(process.message)
        self.assertEquals(len(process._queue), 1)

        # Non-abstract returns
        n2.action = lambda: lambda: n1

        r = process(process.NEW, n2)
        self.assertTrue(r)
        self.assertEqual(process.current, n1)

        tc = TestCalls()

        n2.action = tc.return_true

        r = process(process.NEW, n2)
        self.assertTrue(r)
        self.assertEqual(process.current, n2)

        # Non-abstract relation object
        rel.object = tc.return_true

        r = process(process.NEW, rel)
        self.assertTrue(r)
        self.assertEqual(process.current, tc.return_true)

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

        process.skip()
        r = process(test='test_skip_1')  # Make process pop from stack

        self.assertEqual(process.current, e)
        self.assertTrue(r is False)
        self.assertEqual(len(process._queue), 1)
        self.assertEqual(process.message[0], unk)

        process.skip()
        r = process(test='test_skip_2')  # Trying empty stack

        self.assertEqual(process.current, e)  # Nowhere to go
        self.assertTrue(r is False)
        self.assertEqual(len(process._queue), 1)
        self.assertFalse(process.message)

        # Trying list message
        process(e, b)
        process.skip()
        r = process()
        self.assertTrue(r)
        self.assertEqual(process.current, b)
        self.assertEqual(len(process._queue), 1)
        self.assertFalse(process.message)

    def test_9_shared(self):
        # Verify correctness of adding
        # Root -> (a, b)
        root = ComplexNotion('root')
        a = Notion('a')

        process = SharedProcess()

        ctx_key = 'ctx'
        l = lambda: {process.ADD_CONTEXT: {ctx_key: True}}
        a.on_forward(l)

        b = ActionNotion('b', lambda **c: process.STOP if ctx_key in c else process.OK)

        NextRelation(root, a)
        NextRelation(root, b)

        r = process(root, test='test_context_add_1')
        self.assertEqual(r, process.STOP)
        self.assertIn(ctx_key, process.context)
        self.assertEqual(process.current, b)

        # Testing the order of execution/update and keeping of source values in context if adding
        process.context[ctx_key] = 1
        r = process(process.NEW, {process.ADD_CONTEXT: {'from': 'me'}}, root, test='test_context_add_2')

        self.assertEqual(r, process.STOP)
        self.assertEqual(1, process.context[ctx_key])
        self.assertEqual('me', process.context['from'])
        self.assertEqual(process.current, b)

        # Verify updating
        a.off_event(l)
        l = lambda: {process.UPDATE_CONTEXT: {ctx_key: 'new'}}
        a.on_forward(l)

        process.context[ctx_key] = 2

        r = process(process.NEW, root, test='test_context_update')
        self.assertEqual(r, process.STOP)
        self.assertEqual('new', process.context[ctx_key])
        self.assertEqual(process.current, b)

        # Verify deleting & mass deleting
        a.off_event(l)
        l = lambda: {process.DELETE_CONTEXT: ctx_key}
        a.on_forward(l)

        r = process(process.NEW, root, test='test_context_del')
        self.assertEqual(r, process.OK)
        self.assertNotIn(ctx_key, process.context)
        self.assertEqual(process.current, b)

        a.off_event(l)
        l = lambda: {process.DELETE_CONTEXT: ['more', 'more2']}
        a.on_forward(l)

        r = process(process.NEW, root, test='test_context_del', more=False)
        self.assertEqual(r, process.OK)
        self.assertNotIn('more', process.context)
        self.assertEqual(process.current, b)

        # See what's happening if command argument is incorrect
        a.off_event(l)
        a.on_forward(process.ADD_CONTEXT)

        r = process(process.NEW, root, test='test_context_bad')
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
            DictChangeOperation('fail', 1, 2).do()

    def test_b_stacking_context(self):
        # Testing without tracking
        root = ComplexNotion('root')
        process = StackingProcess()

        NextRelation(root, ActionNotion('change_context',
                                          {process.ADD_CONTEXT: {'inject': 'ninja'}}))

        NextRelation(root, ActionNotion('change_context2',
                                          {process.UPDATE_CONTEXT: {'inject': 'revenge of ninja'}}))

        NextRelation(root, ActionNotion('del_context', {process.DELETE_CONTEXT: 'inject'}))

        p = ActionNotion('pop_context', process.POP_CONTEXT)
        NextRelation(root, p)

        r = process(root, test='test_stacking_1')

        self.assertTrue(r is False)
        self.assertEqual(process.current, p)
        self.assertNotIn('inject', process.context)

        # Now tracking is on!
        root = ComplexNotion('root')

        NextRelation(root, ActionNotion('push_context', process.PUSH_CONTEXT))

        NextRelation(root, ActionNotion('change_context',
                                          {process.ADD_CONTEXT: {'terminator': '2'}}))

        NextRelation(root, ActionNotion('delete_context',
                                          {process.DELETE_CONTEXT: 'terminator'}))

        NextRelation(root, ActionNotion('change_context2',
                                          {process.UPDATE_CONTEXT: {'alien': 'omnomnom'}}))

        NextRelation(root, ActionNotion('check_context', lambda **c: None if 'alien' in c else 'Ripley!'))

        NextRelation(root, ActionNotion('push_context2', process.PUSH_CONTEXT))

        NextRelation(root, ActionNotion('change_context3',
                                          {process.UPDATE_CONTEXT: {'test': 'predator'}}))

        NextRelation(root, ActionNotion('forget_context', process.FORGET_CONTEXT))

        pop = ActionNotion('pop_context', process.POP_CONTEXT)
        NextRelation(root, pop)

        r = process(process.NEW, root, test='test_stacking_2')

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

        self.assertEqual(r, process.OK)
        self.assertEqual(process.current, check)
        self.assertEqual(process.states[inc]['v'], 2)

        # Checking clearing of states when new
        r = process(process.NEW, root, test='test_states_2')
        self.assertEqual(r, process.OK)
        self.assertEqual(process.states[inc]['v'], 2)
        self.assertEqual(process.current, check)

        # Manual clearing of states
        inc.action = process.CLEAR_STATE
        r = process(root, test='test_states_3')

        self.assertEqual(r, False)  # Because cleared 2 times
        self.assertFalse(process.states)
        self.assertEqual(process.current, inc)

    def test_d_parsing(self):
        # Proceed test
        root = ComplexNotion('root')
        process = ParsingProcess()

        mover = ActionNotion('move', lambda: {process.PROCEED: 2})
        NextRelation(root, mover)

        # Good (text fully parsed)
        r = process(root, **{process.TEXT: 'go', 'test': 'test_parsing_1', Handler.ANSWER: Handler.RANK})

        self.assertTrue(r[0] is None)
        self.assertEqual(r[1], 2)
        self.assertEqual(r[1], process.parsed_length)
        self.assertEqual('go', process.last_parsed)

        # Bad (incomplete parsing)
        r = process(process.NEW, root, **{process.TEXT: 'gogo', 'test': 'test_parsing_2'})

        self.assertTrue(r is False)
        self.assertEqual(process.parsed_length, 2)
        self.assertEqual(process.text, 'go')
        self.assertEqual('go', process.last_parsed)

        # State check - nothing changed if POP
        r = process(process.NEW, process.PUSH_CONTEXT, root, process.POP_CONTEXT,
                    **{process.TEXT: 'go', 'test': 'test_parsing_3'})

        self.assertTrue(r is False)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.text, 'go')
        self.assertFalse(process.last_parsed)

        # Changing of query
        r = process(process.NEW, Process.NEXT, process.BREAK, process.STOP)

        self.assertFalse(r)
        self.assertEqual(process.query, process.BREAK)

        r = process(process.NEW, process.CONTINUE, process.STOP)

        self.assertFalse(r)
        self.assertEqual(process.query, process.CONTINUE)

        r = process(process.NEW, process.ERROR, process.STOP)

        self.assertFalse(r)
        self.assertEqual(process.query, process.ERROR)

        r = process(process.NEW, process.STOP, **{process.TEXT: 1})
        self.assertEqual(r, process.STOP)

    def test_e_conditions(self):
        # Simple positive condition test root -a-> d for 'a'
        root = ComplexNotion('root')
        process = ParsingProcess()

        action = ActionNotion('passed', lambda **c: c.get(process.LAST_PARSED, process.ERROR))

        parsing = ParsingRelation(root, action, 'a')

        r = parsing(Process.NEXT, **{process.TEXT: 'a', 'test': 'conditions_1'})

        self.assertEqual(r[0].get(process.PROCEED), 1)
        self.assertEqual(r[1], action)

        self.assertEqual(parsing(Process.NEXT), process.ERROR)
        self.assertTrue(parsing(process.BREAK) is None)

        # Using in process

        r = process(root, **{process.TEXT: 'a', 'test': 'conditions_2'})

        self.assertEqual(process.parsed_length, 1)
        self.assertTrue(r is False)
        self.assertEqual(process.current, action)

        # Simple negative condition test root -a-> a for 'n'
        r = process(process.NEW, root, **{process.TEXT: 'n', 'test': 'conditions_3'})

        self.assertTrue(r is False)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, parsing)

        # Simple positive condition test root -function-> None for 'a'
        parsing.condition = lambda **c: 1 if c.get(process.TEXT, '').startswith('a') else -1
        parsing.object = None

        r = process(process.NEW, root, **{process.TEXT: 'a', 'test': 'conditions_4'})

        self.assertEqual(process.parsed_length, 1)
        self.assertTrue(r is None)
        self.assertEqual(process.current, parsing)

        r = process(process.NEW, root, **{process.TEXT: 'b', 'test': 'conditions_5'})

        self.assertTrue(r is False)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, parsing)

        # Optional check
        parsing.optional = True
        r = process(process.NEW, root, **{process.TEXT: '', 'test': 'conditions_6'})

        self.assertTrue(r is not False)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, parsing)

        # Regex check
        parsing.optional = False
        parsing.condition = re.compile(r'(\s)*')

        r = process(process.NEW, root, **{process.TEXT: '     ', 'test': 'conditions_7'})

        self.assertTrue(r is None)
        self.assertEqual(process.parsed_length, 5)
        self.assertEqual(process.current, parsing)

        # Underflow check
        r = process(process.NEW, root, **{process.TEXT: ' z', 'test': 'conditions_8'})

        self.assertTrue(r is False)
        self.assertEqual(process.parsed_length, 1)
        self.assertEqual(process.current, parsing)

        # Zero checker test
        parsing.condition = None
        parsing.object = True
        self.assertEqual(parsing(Process.NEXT), True)

        # Check only test
        parsing.condition = 'x'
        parsing.check_only = True
        parsing.optional = False

        r = process(process.NEW, root, **{process.TEXT: 'x', 'test': 'conditions_9'})

        self.assertTrue(r is False)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, parsing)

        parsing.check_only = False

        r = process(process.NEW, root, **{process.TEXT: 'x', 'test': 'conditions_10'})

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

        r = process(process.NEW, root, **{process.TEXT: 'a', 'test': 'test_complex_2', 'acc': 0})

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

        r = process(process.NEW, root, **{process.TEXT: 'abf', 'test': 'test_complex_3', 'acc': 0})

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

        r = process(root, **{process.TEXT: 'b', 'test': 'test_selective_1'})

        self.assertEqual(process.last_parsed, 'b')
        self.assertTrue(r is None)
        self.assertEqual(process.query, Process.NEXT)
        check_test_result(self, process, b, 1)

        # Alternative negative test: same tree, message 'xx'
        r = process(process.NEW, root, **{process.TEXT: 'xx', 'test': 'test_selective_2'})

        self.assertTrue(r is False)
        self.assertEqual(process.query, process.ERROR)  # No case found
        check_test_result(self, process, root, 0)

        # Default test
        default = ParsingRelation(root, None, re.compile('.'))
        root.default = default

        r = root(Process.NEXT, **{process.TEXT: 'x'})

        self.assertEqual(r, default)

        default.subject = None

        self.assertIsNone(root.default)

        root.default = default

        self.assertIsNone(root.default)

        r = root(Process.NEXT, **{process.TEXT: 'x'})

        self.assertEqual(r, process.ERROR)

        default.subject = root

        r = root(Process.NEXT, **{process.TEXT: 'a'})
        self.assertEqual(r[0], process.PUSH_CONTEXT)

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

        r = process(process.NEW, root, **{process.TEXT: 'aa', 'test': 'test_selective_3'})

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

        s = ActionNotion('stop', process.ERROR)
        ParsingRelation(root, s, 'a')

        r = process(process.NEW, root, **{process.TEXT: 'aaaa', 'test': 'test_selective_4'})

        self.assertEqual(process.last_parsed, 'aaaa')
        self.assertTrue(r is None)
        check_test_result(self, process, bb, 4)

        # Negative test: just wrong text input
        r = process(process.NEW, root, **{process.TEXT: 'x', 'test': 'test_selective_5'})

        self.assertTrue(r is False)
        self.assertEqual(process.query, process.ERROR)
        self.assertEqual(process.last_parsed, '')
        check_test_result(self, process, a1a, 0)

        # Error test: 1 good case, but turns out to be invalid
        root.remove_all()
        breaker = ActionNotion('breaker', process.ERROR)
        c1 = ParsingRelation(root, breaker, 'a')
        NextRelation(root, ActionNotion('adder', common_state_acc))

        r = process(process.NEW, root, **{process.TEXT: 'a', 'test': 'test_selective_6'})

        self.assertTrue(r is False)
        self.assertEqual(process.query, process.ERROR)
        check_test_result(self, process, breaker, 1)

        # Error test 2: 2 good cases, both invalid
        c2.subject = root
        c2.object = breaker
        c2.condition = 'a'

        r = process(process.NEW, root, **{process.TEXT: 'a', 'test': 'test_selective_7'})

        self.assertTrue(r is False)
        self.assertEqual(process.query, process.ERROR)
        check_test_result(self, process, root, 1)

        c2.subject = None

        # No error, 1 good relation so there are no returns
        breaker.action = process.OK  # In this case Selective will not offer new cases

        r = process(process.NEW, root, ** {process.TEXT: 'a', 'test': 'test_selective_8'})

        self.assertTrue(r, process.OK)
        check_test_result(self, process, breaker, 1)

        # Testing non-parsing relations
        breaker.action = process.ERROR
        c1.subject = None
        NextRelation(root, breaker)

        r = process(process.NEW, root, **{process.TEXT: '', 'test': 'test_selective_9'})

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

        r = process(root, **{process.TEXT: 'aaaaa', 'test': 'test_loop_basic'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 5)

        # Negative loop test: root -5!-> aa -a-> a for 'aaaa'
        r = process(process.NEW, root, **{process.TEXT: 'aaaa', 'test': 'test_loop_neg'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 4)

        # n=0 test
        l.condition = 0
        r = process(process.NEW, root, **{process.TEXT: '', 'test': 'test_loop_n=0'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 0)

        # Numeric ranges test
        l.condition = (2, 4)

        self.assertTrue(l.is_numeric())
        self.assertTrue(l.is_flexible())

        r = process(process.NEW, root, **{process.TEXT: 'aaa', 'test': 'test_loop_m..n'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 3)

        r = process(process.NEW, root, **{process.TEXT: 'a', 'test': 'test_loop_m..n_2'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 1)

        r = process(process.NEW, root, **{process.TEXT: 'aaaa', 'test': 'test_loop_m..n_3'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 4)

        r = process(process.NEW, root, **{process.TEXT: 'aaaaa', 'test': 'test_loop_m..n_neg'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 4)

        # Numeric flexibles test
        # No minimum
        l.condition = (None, 2)

        self.assertTrue(l.is_numeric())
        self.assertTrue(l.is_flexible())

        r = process(process.NEW, root, **{process.TEXT: '', 'test': 'test_loop_none..n'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 0)

        r = process(process.NEW, root, **{process.TEXT: 'aa', 'test': 'test_loop_none..n_2'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 2)

        r = process(process.NEW, root, **{process.TEXT: 'aaa', 'test': 'test_loop_none..n_3'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 2)

        # No maximum
        l.condition = 3, None

        self.assertTrue(l.is_numeric())
        self.assertTrue(l.is_flexible())

        r = process(process.NEW, root, **{process.TEXT: 'aa', 'test': 'test_loop_m..none_neg'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 2)

        r = process(process.NEW, root, **{process.TEXT: 'aaa', 'test': 'test_loop_m..none'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 3)

        r = process(process.NEW, root, **{process.TEXT: 'aaaa', 'test': 'test_loop_m..none_2'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 4)

        # Loop test for arbitrary count root -*!-> a's -a-> a for 'aaaa'
        l.condition = '*'

        self.assertTrue(l.is_wildcard())
        self.assertTrue(l.is_flexible())

        r = process(process.NEW, root, **{process.TEXT: 'aaaa', 'test': 'test_loop_*'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 4)

        # Loop test for >1 count root -+!-> a's -a-> a for 'aaaa'
        l.condition = '+'

        self.assertTrue(l.is_wildcard())
        self.assertTrue(l.is_flexible())

        r = process(process.NEW, root, **{process.TEXT: 'aaaa', 'test': 'test_loop_+'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 4)

        # Loop negative test for >1 count root -+!-> a's -a-> a for 'b'
        r = process(process.NEW, root, **{process.TEXT: 'b', 'test': 'test_loop_+_neg'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 0)

        # Loop test for ? count root -?-> a's -a-> a for 'a'
        l.condition = '?'

        self.assertTrue(l.is_wildcard())
        self.assertTrue(l.is_flexible())

        r = process(process.NEW, root, **{process.TEXT: 'a', 'test': 'test_loop_?'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 1)

        # Loop test for ? count root -?-> a's -a-> a for ''
        r = process(process.NEW, root, **{process.TEXT: '', 'test': 'test_loop_?_2'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 0)

        r = process(process.NEW, root, **{process.TEXT: 'aa', 'test': 'test_loop_?_2'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 1)

        # Loop test for endless count root -*!-> a's -a-> a for some number of a's
        l.condition = True

        self.assertFalse(l.is_wildcard())
        self.assertFalse(l.is_numeric())
        self.assertTrue(l.is_infinite())

        r = process(process.NEW, root, **{process.TEXT: 'aaaaa', 'test': 'test_loop_true_n'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 5)

        # Loop test for external function: root -function!-> a's -a-> a for 'aaaa'
        l.condition = lambda state: 5 if not 'i' in state else state['i'] - 1

        self.assertFalse(l.is_general())
        self.assertFalse(l.is_flexible())
        self.assertTrue(l.is_custom())

        r = process(process.NEW, root, **{process.TEXT: 'aaaaa', 'test': 'test_loop_ext_func'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l, 5)  # External functions stops at 5

        # Error in the custom loop
        r = process(process.NEW, root, **{process.TEXT: 'aaaa', 'test': 'test_loop_ext_func_neg'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 4)

        # Error in custom loop start
        l.condition = lambda: False
        r = process(process.NEW, root, **{process.TEXT: 'a', 'test': 'test_loop_ext_func_neg_2'})

        self.assertTrue(r is False)
        check_loop_result(self, process, l, 0)

        # Nested loops
        # Positive test: root -2!-> a2 -2!-> a's -a-> a for 'aaaa'
        l.condition = 2

        aaa = ComplexNotion('aaa')
        l.subject = aaa

        l2 = LoopRelation(root, aaa, 2)

        r = process(process.NEW, root, **{process.TEXT: 'aaaa', 'test': 'test_loop_nested'})

        self.assertTrue(r is None)
        check_loop_result(self, process, l2, 4)

        # Nested loops negative test: root -2!-> a2 -2!-> a's -a-> a for 'aaab'
        r = process(process.NEW, root, **{process.TEXT: 'aaab', 'test': 'test_loop_nested_neg'})

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

        r = process(process.NEW, root, **{process.TEXT: 'ac', 'test': 'test_loop_break_neg'})

        self.assertTrue(r is False)
        self.assertEqual(process.query, process.ERROR)
        self.assertEqual(process.states[b]['v'], 1)
        check_loop_result(self, process, p, 1)

        a.action = lambda **c: [common_state_acc(**c), process.BREAK]

        r = process(process.NEW, root, **{process.TEXT: 'ac', 'test': 'test_loop_break'})

        self.assertTrue(r is None)
        self.assertEqual(process.query, Process.NEXT)
        self.assertNotIn(b, process.states)
        check_loop_result(self, process, c, 2)

        # Continue test
        l.condition = 2
        a.action = common_state_acc
        p.subject = None

        r = process(process.NEW, root, **{process.TEXT: 'aa', 'test': 'test_loop_continue_neg'})

        self.assertTrue(r is None)
        self.assertEqual(process.states[b]['v'], 2)
        self.assertEqual(process.query, Process.NEXT)
        check_loop_result(self, process, l, 2)

        a.action = lambda **c: [common_state_acc(**c), process.CONTINUE]

        r = process(process.NEW, root, **{process.TEXT: 'aa', 'test': 'test_loop_continue'})

        self.assertTrue(r is None)
        self.assertEqual(process.query, Process.NEXT)
        self.assertNotIn(b, process.states)
        check_loop_result(self, process, l, 2)

        l.condition = lambda state: 2 if not 'i' in state else state['i'] - 1

        r = process(process.NEW, root, **{process.TEXT: 'aa', 'test': 'test_loop_continue_custom'})

        self.assertTrue(r is None)
        self.assertEqual(process.query, Process.NEXT)
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

        self.assertFalse(graph.do_element(**{Handler.SENDER: self}))

        # Root
        with self.assertRaises(ValueError):
            graph.root = rel

        rave.owner = None

        with self.assertRaises(ValueError):
            graph.root = rave

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

        self.assertListEqual(graph.relations({Relation.SUBJECT: root}), [rel, rel3])
        self.assertListEqual(graph.relations({Relation.OBJECT: rave}), [rel])
        self.assertListEqual(graph.relations({Relation.SUBJECT: rave, Relation.OBJECT: lock}), [rel2])
        self.assertListEqual(graph.relations(lambda r: r == rel3), [rel3])

        # Name, Str, and Next
        self.assertEqual(graph.__str__(), '{""}')

        graph.root = root
        self.assertEqual(graph(Process.NEXT), root)

        graph.name = 'graph'
        self.assertEqual(root.name, graph.name)
        self.assertEqual(graph.__str__(), '{"%s"}' % root.name)

        sub_graph = Graph('sub', graph)
        self.assertEqual(sub_graph.name, 'sub')

        self.assertEqual(sub_graph.__repr__(), '{%s(%s, %s)}' % (get_object_name(sub_graph.__class__),
                                                                 sub_graph.__str__(), graph))

        self.assertEqual(graph.__repr__(), '{%s(%s)}' % (get_object_name(graph.__class__), graph.__str__()))

        self.assertEqual(graph.notion('sub'), sub_graph)

    def test_h_builder(self):
        b = GraphBuilder()

        self.assertIsNone(b.graph)
        self.assertIsNone(b.current)

        # Constructor
        graph = Graph()
        b = GraphBuilder(graph)
        self.assertEqual(b.graph, graph)
        self.assertIsNone(b.current)

        b = GraphBuilder('BT')
        self.assertIsNotNone(b.graph)
        self.assertEqual(b.current, b.graph.root)
        graph = b.graph

        # Complex
        self.assertEqual(b, b.complex('Complex'))
        c = b.current

        self.assertEqual(c.name, 'Complex')
        self.assertEqual(c.owner, graph)
        self.assertEqual(graph.notion(c.name), c)
        self.assertTrue(isinstance(b.current, ComplexNotion))

        # Notion
        self.assertEqual(b, b.notion('Notion'))
        n = b.current

        self.assertEqual(n.name, 'Notion')
        self.assertEqual(n.owner, graph)
        self.assertEqual(graph.notion(n.name), n)
        self.assertTrue(isinstance(b.current, Notion))

        b.current = c
        self.assertEqual(b.current, c)

        # Next
        self.assertEqual(b, b.next_rel(1, n, ignore_case=True))
        n_r = b.current

        self.assertEqual(n_r.owner, graph)
        self.assertEqual(n_r.subject, c)
        self.assertEqual(n_r.object, n)
        self.assertTrue(n_r.condition, 1)
        self.assertTrue(n_r.condition_access._ignore_case, True)
        self.assertEqual(graph.relation({Relation.SUBJECT: c}), n_r)
        self.assertTrue(isinstance(n_r, NextRelation))

        # Action
        self.assertEqual(b, b.act('Action', True))
        a = b.current

        self.assertEqual(a.name, 'Action')
        self.assertEqual(a.owner, graph)
        self.assertEqual(a.action, True)
        self.assertEqual(graph.notion(a.name), a)
        self.assertTrue(isinstance(b.current, ActionNotion))

        # Action relation
        self.assertEqual(b, b.act_rel(2, a))
        a_r = b.current

        self.assertEqual(a_r.owner, graph)
        self.assertEqual(a_r.subject, None)
        self.assertEqual(a_r.object, a)
        self.assertTrue(a_r.action, 2)
        self.assertEqual(a_r, graph.relation({Relation.OBJECT: a}))
        self.assertTrue(isinstance(a_r, ActionRelation))

        # Parsing relation
        self.assertEqual(b, b.parse_rel(3, None, ignore_case=True, optional=True, check_only=True))
        p_r = b.current

        self.assertEqual(p_r.owner, graph)
        self.assertEqual(p_r.subject, None)
        self.assertEqual(p_r.object, None)
        self.assertTrue(p_r.condition, 3)
        self.assertTrue(p_r.condition_access._ignore_case)
        self.assertTrue(p_r.optional)
        self.assertTrue(p_r.check_only)
        self.assertIn(p_r, graph.relations())
        self.assertTrue(isinstance(p_r, ParsingRelation))

        # Selective
        self.assertEqual(b, b.select('Select'))
        s = b.current

        self.assertEqual(s.name, 'Select')
        self.assertEqual(s.owner, graph)
        self.assertEqual(graph.notion(s.name), s)
        self.assertTrue(isinstance(b.current, SelectiveNotion))
        self.assertEqual(p_r.object, s)

        # Loop
        self.assertEqual(b, b.loop_rel(4, n))
        l_r = b.current

        self.assertEqual(l_r.owner, graph)
        self.assertEqual(l_r.subject, s)
        self.assertEqual(l_r.object, n)
        self.assertTrue(l_r.condition, 4)
        self.assertEqual(l_r, graph.relation({Relation.SUBJECT: s}))
        self.assertTrue(isinstance(l_r, LoopRelation))

        # Default
        b.default()
        self.assertEqual(s.default, l_r)

        # Sub-graphs
        self.assertEqual(b, b.sub_graph('Sub'))
        sub = b.graph

        self.assertEqual(sub.owner, graph)
        self.assertNotEqual(b.graph, graph)
        self.assertEqual(sub.root, b.current)

        b2 = GraphBuilder()
        b2.sub_graph('Sub2')

        self.assertEqual(b2.graph.name, 'Sub2')
        self.assertEqual(b2.graph.root.name, 'Sub2')

        # Pop
        self.assertEqual(b, b.pop())
        self.assertEqual(b.current, graph.root)

        with self.assertRaises(IndexError):
            b.pop()

        self.assertEqual(b.current, graph.root)

        # At ([])
        self.assertTrue(b, b[a])
        self.assertEqual(b.current, a)

        b.set_current(sub.root)
        self.assertEqual(b.graph, sub)

        b.set_current(graph.root)
        self.assertEqual(b.graph, graph)

        self.assertEqual(b[s.name].current, s)

        # Back
        b.set_current(n)
        self.assertEqual(b.back().current, n_r)

        self.assertEqual(b.back().current, c)

        # Errors
        with self.assertRaises(TypeError):
            b.default()

        with self.assertRaises(TypeError):
            b.attach(b)

    def test_i_visitor(self):
        process = VisitorProcess()
        graph = Graph()

        cn = ComplexNotion('CN', graph)
        graph.root = cn

        cn2 = ComplexNotion('CN2', graph)
        r0 = NextRelation(cn, cn2, graph)

        n1 = Notion('N1', graph)
        r1 = NextRelation(cn2, n1, graph)

        n2 = ActionNotion('N2', [True, process.STOP], graph)
        r2 = NextRelation(cn, n2, graph)

        r3 = NextRelation(cn, n1, graph)

        r = process(r1, test='visit_relation')
        self.assertTrue(r)
        self.assertEqual(process.current, n1)
        self.assertEqual(process.visited, [r1, n1])

        r = process(process.NEW, cn2, test='visit_complex')
        self.assertTrue(r)
        self.assertEqual(process.current, n1)
        self.assertEqual(process.visited, [cn2, r1, n1])

        r = process(process.NEW, cn, test='visit_subgraph')
        self.assertTrue(r)
        self.assertEqual(process.current, n1)
        self.assertEqual(process.visited, [cn, r0, cn2, r1, n1, r2, n2, r3])

        r = process(process.NEW, graph, test='visit_graph')
        self.assertTrue(r)
        self.assertEqual(process.current, n1)
        self.assertEqual(process.visited, [graph, cn, r0, cn2, r1, n1, r2, n2, r3])

        process.visit_event = Event(False)

        r = process(process.NEW, graph, test='visit_disabled')
        self.assertTrue(r)
        self.assertEqual(process.current, graph)
        self.assertEqual(process.visited, [])

    def test_j_export(self):
        # Base class test
        b = GraphBuilder('Export Graph')
        b.next_rel()
        b.complex('complex')

        fname = 'et.tmp'

        p = ExportProcess()

        r = p(p.NEW, b.graph, file=fname)
        self.assertTrue(r)
        self.assertTrue(os.path.isfile(fname))
        self.assertEqual(fname, p.filename)

        os.remove(fname)

        r = p(p.NEW, b.graph)
        self.assertTrue(r)
        self.assertFalse(os.path.isfile(fname))
        self.assertIsNone(p.filename)

        # Export test
        class ExportTest(ExportProcess):
            def export_graph(self, graph):
                return '(g:%s)' % graph.name

            def export_notion(self, notion):
                return '(n:%s)' % notion.name

            def export_relation(self, relation):
                return '-'

        p = ExportTest()

        self.assertEqual(p.get_type_id(b.graph), p.GRAPH_ID)
        self.assertEqual(p.get_type_id(b.graph.root), 'cn')

        self.assertEqual(p.get_serial_id('test'), 'test_0')
        self.assertEqual(p.get_serial_id('test'), 'test_1')

        self.assertEqual(p.get_serial_id('tset'), 'tset_0')

        self.assertEqual(p.get_element_id(b.graph.root), 'cn_0')
        self.assertEqual(p.get_element_id(b.graph.root), 'cn_0')

        self.assertEqual(p.get_element_id(b.current), 'cn_1')
        self.assertEqual(p.get_element_id(b.current), 'cn_1')

        self.assertEqual(p.get_element_id(1), '1')

        r = p(b.graph)
        self.assertTrue(r)
        self.assertEqual(p.out, '(g:%s)(n:%s)-(n:%s)' % (b.graph.name, b.graph.root.name, b.current.name))

        r = p(p.NEW, b.graph, file=fname)
        self.assertTrue(r)
        self.assertTrue(os.path.isfile(fname))
        self.assertEqual(fname, p.filename)

        os.remove(fname)

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

        # Examples from the Dev's Guide
        h = Handler()

        def show_me(*m, **c):
            print(c)

            return

        h.on(re.compile('a+'), show_me)

        h('aaa')

        h.clear_events()
        c = Condition(re.compile('a+'))
        e = Event(show_me)
        h.on_access(c, e)

        e.pre = 1

        print(h('a'))

        print(h.handle(['aa'], {}))

        print(h.handle([], {}))

        # Tags example
        class TagsExample(Handler):
            def __init__(self):
                super(TagsExample, self).__init__()
                self.fixed_tags = set()

            def update_tags(self):
                return self.fixed_tags

        u = TagsExample()

        u.on('move', Event(True), 'has_fuel', 'has_direction')

        print(u('move'))

        u.fixed_tags = {'has_fuel', 'maps_loading'}
        u.update()

        print(u('move'))

        u.fixed_tags = {'has_fuel', 'has_direction'}
        u.update()

        print(u('move'))

        # GraphBuilder

        builder = GraphBuilder('New Graph')

        builder.next_rel().complex('initiate').next_rel().notion('remove breaks').back().back().next_rel().act('ignite', 1)

        print(builder.complex('complex').next_rel().notion('simple'))
        print(Process()(builder.graph))

        print(builder.graph.notions(re.compile('i*')))

        # Process debugger
        p = Process()
        d = ProcessDebugger(p, True)

        cn = ComplexNotion('CN')
        n1 = Notion('N1')
        n2 = Notion('N2')

        NextRelation(cn, n1)
        NextRelation(cn, n2)

        p(cn)

        root = ComplexNotion('root')
        n = ComplexNotion('n')

        NextRelation(root, n)

        d.reply_at(n, process.STOP)

        print(p(p.NEW, root))

        p = StatefulProcess()
        a = ActionNotion('Changed my mind', {StatefulProcess.SET_STATE: {'mind': 'New York'}})
        print(p(a, {SharedProcess.ADD_CONTEXT: {'key': 'skeleton'}}))


def test():
    suite = unittest.TestLoader().loadTestsFromTestCase(UtTests)
    #suite = unittest.TestLoader().loadTestsFromName('test.UtTests.test_z_special')
    unittest.TextTestRunner(verbosity=2).run(suite)
