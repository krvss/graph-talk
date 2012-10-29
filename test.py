from ut import *

import unittest

# Simple process logger
class Logger(Abstract):
    filter = None
    logging = True

    def parse(self, *message, **kwmessage):
        if not self.logging:
            return None

        if Logger.filter and not Logger.filter in message:
            return False

        print "%s: at: %s, reply: %s, message: %s, kwmessage: %s" % (message[0], kwmessage["from"].current,
                                                                     kwmessage["from"].reply, kwmessage["message"],
                                                                     kwmessage["kwmessage"])

        return True

logger = Logger()


def showstopper(notion, *message, **kwmessage):
    return notion.name

def errorer(notion, *message, **kwmessage):
    return {"error": "i_m_bad"}

def texter(notion, *message, **kwmessage):
    return {"text": "new_text"}

_acc = 0
def acc(notion, *message, **kwmessage):
    global _acc
    _acc += 1
    return _acc

def accF(notion, *message, **kwmessage):
    global _acc
    _acc += 1
    return False

'''
def add_to_result(notion, message, **context):
    if not "result" in kwmessage:
        kwmessage["result"] = ""

    kwmessage["result"] += notion.name

def if_loop(loop, context):
    if not loop in context:
        context[loop] = 5
        return True

    i = context[loop] - 1

    if i > 0:
        context[loop] = i
        return True

    return False

'''
def is_a(condition, *message, **kwmessage):
    if message[0].startswith("a"):
        return True, 1
    else:
        return False, 0


# TODO: check test coverage
class BasicTests(unittest.TestCase):

    def test_objects(self):
        n1 = Notion("n1")
        n2 = Notion("n2")

        r1 = Relation(n1, n2)

        # Generic relation test
        self.assertEqual(r1.subject, n1)
        self.assertEqual(r1.object, n2)

        cn = ComplexNotion("cn")
        r1.subject = cn

        # If relation is only one ComplexNotion should return it
        self.assertEqual(cn.parse(), r1)

        r2 = Relation(cn, n1)

        # If there is more than 1 relation ComplexNotion should return the list
        self.assertListEqual(cn.parse(), [r1, r2])


    def test_next(self):
        #logger.logging = True

        # Simple next test: root -> a
        root = ComplexNotion("root")
        a = FunctionNotion("a", showstopper)

        NextRelation(root, a)

        process = Process()
        process.call(logger)

        r = process.parse("test_next", start=root)

        self.assertEqual(process.reply, "a")
        self.assertEqual(process.current, a)
        self.assertEqual(r["result"], "unknown")

        a.function = None
        r = process.parse("test_next_2", start=root)

        self.assertEqual(process.reply, None)
        self.assertEqual(process.current, a)
        self.assertEqual(r["result"], "ok")


    def test_stack(self):
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

        process = StackedProcess()
        process.call(logger)

        _acc = 0
        r = process.parse("test_stack", start=root)

        self.assertEqual(process.reply, "c")
        self.assertEqual(process.current, c)
        self.assertEqual(r["result"], "unknown")
        self.assertEqual(_acc, 1)

        r = process.parse("test_stack 2", start=None) # Make process pop from stack

        self.assertEqual(process.reply, "d")
        self.assertEqual(process.current, d)
        self.assertEqual(r["result"], "unknown")

        r = process.parse("test_stack_3", start=None) # Trying empty stack

        self.assertEqual(process.reply, None)
        self.assertEqual(process.current, None)
        self.assertEqual(r["result"], "ok")


    def test_stop(self):
        #logger.logging = True
        root = ComplexNotion("root")
        a = ComplexNotion("a")

        NextRelation(root, a)

        b = FunctionNotion("error", showstopper) # First stop by error
        c = FunctionNotion("continue", showstopper) # Keep going
        d = FunctionNotion("stop", showstopper) # Stop here
        e = FunctionNotion("errorer", errorer) # And finally here
        f = FunctionNotion("end", showstopper) # And finally here

        NextRelation(a, b)
        NextRelation(a, c)
        NextRelation(a, d)
        NextRelation(a, e)
        NextRelation(a, f)

        process = ControlledProcess()
        process.call(logger)

        r = process.parse("test_stop", start=root)

        self.assertEqual(process.reply, "stop")
        self.assertEqual(process.current, d)
        self.assertEqual(r["result"], "error")
        self.assertIn(b, r["errors"])

        # Now let's try to resume
        r = process.parse("test_stop_2", "continue")

        self.assertEqual(process.reply, "end")
        self.assertEqual(process.current, f)
        self.assertEqual(r["result"], "error")
        self.assertIn(e, r["errors"])
        self.assertEqual("i_m_bad", r["errors"][e])

        # And now go None
        r = process.parse("test_stop_3", start=None)

        self.assertEqual(process.reply, None)
        self.assertEqual(process.current, None)
        self.assertEqual(r["result"], "ok")


    def test_condition(self):
        #logger.logging = True
        # Simple positive condition test root -a-> a for "a"
        root = ComplexNotion("root")

        c = ConditionalRelation(root, None, "a")

        process = TextParsingProcess()
        process.call(logger)

        r = process.parse("a", start = root)

        self.assertEqual(r["length"], 1)
        self.assertEqual(r["result"], "ok")

        # Simple negative condition test root -a-> a for "n"
        r = process.parse("n", start = root)

        self.assertEqual(r["result"], "error")
        self.assertIn(c, r["errors"])
        self.assertEqual(r["errors"][c], "error")

        # Simple positive condition test root -function-> a for "a"
        c.checker = is_a

        r = process.parse("a", start = root)

        self.assertEqual(r["length"], 1)
        self.assertEqual(r["result"], "ok")

        c.object = FunctionNotion("text", texter)

        r = process.parse("a", start = root)
        self.assertEqual(r["result"], "ok")
        self.assertIn("new_text", r["message"])
        self.assertEqual(r["length"], 0)

    '''
    def test_complex(self):
        logger.logging = True
        # Complex notion test: root -> ab -> (a , b) with empty message
        root = ComplexNotion("root")
        ab = ComplexNotion("ab")
        NextRelation(root, ab)

        a = FunctionNotion("a", add_to_result)
        r1 = NextRelation(ab, a)

        b = FunctionNotion("b", add_to_result)
        r2 = NextRelation(ab, b)

        process = TextParsingProcess()
        process.call(logger)

        r = process.parse("", start=root)

        self.assertEqual(r["result"], "ab")
        self.assertTrue(r["result"])
        self.assertEqual(r["length"], 0)

        # Complex notion negative test: root -> ab -> ( (-a-> a) , (-b-> b) ) for "a"

        r1.subject = None
        r2.subject = None

        ConditionalRelation(ab, a, "a")
        r2 = ConditionalRelation(ab, b, "b")

        context = {"start": root}
        r = process.parse("a", context)

        self.assertEqual(context["result"], "a")
        self.assertFalse(r["result"])
        self.assertEqual(r["length"], 1)
        self.assertListEqual(context["error"], [r2])

        # Nested complex notion test: root -> ab -> ( (-a-> a) , (-b-> b)  -> c -> (d, e), f) for "abf"
        c = ComplexNotion("c")
        NextRelation(ab, c)

        d = FunctionNotion("d", add_to_result)
        NextRelation(c, d)

        e = FunctionNotion("e", add_to_result)
        NextRelation(c, e)

        f = FunctionNotion("f", add_to_result)
        ConditionalRelation(ab, f, "f")

        context = {"start": root}
        r = process.parse("abf", context)

        self.assertEqual(context["result"], "abdef")
        self.assertTrue(r["result"])
        self.assertEqual(r["length"], 3)
        self.assertTrue(not "error" in context)

    def test_loop(self):
        # Simple loop test: root -5!-> a's -a-> a for "aaaaa"
        root = ComplexNotion("root")
        aa = ComplexNotion("a's")
        l = LoopRelation(root, aa, 5)

        a = FunctionNotion("a", add_to_result)
        c = ConditionalRelation(aa, a, "a")

        process = ParserProcess()
        process.call(logger)

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
        process.call(logger)

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


