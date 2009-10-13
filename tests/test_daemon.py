"""Top level tests; see also test_tutorial and test_daemon.
"""
import commands
import os
import socket
import sys
import time
from subprocess import Popen, PIPE, STDOUT

import aspen
from aspen.configuration import Configuration
from aspen.server import Server
from tests import LOG, hit_with_timeout
from tests import assert_, assert_actual, assert_logs, assert_raises
from tests.fsfix import mk, attach_teardown
from nose import SkipTest


if aspen.WINDOWS:
    raise SkipTest


# Fixture
# =======

ARGV = ['aspen']
PIDPATH = os.path.join('fsfix', 'var', 'aspen.pid')
def getpid(): # for our use of this in these test, missing PIDPATH is a bug
    return open(PIDPATH).read()

def daemon_cmd(cmd):
    fp = open(LOG, 'a')
    argv = ['aspen', '--root=fsfix', '--address=:53700', cmd]
    proc = Popen(argv, stdout=fp, stderr=STDOUT)
    proc.wait()

def with_daemon(func):
    daemon_cmd('start')
    try:
        func()
    finally:
        daemon_cmd('stop')


# Tests
# =====

def test_daemon():
    mk() 
    daemon_cmd('start')
    daemon_cmd('stop')
    assert_logs(None)

def test_daemon_restart():
    mk() 
    daemon_cmd('start')
    daemon_cmd('restart')
    daemon_cmd('stop')
    assert_logs(None)

def test_daemon_status():
    mk() 
    daemon_cmd('start')
    pid = getpid()
    daemon_cmd('status')
    daemon_cmd('stop')
    assert_logs('daemon running with pid %s' % pid)

def test_daemon_start_twice():
    mk() 
    daemon_cmd('start')
    pid = getpid()
    daemon_cmd('start')
    daemon_cmd('stop')
    assert_logs('daemon already running with pid %s' % pid)

def test_daemon_stop_not_running():
    mk() 
    daemon_cmd('stop')
    assert_logs('pidfile ./fsfix/var/aspen.pid is missing (is aspen running?)')

def test_daemon_restart_not_running():
    mk() 
    daemon_cmd('restart')
    assert_logs('pidfile ./fsfix/var/aspen.pid is missing (is aspen running?)')

def test_daemon_status_not_running():
    mk() 
    daemon_cmd('status')
    assert_logs('daemon not running (no pidfile)')
    
def test_daemon_creates_var_dir():
    mk() 
    daemon_cmd('start')
    daemon_cmd('stop')
    assert os.path.isdir(os.path.join('fsfix', 'var'))


def test_aspen_hit_it():
    mk('www', ('www/index.html', 'Greetings, program!'))
    def test():
        expected = 'Greetings, program!'
        actual = hit_with_timeout('http://localhost:53700/')
        assert actual == expected, actual
    with_daemon(test)


def test_conflicting_address():
    def test():
        configuration = Configuration(['--address=:53700'])
        server = Server(configuration)
        yield assert_raises, socket.error, server.start
    with_daemon(test)


def test_privilege_dropping():
    # We make assumptions about uid 1 and about ps. These assumptions have been
    # validated on FreeBSD 6 and Ubuntu 8.
    if aspen.WINDOWS or (os.getuid() != 0):
        raise SkipTest("can only test privilege dropping as root on UNIX")
    mk('etc', ( 'etc/aspen.conf', '[main]\nuser=1'))
    def test():
        pid = open('fsfix/var/aspen.pid').read()
        uid = commands.getoutput('ps -o uid %s' % pid).splitlines()[1].strip()
        expected = '1'
        actual = uid
        assert actual == expected, actual
    with_daemon(test)


attach_teardown(globals())
