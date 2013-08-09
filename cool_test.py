from cool import lex_file, lex, get_content

import glob
import difflib
import sys

#print lex('"sss"')

c = get_content("/Users/skravets/Projects/virtualenvs/ut/ut/grading/wq0607-c4.cool")
c = r'''"\\-"-"-\-"--\""\\"-"\"\\"-\-"\\"""\--"\""\"
"\\""\"--\""\-\""\"--\\"\"\\"--""\"\--""\"
'''
print lex(c)
exit()

for f in glob.glob("grading/*.cool"):
    print "Lexing " + f,
    ou1 = lex_file(f)
    ou2 = get_content(f + ".out")
    i = ou2.index("\n")
    ou2 = ou2[i + 1:]

    if not ou1 == ou2:
        print "Different-----------------:"

        #d = difflib.Differ()
        #diff = list(d.compare(ou1.split('\n'), ou2.split('\n')))
        #sys.stdout.writelines(diff)
        #print ou1
    else:
        print " ok"

    pass