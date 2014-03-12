from cool_lexer import lex_file, get_content

import glob

for f in glob.glob("grading/*.cool"):
    print "Lexing " + f,
    ou1 = lex_file(f)
    ou2 = get_content(f + ".out")
    i = ou2.index("\n")
    ou2 = ou2[i + 1:]

    if not ou1 == ou2:
        print "!!! Different !!!"
    else:
        print " ok"

# TODO: profiler