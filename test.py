from ut import *

# Simple process logger
class Logger(Abstract):
    filter = None
    logging = True

    def parse(self, message, context = None):
        if not Logger.logging:
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


def test_next():
    root = ComplexNotion("root")
    a = FunctionNotion("a", add_to_result)

    NextRelation(root, a)

    process = ParserProcess()
    process.call(logger)

    context = {"start": root}
    r = process.parse("", context)

    return context["result"] == "a" and r.result and r.length == 0

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


def test_condition():
    root = ComplexNotion("root")
    a = FunctionNotion("a", add_to_result)

    c = ConditionalRelation(root, a, "a")

    process = ParserProcess()
    process.call(logger)

    context = {"start": root}
    r = process.parse("a", context)

    if context["result"] != "a" and r.result and r.length == 1:
        return False

    context = {"start": root}
    r = process.parse("n", context)

    if context["error"] != c and not r.result and r.length == 0:
        return False

    c.checker = is_a

    context = {"start": root}
    r = process.parse("a", context)

    return context["result"] == "a" and r.result and r.length == 1


def test_complex():
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

    if context["result"] != "ab" and not r.result and r.length:
        return False

    r1.subject = None
    r2.subject = None

    ConditionalRelation(ab, a, "a")
    r2 = ConditionalRelation(ab, b, "b")

    context = {"start": root}
    r = process.parse("a", context)

    return context["result"] == "a" and r.length == 1 and context["error"] == r2

def test_loop():
    root = ComplexNotion("root")
    aa = ComplexNotion("a's")
    l = LoopRelation(root, aa, 5)

    a = FunctionNotion("a", add_to_result)
    c = ConditionalRelation(aa, a, "a")

    process = ParserProcess()
    process.call(logger)

    context = {"start": root}
    r = process.parse("aaaaa", context)

    if not context["result"] == "aaaaa" and not r.result and r.length != 5: #TODO: check state space
        return False

    context = {"start": root}
    r = process.parse("aaaa", context)

    if context["error"] != c and r.result and r.length != 4:
        return False

    l.n = None

    context = {"start": root}
    r = process.parse("aaaa", context)

    if context["result"] != "aaaa" and not r.result and not r.length == 4:
        return False

    l.n = if_loop

    context = {"start": root}
    r = process.parse("aaaaa", context)

    return context["result"] == "aaaaa" and r.result and r.length == 5 and not "error" in context


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
    print "** Next test %s" % test_next()
    print "** Condition test %s" % test_condition()
    print "** Complex test %s" % test_complex()
    print "** Loop test %s" % test_loop()
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


