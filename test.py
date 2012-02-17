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
    process.parse("", context)

    return context["result"] == "a"


# Custom processing function
def custom_func(notion, context):
    print notion
    return True

def test():
    print "Next test %s" % test_next()

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


