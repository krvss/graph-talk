from ut import *

import unittest

# Simple process logger
class Logger(Abstract):
    filter = None
    logging = True

    def parse(self, *message, **context):
        if not self.logging:
            return None

        if Logger.filter and not Logger.filter in message:
            return False

        process = context['from']

        log_str = '%s:' % message[0]
        properties = ', '.join([ ('%s: %s' % (p, getattr(process, p))) for p in process._queueing_properties() ])

        print log_str + properties

        return None

logger = Logger()

class Debugger(Abstract):
    def parse(self, *message, **context):
        if message[0] == "next_post" and str(context["from"].current) == '"here"':
            return "debug"


class Skipper(Abstract):
    def parse(self, *message, **context):
        if message[0] == "unknown_pre":
            return "skip"


def showstopper(abstract, *message, **context):
    return abstract.name

def state_stater(notion, *message, **context):
    if "state" in context and "v" in context["state"]:
        return {"set_state" : {"v": context["state"]["v"] + 1}}
    else:
        return {"set_state" : {"v":1}}

def state_checker(notion, *message, **context):
    if "state" in context and "v" in context["state"]:
        return "error"
    else:
        return None

_acc = 0
def acc(notion, *message, **context):
    global _acc
    _acc += 1
    return _acc

def accF(notion, *message, **context):
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

# TODO: ensure test coverage
class BasicTests(unittest.TestCase):

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

        # If relation is only one ComplexNotion should return it
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

        r = process.parse(root, test="next")

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

        r = process.parse(root, test="debugging")

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

        c = FunctionNotion("c", accF)
        NextRelation(a, c)

        skipper = Skipper()
        process.callback = skipper

        _acc = 0
        r = process.parse("new", root, test="skipper")

        self.assertEqual(r, "ok")
        self.assertEqual(_acc, 1)
        self.assertEqual(process.current, a)


    def test_queue(self):
        global _acc

        #logger.logging = True

        # Stack test: root -> (a, d); a -> (b,c)
        root = ComplexNotion("root")
        a = ComplexNotion("a")

        NextRelation(root, a)

        b = FunctionNotion("b", accF) # Just return False to keep going to C
        b2 = ValueNotion("b2", []) # Test of empty array
        c = FunctionNotion("c", showstopper) # Stop here

        NextRelation(a, b)
        NextRelation(a, b2)
        NextRelation(a, c)

        d = FunctionNotion("d", showstopper)

        NextRelation(root, d)

        process = Process()
        process.callback = logger

        _acc = 0
        r = process.parse(root, test="test_queue")

        self.assertEqual(process.reply, "c")
        self.assertEqual(process.current, c)
        self.assertEqual(r, "unknown")
        self.assertEqual(_acc, 1)

        r = process.parse("skip", test="test_skip") # Make process pop from stack

        self.assertEqual(process.reply, "d")
        self.assertEqual(process.current, d)
        self.assertEqual(r, "unknown")

        r = process.parse("skip", test="test_skip_2") # Trying empty stack

        self.assertEqual(process.reply, [])
        self.assertEqual(process.current, root) # Root is because it was ComplexNotion
        self.assertEqual(r, "ok")

        # Trying list message
        _acc = 0
        process.parse(b, b, b)
        self.assertEqual(_acc, 3)


    def test_context(self):
        #logger.logging = True

        # Verify correctness of adding
        root = ComplexNotion("root")
        a = FunctionNotion("context", lambda notion, *message, **context:{"add_context":{"context": True}})
        b = FunctionNotion("check_context", lambda notion, *message, **context: 'stop' if 'context' in context else False)

        NextRelation(root, a)
        NextRelation(root, b)

        process = ContextProcess()
        process.callback = logger

        r = process.parse(root, test = "context_add")
        self.assertEqual(r, "stop")
        self.assertIn("context", process.context)

        process.context["context"] = False

        r = process.parse("new", root, {"add_context": {"from": "message"}}, test = "context_add_2", context = "1")
        self.assertEqual(r, "stop")
        self.assertEqual("1", process.context["context"])
        self.assertEqual("message", process.context["from"])

        # Checking that context is the same if there is no new command
        r = process.parse(root)
        self.assertEqual("message", process.context["from"])

        # Checking that context is NOT the same if there is new command
        r = process.parse("new", root)
        self.assertNotIn("from", process.context)

        # Verify updating
        a.function = lambda notion, *message, **context: {"update_context":{"context": "new"}}

        r = process.parse("new", root, test = "context_update", context = "2")
        self.assertEqual(r, "stop")
        self.assertEqual("new", process.context["context"])

        # Verify deleting & mass deleting
        a.function = lambda notion, *message, **context: {"delete_context":"context"}

        r = process.parse("new", root, test = "context_del", context = "3")
        self.assertEqual(r, "ok")
        self.assertNotIn("context", process.context)

        a.function = lambda notion, *message, **context: {"delete_context":["context", "more", "more2"]}

        r = process.parse("new", root, test = "context_del", context = "4", more = False)
        self.assertEqual(r, "ok")
        self.assertNotIn("context", process.context)
        self.assertNotIn("more", process.context)

        # See what's happening if command argument is incorrect
        a.function = lambda notion, *message, **context: {"update_context"}

        r = process.parse("new", root, test = "context_bad")
        self.assertEqual(r, "unknown")


    def test_errors(self):
        #logger.logging = True
        root = ComplexNotion("root")
        a = ComplexNotion("a")

        NextRelation(root, a)

        b = FunctionNotion("stop", showstopper) # First stop
        c = FunctionNotion("error", showstopper) # Error!
        d = FunctionNotion("errorer", lambda notion, *message, **context: {"error": "i_m_bad"}) # Another error!
        e = FunctionNotion("end", showstopper) # And finally here

        NextRelation(a, b)
        NextRelation(a, c)
        NextRelation(a, d)
        NextRelation(a, e)

        process = TextParsingProcess()
        process.callback = logger

        r = process.parse(root, test="test_errors")

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

        d = FunctionNotion("noti", has_condition)

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

        c.object = FunctionNotion("text", lambda notion, *message, **context: {"update_context": {"text": "new_text"}})

        r = process.parse("new", root, "a")

        self.assertEqual(r, "error")
        self.assertEqual(process.parsed_length, 0)


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
        self.assertEqual(process.current, ab) # Because root has 1 child only, so no lists

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
        self.assertEqual(process.current, ab) # Nowhere to go

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
        self.assertEqual(process.current, ab) # Last complex notion with list


    def test_states(self):
        #logger.logging = True
        root = ComplexNotion("root")

        inc = FunctionNotion("1", state_stater)

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
        r = process.parse("new", root, test="test_states_1")
        self.assertEqual(r, "stop")
        self.assertEqual(process.states[inc]["v"], 2)

        # Manual clearing of states
        inc.function = lambda n, *m, **c: "clear_state"

        r = process.parse(test="test_states_3")

        self.assertEqual(r, "ok")
        self.assertNotIn(inc, process.states)

'''
    def if_loop(loop, context):
        if not loop in context:
            context[loop] = 5
            return True

        i = context[loop] - 1

        if i > 0:
            context[loop] = i
            return True

        return False


    def test_loop(self):
        # Simple loop test: root -5!-> a's -a-> a for "aaaaa"
        root = ComplexNotion("root")
        aa = ComplexNotion("a's")
        l = LoopRelation(root, aa, 5)

        a = FunctionNotion("a", add_to_result)
        c = ConditionalRelation(aa, a, "a")

        process = ParserProcess()
        process.callback = logger

        context = {"start": root}
        r = process.parse("aaaaa", context)

        self.assertEqual(context["result"], "aaaaa")
        self.assertTrue(r["result"])
        self.assertEqual(r["length"], 5)
        self.assertTrue(not l in context)
        self.assertFalse(context[process]["states"])

        # Negative loop test: root -5!-> a's -a-> a for "aaaa"
        context = {"start": root}
        r = process.parse("aaaa", context)

        self.assertEqual(context["result"], "aaaa")
        self.assertFalse(r["result"])
        self.assertEqual(r["length"], 4)
        self.assertListEqual(context["error"], [c, l])
        self.assertTrue(not l in context)
        self.assertFalse(context[process]["states"])

        # Loop test for arbitrary count root -*!-> a's -a-> a for "aaaa"
        l.n = None

        context = {"start": root}
        r = process.parse("aaaa", context)

        self.assertEqual(context["result"], "aaaa")
        self.assertTrue(r["result"])
        self.assertEqual(r["length"], 4)
        self.assertTrue(not l in context)
        self.assertFalse(context[process]["states"])

        # Loop test for external function: root -function!-> a's -a-> a for "aaaa"
        l.n = if_loop

        context = {"start": root}
        r = process.parse("aaaaa", context)

        self.assertEqual(context["result"], "aaaaa")
        self.assertTrue(r["result"])
        self.assertEqual(r["length"], 5)
        self.assertTrue(not "error" in context)
        self.assertTrue(not l in context)
        self.assertFalse(context[process]["states"])

        # Nested loops test: root -2!-> a2 -2!-> a's -a-> a for "aaaa"
        l.n = 2

        aaa = ComplexNotion("a2")
        l.subject = aaa

        l2 = LoopRelation(root, aaa, 2)

        context = {"start": root}
        r = process.parse("aaaaa", context)

        self.assertEqual(context["result"], "aaaa")
        self.assertTrue(r["result"])
        self.assertEqual(r["length"], 4)
        self.assertTrue(not "error" in context)
        self.assertTrue(not l in context)
        self.assertTrue(not l2 in context)
        self.assertFalse(context[process]["states"])

        # Nested loops negative test: root -2!-> a2 -2!-> a's -a-> a for "aaab"
        context = {"start": root}
        r = process.parse("aaab", context)

        self.assertEqual(context["result"], "aaa")
        self.assertFalse(r["result"])
        self.assertEqual(r["length"], 3)
        self.assertListEqual(context["error"], [c, l, l2])
        self.assertTrue(not l in context)
        self.assertTrue(not l2 in context)
        self.assertFalse(context[process]["states"])


    def test_selective(self):
        process = ParserProcess()
        process.callback = logger

        # Simple selective test: root -a-> a, -b-> b for "b"
        root = SelectiveNotion("root")
        a = FunctionNotion("a", add_to_result)

        c1 = ConditionalRelation(root, a, "a")

        b = FunctionNotion("b", add_to_result)
        c2 = ConditionalRelation(root, b, "b")

        context = {"start": root}
        r = process.parse("b", context)

        self.assertEqual(context["result"], "b")
        self.assertTrue(r["result"])
        self.assertEqual(r["length"], 1)
        self.assertTrue(not "error" in context)
        self.assertTrue(not root in context)
        self.assertFalse(context[process]["states"])

        # Alternative negative test: same tree, message "xx"
        context = {"start": root}
        r = process.parse("xx", context)

        self.assertFalse("result" in context)
        self.assertFalse(r["result"])
        self.assertEqual(r["length"], 0)
        self.assertListEqual(context["error"], [c2, root])
        self.assertFalse(context[process]["states"])

        # Alternative test: root ->( a1 -> (-a-> a, -b->b) ), a2 -> (-aa->aa, -bb->bb) ) ) for "aa"
        c1.subject = None
        c2.subject = None

        a1 = ComplexNotion("a1")
        NextRelation(root, a1)

        a = ComplexNotion("a")
        ConditionalRelation(a1, a, "a")

        b = FunctionNotion("b", add_to_result)
        ConditionalRelation(a, b, "b")

        a2 = ComplexNotion("a2")
        NextRelation(root, a2)

        aa = FunctionNotion("aa", add_to_result)
        ConditionalRelation(a2, aa, "aa")

        bb = FunctionNotion("bb", add_to_result)
        NextRelation(root, bb)

        context = {"start": root}
        r = process.parse("aa", context)

        self.assertEqual(context["result"], "aa")
        self.assertTrue(r["result"])
        self.assertEqual(r["length"], 2)
        self.assertTrue(not "error" in context)
        self.assertTrue(not root in context)
        self.assertFalse(context[process]["states"])
        '''

# Custom processing function
def custom_func(notion, context):
    print notion
    return True

def test():
    logger.logging = False
    suite = unittest.TestLoader().loadTestsFromTestCase(BasicTests)
    #suite = unittest.TestLoader().loadTestsFromName('test.BasicTests.test_complex')
    unittest.TextTestRunner(verbosity=2).run(suite)

    return


    # Complex loop test
    root = ComplexNotion("root")
    sequence = ComplexNotion("sequence")

    LoopRelation(root, sequence)

    a_seq = ComplexNotion("a's")
    LoopRelation(sequence, a_seq)
    a = FunctionNotion("a", custom_func)

    ConditionalRelation(a_seq, a, "a")

    b_seq = ComplexNotion("b's")
    LoopRelation(sequence, b_seq)
    b = FunctionNotion("b", custom_func)

    ConditionalRelation(b_seq, b, "b")

    test_string = "bbaabb"

    #test_string = "aaaaaab"

    process = ParserProcess()
    context = {"start": root}
    process.parse(test_string, context)

    print context


