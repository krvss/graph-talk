from ut import *

def add_to_result(notion, context):
    if not "result" in context:
        context["result"] = ""

    context["result"] += notion.name


def test_next():
    root = ComplexNotion("root")
    a = FunctionNotion("a", add_to_result)

    NextRelation(root, a)

    process = ParserProcess()
    context = {"start": root}
    r = process.parse("", context)

    return context["result"] == "a" and r.result and r.length == 0


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


def test_loop():
    root = ComplexNotion("root")
    aa = ComplexNotion("a's")
    l = LoopRelation(root, aa, 5)

    a = FunctionNotion("a", add_to_result)
    c = ConditionalRelation(aa, a, "a")

    process = ParserProcess()
    context = {"start": root}
    r = process.parse("aaaaa", context)

    if not context["result"] == "aaaaa" and not r.result and r.length != 5:
        return False

    context = {"start": root}
    r = process.parse("aaaa", context)

    if context["error"] != c and r.result and r.length != 4:
        return False

    l.n = None

    context = {"start": root}
    r = process.parse("aaaa", context)

    return context["result"] == "aaaa" and r.result and r.length == 4


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
    context = {"start": root}
    r = process.parse("aa", context)

    return context["result"] == "aa" and r.result and r.length == 2


# Custom processing function
def custom_func(notion, context):
    print notion
    return True

def test():
    print "Next test %s" % test_next()
    print "Condition test %s" % test_condition()
    print "Loop test %s" % test_loop()
    print "Alternative test %s" % test_alternative()

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


