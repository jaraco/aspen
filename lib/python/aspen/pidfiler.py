"""A class to monitor a PID file.
"""
import os
import sys
import threading
import time
from os.path import isfile


class PIDFiler(threading.Thread):
    """Thread to continuously monitor a pidfile, keeping our pid in the file.

    This is run when we are a daemon, in the child process. It checks every
    second to see if the file exists, recreating it if not. It also rewrites the
    file every 60 seconds, just in case the contents have changed, and resets
    the mode to 0600 just in case it has changed.

    """

    stop = threading.Event()
    path = '' # path to the pidfile
    pidcheck_timeout = 60 # seconds between pidfile writes
    pidfile_mode = 0600 # the permission bits on the pidfile

    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def write(self):
        open(self.path, 'w+').write(str(os.getpid()))
        self.set_perms()

    def set_perms(self):
        os.chmod(self.path, self.pidfile_mode)

    def run(self):
        """Pidfile is initially created and finally destroyed by our Daemon.
        """
        self.set_perms()
        last_pidcheck = 0
        while not self.stop.isSet():
            if not isfile(self.path):
                print "no pidfile; recreating"
                sys.stdout.flush()
                self.write()
            elif (last_pidcheck + self.pidcheck_timeout) < time.time():
                self.write()
                last_pidcheck = time.time()
            time.sleep(1)
        if isfile(self.path): # sometimes we beat handlesigterm
            os.remove(self.path)
