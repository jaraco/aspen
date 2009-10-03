import os
import StringIO
import sys
from multiprocessing import Process

import aspen
from tests import assert_actual, assert_raises
from tornado.httpclient import HTTPClient


class AspenRunning:

    def __enter__(self):
        #TODO can't use Process here, because it is not designed for tweaking
        # cli args. So we call aspen.main with nosetext -sx args and Conf 
        # breaks.
        self.proc = Process(target=aspen.main)
        self.proc.start()

    def __exit__(self, *exc):
        self.proc.terminate() # unclean!
            #TODO: bring over robust proc testing with proc mgmt (daemon, etc.)
            # would be swell to update that for multiprocessing?
            # nah, leave it with subprocess for usage on < 2.6
        self.proc.join()


def test_greetings_program():
    with AspenRunning():
        client = HTTPClient()
        response = client.fetch('http://localhost:5370/')
        assert response.body == 'Greetings, program!', response.body


def test_config_error():
    sys.stderr = stderr = StringIO.StringIO()
    try:
        argv = ['aspen', 'bad-command']
        exc = assert_raises(SystemExit, aspen.main, argv=argv)
    finally:
        sys.stderr = sys.__stderr__

    expected = 2
    actual = exc.code
    yield assert_actual, expected, actual

    stderr.seek(0)
    expected = ( "aspen [options] [restart,start,status,stop]; --help for more"
               , "Bad command: bad-command"
               , ""
                )
    expected = os.linesep.join(expected)
    actual = stderr.read()
    yield assert_actual, expected, actual



