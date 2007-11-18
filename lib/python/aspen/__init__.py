"""Define the main program loop.
"""
import base64
import logging
import os
import pprint
import signal
import socket
import stat
import sys
import threading
import time
import traceback
from os.path import isdir, isfile, join

from aspen import configuration, mode, restarter, website
from aspen.pidfiler import PIDFiler
from wsgiserver import CherryPyWSGIServer as BaseServer


if 'win' in sys.platform:
    WINDOWS = True
    Daemon = None # daemonization not available on Windows; @@: service?
else:
    WINDOWS = False
    from aspen.daemon import Daemon # this actually fails on Windows; needs pwd


__version__ = '~~VERSION~~'
__all__ = ['configuration', 'conf', 'paths', '']


log = logging.getLogger('aspen.main')


# Module-level API
# ================
# No base modules within the aspen package should use this API, only add-on
# apps. That ensures that people can use the base objects more freely.

conf = None # an aspen.configuration.ConfFile instance
paths = None # an aspen.configuration.Paths instance
server = None # an aspen.Server instance
CONFIGURED = False


def find_root():
    """Given a script in <root>/bin/, return <root>
    """
    # This should just use some workingenv environment variable
    # or be otherwise smart
    root = os.getcwd()
    log.debug("returning %s" % root)
    return root


globals_ = globals()
def set_API(server=None):
    global globals_

    _configuration = configuration.Configuration(server.argv)
    if server is None: # we're being called from a helper script
        argv = ['--root', find_root()]
        globals_['server'] = None # no change
    else:
        argv = server.argv
        globals_['server'] = server

    globals_['conf'] = _configuration.conf
    globals_['paths'] = _configuration.paths
    globals_['CONFIGURED'] = True

    log.debug("returning %s" % pprint.pformat(_configuration))
    return _configuration

def unset_API(): # for completeness and tests
    global globals_
    globals_['conf'] = None
    globals_['paths'] = None
    globals_['server'] = None
    globals_['CONFIGURED'] = False
    mode.set('development') # back to the default
    log.debug("returning None")


class Server(BaseServer):

    def __init__(self, argv=None):
        """Extend.
        """

        if argv is None:
            self.argv = sys.argv

        try:
            self.configuration = set_API(self)
        except configuration.ConfigurationError, err:
            print >> sys.stderr, configuration.USAGE
            print >> sys.stderr, err.msg
            raise SystemExit(2)


        self.protocol = "HTTP/%s" % self.configuration.http_version
        self.version = "Aspen/%s" % __version__
        self.cleanups = [] # functions to run before stopping

        BaseServer.__init__( self
                           , self.configuration.address
                           , website.Website(self)
                           , self.configuration.threads
                            )

        self.pidfiler = PIDFiler()
        log.debug("returning None")


    def tick(self):
        """Extend to support restarting.

        Giving server a chance to shutdown cleanly fixes the terminal screw-up
        bug that plagued httpy < 1.0.

        """
        BaseServer.tick(self)
        if restarter.CHILD:
            if restarter.should_restart():
                log.warn("restarting ...")
                self.stop(None, None)
                raise SystemExit(75)
        #log.debug("Server.tick(): None") too much!


    def start(self):
        """Extend to support signals and graceful shutdown.
        """

        # Bind to OS signals.
        # ===================

        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)


        # Start up.
        # =========
        # And gracefully handle exit conditions.

        log.info("aspen starting on %s" % str(self.configuration.address))
        try:
            BaseServer.start(self)
        except SystemExit, exc:
            log.warn("exiting with code %d" % exc.code)
            raise
        except:
            log.critical( "cleaning up after critical exception:"
                        + os.linesep
                        + traceback.format_exc()
                         )
            self.stop(None, None)
            raise SystemExit(1)

        log.debug("returning None")


    def stop(self, signum, frame):
        msg = ""
        if signum is not None:
            msg = "caught "
            msg += { signal.SIGINT:'SIGINT'
                   , signal.SIGTERM:'SIGTERM'
                    }.get(signum, "signal %d" % signum)
            msg += ", "
        log.warn(msg + "shutting down")


        # Base class cleanup
        # ==================

        BaseServer.stop(self)


        # User cleanup hook
        # =================

        self.cleanup()


        # Our own cleanup routines
        # ========================

        if not WINDOWS:
            if self.configuration.sockfam == socket.AF_UNIX: # clean up socket
                try:
                    os.remove(self.configuration.address)
                except EnvironmentError, exc:
                    log.error( "error removing socket:"
                             + os.linesep
                             + exc.strerror
                              )
        if self.pidfiler.isAlive():                         # we're a daemon
            self.pidfiler.stop.set()
            self.pidfiler.join()

        log.debug("returning None")
        logging.shutdown()


    def register_cleanup(self, func):
        self.cleanups.append(func)
        log.debug("returning None")

    def cleanup(self):
        if self.cleanups:
            log.info("cleaning up ...")
            for func in self.cleanups:
                func()
        log.debug("returning None")


def drive_daemon():
    """Manipulate a daemon or become one ourselves.
    """

    # Locate some paths.
    # ==================

    __ = join(configuration.paths.root, '__')
    if isdir(__):
        var = join(__, 'var')
        if not isdir(var):
            os.mkdir(var)
        pidfile = join(var, 'aspen.pid')
    else:
        key = ' '.join([str(configuration.address), configuration.paths.root])
        key = base64.urlsafe_b64encode(key)
        pidfile = os.sep + join('tmp', 'aspen-%s.pid' % key)
    DEVNULL = '/dev/null'


    # Instantiate the daemon.
    # =======================

    daemon = Daemon(stdout=DEVNULL, stderr=DEVNULL, pidfile=pidfile)


    # Start/stop wrappers
    # ===================
    # Set the logpath perms here; pidfile perms taken care of by pidfiler.

    def start():
        daemon.start()
        pidfiler = PIDFiler()
        pidfiler.path = pidfile
        pidfiler.start()
        start_server()
        log.debug("returning None")


    def stop(stop_output=True):

        # Get the pid.
        # ============

        if not isfile(pidfile):
            log.error("daemon not running")
            raise SystemExit(1)
        data = open(pidfile).read()
        try:
            pid = int(data)
        except ValueError:
            log.error("mangled pidfile: '%r'" % data)
            raise SystemExit(1)


        # Try pretty hard to kill the process nicely.
        # ===========================================
        # We send two SIGTERMs and a SIGKILL before quitting. The daemon gets
        # 5 seconds after each to shut down.

        kill_timeout = 5

        def kill(sig):
            try:
                os.kill(pid, sig)
            except OSError, exc:
                log.error(str(exc))
                raise SystemExit(1)

        nattempts = 0
        while isfile(pidfile):

            if nattempts == 0:
                kill(signal.SIGTERM)
            elif nattempts == 1:
                log.error("%d still going; resending SIGTERM" % pid)
                kill(signal.SIGTERM)
            elif nattempts == 2:
                log.critical( "%d STILL going; sending SIGKILL and quiting"
                            % pid
                             )
                kill(signal.SIGKILL)
                raise SystemExit(1)
            nattempts += 1

            last_attempt = time.time()
            while 1:
                if not isfile(pidfile):
                    log.debug("returning None")
                    return # daemon has stopped
                elif (last_attempt + kill_timeout) < time.time():
                    break # daemon hasn't stopped; time to escalate
                else:
                    time.sleep(0.2)


    # Branch
    # ======

    if configuration.command == 'start':
        if isfile(pidfile):
            log.error( "pidfile already exists with pid %s"
                     % open(pidfile).read()
                      )
            raise SystemExit(1)
        start()

    elif configuration.command == 'status':
        if isfile(pidfile):
            pid = int(open(pidfile).read())
            command = "ps auxww|grep ' %d .*aspen'|grep -v grep" % pid
            # @@: I, um, doubt this command is portable. :^)
            os.system(command)
            raise SystemExit(0)
        else:
            log.error("daemon not running")
            raise SystemExit(0)

    elif configuration.command == 'stop':
        stop()
        raise SystemExit(0)

    elif configuration.command == 'restart':
        stop()
        start()


def main(argv=None):
    """Initial phase of configuration, and daemon/restarter/server branch.
    """

    try:
        server = Server(argv)

        if server.configuration.daemon:
            drive_daemon()
        elif mode.DEBDEV and restarter.PARENT:
            log.info('launching child process')
            restarter.launch_child()
        elif restarter.CHILD:
            if paths.aspen_conf is not None:
                restarter.track(paths.aspen_conf)
            log.info('starting child server')
            server.start()
        else:
            log.info('starting server')
            server.start()

    except KeyboardInterrupt:
        pass

    log.debug("returning None")
