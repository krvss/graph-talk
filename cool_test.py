from cool_lexer import *
from brainfuck import test_interpreter
from line_profiler import LineProfiler

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

start_profiler('c')

#l_pr.add_function(Handler.handle)
l_pr.add_function(Condition.check_string)
l_pr.add_function(Condition.check_function)
l_pr.add_function(Condition.check_list)


#print lex(generate_ints(), '')
#h_pr.runcall(lex_file, "grading/arith.cool")

#set_logging(True)

#total_test()
#t1 = time.time()
lex_file("grading/arith.cool")
#print time.time() - t1

'''
from ut import *
builder = GraphBuilder('Test')
builder.next_rel('a').act('A', True)

p = ParsingProcess()
start_profiler('c')
set_logging(True)
print p(builder.graph.root, TEXT='a')
'''

'''
test_interpreter()
'''
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