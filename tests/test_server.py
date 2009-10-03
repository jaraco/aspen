import time
import threading
import urllib
from pprint import pformat
from subprocess import Popen, PIPE

import aspen
from aspen.configuration import Configuration
from aspen.ipc import restarter
from aspen.server import Server
from tests.fsfix import mk, attach_teardown
from tests import assert_logs, log, set_log_filter, set_log_format


# Fixture
# =======

def check(url, response, log_filter=''):
    configuration = Configuration(['--root=fsfix'])
    server = Server(configuration)
    t = threading.Thread(target=server.start)
    t.start()
    time.sleep(0.2) # give server time to start up
    try:
        expected = response
        actual = urllib.urlopen(url).read()
        assert actual == expected, actual
    finally:
        server.stop()
        t.join()


# Tests
# =====

def test_basic():
    mk('www', ('www/index.html', 'foo'))
    check("http://localhost:5370/", "foo")

def test_log():
    mk('www', ('www/index.html', 'bar'))
    set_log_filter('aspen')
    check("http://localhost:5370/", "bar")
    assert_logs( "logging is already configured"
               , "starting on ('0.0.0.0', 5370)"
               , "configuring filesystem monitor"
               , "cleaning up server"
               , force_unix_EOL=True
                )

def test_from_aspen_import_config(): #TODO fix this once we have Simplates
    """multi-test for app, conf, address
    """
    mk( 'etc'
      , 'lib/python' 
      , ('etc/aspen.conf', '[main]\naddress=:53700\n[my_settings]\nfoo=bar')
      , ('lib/python/foo.py', """\
import aspen

def wsgi_app(environ, start_response):
    my_setting = aspen.conf.my_settings.get('foo', 'default')
    start_response('200 OK', [])
    return ["My setting is %s" % my_setting]
""")
       )
    check("http://localhost:53700/", "My setting is bar")


def test_thread_clobbering():
    """nasty test to ensure restarter thread gets stopped

    This is actually a restarter problem, but this is the test that found it so
    I'm leaving it in here.

    """
    def test(run_num):
        set_log_format("%(threadName)s  %(message)s")
        def log_threads(i):
            log.debug("%s%s: %s" % (i, run_num, pformat(threading.enumerate()[1:])))
            time.sleep(1)
        mk()
        configuration = Configuration(['--root=fsfix'])
        server = Server(configuration)
        t = threading.Thread(target=server.start)
        t.setDaemon(True)
        t.start()
        log_threads(' 1')
#        time.sleep(0.2) # give server.start time to run; log_threads sleeps
        server.stop()
        log_threads(' 2')
        t.join()
        log_threads(' 3')
    yield test, 'a'
    log.debug("")
    yield test, 'b'


attach_teardown(globals())
