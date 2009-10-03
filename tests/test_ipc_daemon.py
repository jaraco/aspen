import StringIO
import os
import signal
import socket
import stat
import subprocess
import sys
import time
import urllib

import aspen
from tests import NAMED_PIPE, TestTalker, hit_with_timeout
from tests import assert_logs 
from tests.fsfix import mk, attach_teardown
from nose import SkipTest


if sys.platform == 'win32':
    raise SkipTest


ARGV = ['python', os.path.join('fsfix', 'aspen-test.py')]


PIPE_TEST_PROGRAM = """\
from tests import TestListener

listener = TestListener()
listener.listen_actively()
"""

def test_named_pipe():
    mk(('aspen-test.py', PIPE_TEST_PROGRAM))
    proc = subprocess.Popen(ARGV)
    talk = TestTalker() # blocks until FIFO is created by TestListener in proc
    talk('foo')
    talk('q')
    proc.wait()
    assert_logs("foo")


DAEMON = """\
import aspen
from aspen.ipc.daemon import Daemon
from tests import TestListener, configure_logging, log 


configuration = aspen.Configuration(['--root=fsfix'])
daemon = Daemon(configuration)
log.info("daemonizing, bye ...")

daemon.start() # turns us into a daemon 

configure_logging() # all fd's were closed
log.info('... daemonized, blam')

listener = TestListener()
listener.listen_actively()

"""


def test_basic():
    mk(('aspen-test.py', DAEMON))

    proc = subprocess.Popen(ARGV)

    talk = TestTalker()
    talk("Greetings, program!")
    talk('q')

    assert_logs( "daemonizing, bye ..."
               , "... daemonized, blam"
               , "Greetings, program!"
                )


attach_teardown(globals())
