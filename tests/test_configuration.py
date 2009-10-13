import re
import os
import sys
import threading
import urllib

import aspen
from aspen import mode
from aspen.configuration import ConfFile, Configuration as Config
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


# defaults
# ========

def test_default_defaults():
    mk()
    expected = ('index.html', 'index.htm')
    actual = Config(['--root=fsfix']).defaults
    assert actual == expected, actual

def test_defaults_space_separated():
    mk('etc', ('etc/aspen.conf', '[main]\ndefaults=foo bar'))
    expected = ('foo', 'bar')
    actual = Config(['--root=fsfix']).defaults
    assert actual == expected, actual

def test_defaults_comma_separated():
    mk('etc', ('etc/aspen.conf', '[main]\ndefaults=foo,bar'))
    expected = ('foo', 'bar')
    actual = Config(['--root=fsfix']).defaults
    assert actual == expected, actual

def test_defaults_comma_and_space_separated():
    mk('etc', ('etc/aspen.conf', '[main]\ndefaults=foo, bar, baz'))
    expected = ('foo', 'bar', 'baz')
    actual = Config(['--root=fsfix']).defaults
    assert actual == expected, actual


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
