import unittest

from ut import *
import re


# Simple process logger
class Logger(Abstract):
    filter = None
    logging = False

    def parse(self, *message, **context):
        if not self.logging:
            return None

        if Logger.filter and not Logger.filter in message:
            return False

        process = context['from']

        log_str = '%s:' % message[0]
        properties = ', '.join([('%s: %s' % (p, getattr(process, p))) for p in process._queueing_properties()])

        print log_str + properties

        return None

logger = Logger()


# Dialog test
class Debugger(Abstract):
    def parse(self, *message, **context):
        if message[0] == "next_post" and str(context["from"].current) == '"here"':
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


def accumulate_false(notion, *message, **context):
    global _acc
    _acc += 1
    return False


def is_a(condition, *message, **context):
    if "text" in context and context["text"].startswith("a"):
        return True, 1
    else:
        return False, 0


def has_condition(notion, *message, **context):
    if 'state' in context and 'notifications' in context['state']:
        return context['state']['notifications']['condition']
    else:
        return False


def add_to_result(notion, *message, **context):
    add = notion.name
    if "result" in context:
        add = context["result"] + add

    return {"update_context":{"result": add}}

_loop = 5


def if_loop(*message, **context):
    global _loop

    _loop -= 1

    if _loop >= 0:
        return True

    _loop = 5

    return False


class UtTests(unittest.TestCase):

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
        self.assertEqual(cn.parse(), r1)

        r2 = Relation(cn, n1)
        r2.subject = cn

        # If there is more than 1 relation ComplexNotion should return the list
        self.assertListEqual(cn.parse(), [r1, r2])

    def test_next(self):
        #logger.logging = True

        # Simple next test: root -> a
        root = ComplexNotion("root")
        a = FunctionNotion("a", showstopper)

        NextRelation(root, a)

        process = Process()
        process.callback = logger

        r = process.parse(root, test="test_next_1")

        self.assertEqual(process.reply, "a")
        self.assertEqual(process.current, a)
        self.assertEqual(r, "unknown")

        # Now function will not confuse process
        a.function = None
        r = process.parse("new", root, test="test_next_2")

        self.assertEqual(process.reply, None)
        self.assertEqual(process.current, a)
        self.assertEqual(r, "ok")

    def test_callback(self):
        global _acc

        # Simple debugger test: stop at "a" notion, skip the result by the command and go further
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
        b = FunctionNotion("b", showstopper)
        NextRelation(a, b)

        c = FunctionNotion("c", accumulate_false)
        NextRelation(a, c)

        skipper = Skipper()
        process.callback = skipper

        _acc = 0
        r = process.parse("new", root, test="test_skipper")

        self.assertEqual(r, "ok")
        self.assertEqual(_acc, 1)
        self.assertEqual(process.current, a)

    def test_queue(self):
        global _acc

        #logger.logging = True

        # Stack test: root -> (a, d); a -> (b, b2, c)
        root = ComplexNotion("root")
        a = ComplexNotion("a")

        NextRelation(root, a)

        b = FunctionNotion("b", accumulate_false)  # Just return False to keep going to C
        b2 = ValueNotion("b2", [])  # Test of empty array
        c = FunctionNotion("c", showstopper)  # Stop here

        NextRelation(a, b)
        NextRelation(a, b2)
        NextRelation(a, c)

        d = FunctionNotion("d", showstopper)  # And stop here too

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

        self.assertEqual(process.reply, [])
        self.assertEqual(process.current, root)  # Root is because it was ComplexNotion
        self.assertEqual(r, "ok")

        # Trying list message
        _acc = 0
        process.parse(b, b, b)
        self.assertEqual(_acc, 3)

    def test_context(self):
        #logger.logging = True

        # Verify correctness of adding
        root = ComplexNotion("root")
        a = FunctionNotion("ctx", lambda notion, *message, **context:
                           {"add_context": {"ctx": True}})

        b = FunctionNotion("check_context", lambda notion, *message, **context:
                           'stop' if 'ctx' in context else False)

        NextRelation(root, a)
        NextRelation(root, b)

        process = SharedContextProcess()
        process.callback = logger

        r = process.parse(root, test="test_context_add_1")
        self.assertEqual(r, "stop")
        self.assertIn("ctx", process.context)

        process.context["ctx"] = False

        r = process.parse("new", root, {"add_context": {"from": "me"}}, test="test_context_add_2", ctx="1")

        self.assertEqual(r, "stop")
        self.assertEqual("1", process.context["ctx"])
        self.assertEqual("me", process.context["from"])

        # Checking that context is the same if there is no new command
        r = process.parse(root)
        self.assertEqual(r, "stop")
        self.assertEqual("me", process.context["from"])

        # Checking that context is NOT the same if there is new command
        r = process.parse("new", root)
        self.assertEqual(r, "stop")
        self.assertNotIn("from", process.context)

        # Verify updating
        a.function = lambda notion, *message, **context: {"update_context": {"ctx": "new"}}

        r = process.parse("new", root, test="test_context_update", ctx="2")
        self.assertEqual(r, "stop")
        self.assertEqual("new", process.context["ctx"])

        # Verify deleting & mass deleting
        a.function = lambda notion, *message, **context: {"delete_context": "ctx"}

        r = process.parse("new", root, test="test_context_del", ctx="3")
        self.assertEqual(r, "ok")
        self.assertNotIn("ctx", process.context)

        a.function = lambda notion, *message, **context: {"delete_context": ["ctx", "more", "more2"]}

        r = process.parse("new", root, test="test_context_del", ctx="4", more=False)
        self.assertEqual(r, "ok")
        self.assertNotIn("ctx", process.context)
        self.assertNotIn("more", process.context)

        # See what's happening if command argument is incorrect
        a.function = lambda notion, *message, **context: {"update_context"}

        r = process.parse("new", root, test="test_context_bad")
        self.assertEqual(r, "unknown")

    def test_errors(self):
        #logger.logging = True
        root = ComplexNotion("root")
        a = ComplexNotion("a")

        NextRelation(root, a)

        b = FunctionNotion("stop", showstopper)  # First stop
        c = FunctionNotion("error", showstopper)  # Error!
        d = FunctionNotion("errorer", lambda notion, *message, **context: {"error": "i_m_bad"})  # Another error!
        e = FunctionNotion("end", showstopper)  # And finally here

        NextRelation(a, b)
        NextRelation(a, c)
        NextRelation(a, d)
        NextRelation(a, e)

        process = TextParsingProcess()
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
        self.assertEqual(process.current, None)
        self.assertEqual(r, "ok")

    def test_condition(self):
        #logger.logging = True
        # Simple positive condition test root -a-> a for "a"
        root = ComplexNotion("root")

        d = FunctionNotion("d", has_condition)

        c = ConditionalRelation(root, d, "a")

        process = TextParsingProcess()
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

        # Simple positive condition test root -function-> a for "a"
        c.checker = is_a
        c.object = None

        r = process.parse("new", root, text="a")

        self.assertEqual(process.parsed_length, 1)
        self.assertEqual(r, "ok")

        r = process.parse("new", root, text="b")

        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 0)

        # Optional check
        c.optional = True

        r = process.parse("new", root, text="")

        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 0)

        # Regex check
        c.optional = False

        c.checker = re.compile(r"(\s)*")

        r = process.parse("new", root, text="     ")

        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 5)

        # Underflow check
        r = process.parse("new", root, text=" z")

        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 1)


    def test_complex(self):
        #logger.logging = True
        # Complex notion test: root -> ab -> (a , b) with empty message
        root = ComplexNotion("root")
        ab = ComplexNotion("ab")
        NextRelation(root, ab)

        a = FunctionNotion("a", add_to_result)
        r1 = NextRelation(ab, a)

        b = FunctionNotion("b", add_to_result)
        r2 = NextRelation(ab, b)

        process = TextParsingProcess()
        process.callback = logger

        r = process.parse(root, test="test_complex_1")

        self.assertEqual(process.context["result"], "ab")
        self.assertTrue(r)
        self.assertEqual(process.parsed_length, 0)
        self.assertEqual(process.current, ab)  # Because root has 1 child only, so no lists

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
        self.assertEqual(process.current, ab)  # Nowhere to go

        # Nested complex notion test: root -> ab -> ( (-a-> a) , (-b-> b)  -> c -> (d, e), f) for "abf"
        c = ComplexNotion("c")
        NextRelation(ab, c)

        d = FunctionNotion("d", add_to_result)
        NextRelation(c, d)

        e = FunctionNotion("e", add_to_result)
        NextRelation(c, e)

        f = FunctionNotion("f", add_to_result)
        ConditionalRelation(ab, f, "f")

        r = process.parse("new", root, text="abf", test="test_complex_3")

        self.assertEqual(process.context["result"], "abdef")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 3)
        self.assertTrue(not process.errors)
        self.assertEqual(process.current, ab)  # Last complex notion with list

    def test_states(self):
        #logger.logging = True
        root = ComplexNotion("root")

        inc = FunctionNotion("1", state_starter)

        NextRelation(root, inc)
        NextRelation(root, inc)
        NextRelation(root, FunctionNotion("stop", showstopper))
        NextRelation(root, FunctionNotion("state_check", state_checker))
        NextRelation(root, inc)

        process = StatefulProcess()
        process.callback = logger

        r = process.parse(root, test="test_states_1")

        self.assertEqual(r, "stop")
        self.assertEqual(process.states[inc]["v"], 2)

        # Checking clearing of states when new
        r = process.parse("new", root, test="test_states_2")
        self.assertEqual(r, "stop")
        self.assertEqual(process.states[inc]["v"], 2)

        # Manual clearing of states
        inc.function = lambda n, *m, **c: "clear_state"

        r = process.parse(test="test_states_3")

        self.assertEqual(r, "ok")
        self.assertNotIn(inc, process.states)

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
        #logger.logging = True
        # Testing without tracking
        root = ComplexNotion("root")

        NextRelation(root, FunctionNotion("change_context",
                                          lambda n, *m, **c: {"add_context": {"inject": "ninja"}}))

        NextRelation(root, FunctionNotion("change_context2",
                                          lambda n, *m, **c: {"update_context": {"inject": "revenge of ninja"}}))

        NextRelation(root, FunctionNotion("del_context", lambda n, *m, **c: {"delete_context": "inject"}))

        NextRelation(root, FunctionNotion("pop_context", lambda n, *m, **c: "pop_context"))

        process = StackingContextProcess()
        process.callback = logger

        r = process.parse(root, test="test_stacking_1")

        self.assertEqual(r, "ok")
        self.assertNotIn("inject", process.context)

        # Now tracking is on!
        root = ComplexNotion("root")

        push_l = lambda n, *m, **c: "push_context"

        NextRelation(root, FunctionNotion("push", push_l))

        NextRelation(root, FunctionNotion("change_context", lambda n, *m, **c: {"add_context": {"terminator": "2"}}))

        NextRelation(root, FunctionNotion("delete_context", lambda n, *m, **c: {"delete_context": "terminator"}))

        NextRelation(root, FunctionNotion("change_context2", lambda n, *m, **c:
                                          {"update_context": {"alien": "omnomnom"}}))

        NextRelation(root, FunctionNotion("check_context", lambda n, *m, **c: False if "alien" in c else "error"))

        NextRelation(root, FunctionNotion("push", push_l))

        NextRelation(root, FunctionNotion("change_context3", lambda n, *m, **c:
                                          {"update_context": {"test": "predator"}}))

        NextRelation(root, FunctionNotion("forget", lambda n, *m, **c: "forget_context"))

        pop = FunctionNotion("pop", lambda n, *m, **c: "pop_context")
        NextRelation(root, pop)

        r = process.parse(root, test="test_stacking_2")

        self.assertEqual(r, "ok")
        self.assertNotIn("alien", process.context)
        self.assertNotIn("terminator", process.context)
        self.assertEqual("predator", process.context["test"])  # Lasts because context changes were forgotten

        r = process.parse("new", pop, test="test_stacking_3")

        self.assertEqual(r, "ok")
        self.assertFalse(process.context_stack)

    def test_loop(self):
        #logger.logging = True
        # Simple loop test: root -5!-> a's -a-> a for "aaaaa"
        root = ComplexNotion("root")
        aa = ComplexNotion("a's")
        l = LoopRelation(root, aa, 5)

        a = FunctionNotion("a", add_to_result)
        c = ConditionalRelation(aa, a, "a")

        process = TextParsingProcess()
        process.callback = logger

        r = process.parse(root, text="aaaaa", test="test_loop_1")

        self.assertEqual(process.context["result"], "aaaaa")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 5)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)

        # Negative loop test: root -5!-> a's -a-> a for "aaaa"
        r = process.parse("new", root, text="aaaa", test="test_loop_2")

        self.assertEqual(process.context["result"], "aaaa")
        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 4)
        self.assertIn(c, process.errors)
        self.assertIn(l, process.errors)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)

        # Loop test for arbitrary count root -*!-> a's -a-> a for "aaaa"
        l.n = None

        r = process.parse("new", root, text="aaaa", test="test_loop_3")

        self.assertEqual(process.context["result"], "aaaa")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 4)
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)

        # Loop test for external function: root -function!-> a's -a-> a for "aaaa"
        l.n = if_loop

        r = process.parse("new", root, text="aaaaa", test="test_loop_4")

        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 5)  # External functions stops at 5
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)

        # n=0 test
        l.n = 0
        r = process.parse("new", root, text="", test="test_loop_5")

        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 0)  # External functions stops at 5
        self.assertNotIn(l, process.states)
        self.assertFalse(process.context_stack)

        # Nested loops test: root -2!-> a2 -2!-> a's -a-> a for "aaaa"
        l.n = 2

        aaa = ComplexNotion("a2")
        l.subject = aaa

        l2 = LoopRelation(root, aaa, 2)

        r = process.parse("new", root, text="aaaa", test="test_loop_6")

        self.assertEqual(process.context["result"], "aaaa")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 4)
        self.assertNotIn(l, process.states)
        self.assertNotIn(l2, process.states)
        self.assertFalse(process.context_stack)

        # Nested loops negative test: root -2!-> a2 -2!-> a's -a-> a for "aaab"
        r = process.parse("new", root, text="aaab", test="test_loop_7")

        self.assertEqual(process.context["result"], "aaa")
        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 3)
        self.assertIn(l, process.errors)
        self.assertIn(l2, process.errors)
        self.assertIn(c, process.errors)
        self.assertNotIn(l, process.states)
        self.assertNotIn(l2, process.states)
        self.assertFalse(process.context_stack)

    def test_selective(self):
        #logger.logging = True
        process = TextParsingProcess()
        process.callback = logger

        # Simple selective test: root -a-> a, -b-> b for "b"
        root = SelectiveNotion("root")
        a = FunctionNotion("a", add_to_result)

        c1 = ConditionalRelation(root, a, "a")

        b = FunctionNotion("b", add_to_result)
        c2 = ConditionalRelation(root, b, "b")

        r = process.parse(root, text="b", test="test_selective_1")

        self.assertEqual(process.context["result"], "b")
        self.assertEqual(r, "ok")
        self.assertEqual(process.parsed_length, 1)
        self.assertFalse(process.errors)
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)

        # Alternative negative test: same tree, message "xx"
        r = process.parse("new", root, text="xx", test="test_selective_2")

        self.assertNotIn("result", process.context)
        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 0)
        self.assertIn(root, process.errors)
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)

        # Alternative test: root ->( a1 -> (-a-> a, -b->b) ), a2 -> (-aa->aa), -bb->bb ) ) for "aa"
        c1.subject = None
        c2.subject = None

        a1 = ComplexNotion("a1")
        NextRelation(root, a1)

        a = ComplexNotion("a")
        ConditionalRelation(a1, a, "a")

        b = FunctionNotion("b", add_to_result)
        ConditionalRelation(a, b, "b")

        a2 = ComplexNotion("a2")
        na2 = NextRelation(root, a2)

        aa = FunctionNotion("aa", add_to_result)
        caa = ConditionalRelation(a2, aa, "aa")

        bb = FunctionNotion("bb", add_to_result)
        nbb = NextRelation(root, bb)

        r = process.parse("new", root, text="aa", test="test_selective_3")

        self.assertEqual(process.context["result"], "aa")
        self.assertTrue(r, "ok")
        self.assertEqual(process.parsed_length, 2)
        self.assertFalse(process.errors)
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)

        # Longest regex/selection
        # Alternative test: root ->( a1 -> (-a-> a, -b->b) ), -a-> a2 -> (-c->aa), -a+->bb ) ) for "aaaa"
        na2.subject = None
        na2.object = None

        ConditionalRelation(root, a2, "a")
        caa.checker = "c"

        nbb.subject = None
        nbb.object = None
        cbb = ConditionalRelation(root, bb, re.compile("(a)+"))

        r = process.parse("new", root, text="aaaa", test="test_selective_4")

        self.assertEqual(process.context["result"], "bb")
        self.assertTrue(r, "ok")
        self.assertEqual(process.parsed_length, 4)
        self.assertFalse(process.errors)
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)

        # Negative test
        r = process.parse("new", root, text="x", test="test_selective_5")
        self.assertTrue(r, "error")
        self.assertEqual(process.parsed_length, 0)
        self.assertIn(root, process.errors)
        self.assertIn(cbb, process.errors)
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)

    def test_special(self):
        #logger.logging = True
        # Complex loop test: root -(*)-> sequence [-(a)-> a's -> a, -(b)-> b's -> b]
        root = ComplexNotion("root")
        sequence = ComplexNotion("sequence")

        LoopRelation(root, sequence, 6)

        a_seq = ComplexNotion("a's")
        LoopRelation(sequence, a_seq)
        a = FunctionNotion("a", add_to_result)

        ConditionalRelation(a_seq, a, "a")

        b_seq = ComplexNotion("b's")
        LoopRelation(sequence, b_seq)
        b = FunctionNotion("b", add_to_result)

        ConditionalRelation(b_seq, b, "b")

        test_string = "bbaabb"

        process = TextParsingProcess()
        process.callback = logger

        r = process.parse(root, text=test_string, test="special_test_1")

        self.assertEqual(r, "ok")
        self.assertEqual(process.context["result"], test_string)
        self.assertEqual(process.parsed_length, 6)
        self.assertFalse(process.errors)
        self.assertNotIn(root, process.states)
        self.assertFalse(process.context_stack)


def test():
    suite = unittest.TestLoader().loadTestsFromTestCase(UtTests)
    #suite = unittest.TestLoader().loadTestsFromName('test.UtTests.test_special')
    unittest.TextTestRunner(verbosity=2).run(suite)

