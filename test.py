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

        return None

logger = Logger()

class Debugger(Abstract):
    def parse(self, *message, **kwmessage):
        if message[0] == "next" and str(kwmessage["from"].current) == '"here"':
            return "debug"


class Skipper(Abstract):
    def parse(self, *message, **kwmessage):
        if message[0] == "next_unknown":
            return "skip"


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

def is_a(condition, *message, **kwmessage):
    if message[0].startswith("a"):
        return True, 1
    else:
        return False, 0

def has_notify(notion, *message, **kwmessage):
    if 'notifications' in kwmessage:
       return kwmessage['notifications']
    else:
        return False


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

        # If there is more than 1 relation ComplexNotion should return the list
        self.assertListEqual(cn.parse(), [r1, r2])


    def test_next(self):
        #logger.logging = True

        # Simple next test: root -> a
        root = ComplexNotion("root")
        a = FunctionNotion("a", showstopper)

        NextRelation(root, a)

        process = Process()
        process.callback(logger)

        r = process.parse("test_next", start=root)

        self.assertEqual(process.reply, "a")
        self.assertEqual(process.current, a)
        self.assertEqual(r["result"], "unknown")

        a.function = None
        r = process.parse("test_next_2", start=root)

        self.assertEqual(process.reply, None)
        self.assertEqual(process.current, None)
        self.assertEqual(r["result"], "ok")


    def test_callback(self):
        global _acc

        # Simple debugger test: stop at "a" notion, skip the result by the command and go further
        root = ComplexNotion("here")
        a = ComplexNotion("a")

        NextRelation(root, a)

        process = Process()
        debugger = Debugger()

        process.callback(debugger)
        r = process.parse("debugging", start=root)

        self.assertEqual(r["result"], "unknown")
        self.assertEqual(process.current, debugger)
        self.assertIn("debugging", process.message)

        r = process.parse("skip")

        self.assertEqual("ok", r["result"])
        self.assertEqual(process.current, None)

        # Simple skip test: always skip unknowns
        b = FunctionNotion("b", showstopper)
        NextRelation(a, b)

        c = FunctionNotion("c", accF)
        NextRelation(a, c)

        skipper = Skipper()
        process.callback(skipper)

        _acc = 0
        r = process.parse("skipper", start=root)

        self.assertEqual(r["result"], "ok")
        self.assertEqual(_acc, 1)
        self.assertEqual(process.current, None)


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
        process.callback(logger)

        _acc = 0
        r = process.parse("test_queue", start=root)

        self.assertEqual(process.reply, "c")
        self.assertEqual(process.current, c)
        self.assertEqual(r["result"], "unknown")
        self.assertEqual(_acc, 1)

        r = process.parse("skip") # Make process pop from stack

        self.assertEqual(process.reply, "d")
        self.assertEqual(process.current, d)
        self.assertEqual(r["result"], "unknown")

        r = process.parse("skip") # Trying empty stack

        self.assertEqual(process.reply, None)
        self.assertEqual(process.current, None)
        self.assertEqual(r["result"], "ok")


    def test_stop(self):
        logger.logging = True
        root = ComplexNotion("root")
        a = ComplexNotion("a")

        NextRelation(root, a)

        b = FunctionNotion("stop", showstopper) # First stop
        c = FunctionNotion("error", showstopper) # Error!
        d = FunctionNotion("errorer", errorer) # Another error!
        e = FunctionNotion("end", showstopper) # And finally here

        NextRelation(a, b)
        NextRelation(a, c)
        NextRelation(a, d)
        NextRelation(a, e)

        process = CarrierProcess()
        process.callback(logger)

        r = process.parse("test_stop", start=root)

        self.assertEqual(r["result"], "stopped")
        self.assertEqual(process.current, b)

        # Now let's try to resume
        r = process.parse("skip")

        self.assertEqual(r["result"], "error")
        self.assertIn(c, r["errors"])
        self.assertIn(d, r["errors"])

        self.assertEqual(process.reply, "end")
        self.assertEqual(process.current, e)

        self.assertEqual("i_m_bad", r["errors"][d])

        # And now go None to check the errors cleared
        r = process.parse("test_stop_2", start=None)

        self.assertEqual(process.reply, None)
        self.assertEqual(process.current, None)
        self.assertEqual(r["result"], "ok")


    def test_condition(self):
        logger.logging = True
        # Simple positive condition test root -a-> a for "a"
        root = ComplexNotion("root")

        d = FunctionNotion("noti", has_notify)

        c = ConditionalRelation(root, d, "a")

        process = TextParsingProcess()
        process.callback(logger)

        r = process.parse("a", start = root)

        self.assertEqual(r["length"], 1)
        self.assertEqual(r["result"], "unknown")
        self.assertEqual(process.current, d)

        # Simple negative condition test root -a-> a for "n"
        r = process.parse("n", start = root)

        self.assertEqual(r["result"], "error")
        self.assertIn(c, r["errors"])
        self.assertEqual(r["errors"][c], "error")
        self.assertEqual(r["length"], 0)

        # Simple positive condition test root -function-> a for "a"
        c.checker = is_a
        c.object = None

        r = process.parse("a", start = root)

        self.assertEqual(r["length"], 1)
        self.assertEqual(r["result"], "ok")

        return

        # TODO: check notifications
        c.object = FunctionNotion("text", texter)

        r = process.parse("a", start = root)

        self.assertEqual(r["result"], "ok")
        self.assertIn("new_text", r["message"])
        self.assertEqual(r["length"], 0)


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
        process.callback(logger)

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
        process.callback(logger)

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
        process.callback(logger)

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
    #suite = unittest.TestLoader().loadTestsFromTestCase(BasicTests)
    suite = unittest.TestLoader().loadTestsFromName('test.BasicTests.test_condition')
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


