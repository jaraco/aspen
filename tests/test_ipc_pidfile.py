import os
import stat
import sys

from aspen.ipc.pidfile import *
from tests import assert_issubclass, assert_logs, assert_raises, set_log_filter
from tests.fsfix import attach_teardown, mk
from nose import SkipTest


if 'win32' == sys.platform:
    raise SkipTest # PIDFile object is created on windows but never written


class TestPIDFile(PIDFile):
    def __init__(self):
        PIDFile.__init__(self, os.path.join('fsfix', 'pidfile'))


def test_basic():
    pid = os.getpid()
    mk(('pidfile', str(pid)))
    pidfile = TestPIDFile()
    actual = pidfile.getpid()
    expected  = pid
    assert actual == expected, actual


# Basic Management
# ================

def test_write():
    mk()
    pidfile = TestPIDFile()
    pidfile.write()
    actual = os.path.isfile(pidfile.path)
    expected = True
    assert actual == expected, actual

def test_write_writes_it():
    mk()
    pidfile = TestPIDFile()
    pidfile.write()
    actual = int(open(pidfile.path).read())
    expected = os.getpid()
    assert actual == expected, actual

def test_write_sets_perms():
    mk()
    pidfile = TestPIDFile()
    pidfile.write()
    actual = os.stat(pidfile.path)[stat.ST_MODE] & 0777
    expected = pidfile.mode 
    assert actual == expected, actual

def test_write_creates_directory():
    mk()
    nested = os.path.join('fsfix', 'var', 'pidfile')
    pidfile = TestPIDFile()
    pidfile.path = nested
    pidfile.write()
    actual = os.path.isfile(nested)
    expected = True
    assert actual == expected, actual

def test_write_sets_directory_perms():
    mk()
    nested = os.path.join('fsfix', 'var', 'pidfile')
    pidfile = TestPIDFile()
    pidfile.path = nested
    pidfile.write()
    actual = os.stat(os.path.dirname(pidfile.path))[stat.ST_MODE] & 0777
    expected = pidfile.dirmode 
    assert actual == expected, actual


def test_setperms(): # yes, this is a cheap dot
    pidfile = TestPIDFile()
    mk(('pidfile', 'foo'))
    pidfile.setperms()
    actual = os.stat(pidfile.path)[stat.ST_MODE] & 0777
    expected = pidfile.mode
    assert actual == expected, actual


def test_remove():
    mk()
    pidfile = TestPIDFile()
    pidfile.write()
    pidfile.remove()
    actual = os.path.isfile(pidfile.path)
    expected = False
    assert actual == expected, actual


# Get PID
# =======

def test_getpid(): # another cheap dot :^)
    pid = os.getpid()
    mk(('pidfile', str(pid)))
    pidfile = TestPIDFile()
    actual = pidfile.getpid()
    expected  = pid
    assert actual == expected, actual

def test_getpid_path_not_set():
    pidfile = TestPIDFile()
    pidfile.path = None
    assert_raises(PIDFilePathNotSet, pidfile.getpid)

def test_getpid_missing():
    for exc in (PIDFileMissing, StaleState):
        pidfile = TestPIDFile()
        assert_raises(exc, pidfile.getpid)

def test_getpid_restricted():
    mk(('pidfile', str(os.getpid())))
    pidfile = TestPIDFile()
    os.chmod(pidfile.path, 0000)
    assert_raises(PIDFileRestricted, pidfile.getpid)
    # I tried yielding assert_raises, exc, pidfile.getpid, but then 
    # teardown isn't called and we get OSError because of the already-
    # existing fsfix directory. Patch was rejected:
    # http://code.google.com/p/python-nose/issues/detail?id=202
    # So now I test have another test below for subclasses.


def test_getpid_empty():
    mk(('pidfile', ''))
    pidfile = TestPIDFile()
    assert_raises(PIDFileEmpty, pidfile.getpid)

def test_getpid_mangled():
    mk(('pidfile', 'foo'))
    pidfile = TestPIDFile()
    assert_raises(PIDFileMangled, pidfile.getpid)

def test_getpid_mangled_newline():
    mk(('pidfile', str(os.getpid)+'\n'))
    pidfile = TestPIDFile()
    assert_raises(PIDFileMangled, pidfile.getpid)


def test_getpid_dead():
    mk(('pidfile', '99999')) # yes, this could fail
    pidfile = TestPIDFile()
    assert_raises(PIDDead, pidfile.getpid)

def test_getpid_not_aspen():
    pid = os.getpid()
    mk(('pidfile', str(pid)))
    pidfile = TestPIDFile()
    pidfile.ASPEN = 'flahflah'
    assert_raises(PIDNotAspen, pidfile.getpid)


def test_error_subclasses():
    yield assert_issubclass, PIDFileRestricted, ErrorState
    yield assert_issubclass, PIDFileEmpty, ErrorState
    yield assert_issubclass, PIDFileMangled, ErrorState
    yield assert_issubclass, PIDDead, StaleState
    yield assert_issubclass, PIDNotAspen, StaleState



attach_teardown(globals())
