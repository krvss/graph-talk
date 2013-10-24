import unittest

from ut import *
from debug import *

import re

logger = Analyzer()


# Dialog test
class Debugger(Abstract):
    def parse(self, *message, **context):
        if message[0] == "query_post" and str(context["from"].current) == '"here"':
            return "debug"


# Skip test
class Skipper(Abstract):
    def parse(self, *message, **context):
        if message[0] == "unknown_pre":
            return "skip"


# Test functions
def showstopper(notion, *message, **context):
    return notion.name


def state_starter(notion, *message, **context):
    if "state" in context and "v" in context["state"]:
        return {"set_state": {"v": context["state"]["v"] + 1}}
    else:
        return {"set_state": {"v": 1}}


def state_checker(notion, *message, **context):
    if "state" in context and "v" in context["state"]:
        return "error"
    else:
        return None

_acc = 0


def accumulate_false(abstract, *message, **context):
    global _acc
    _acc += 1
    return False


def is_a(condition, *message, **context):
    if "text" in context and context["text"].startswith("a"):
        return True, 1
    else:
        return False, 0


def has_condition(notion, *message, **context):
    if 'passed_condition' in context:
        return context['passed_condition']
    else:
        return False


def has_notification(notion, *message, ** context):
    if 'state' in context and 'notifications' in context['state']:
        return context['state']['notifications']['condition']
    else:
        return False


def add_to_result(notion, *message, **context):
    add = notion.name
    if "result" in context:
        add = context["result"] + add

    return {"update_context": {"result": add}}


def if_loop(*message, **context):
    if not 'n' in context['state']:
        return 5
    else:
        return context['state']['n'] - 1


def stop_infinite(notion, *message, **context):
    counter = 1

    if "infinite" in context:
        if context["infinite"] == 4:
            return "break"
        else:
            counter = context["infinite"] + 1

    return {"update_context": {"infinite": counter}, "error": "trying to break"}


# New style
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
        a = Abstract()
        self.assertEqual(a.parse(), a())

    def test_2_handler(self):
        h = Handler()

        handler1 = True, 1
        handler2 = lambda: (True, 2)

        # Generic "on"
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

        # Off-all
        h.on_any(handler1)

        h.off_all(handler1)
        h.off_all(1)
        self.assertEqual(len(h.handlers), 0)

        # Get handlers
        h.on('event', handler1)
        h.on('event', handler2)

        h.on_any(handler2)

        self.assertEqual(h.get_handlers('event'), [handler1, handler2])
        self.assertEqual(h.get_handlers(), [handler2])

        # Smart calls
        self.assertEqual(h.smart_call_result(lambda: 1, [], {}), 1)
        self.assertEqual(h.smart_call_result(lambda *m: m[0], [2], {}), 2)
        self.assertEqual(h.smart_call_result(lambda *m, **c: c[m[0]], ["3"], {"3": 3}), 3)

        # Conditions
        condition1 = lambda *m: m[0] == 1

        tc = TestCalls()

        condition_r = re.compile('a+')

        self.assertTrue(h.can_handle(condition1, [1], {}))
        self.assertFalse(h.can_handle(condition1, [2], {}))

        self.assertFalse(h.can_handle(tc.return_false, [], {}))

        self.assertTrue(h.can_handle(condition_r, ['a'], {}))
        self.assertTrue(h.can_handle(condition_r, ['ab'], {}))
        self.assertFalse(h.can_handle(condition_r, ['b'], {}))

        self.assertTrue(h.can_handle('aa', ['aa'], {}))
        self.assertFalse(h.can_handle('b', ['aa'], {}))

        self.assertTrue(h.can_handle(('aa', 'bb'), ['bb'], {}))
        self.assertFalse(h.can_handle(('aa', 'bb'), ['c'], {}))

        # Run handler
        self.assertFalse(h.run_handler(tc.return_false, [], {})[0])
        self.assertTrue(h.run_handler(handler1, [], {})[0])

        handler4 = 1, 2, 3
        self.assertEqual(h.run_handler(handler4, [], {}), ((1, 2, 3), 0, handler4))

        handler4 = 1, 2
        self.assertEqual(h.run_handler(handler4, [], {}), (1, 2, handler4))

        # Handle itself
        del h.handlers[:]
        h.on('event', handler1)
        h.on('event', handler2)

        # Specified event - highest rank wins
        handler3 = lambda *m, **c: 2 if (c[Handler.SENDER] == h and c[Handler.CONDITION] is True) else 0

        r = h.handle('event')

        self.assertTrue(r[0])
        self.assertEqual(r[1], 2)
        self.assertEqual(r[2], handler2)

        self.assertFalse(h.parse('eve'))

        # Any event - no-condition wins
        h.on_any(handler3)

        r = h.handle('even')
        self.assertEqual(r[0], 2)
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2], handler3)

        # Specific event beats any handler
        r = h.handle('event')
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], 2)
        self.assertEqual(r[2], handler2)

        # For any events first default wins wins
        h.on_any(tc.return_true)

        r = h.handle('even')
        self.assertEqual(r[0], 2)
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2], handler3)

        # Args count test
        self.assertEqual(var_arg_count(tc.parse), 2)

    def test_3_talker(self):
        t = Talker()
        tc = TestCalls()

        # Names
        self.assertEqual(t.add_prefix('event', '1'), Talker.SEP.join(['1', 'event']))
        self.assertEqual(get_object_name(t.add_prefix), 'add_prefix')
        self.assertEqual(t.add_prefix(['event', 1], t.POST_PREFIX), ('post_event', 1))
        self.assertEqual(t.add_prefix('post_event', t.POST_PREFIX), 'post_event')
        self.assertEqual(t.add_prefix(['post_event'], t.POST_PREFIX), ('post_event', ))

        self.assertEqual(t.remove_prefix('e', 'p'), None)
        self.assertEqual(t.remove_prefix('p_e_v', 'p'), 'e_v')
        self.assertEqual(t.remove_prefix(['p_e']), 'e')

        # Silent
        self.assertTrue(t.is_silent(t.PRE_PREFIX))
        self.assertTrue(t.is_silent(t.POST_PREFIX))
        for s in t.SILENT:
            self.assertTrue(t.is_silent(s))

        self.assertFalse(t.is_silent('loud'))

        # Handling
        handler1 = 'handler1'

        # Stopping before return
        t.on('event', tc.return_true)
        t.on('pre_event', handler1)

        r = t.handle('event')
        self.assertEqual(r[0], 'handler1')
        self.assertEqual(r[1], 0)
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

        t.off_all(2)
        r = t.handle(1)
        self.assertEqual(r[0], 1)
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2], 1)

        # Overriding result
        t.off('pre_event', handler1)

        handler2 = lambda *m, **c: ('handler2', 1) if (c.get(Talker.RESULT) and c.get(Talker.RANK) == 0
                                                       and c.get(Talker.HANDLER) == tc.return_true) else None
        t.on('post_event', handler2)

        r = t.handle('event')
        self.assertEqual(r[0], 'handler2')
        self.assertEqual(r[1], 1)
        self.assertEqual(r[2], handler2)

        # Now clean run
        t.off('post_event', handler2)

        r = t.handle('event')
        self.assertTrue(r[0])
        self.assertEqual(r[1], 0)
        self.assertEqual(r[2], tc.return_true)

        # Recursion test
        t.on('r', lambda *m, **c: c[t.SENDER].handle('r', **c))
        self.assertTrue(t.handle('r'))

        # Result test
        t.on('pre_result', tc.return_true)  # Will not be called
        t.on(t.RESULT, handler2)
        self.assertEqual(t.parse('event'), 'handler2')

        t.on(t.UNKNOWN, handler1)
        self.assertEqual(t.parse('event2'), 'handler1')

    def test_4_element(self):
        e = Element()
        tc = TestCalls()

        # Can change property or not
        self.assertFalse(e.can_set_property('x'))
        self.assertFalse(e.can_set_property('set_owner'))
        self.assertFalse(e.can_set_property('set_owner', **{e.OLD_VALUE: '1'}))
        self.assertFalse(e.can_set_property('set_owner', **{e.OLD_VALUE: '1', e.NEW_VALUE: None}))

        self.assertTrue(e.can_set_property('set_owner', **{e.OLD_VALUE: '1', e.NEW_VALUE: '2'}))

        # Preventing the change
        e.on('pre_set_owner', tc.return_true)
        e.owner = tc
        self.assertIsNone(e.owner)

        # Allowing the change and verifying data
        e.off_all(tc.return_true)
        e.owner = tc

        self.assertEqual(e.owner, tc)
        self.assertEqual(tc.last_message, ('set_owner', ))
        self.assertEqual(tc.last_context[e.CONDITION], 'owner')
        self.assertEqual(tc.last_context[e.HANDLER], e.set_property)
        self.assertEqual(tc.last_context[e.OLD_VALUE], None)
        self.assertEqual(tc.last_context[e.NEW_VALUE], tc)
        self.assertEqual(tc.last_context[e.SENDER], e)

        # Allowing the change to non-abstract
        self.assertTrue(e.change_property('owner', 1))
        self.assertFalse(e.change_property('owner', 1))

        self.assertEqual(e.owner, 1)

        # Move test
        handler1 = lambda *m: m[0] if m[0] in e.MOVE else None

        e.on_forward(handler1)
        e.on_backward(handler1)

        self.assertEqual(e.parse(e.NEXT), e.NEXT)
        self.assertEqual(e.parse(e.BREAK), e.BREAK)

        e.off_all(handler1)
        e.on_move(handler1)

        self.assertEqual(e.parse(e.NEXT), e.NEXT)
        self.assertEqual(e.parse(e.BREAK), e.BREAK)

    def test_5_objects(self):
        # Notions test
        n1 = Notion2('n1')
        n2 = Notion2('n2')
        n1.owner = n2

        self.assertEqual(n1.name, 'n1')
        self.assertEqual(n1.__str__(), '"' + n1.name + '"')
        self.assertEqual(n1.__repr__(), '<' + get_object_name(n1.__class__) + '("' + n1.name + '", "' + n2.name + '")>')
        self.assertEqual(n1.owner, n2)

        n1.owner = None

        # Relations test
        r1 = Relation2(n1, n2)

        # Generic relation test
        self.assertEqual(r1.subject, n1)
        self.assertEqual(r1.object, n2)

        self.assertEqual(r1.__str__(), '<"n1" - "n2">')
        self.assertEqual(r1.__str__(), r1.__repr__())

        # Complex notion test
        cn = ComplexNotion2('cn')
        r1.subject = cn

        # If relation is only one ComplexNotion should return it, not a list
        self.assertEqual(cn.parse(cn.NEXT), r1)

        r2 = Relation2(n2, n1)
        r2.subject = cn

        # If there is more than 1 relation ComplexNotion should return the list
        self.assertEqual(cn.parse(cn.NEXT), (r1, r2))

        r2.subject = n2
        self.assertEqual(len(cn.relations), 1)

        # Trying direct calls to relate
        r3 = Relation2(n1, n2)
        self.assertFalse(cn.relate(**{cn.OLD_VALUE: None, cn.SENDER: r3, cn.NEW_VALUE: None}))
        self.assertFalse(cn.relate(**{cn.OLD_VALUE: cn, cn.SENDER: r3, cn.NEW_VALUE: None}))

        self.assertTrue(cn.relate(**{cn.OLD_VALUE: None, cn.SENDER: r3, cn.NEW_VALUE: cn}))
        self.assertFalse(cn.relate(**{cn.OLD_VALUE: None, cn.SENDER: r3, cn.NEW_VALUE: cn}))
        self.assertTrue(cn.relate(**{cn.OLD_VALUE: cn, cn.SENDER: r3, cn.NEW_VALUE: None}))

        # Next test
        nr = NextRelation2(n1, n2)
        self.assertEqual(nr.parse(nr.NEXT), n2)

    def test_6_process(self):
        p = Process2()

        cn = ComplexNotion2('CN')
        n1 = Notion2('N1')
        n2 = Notion2('N2')

        n2.on_forward(p.STOP)

        NextRelation2(cn, n1)
        NextRelation2(cn, n2)

        r = p.parse(cn)
        self.assertEqual(r, p.STOP)

    '''

    # Old style
    # General objects test
    def test_objects(self):
        n1 = Notion("n1")
        n2 = Notion("n2")

        self.assertEqual(n1.__str__(), '"' + n1.name + '"')
        self.assertEqual(n1.__str__(), n1.__repr__())

        r1 = Relation(n1, n2)

        # Generic relation test
        self.assertEqual(r1.subject, n1)
        self.assertEqual(r1.object, n2)

        self.assertEqual(r1.__str__(), '<"n1" - "n2">')
        self.assertEqual(r1.__str__(), r1.__repr__())

        cn = ComplexNotion("cn")
        r1.subject = cn

        # If relation is only one ComplexNotion should return it, not a list
        self.assertEqual(cn.parse('next'), r1)

        r2 = Relation(cn, n1)
        r2.subject = cn

        # If there is more than 1 relation ComplexNotion should return the list
        self.assertListEqual(cn.parse('next'), [r1, r2])

    def test_next(self):
        global _acc

        # logger.add_queries()

        # Simple next test: root -> a
        root = ComplexNotion("root")
        a = ActionNotion("a", showstopper)

        f = ActionRelation(root, a, accumulate_false)

        process = Process()
        process.callback = logger

        _acc = 0
        r = process.parse(root, test="test_next_1")

        self.assertEqual(process.reply, "a")
        self.assertEqual(process.current, a)
        self.assertEqual(r, "unknown")
        self.assertEqual(_acc, 1)

        # Now function will not confuse process
        a.action = None
        r = process.parse("new", root, test="test_next_2")

        self.assertEqual(process.reply, None)
        self.assertEqual(process.current, a)
        self.assertEqual(r, "ok")

        # Now we will stop at the relation
        f.action = lambda a, *m, **c: 'stop' if has_first(m, 'next') else False
        r = process.parse(root, test="test_next_3")

        self.assertEqual(process.reply, None)
        self.assertEqual(process.current, f)
        self.assertEqual(r, "stop")

    def test_callback(self):
        global _acc

        # Simple debugger test: stop at "a" notion, skip the result by the command and go further
        # Root -> a
        root = ComplexNotion("here")
        a = ComplexNotion("a")

        NextRelation(root, a)

        process = Process()
        debugger = Debugger()

        process.callback = debugger
        self.assertEqual(process.callback, debugger)

        r = process.parse(root, test="test_debugging")

        self.assertEqual(r, "unknown")
        self.assertEqual(process.current, debugger)
        self.assertEqual(process.reply, "debug")

        # Skipping unknown
        r = process.parse("skip")

        self.assertEqual("ok", r)
        self.assertEqual(process.current, a)

        # Simple skip test: always skip unknowns
        # Root -> a -> (b, c)
        b = ActionNotion("b", showstopper)
        NextRelation(a, b)

        c = ActionNotion("c", accumulate_false)
        NextRelation(a, c)

        skipper = Skipper()
        process.callback = skipper

        _acc = 0
        r = process.parse("new", root, test="test_skipper")

        self.assertEqual(r, "ok")
        self.assertEqual(_acc, 1)
        self.assertEqual(process.current, c)

    def test_queue(self):
        global _acc

        #logger.add_queries()

        # Stack test: root -> (a, d); a -> (b, b2, c)
        root = ComplexNotion("root")
        a = ComplexNotion("a")

        NextRelation(root, a)

        b = ActionNotion("b", accumulate_false)  # Just return False to keep going to C
        b2 = ActionNotion("b2", [])  # Test of empty array
        c = ActionNotion("c", showstopper)  # Stop here

        NextRelation(a, b)
        NextRelation(a, b2)
        NextRelation(a, c)

        d = ActionNotion("d", showstopper)  # And stop here too

        NextRelation(root, d)

        process = Process()
        process.callback = logger

        _acc = 0
        r = process.parse(root, test="test_queue")

        self.assertEqual(process.reply, "c")
        self.assertEqual(process.current, c)
        self.assertEqual(r, "unknown")
        self.assertEqual(_acc, 1)

        r = process.parse("skip", test="test_skip_1")  # Make process pop from stack

        self.assertEqual(process.reply, "d")
        self.assertEqual(process.current, d)
        self.assertEqual(r, "unknown")

        r = process.parse("skip", test="test_skip_2")  # Trying empty stack

        self.assertEqual(process.reply, None)
        self.assertEqual(process.current, None)  # Because everything skipped
        self.assertEqual(r, "ok")

        # Trying list message
        _acc = 0
        process.parse(b, b, b)
        self.assertEqual(_acc, 3)
        self.assertEqual(process.current, b)

    def test_context(self):
        #logger.add_queries()

        # Verify correctness of adding
        # Root -> (a, b)
        root = ComplexNotion("root")
        a = ActionNotion("ctx", {"add_context": {"ctx": True}}, True)

        b = ActionNotion("check_context", lambda notion, *message, **context: 'stop' if 'ctx' in context else False)

        NextRelation(root, a)
        NextRelation(root, b)

        process = SharedContextProcess()
        process.callback = logger

        r = process.parse(root, test="test_context_add_1")
        self.assertEqual(r, "stop")
        self.assertIn("ctx", process.context)
        self.assertEqual(process.current, b)

        process.context["ctx"] = False

        r = process.parse("new", root, {"add_context": {"from": "me"}}, test="test_context_add_2", ctx="1")

        self.assertEqual(r, "stop")
        self.assertEqual("1", process.context["ctx"])
        self.assertEqual("me", process.context["from"])
        self.assertEqual(process.current, b)

        # Checking that context is the same if there is no new command
        r = process.parse(root)
        self.assertEqual(r, "stop")
        self.assertEqual("me", process.context["from"])
        self.assertEqual(process.current, b)

        # Checking that context is NOT the same if there is new command
        r = process.parse("new", root)
        self.assertEqual(r, "stop")
        self.assertNotIn("from", process.context)
        self.assertEqual(process.current, b)

        # Verify updating
        value = {"update_context": {"ctx": "new"}}
        a.action = value

        r = process.parse("new", root, test="test_context_update", ctx="2")
        self.assertEqual(r, "stop")
        self.assertEqual("new", process.context["ctx"])
        self.assertEqual(process.current, b)

        # Check copying of actions
        self.assertTrue("update_context" in value)

        # Verify deleting & mass deleting
        a.action = {"delete_context": "ctx"}

        r = process.parse("new", root, test="test_context_del", ctx="3")
        self.assertEqual(r, "ok")
        self.assertNotIn("ctx", process.context)
        self.assertEqual(process.current, b)

        a.copy = False
        value = {"delete_context": ["ctx", "more", "more2"]}
        a.action = value

        r = process.parse("new", root, test="test_context_del", ctx="4", more=False)
        self.assertEqual(r, "ok")
        self.assertNotIn("ctx", process.context)
        self.assertNotIn("more", process.context)
        self.assertEqual(process.current, b)

        # Check disabled copy
        self.assertFalse(value)

        # See what's happening if command argument is incorrect
        a.action = "update_context"

        r = process.parse("new", root, test="test_context_bad")
        self.assertEqual(r, "unknown")
        self.assertEqual(process.current, a)

    def test_errors(self):
        #logger.add_queries()
        # Root -> a (b, c, d, e)
        root = ComplexNotion("root")
        a = ComplexNotion("a")

        NextRelation(root, a)

        b = ActionNotion("stop", showstopper)  # First stop
        c = ActionNotion("error", showstopper)  # Error!
        d = ActionNotion("errorer", {"error": "i_m_bad"})  # Another error!
        e = ActionNotion("end", showstopper)  # And finally here

        NextRelation(a, b)
        NextRelation(a, c)
        NextRelation(a, d)
        NextRelation(a, e)

        process = ParsingProcess()
        process.callback = logger

        r = process.parse(root, test="test_stop_1")

        self.assertEqual(r, "stop")
        self.assertEqual(process.current, b)

        # Now let's try to resume
        r = process.parse("skip")

        self.assertEqual(r, "error")
        self.assertIn(c, process.errors)
        self.assertIn(d, process.errors)

        self.assertEqual(process.reply, "end")
        self.assertEqual(process.current, e)

        self.assertEqual("i_m_bad", process.errors[d])

        # Check that if there is no problems if there is nothing new
        r = process.parse(test="test_stop_2")

        self.assertEqual(r, "error")
        self.assertIn(c, process.errors)
        self.assertIn(d, process.errors)

        self.assertEqual(process.reply, "end")
        self.assertEqual(process.current, e)

        self.assertEqual("i_m_bad", process.errors[d])

        # And now go None to check the errors cleared
        r = process.parse("new", test="test_stop_3")

        self.assertFalse(process.reply)
        self.assertFalse(process.errors)
        self.assertEqual(process.current, None)  # Because queue was cleared by new
        self.assertEqual(r, "ok")

    def test_condition(self):
        #logger.add_queries()
        # Simple positive condition test root -a-> d for "a"
        root = ComplexNotion("root")

        d = ActionNotion("d", has_condition)

        c = ConditionalRelation(root, d, "a")

        self.assertIsNone(c.parse("test"))

        process = ParsingProcess()
        process.callback = logger

        r = process.parse(root, text="a")

        self.assertEqual(process.parsed_length, 1)
        self.assertEqual(r, "unknown")
        self.assertEqual(process.current, d)

        # Simple negative condition test root -a-> a for "n"
        r = process.parse("new", root, text="n")

        self.assertEqual(r, "error")
        self.assertIn(c, process.errors)
        self.assertEqual(process.errors[c], "error")
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, c)

        # Simple positive condition test root -function-> None for "a"
        c.checker = is_a
        c.object = None

        r = process.parse("new", root, text="a")

        self.assertEqual(process.parsed_length, 1)
        self.assertEqual(r, "ok")
        self.assertEqual(process.current, c)

        r = process.parse("new", root, text="b")

        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, c)

        # Optional check
        c.mode = 'optional'

        r = process.parse("new", root, text="")

        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, c)

        # Test check
        c.mode = 'test'

        r = process.parse("new", root, text="a")

        self.assertEqual(r, "error")
        self.assertIn(process, process.errors)
        self.assertNotIn(c, process.errors)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, c)

        r = process.parse("new", root, text="b")

        self.assertEqual(r, "error")
        self.assertIn(process, process.errors)
        self.assertNotIn(c, process.errors)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, c)

        # Regex check
        c.mode = None

        c.checker = re.compile(r"(\s)*")

        r = process.parse("new", root, text="     ")

        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 5)
        self.assertEqual(process.current, c)

        # Underflow check
        r = process.parse("new", root, text=" z")

        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 1)
        self.assertEqual(process.current, c)
        self.assertEqual(process.errors[process], "underflow")

        # Zero checker test
        c.checker = None

        self.assertIsNone(c.parse("check"))

    def test_complex(self):
        #logger.add_queries()
        # Complex notion test: root -> ab -> (a , b) with empty message
        root = ComplexNotion("root")
        ab = ComplexNotion("ab")
        NextRelation(root, ab)

        a = ActionNotion("a", add_to_result)
        r1 = NextRelation(ab, a)

        b = ActionNotion("b", add_to_result)
        r2 = NextRelation(ab, b)

        process = ParsingProcess()
        process.callback = logger

        r = process.parse(root, test="test_complex_1")

        self.assertEqual(process.context["result"], "ab")
        self.assertTrue(r)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, b)

        # Complex notion negative test: root -> ab -> ( (-a-> a) , (-b-> b) ) for "a"
        r1.subject = None
        r2.subject = None

        ConditionalRelation(ab, a, "a")
        r2 = ConditionalRelation(ab, b, "b")

        r = process.parse(root, text="a", test="test_complex_2")

        self.assertEqual(process.context["result"], "a")
        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 1)
        self.assertIn(r2, process.errors)
        self.assertEqual(process.current, r2)  # Finished at error

        # Nested complex notion test: root -> ab -> ( (-a-> a) , (-b-> b)  -> c -> (d, e), f) for "abf"
        c = ComplexNotion("c")
        NextRelation(ab, c)

        d = ActionNotion("d", add_to_result)
        NextRelation(c, d)

        e = ActionNotion("e", add_to_result)
        NextRelation(c, e)

        f = ActionNotion("f", add_to_result)
        ConditionalRelation(ab, f, "f")

        r = process.parse("new", root, text="abf", test="test_complex_3")

        self.assertEqual(process.context["result"], "abdef")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 3)
        self.assertTrue(not process.errors)
        self.assertEqual(process.current, f)

    def test_states(self):
        #logger.add_queries()
        # Root -> (inc, inc, s, "state_check", inc)
        root = ComplexNotion("root")

        inc = ActionNotion("1", state_starter)

        NextRelation(root, inc)
        NextRelation(root, inc)
        s = ActionNotion("stop", showstopper)
        NextRelation(root, s)
        NextRelation(root, ActionNotion("state_check", state_checker))
        NextRelation(root, inc)

        process = StatefulProcess()
        process.callback = logger

        r = process.parse(root, test="test_states_1")

        self.assertEqual(r, "stop")
        self.assertEqual(process.current, s)
        self.assertEqual(process.states[inc]["v"], 2)

        # Checking clearing of states when new
        r = process.parse("new", root, test="test_states_2")
        self.assertEqual(r, "stop")
        self.assertEqual(process.states[inc]["v"], 2)
        self.assertEqual(process.current, s)

        # Manual clearing of states
        inc.action = "clear_state"

        r = process.parse(test="test_states_3")

        self.assertEqual(r, "ok")
        self.assertNotIn(inc, process.states)
        self.assertEqual(process.current, inc)

        # Notifications
        while root.relations:
            root.un_relate(root.relations[0])

        t = ActionNotion("terminator", has_notification)
        ActionRelation(root, t, {'notify': {'to': t, 'data': {'condition': 'stop'}}}, True)

        r = process.parse("new", root, test="test_states_4")
        self.assertEqual(r, "stop")
        self.assertEqual(process.current, t)

    def test_dict_tracking(self):
        d = {"a": 1, "c": 12}
        ops = DictChangeGroup()

        d2 = {"a": 1}

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

        self.assertEqual(d["b"], 3)
        self.assertEqual(d2["b"], 3)
        self.assertEqual(d["a"], 0)
        self.assertNotIn("c", d)

        ops.undo()

        self.assertEqual(d["a"], 1)
        self.assertEqual(d["c"], 12)
        self.assertNotIn("b", d)

        self.assertEqual(len(d), 2)

        self.assertEqual(str(a1), "%s %s=%s" % (DictChangeOperation.ADD,  a1._key, a1._value))
        self.assertEqual(repr(s1), "%s %s=%s<-%s" % (DictChangeOperation.SET,  s1._key, s1._value, s1._old_value))

        with self.assertRaises(ValueError):
            DictChangeOperation("fail", 1, 2)

    def test_stacking_context(self):
        #logger.add_queries()
        # Testing without tracking
        root = ComplexNotion("root")

        NextRelation(root, ActionNotion("change_context", {"add_context": {"inject": "ninja"}}))

        NextRelation(root, ActionNotion("change_context2", {"update_context": {"inject": "revenge of ninja"}}))

        NextRelation(root, ActionNotion("del_context", {"delete_context": "inject"}))

        p = ActionNotion("pop_context", "pop_context")
        NextRelation(root, p)

        process = StackingContextProcess()
        process.callback = logger

        r = process.parse(root, test="test_stacking_1")

        self.assertEqual(r, "ok")
        self.assertEqual(process.current, p)
        self.assertNotIn("inject", process.context)

        # Now tracking is on!
        root = ComplexNotion("root")

        NextRelation(root, ActionNotion("push", "push_context"))

        NextRelation(root, ActionNotion("change_context", {"add_context": {"terminator": "2"}}))

        NextRelation(root, ActionNotion("delete_context", {"delete_context": "terminator"}))

        NextRelation(root, ActionNotion("change_context2", {"update_context": {"alien": "omnomnom"}}))

        NextRelation(root, ActionNotion("check_context", lambda n, *m, **c: False if "alien" in c else "error"))

        NextRelation(root, ActionNotion("push", "push_context"))

        NextRelation(root, ActionNotion("change_context3", {"update_context": {"test": "predator"}}))

        NextRelation(root, ActionNotion("forget", "forget_context"))

        pop = ActionNotion("pop", "pop_context")
        NextRelation(root, pop)

        r = process.parse(root, test="test_stacking_2")

        self.assertEqual(r, "ok")
        self.assertEqual(process.current, pop)
        self.assertNotIn("alien", process.context)
        self.assertNotIn("terminator", process.context)
        self.assertEqual("predator", process.context["test"])  # Lasts because context changes were forgotten

        r = process.parse("new", pop, test="test_stacking_3")

        self.assertEqual(r, "ok")
        self.assertEqual(process.current, pop)
        self.assertFalse(process.context_stack)

    def test_loop(self):
        #logger.add_queries()
        # Simple loop test: root -5!-> a's -a-> a for "aaaaa"
        root = ComplexNotion("root")
        aa = ComplexNotion("a's")
        l = LoopRelation(root, aa, 5)

        self.assertIsNone(l.parse("test"))

        a = ActionNotion("a", add_to_result)
        c = ConditionalRelation(aa, a, "a")

        process = ParsingProcess()
        process.callback = logger

        r = process.parse(root, text="aaaaa", test="test_loop_basic")

        self.assertEqual(process.context["result"], "aaaaa")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 5)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l)  # Returning to the loop

        # Negative loop test: root -5!-> a's -a-> a for "aaaa"
        r = process.parse("new", root, text="aaaa", test="test_loop_neg")

        self.assertEqual(process.context["result"], "aaaa")
        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 4)
        self.assertIn(c, process.errors)
        self.assertIn(l, process.errors)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l)  # Returning to the loop

        # Loop test for arbitrary count root -*!-> a's -a-> a for "aaaa"
        l.n = '*'

        r = process.parse("new", root, text="aaaa", test="test_loop_*")

        self.assertEqual(process.context["result"], "aaaa")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 4)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l)  # Returning to the loop

        # Loop test for endless count root -*!-> a's -a-> a for "aaaa"
        l.n = True
        a.action = stop_infinite

        r = process.parse("new", root, text="aaaaaaa", test="test_loop_true_n")

        self.assertEqual(process.context["infinite"], 4)
        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 5)
        self.assertFalse(process.context_stack)
        self.assertIn(a, process.errors)
        self.assertNotIn(l, process.errors)
        self.assertEqual(process.current, l)  # Returning to the loop

        # Loop test for >1 count root -+!-> a's -a-> a for "aaaa"
        l.n = '+'
        a.action = add_to_result

        r = process.parse("new", root, text="aaaa", test="test_loop_+")

        self.assertEqual(process.context["result"], "aaaa")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 4)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l)  # Returning to the loop

        # Loop negative test for >1 count root -+!-> a's -a-> a for "b"
        l.n = '+'

        r = process.parse("new", root, text="b", test="test_loop_+_neg")

        self.assertNotIn("result", process.context)
        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 0)
        self.assertFalse(process.context_stack)
        self.assertIn(c, process.errors)
        self.assertIn(l, process.errors)
        self.assertEqual(process.current, l)  # Returning to the loop

        # Loop test for ? count root -?-> a's -a-> a for "a"
        l.n = '?'

        r = process.parse("new", root, text="a", test="test_loop_?")

        self.assertEqual(process.context["result"], "a")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 1)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l)  # Returning to the loop

        # Loop test for ? count root -?-> a's -a-> a for ""
        l.n = '?'

        r = process.parse("new", root, text="", test="test_loop_?_2")

        self.assertNotIn("result", process.context)
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 0)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l)  # Returning to the loop

        # Loop test for external function: root -function!-> a's -a-> a for "aaaa"
        l.n = if_loop

        r = process.parse("new", root, text="aaaaa", test="test_loop_ext_func")

        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 5)  # External functions stops at 5
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l)  # Returning to the loop

        # n=0 test
        l.n = 0
        r = process.parse("new", root, text="", test="test_loop_n=0")

        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 0)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l)  # Returning to the loop

        # Tuples test
        l2 = LoopRelation(None, None, (1, 2))

        self.assertEqual(l2.m, 1)
        self.assertEqual(l2.n, 2)

        l2 = LoopRelation(None, None, (2, ))

        self.assertEqual(l2.m, 2)
        self.assertEqual(l2.n, None)

        l2 = LoopRelation(None, None, (None, 2))

        self.assertEqual(l2.m, None)
        self.assertEqual(l2.n, 2)

        l.m = 2
        l.n = 4

        r = process.parse("new", root, text="aaa", test="test_loop_m..n")

        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 3)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l)  # Returning to the loop

        r = process.parse("new", root, text="a", test="test_loop_m..n_2")

        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 1)
        self.assertFalse(process.context_stack)
        self.assertNotIn(l, process.states)
        self.assertIn(c, process.errors)
        self.assertIn(l, process.errors)
        self.assertEqual(process.current, l)  # Returning to the loop

        r = process.parse("new", root, text="aaaa", test="test_loop_m..n_3")

        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 4)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l)  # Returning to the loop

        r = process.parse("new", root, text="aaaaa", test="test_loop_m..n_neg")

        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 4)
        self.assertNotIn(l, process.states)
        self.assertNotIn(c, process.errors)  # error is not here
        self.assertNotIn(l, process.errors)  # and not here too
        self.assertEqual(process.current, l)  # Returning to the loop

        l.m = None
        l.n = 2
        r = process.parse("new", root, text="", test="test_loop_none..n")

        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 0)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l)  # Returning to the loop

        r = process.parse("new", root, text="aa", test="test_loop_none..n_2")

        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 2)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l)  # Returning to the loop

        r = process.parse("new", root, text="aaa", test="test_loop_none..n_3")

        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 2)
        self.assertNotIn(c, process.errors)  # just more than
        self.assertNotIn(l, process.errors)  # we can eat
        self.assertNotIn(l, process.states)
        self.assertEqual(process.current, l)  # Returning to the loop

        l.m = 3
        l.n = None

        r = process.parse("new", root, text="aa", test="test_loop_m..none_neg")

        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 2)
        self.assertIn(c, process.errors)
        self.assertIn(l, process.errors)
        self.assertNotIn(l, process.states)
        self.assertEqual(process.current, l)  # Returning to the loop

        r = process.parse("new", root, text="aaa", test="test_loop_m..none")

        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 3)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l)  # Returning to the loop

        r = process.parse("new", root, text="aaaa", test="test_loop_m..none_2")

        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 4)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l)  # Returning to the loop

        # Nested loops test: root -2!-> a2 -2!-> a's -a-> a for "aaaa"
        del l.m
        l.n = 2

        aaa = ComplexNotion("a2")
        l.subject = aaa

        l2 = LoopRelation(root, aaa, 2)

        r = process.parse("new", root, text="aaaa", test="test_loop_nested")

        self.assertEqual(process.context["result"], "aaaa")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 4)
        self.assertNotIn(l, process.states)
        self.assertNotIn(l2, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l2)  # Returning to the top loop

        # Nested loops negative test: root -2!-> a2 -2!-> a's -a-> a for "aaab"
        r = process.parse("new", root, text="aaab", test="test_loop_nested_neg")

        self.assertEqual(process.context["result"], "aaa")
        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 3)
        self.assertIn(l, process.errors)
        self.assertIn(l2, process.errors)
        self.assertIn(c, process.errors)
        self.assertNotIn(l, process.states)
        self.assertNotIn(l2, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, l2)  # Returning to the top loop

        # Break test: root -2!-> a's (-a-> a, -!->)
        l.n = 2
        l.subject = root

        b = ActionNotion("b", add_to_result)
        NextRelation(aa, b)

        c = ActionNotion("c", add_to_result)
        NextRelation(root, c)

        a.action = lambda a, *m, **c: [add_to_result(a, *m, **c), 'break']

        r = process.parse("new", root, text="a", test="test_loop_break")

        self.assertEqual(process.context["result"], "ac")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 1)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, c)
        self.assertEqual(process.query, 'next')

        # Continue test
        a.action = lambda a, *m, **c: [add_to_result(a, *m, **c), 'continue']

        r = process.parse("new", root, text="aa", test="test_loop_continue")

        self.assertEqual(process.context["result"], "aac")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 2)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, c)

        # Final verification
        a.action = add_to_result

        r = process.parse("new", root, text="aa", test="test_loop_action")

        self.assertEqual(process.context["result"], "ababc")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 2)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, c)  # Returning to the loop

    def test_selective(self):
        #logger.add_queries()
        process = ParsingProcess()
        process.callback = logger

        # Simple selective test: root -a-> a, -b-> b for "b"
        root = SelectiveNotion("root")
        a = ActionNotion("a", add_to_result)

        c1 = ConditionalRelation(root, a, "a")

        b = ActionNotion("b", add_to_result)
        c2 = ConditionalRelation(root, b, "b")

        r = process.parse(root, text="b", test="test_selective_1")

        self.assertEqual(process.context["result"], "b")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 1)
        self.assertFalse(process.errors)
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, b)

        # Alternative negative test: same tree, message "xx"
        r = process.parse("new", root, text="xx", test="test_selective_2")

        self.assertNotIn("result", process.context)
        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 0)
        self.assertIn(root, process.errors)
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, root)  # No case found

        # Alternative test: root ->( a1 -> (-a-> a, -b->b) ), a2 -> (-aa->aa), -bb->bb ) ) for "aa"
        c1.subject = None
        c2.subject = None

        a1 = ComplexNotion("a1")
        NextRelation(root, a1)

        a = ComplexNotion("a")
        a1a = ConditionalRelation(a1, a, "a")

        b = ActionNotion("b", add_to_result)
        ConditionalRelation(a, b, "b")

        a2 = ComplexNotion("a2")
        na2 = NextRelation(root, a2)

        aa = ActionNotion("aa", add_to_result)
        caa = ConditionalRelation(a2, aa, "aa")

        bb = ActionNotion("bb", add_to_result)
        nbb = NextRelation(root, bb)

        r = process.parse("new", root, text="aa", test="test_selective_3")

        self.assertEqual(process.context["result"], "aa")
        self.assertTrue(r, "ok")
        self.assertEqual(process.parsed_length, 2)
        self.assertFalse(process.errors)
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, root)

        # Longest regex/selection
        # Alternative test: root ->( a1 -> (-a-> a, -b->b) ), -a-> a2 -> (-c->aa), -a+->bb ) ) for "aaaa"
        na2.subject = None
        na2.object = None

        ConditionalRelation(root, a2, "a")
        caa.checker = "c"

        nbb.subject = None
        nbb.object = None
        ConditionalRelation(root, bb, re.compile("(a)+"))

        s = ActionNotion("stop", showstopper)
        ConditionalRelation(root, s, "a")

        r = process.parse("new", root, text="aaaa", test="test_selective_4")

        self.assertEqual(process.context["result"], "bb")
        self.assertTrue(r, "ok")
        self.assertEqual(process.parsed_length, 4)
        self.assertFalse(process.errors)
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, root)

        # Negative test
        r = process.parse("new", root, text="x", test="test_selective_5")
        self.assertTrue(r, "error")
        self.assertEqual(process.parsed_length, 0)
        self.assertIn(root, process.errors)
        self.assertIn(a1a, process.errors)  # Error for the first real condition after epsilon move to a1
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, root)

        # Error test
        for relation in root.relations:
            relation.subject = None

        breaker = ActionNotion("breaker", ["break", "error"])
        c1 = ConditionalRelation(root, breaker, "a")
        n1 = NextRelation(root, ActionNotion("adder", add_to_result))

        r = process.parse("new", root, text="a", test="test_selective_6")
        self.assertTrue(r, "error")
        self.assertNotIn("result", process.context)
        self.assertEqual(process.parsed_length, 1)
        self.assertIn(root, process.errors)
        self.assertIn(breaker, process.errors)
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, root)

        breaker.action = "break"  # In this case Selective will not offer new cases

        r = process.parse("new", root, text="a", test="test_selective_7")
        self.assertTrue(r, "ok")
        self.assertNotIn("result", process.context)
        self.assertEqual(process.parsed_length, 1)
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, root)

        breaker.action = "error"

        r = process.parse("new", root, text="a", test="test_selective_8")
        self.assertTrue(r, "error")
        self.assertEqual(process.context["result"], "adder")
        self.assertEqual(process.parsed_length, 0)
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)
        self.assertEqual(process.current, root)
        self.assertNotIn(root, process.errors)
        self.assertNotIn(breaker, process.errors)
        self.assertIn(process, process.errors)

    def test_special(self):
        #logger.add_queries()
        # Complex loop test: root -(*)-> sequence [-(a)-> a's -> a, -(b)-> b's -> b]
        root = ComplexNotion("root")
        sequence = ComplexNotion("sequence")

        LoopRelation(root, sequence, 6)

        a_seq = ComplexNotion("a's")
        LoopRelation(sequence, a_seq)
        a = ActionNotion("a", add_to_result)

        ConditionalRelation(a_seq, a, "a")

        b_seq = ComplexNotion("b's")
        LoopRelation(sequence, b_seq)
        b = ActionNotion("b", add_to_result)

        ConditionalRelation(b_seq, b, "b")

        test_string = "bbaabb"

        process = ParsingProcess()
        process.callback = logger

        r = process.parse(root, text=test_string, test="special_test_1")

        self.assertEqual(r, "ok")
        self.assertEqual(process.context["result"], test_string)
        self.assertEqual(process.parsed_length, 6)
        self.assertFalse(process.errors)
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)
    '''
    def test_analyzer(self):
        global _acc

        root = ComplexNotion("root")

        a = Analyzer()
        a.events.append({'filter': 'query', 'abstract': root, 'call': accumulate_false})

        # Simple next test: root -> a
        process = ParsingProcess()
        process.callback = a

        r = process.parse(root, test="analyzer_test_1")
        self.assertEqual(_acc, 2)
        self.assertEqual(r, "ok")

        _acc = 0

        a.events = [lambda *m, **c: 'Skadoosh']
        r = process.parse(root, test="analyzer_test_2")
        self.assertEqual(_acc, 0)
        self.assertEqual(r, "unknown")

        # Uncomment for debug
        '''a.events = []
        a.add_queries()
        a.add_details()

        _acc = 0

        r = process.parse("new", root, test="analyzer_test_2")
        self.assertEqual(_acc, 0)
        self.assertEqual(r, "ok")'''


def test():
    suite = unittest.TestLoader().loadTestsFromTestCase(UtTests)
    #suite = unittest.TestLoader().loadTestsFromName('test.UtTests.test_special')
    unittest.TextTestRunner(verbosity=2).run(suite)

