"""
.. module:: tests.special_test
   :platform: Unix, Windows
   :synopsis: Graph-talk profiling and stress tests

.. moduleauthor:: Stas Kravets (krvss) <stas.kravets@gmail.com>

"""

import datetime
import glob

from examples.cool_lexer import *
from gt.debug import *


class Timer(object):
    """
    Helper class to measure time deltas
    """
    def __init__(self):
        self.start()

    def start(self):
        self.t1 = datetime.datetime.now()
        self.t2 = None

    def stop(self):
        self.t2 = datetime.datetime.now()

    def delta(self):
        if not self.t2:
            self.stop()

        return self.t2 - self.t1


class SpecialTest(object):
    """
    Helper class for stress test
    """
    def __init__(self, **kwargs):
        self.info = kwargs

    def setup(self):
        pass

    def run(self):
        pass


class SpecialTestRunner(SpecialTest):
    """
    Test runner, calls the specified test under specified profiler
    Mode = None - no profiler, "c" - cProfile, "l" - LineProfiler, "h" - hotshot
    """
    def __init__(self, test, mode=None):
        super(SpecialTestRunner, self).__init__()

        self.mode = mode
        self.test = test
        self.profiler = None

    def setup(self):
        if self.mode == 'c':
            import cProfile
            self.profiler = cProfile.Profile()

        elif self.mode == 'l':
            from line_profiler import LineProfiler
            self.profiler = LineProfiler()

        elif self.mode == 'h':
            import hotshot
            self.info['name'] = 'special.prof'
            self.profiler = hotshot.Profile(self.info['name'])

        self.test.setup()

    def run(self):
        if self.mode == 'c':
            self.profiler.enable()
        elif self.mode == 'l':
            self.profiler.enable_by_count()

            self.profiler.add_function(Handler.handle)
            self.profiler.add_function(Condition.check_string_match)
            self.profiler.add_function(Condition.check_function)
            self.profiler.add_function(Condition.check_list)

        t = Timer()

        # Run itself
        if self.mode == 'h':
            self.profiler.runcall(self.test.run)
        else:
            self.test.run()

        print('Test time: %s' % t.delta())

        if self.mode == 'c':
            import pstats
            import StringIO

            self.profiler.disable()
            sio = StringIO.StringIO()

            ps = pstats.Stats(self.profiler, stream=sio).sort_stats('time')
            ps.print_stats()

            print(sio.getvalue())

        elif self.mode == 'h':
            import hotshot.stats

            print('Processing results...')

            self.profiler.close()
            name = self.info['name']
            stats = hotshot.stats.load(name)
            stats.strip_dirs()
            stats.sort_stats('time', 'calls')
            stats.print_stats(50)

            print('Run "hotshot2calltree -o %s.out %s" to generate the cachegrind file' % (name, name))

        elif self.mode == 'l':
            self.profiler.disable()
            self.profiler.print_stats()


class DetailsTest(SpecialTest):
    """
    Checking the processing details
    """
    def setup(self):
        builder = GraphBuilder('Test')
        c = builder.next_rel().select('s').current
        builder.parse_rel('a').act('A', True)
        builder[c].parse_rel('b').act('B', True)

        p = ParsingProcess()
        ProcessDebugger(p).show_log()

        self.info['process'] = p
        self.info['graph'] = builder.graph

    def run(self):
        self.info['process'](self.info['graph'], text='b')


class CoolGradingTest(SpecialTest):
    """
    COOL grading tests, uses Coursera Compilers course files to check the COOL lexer
    """
    def run(self):
        for f in glob.glob('grading/*.cool'):
            selection = self.info.get('selection')

            if selection and not selection in f:
                continue

            print('Lexing ' + f,)

            t = Timer()

            out1 = lex_file(f)
            t.stop()

            out2 = get_content(f + '.out')
            i = out2.index('\n')
            out2 = out2[i + 1:]

            if not out1 == out2:
                print('!!! Different !!!')
            else:
                print(' ok, ' + str(t.delta()))


# Special test itself, for nerds only B-\
runner = SpecialTestRunner(CoolGradingTest(selection='arith'))
runner.setup()
runner.run()
