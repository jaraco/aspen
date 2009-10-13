import re
import os
import sys
import threading
import urllib

import aspen
from aspen import mode
from aspen.configuration import Configuration as Config
from aspen.configuration import ConfFile, ConfigurationError
from aspen.handler import SimpleHandler
from nose import SkipTest
from tests import assert_raises
from tests.fsfix import mk, attach_teardown


# ConfFile
# ========

def test_ConfFile():
    mk(('foo.conf', '[blah]\nfoo = bar\nbaz=True\n[bar]\nbuz=blam\nlaaa=4'))
    conf = ConfFile(os.path.join('fsfix', 'foo.conf'))
    expected = [ ('bar', [ ('buz', 'blam')
                         , ('laaa', '4')])
               , ('blah', [ ('baz', 'True')
                          , ('foo', 'bar')])]
    actual = [(k,[t for t in v.iteritems()]) for (k,v) in conf.iteritems()]
    for foo in actual:
        foo[1].sort()
    actual.sort()
    assert actual == expected, actual


# Configuration
# =============

def test_basic():
    mk('etc', ('etc/aspen.conf', '[main]\n\naddress = :53700'))
    expected = ('0.0.0.0', 53700)
    actual = Config(['--root=fsfix']).address
    assert actual == expected, actual

def test_no_aspen_conf():
    mk()
    expected = ('0.0.0.0', 5370)
    actual = Config(['--root=fsfix']).address
    assert actual == expected, actual

def test_no_main_section():
    mk('etc', ('etc/aspen.conf', '[custom]\nfoo = bar'))
    expected = 'bar'
    actual = Config(['--root=fsfix']).conf.custom['foo']
    assert actual == expected, actual


# user 
# ====

def maybe_skip():
    if aspen.WINDOWS:
        raise SkipTest("no user switching on Windows")
    if os.getuid() != 0:
        raise SkipTest("run tests as root to test user switching")

def test_user_default():
    expected = None
    actual = Config([]).user
    assert actual is expected, actual

def test_user_name():
    maybe_skip()
    expected = 0
    actual = Config(['--user=root']).user
    assert actual == expected, actual

def test_user_uid():
    maybe_skip()
    expected = 0
    actual = Config(['--user=0']).user
    assert actual == expected, actual

def test_user_name_conf_file():
    maybe_skip()
    mk('etc', ('etc/aspen.conf', '[main]\nuser=root'))
    expected = 0
    actual = Config(['--root=fsfix']).user
    assert actual == expected, actual

def test_user_uid_conf_file():
    maybe_skip()
    mk('etc', ('etc/aspen.conf', '[main]\nuser=0'))
    expected = 0
    actual = Config(['--root=fsfix']).user
    assert actual == expected, actual

def test_user_cli_trumps_conf_file():
    maybe_skip()
    mk('etc', ('etc/aspen.conf', '[main]\nuser=blahblah'))
    expected = 0
    actual = Config(['--root=fsfix', '--user=root']).user
    assert actual == expected, actual


# mode
# ====

def test_mode_default():
    mk()
    if 'PYTHONMODE' in os.environ:
        del os.environ['PYTHONMODE']
    Config(['--root=fsfix'])
    expected = 'development'
    actual = mode.get()
    assert actual == expected, actual

def test_mode_set_in_conf_file():
    mk('etc', ('etc/aspen.conf', '[main]\nmode=production'))
    if 'PYTHONMODE' in os.environ:
        del os.environ['PYTHONMODE']
    Config(['--root=fsfix'])
    expected = 'production'
    actual = mode.get()
    assert actual == expected, actual


# python_path
# ===========

def test_python_path():
    __path__ = sys.path[:]
    try:
        path = os.pathsep.join(['foo', 'bar'])
        mk('etc', ('etc/aspen.conf', '[main]\npython_path=%s' % path))
        Config(['--root=fsfix'])
        expected = ['foo', 'bar']
        actual = sys.path[-2:]
        assert actual == expected, actual
    finally:
        sys.path = __path__


# Handler
# =======
# These depend on python_path working.

def test_Handler():
    mk( 'etc'
      , ('etc/aspen.conf',
"""\
[main]
handler=good_handler:Handler
python_path=fsfix
""")
      , ('good_handler.py', # name this something different than below ...
"""\
from tornado.web import RequestHandler
class Handler(RequestHandler):
    foo = 'bar'
""")
       )
    try:
        expected = 'bar'
        actual = Config(['--root=fsfix']).Handler.foo
        assert actual == expected, actual
    finally:
        sys.path.remove('fsfix')


def test_Handler_default():
    expected = SimpleHandler
    actual = Config([]).Handler
    assert actual is expected, actual


def test_Handler_not_RequestHandler():
    mk( 'etc'
      , ('etc/aspen.conf',
"""\
[main]
handler=bad_handler:Handler
python_path=fsfix
""")
      , ('bad_handler.py', # ... to avoid spurious fails here
"""\
from tornado.web import RequestHandler
class Handler:
    foo = 'bar'
""")
       )
    try:
        assert_raises(ConfigurationError, Config, ['--root=fsfix'])
    finally:
        sys.path.remove('fsfix')


def test_Handler_ImportError_caught():
    mk('etc', ('etc/aspen.conf', "[main]\nhandler=missing_module:Handler"))
    assert_raises(ConfigurationError, Config, ['--root=fsfix'])


def test_Handler_AttributeError_caught():
    mk( 'etc'
      , ('etc/aspen.conf',
"""\
[main]
handler=test_handler:Handler
python_path=fsfix
""")
      , ('test_handler.py', "pass")
       )
    try:
        assert_raises(ConfigurationError, Config, ['--root=fsfix'])
    finally:
        sys.path.remove('fsfix')


# pidfile 
# =======

def test_pidfile_var():
    mk('var')
    configuration = Config(['--root', 'fsfix'])
    actual = configuration.pidfile.path
    expected = os.path.realpath(os.path.join('fsfix', 'var', 'aspen.pid'))
    assert actual == expected, actual


# daemon
# ======

def test_daemon_only_when_wanted():
    mk()
    configuration = Config(['--root', 'fsfix'])
    expected = None
    actual = configuration.daemon
    assert actual is expected, actual


# Test layering: CLI, conf file, environment.
# ===========================================

def test_layering_CLI_trumps_conffile():
    mk('etc', ('etc/aspen.conf', '[main]\naddress=:9000'))
    expected = ('0.0.0.0', 5370)
    actual = Config(['--root', 'fsfix', '--address', ':5370']).address
    assert actual == expected, actual

def test_layering_CLI_trumps_environment():
    mk()
    expected = 'production'
    actual = Config(['--root', 'fsfix', '--mode', 'production'])._mode
    assert actual == expected, actual

def test_layering_conffile_trumps_environment():
    mk('etc', ('etc/aspen.conf', '[main]\nmode=production'))
    expected = 'production'
    actual = Config(['--root', 'fsfix'])._mode
    assert actual == expected, actual


attach_teardown(globals())
