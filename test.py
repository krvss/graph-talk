from ut import *

import unittest

# Simple process logger
class Logger(Abstract):
    filter = None
    logging = True

    def parse(self, message, context = None):
        if not self.logging:
            return None

        if Logger.filter and not Logger.filter in message:
            return False

        print "%s: %s, message:%s" % (message, context["abstract"], context["message"] if "message" in context else "")

        return True

logger = Logger()


def add_to_result(notion, context):
    if not "result" in context:
        context["result"] = ""

    context["result"] += notion.name


def if_loop(loop, context):
    if not loop in context:
        context[loop] = 5
        return True

    i = context[loop] - 1

    if i > 0:
        context[loop] = i
        return True

    return False


def is_a(message):
    if message.startswith("a"):
        return True, 1
    else:
        return False, 0


class BasicTests(unittest.TestCase):

    def test_next(self):
        # Simple next test: root -> a
        root = ComplexNotion("root")
        a = FunctionNotion("a", add_to_result)

        NextRelation(root, a)

        process = ParserProcess()
        process.call(logger)

        context = {"start": root}
        r = process.parse("", context)

        self.assertEqual(context["result"], "a")
        self.assertTrue(r.result)
        self.assertEqual(r.length, 0)


    def test_condition(self):
        # Simple positive condition test root -a-> a for "a"
        root = ComplexNotion("root")
        a = FunctionNotion("a", add_to_result)

        c = ConditionalRelation(root, a, "a")

        process = ParserProcess()
        process.call(logger)

        context = {"start": root}
        r = process.parse("a", context)

        self.assertEqual(context["result"], "a")
        self.assertTrue(r.result)
        self.assertEqual(r.length, 1)

        # Simple negative condition test root -a-> a for "n"
        r = process.parse("n", context)

        self.assertListEqual(context["error"], [c])
        self.assertFalse(r.result)
        self.assertEqual(r.length, 0)

        # Simple positive condition test root -function-> a for "a"
        c.checker = is_a

        context = {"start": root}
        r = process.parse("a", context)

        self.assertEqual(context["result"], "a")
        self.assertTrue(r.result)
        self.assertEqual(r.length, 1)


    def test_complex(self):
        # Complex notion test: root -> ab -> (a -> b) with empty message
        root = ComplexNotion("root")
        ab = ComplexNotion("ab")
        NextRelation(root, ab)

        a = FunctionNotion("a", add_to_result)
        r1 = NextRelation(ab, a)

        b = FunctionNotion("b", add_to_result)
        r2 = NextRelation(ab, b)

        process = ParserProcess()
        process.call(logger)

        context = {"start": root}
        r = process.parse("", context)

        self.assertEqual(context["result"], "ab")
        self.assertTrue(r.result)
        self.assertEqual(r.length, 0)

        # Complex notion negative test: root -> ab -> ( (-a-> a) -> (-b-> b) ) for "a"

        r1.subject = None
        r2.subject = None

        ConditionalRelation(ab, a, "a")
        r2 = ConditionalRelation(ab, b, "b")

        context = {"start": root}
        r = process.parse("a", context)

        self.assertEqual(context["result"], "a")
        self.assertFalse(r.result)
        self.assertEqual(r.length, 1)
        self.assertListEqual(context["error"], [r2])


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
        self.assertTrue(r.result)
        self.assertEqual(r.length, 5)

        # Negative loop test: root -5!-> a's -a-> a for "aaaa"
        context = {"start": root}
        r = process.parse("aaaa", context)

        self.assertEqual(context["result"], "aaaa")
        self.assertFalse(r.result)
        self.assertEqual(r.length, 4)
        self.assertListEqual(context["error"], [c, l])

        # Loop test for arbitrary count root -*!-> a's -a-> a for "aaaa"
        l.n = None

        context = {"start": root}
        r = process.parse("aaaa", context)

        self.assertEqual(context["result"], "aaaa")
        self.assertTrue(r.result)
        self.assertEqual(r.length, 4)

        # Loop test for external function: root -function!-> a's -a-> a for "aaaa"
        l.n = if_loop

        context = {"start": root}
        r = process.parse("aaaaa", context)

        self.assertEqual(context["result"], "aaaaa")
        self.assertTrue(r.result)
        self.assertEqual(r.length, 5)
        self.assertTrue(not "error" in context)

        # Nested loops test: root -2!-> a2 -2!-> a's -a-> a for "aaaa"
        l.n = 2

        aaa = ComplexNotion("a2")
        l.subject = aaa

        l2 = LoopRelation(root, aaa, 2)

        context = {"start": root}
        r = process.parse("aaaaa", context)

        self.assertEqual(context["result"], "aaaa")
        self.assertTrue(r.result)
        self.assertEqual(r.length, 4)
        self.assertTrue(not "error" in context)

        # Nested loops negative test: root -2!-> a2 -2!-> a's -a-> a for "aaab"
        context = {"start": root}
        r = process.parse("aaab", context)

        self.assertEqual(context["result"], "aaa")
        self.assertFalse(r.result)
        self.assertEqual(r.length, 3)
        self.assertListEqual(context["error"], [c, l, l2])


def test_alternative():
    root = ComplexNotion("root")
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

    process = ParserProcess()
    process.call(logger)

    context = {"start": root}
    r = process.parse("aa", context)

    return context["result"] == "aa" and r.result and r.length == 2


# Custom processing function
def custom_func(notion, context):
    print notion
    return True

def test():
    logger.logging = False
    suite = unittest.TestLoader().loadTestsFromTestCase(BasicTests)
    unittest.TextTestRunner(verbosity=2).run(suite)

    #print "** Complex test %s" % test_complex()
    #print "** Loop test %s" % test_loop()
    #print "** Alternative test %s" % test_alternative()

    return


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


