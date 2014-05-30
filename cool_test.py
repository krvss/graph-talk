from cool_lexer import *
from debug import *
from line_profiler import LineProfiler
from pycparser import CppHeaderParser

import glob

import cProfile, pstats, StringIO, hotshot, datetime, hotshot.stats
c_pr = cProfile.Profile()
h_pr = hotshot.Profile("ut.prof")
l_pr = LineProfiler()

mode = None


# Total test of grading
def total_test():
    for f in glob.glob("grading/*.cool"):
        print "Lexing " + f,

        t1 = datetime.datetime.now()

        ou1 = lex_file(f)
        t2 = datetime.datetime.now()

        ou2 = get_content(f + ".out")
        i = ou2.index("\n")
        ou2 = ou2[i + 1:]

        if not ou1 == ou2:
            print "!!! Different !!!"
        else:
            print " ok, " + str(t2-t1)


def generate_tokens():
    no_errors = dict(TOKEN_DICT)
    no_errors.pop(ERROR_TOKEN)
    line = " ".join(no_errors.values())
    line += " "

    return line * 10


def generate_ints():
    line = '100000 '

    return line * 10 * 10


def start_profiler(m):
    global mode
    mode = m

    if mode == 'c':
        c_pr.enable()
    elif mode == 'h':
        pass#h_pr.start()
    elif mode == 'l':
        l_pr.enable_by_count()


def end_profiler():
    if mode == 'c':
        c_pr.disable()
        s = StringIO.StringIO()
        sortby = 'time'
        ps = pstats.Stats(c_pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print s.getvalue()

    elif mode == 'h':
        #h_pr.stop()
        h_pr.close()
        stats = hotshot.stats.load("ut.prof")
        stats.strip_dirs()
        stats.sort_stats('time', 'calls')
        stats.print_stats(20)

    elif mode == 'l':
        l_pr.disable()
        l_pr.print_stats()


def get_test_graph():
    #from ut import *
    builder = GraphBuilder('Test')
    c = builder.next_rel().select('s').current
    builder.parse_rel('a').act('A', True)
    builder[c].parse_rel('b').act('B', True)

    p = ParsingProcess()
    set_logging(True)
    #ProcessDebugger(p).show_log()
    return p, builder.graph

#p, g = get_test_graph()

#start_profiler('c')

#l_pr.add_function(Handler.handle)
l_pr.add_function(Condition.check_string)
l_pr.add_function(Condition.check_function)
l_pr.add_function(Condition.check_list)


#print lex(generate_tokens(), '')
#print lex(generate_ints(), '')
#h_pr.runcall(lex_file, "grading/arith.cool")

t1 = time.time()

#print lex(r'"\"this"', "")

#print lex_file("grading/backslash.cool")
lex_file("grading/arith.cool")
#total_test()

#print p(g, text='b')


'''
try:
    cppHeader = CppHeaderParser.CppHeader("/Users/skravets/Desktop/ui.h")
except CppHeaderParser.CppParseError as e:
    print(e)
    sys.exit(1)

print cppHeader.classes
'''

print time.time() - t1

# TODO: profiler

end_profiler()

'''
arith.cool - 29
life.cool - 29
pathologicalstrings.cool - 20
twice_512_nested_comments.cl.cool - 7
longstring_escapedbackslashes.cool - 11
book_list.cl.cool - 7
sort_list.cl.cool - 8
atoi.cool - 7
io.cool - 6
new_complex.cool - 2
hairyscary.cool - 2
'''