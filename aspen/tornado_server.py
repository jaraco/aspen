import atexit
import logging
import os
import socket
import sys
import traceback

import aspen
from aspen.ipc import restarter
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application


log = logging.getLogger('aspen.server')


class Server:

    def __init__(self, configuration):
        """Extend to take a Configuration object.
        """
        self.configuration = configuration
        self.version = "Aspen/%s" % aspen.__version__
        atexit.register(self.stop)
   

    def start(self):
        """Start the server with filesystem monitoring.
        """
        log.warn("starting on %s" % str(self.configuration.address))
   
        if aspen.mode.DEBDEV:
            log.info("configuring filesystem monitor")
            for path in ( os.path.join('etc', 'aspen.conf')
                        , os.path.join('etc', 'logging.conf')
                         ):
                if os.path.isfile(path):
                    restarter.monitor(path)
            restarter.start_monitoring()


        # Now it's time for the Tornado API.
        # ==================================

        app = Application( [('^.*$', self.configuration.Handler)]
                         , debug=aspen.mode.DEBDEV
                          )
        app.configuration = self.configuration
        self.server = HTTPServer(app)
        self.server.listen(self.configuration.address[1]) #TODO AF_UNIX?

        uid = self.configuration.user
        if uid is not None:
            
            # Drop privileges.
            # ================
            # "Since setresuid has a clear semantics and is able to set each
            # user ID individually, it should always be used if available.
            # Otherwise, to set only the effective uid, seteuid(new euid)
            # should be used; to set all three user IDs, setreuid(new uid, new
            # uid) should be used."
            #
            # http://www.cs.berkeley.edu/~daw/papers/setuid-usenix02.pdf, p16

            os.setreuid(uid, uid)

        loop = IOLoop.instance()
        loop.start()


    def stop(self):
        """Clean up and exit.

        Tornado does not close HTTPServer's socket itself, relying on garbage
        collection. This works fine when the program is ending anyway, but in 
        testing we need to be able to rebind to the socket again in the same
        process. So we close it when the loop is over.

        """
        log.debug("cleaning up server")
        sys.stdout.flush()

        loop = IOLoop.instance()
        loop.add_callback(lambda: self.server._socket.close())
        loop.stop()

        if not aspen.WINDOWS: 
            if self.configuration.sockfam == socket.AF_UNIX: # clean up socket
                try:
                    os.remove(configuration.address)
                except EnvironmentError, exc:
                    log.error("error removing socket:", exc.strerror)

        # pidfile removed in __init__.py:_main
        # restarter stopped in ipc/restarter.py:_atexit


# Support restarting when we are restarter.CHILD.
# ===============================================
# Note that when using aspen._main, Server is only ever instantiated within 
# restarter.CHILD.

if restarter.CHILD:

    def check_restart():
        if restarter.should_restart():
            log.info("restarting")
            raise SystemExit(75) # will trigger self.stop via atexit

    loop = IOLoop.instance() 
    loop.add_callback(check_restart)

