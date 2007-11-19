"""Define configuration objects.

    1. validator_address -- called in a couple places
    2. optparse -- command line interface
    3. paths -- path storage
    4. ConfFile -- represents a configuration file
    5. Configuration -- puts it all together

This module is so-named because we place an instance of Configuration in the
global aspen namespace.

"""
import logging
import logging.handlers
import os
import socket
import sys
import optparse
import ConfigParser
from os.path import dirname, join, isabs, isdir, isfile, realpath

import aspen
from aspen import mode


log = logging.getLogger('aspen.configuration')
MEGABYTE = pow(2, 20)
COMMANDS = ('start', 'status', 'stop', 'restart', 'runfg')
WINDOWS = 'win' in sys.platform
if not WINDOWS:
    import pwd


class ConfigurationError(StandardError):
    """This is an error in any part of our configuration.
    """

    def __init__(self, msg):
        StandardError.__init__(self)
        self.msg = msg

    def __str__(self):
        return self.msg


class AttrMixin(object):
    """Mix attribute access into a mapping type.
    """

    def __delattr__(self, name):
        del self[name]

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            msg = "%s has no attribute '%s'" % (repr(self), name)
            raise AttributeError(msg)

    def __setattr__(self, name, value):
        self[name] = value


def validate_address(address):
    """Given a socket address string, return a tuple (sockfam, address).

    This is called from a couple places, and is a bit complex.

    """

    if address[0] in ('/','.'):
        if WINDOWS:
            raise ConfigurationError("Can't use an AF_UNIX socket on Windows.")
            # but what about named pipes?
        sockfam = socket.AF_UNIX
        # We could test to see if the path exists or is creatable, etc.
        address = realpath(address)

    elif address.count(':') > 1:
        sockfam = socket.AF_INET6
        # @@: validate this, eh?

    else:
        sockfam = socket.AF_INET
        # Here we need a tuple: (str, int). The string must be a valid
        # IPv4 address or the empty string, and the int -- the port --
        # must be between 0 and 65535, inclusive.


        err = "Bad address %s" % str(address)


        # Break out IP and port.
        # ======================

        if isinstance(address, (tuple, list)):
            if len(address) != 2:
                raise err
            ip, port = address
        elif isinstance(address, basestring):
            if address.count(':') != 1:
                raise err
            ip_port = address.split(':')
            ip, port = [i.strip() for i in ip_port]
        else:
            raise err


        # IP
        # ==

        if not isinstance(ip, basestring):
            raise err
        elif ip == '':
            ip = '0.0.0.0' # IP defaults to INADDR_ANY for AF_INET; specified
                           # explicitly to avoid accidentally binding to
                           # INADDR_ANY for AF_INET6.
        else:
            try:
                socket.inet_aton(ip)
            except socket.error:
                raise err


        # port
        # ====
        # Coerce to int. Must be between 0 and 65535, inclusive.

        if isinstance(port, basestring):
            if not port.isdigit():
                raise err
            else:
                port = int(port)
        elif isinstance(port, int) and not (port is False):
            # already an int for some reason (called interactively?)
            pass
        else:
            raise err

        if not(0 <= port <= 65535):
            raise err


        # Success!
        # ========

        address = (ip, port)


    return address, sockfam


# optparse
# ========

USAGE = "aspen [options] [start,stop,&c.]; --help for more"
optparser = optparse.OptionParser(usage=USAGE)


# address
# -------

def callback_address(option, opt, value, parser_):
    """Must be a valid AF_INET or AF_UNIX address.
    """
    address, sockfam = validate_address(value)
    parser_.values.address = address
    parser_.values.sockfam = sockfam
    parser_.values.have_address = True

optparser.add_option( "-a", "--address"
                    , action="callback"
                    , callback=callback_address
                    , default=('0.0.0.0', 8080)
                    , dest="address"
                    , help="the IP or Unix address to bind to [:8080]"
                    , type='string'
                     )


# conf
# ----

optparser.add_option( "-f", "--conf"
                    , action="store"
                    , default=""
                    , dest="conf"
                    , help="the configuration file [see doc]"
                    , type='string'
                     )


# mode
# ----

def callback_mode(option, opt, value, parser_):
    """Indicate that we have a mode from the command line.
    """
    parser_.values.mode = value
    parser_.values.have_mode= True

optparser.add_option( "-m", "--mode"
                    , action="callback"
                    , callback=callback_mode
                    , choices=[ 'debugging', 'deb', 'development', 'dev'
                              , 'staging', 'st', 'production', 'prod'
                               ]
                    , default='development'
                    , dest="mode"
                    , help=( "one of: debugging, development, staging, "
                           + "production [development]"
                            )
                    , type='choice'
                     )


class Paths(dict, AttrMixin):
    """Junkdrawer for a few paths we like to keep around (key & attr access)
    """

    def __init__(self, conf):
        """Takes the website's configuration file.

            conf        one of:
                          --conf=...
                          /etc/aspen.conf
                          /usr/etc/aspen.conf
                          /usr/local/etc/aspen.conf
                          <root>/etc/aspen.conf
            root        website's filesystem root; cwd or explicitly set in conf
            docroot     website's document root on the filesystem; <root>/www
            lib         <root>/lib/python
            pkg         <lib>/site-packages
            plat        <lib>/plat-<foo>

        All can be None. If lib, pkg and plat are not None, they are added to
        sys.path. The latter must be set at a later phase of config parsing.

        """

        if conf:                    # we have a file named on the command line
            if not isabs(conf):
                conf = join(os.getcwd(), conf)
            if not isfile(conf):
                raise ConfigurationError( "Configuration file does not exist: "
                                        + conf
                                         )
        else:                       # no file named on the command line
            PATH = [ join('', 'etc', 'aspen.conf')
                   , join('', 'usr', 'etc', 'aspen.conf')
                   , join('', 'usr', 'local', 'etc', 'aspen.conf')
                   , join(os.getcwd(), 'etc', 'aspen.conf')
                    ]
            for path in PATH:
                if isfile(path):
                    conf = path # last match wins
        self.conf = conf


    def __init_phase_2__(self, conf):
        """Takes a parsed conf file and sets the remaining attributes.
        """

        # root
        # ====

        root = None
        if 'root' in conf.main:
            root = conf.main['root']
            if not isabs(root):
                raise ConfigurationError("root is not absolute: %s" % root)
            if not isdir(root):
                raise ConfigurationError("root does not exist: %s" % root)
            root = realpath(root)
        else:
            root = os.getcwd()
        self.root = root
        log.debug("configured docroot %s" % root)


        # docroot
        # =======

        docroot = None
        if 'docroot' in conf.main:
            docroot = conf.main['docroot']
            if not isabs(docroot):
                docroot = join(root, docroot)
            docroot = realpath(docroot)
            if not isdir(docroot):
                raise ConfigurationError("docroot does not exist: %s" % docroot)
        else:
            _docroot = join(root, 'www')
            if isdir(_docroot):
                docroot = _docroot
        self.docroot = docroot
        log.debug("configured docroot %s" % docroot)


        # PYTHONPATH additions
        # ====================

        lib = join(root, 'lib', 'python')
        if isdir(lib):  # lib/python
            self.lib = lib
            sys.path.insert(0, lib)
        else:           # lib/python2.5
            lib = join(root, 'lib', 'python'+sys.version[:3])
            if isdir(lib):
                self.lib = lib
                sys.path.insert(0, lib)
            else:
                self.lib = None

        pkg = join(lib, 'site-packages')
        if isdir(pkg):
            self.pkg = pkg
            sys.path.insert(0, pkg)
        else:
            self.pkg = None

        plat = join(lib, 'plat-'+sys.platform)
        if isdir(plat):
            self.plat = plat
            sys.path.insert(0, plat)
        else:
            self.plat = None


class ConfFile(object, ConfigParser.RawConfigParser):
    """Represent a configuration file.

    This class wraps the standard library's RawConfigParser class. The
    constructor takes the path of a configuration file. If the file does not
    exist, you'll get an empty object. Use either attribute or key access on
    instances of this class to return section dictionaries. If a section doesn't
    exist, you'll get an empty dictionary.

    """

    def __init__(self, filepath=False):
        ConfigParser.RawConfigParser.__init__(self)
        if filepath:
            self.readfp(open(filepath))

    def __getitem__(self, name):
        return self.has_section(name) and dict(self.items(name)) or {}

    def __getattr__(self, name):
        try:
            self.__getattribute__(name)
        except AttributeError:
            return self.__getitem__(name)

    def __repr__(self):
        return str([self.items(section) for section in self.sections()])


    # Iteration API
    # =============
    # mostly for testing

    def iterkeys(self):
        return iter(self.sections())
    __iter__ = iterkeys

    def iteritems(self):
        for k in self:
            yield (k, self[k])

    def itervalues(self):
        for k in self:
            yield self[k]


class Configuration(dict, AttrMixin):
    """A dictionary w/ attribute access too.
    """

    def __init__(self, argv):
        dict.__init__(self)


        # Prime some objects
        # ==================

        self.argv = argv
        self.args = None
        self.apps = None
        self.conf = None
        self.middleware = None
        self.optparser = None
        self.opts = None
        self.paths = None


        # Defaults
        # ========

        self.address = ('0.0.0.0', 8080)
        self.command = 'runfg'
        self.conf = join('etc', 'aspen.conf')
        self.daemon = False
        self.defaults = ('index.html', 'index.htm')
        self.http_version = '1.1'
        self.log_filepath = join('var', 'aspen.log')
        self.log_filter = ''
        self.log_format = 'compact' # or 'verbose'
        self.log_keep = 5
        self.log_level = logging.INFO
        self.log_size = 1.0
        #self.pidfile = join('etc', 'aspen.pid')
        self.sockfam = socket.AF_INET
        self.threads = 10
        #self.user = ...
        #self.group = ...
        self._mode = 'development'


        # Update
        # ======

        self.update_from_environment()
        self.update_from_command_line(argv)
        self.update_from_conf_file(self.paths.conf)


        # Propagate logging configuration.
        # ================================
        # For advanced configuration, use the logging package directly.

        # format
        # ------

        haveFuncName = (sys.version_info >= (2, 5))
        func = (haveFuncName and "in %(funcName)s()" or "")
        if self.log_format == 'compact':
            format = logging.Formatter(os.linesep.join([
                  "-"*79
                , "%(levelname)s " + func + " [%(name)s]"
                , "  %(pathname)s:%(lineno)d"
                , ""
                , "%(message)s"
                , ""
                 ]))
        elif self.log_format == 'verbose':
            format = logging.Formatter(os.linesep.join([
                  "-"*79
                , "   Logger: %(name)s"
                , "    Level: %(levelname)s"
                , " Function: " + (haveFuncName and "%(funcName)s" or "n/a")
                , "     File: %(pathname)s"
                , "   LineNo: %(lineno)d"
                , "   Thread: %(threadName)s [%(thread)d]"
                , "  Process: %(process)d"
                , "Timestamp: %(asctime)s"
                , ""
                , "%(message)s"
                , ""
                 ]))
        else:
            raise ConfigurationError("Sanity check.")


        # filter
        # ------
        # Aha! "Note that a filter on a logger applies only to messages sent
        # directly to that logger, whereas a filter on a handler applies also to
        # messages received from child loggers."
        #
        #   http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/412552

        filt = logging.Filter(self.log_filter) # '' == unfiltered


        # handler
        # -------

        if self.daemon is False:                        # stderr
            handler = logging.StreamHandler()
        else:                                           # rotating log file
            assert self.daemon is True # sanity check
            Handler = logging.handlers.RotatingFileHandler
            handler = Handler( self.log_filepath
                             , 'a'
                             , self.log_size * MEGABYTE
                             , self.log_keep
                              )

        handler.setFormatter(format)
        handler.addFilter(filt)


        # final assembly
        # --------------

        aspen_log = logging.getLogger('aspen')
        aspen_log.addHandler(handler)
        aspen_log.setLevel(self.log_level)
        aspen_log.propagate = False
        log.info("logging configured") # first log that works

        log.debug("returning None")


    # Updates
    # =======

    def update_from_environment(self):
        """Given a Configuration object, update it from the environment.
        """
        self._mode = mode.get() # mostly for testing
        log.debug("returning None")


    def update_from_command_line(self, argv):
        """Given a Configuration object, update it from the command line.
        """
        opts, args = optparser.parse_args(argv)
        paths = Paths(opts.conf)

        self.optparser = optparser
        self.opts = opts
        self.args = args
        self.paths = paths


        # command/daemon
        # ==============

        command = len(args) > 1 and args[1] or 'runfg'
        if command not in COMMANDS:
            raise ConfigurationError("Bad command: %s" % command)
        daemon = command != 'runfg'
        if daemon and WINDOWS:
            raise ConfigurationError("Can only daemonize on UNIX.")

        self.command = command
        self.daemon = daemon


        # address/sockfam
        # ===============
        # These can also be set in the conf file.

        if getattr(opts, 'have_address', False):
            self.address = opts.address
            self.sockfam = opts.sockfam


        # mode
        # ====
        # This can also be set in the environment and in the conf file.

        if getattr(opts, 'have_mode', False):
            mode.set(opts.mode)
            self._mode = opts.mode # mostly for testing

        log.debug("returning None")


    def update_from_conf_file(self, path):
        """Given a path to a conf file, update ourself.
        """

        self.conf = ConfFile(path)
        self.paths.__init_phase_2__(self.conf)
        if path is None:
            log.debug("returning None")
            return


        # address
        # =======

        if 'address' in self.conf.main:
            address, sockfam = validate_address(self.conf.main['address'])
            self.address = address
            self.sockfam = sockfam


        # defaults
        # ========

        if 'defaults' in self.conf.main:
            defaults = self.conf.main['defaults']
            if isinstance(defaults, basestring):
                if ',' in defaults:
                    defaults = [d.strip() for d in defaults.split(',')]
                else:
                    defaults = defaults.split()
            self.defaults = tuple(defaults)


        # http_version
        # ============

        if 'http_version' in self.conf.main:
            http_version = self.conf.main['http_version']
            if http_version not in ('1.0', '1.1'):
                raise TypeError( "http_version must be 1.0 or 1.1, "
                               + "not '%s'" % http_version
                                )
            self.http_version = http_version


        # logging
        # =======

        if self.conf.logging:

            if 'filepath' in self.conf.logging:
                value = self.conf.logging['filepath']
                if not isabs(value):
                    value = join(self.paths.root, value)
                if not isdir(dirname(value)):
                    raise ConfigurationError( "Log file's parent directory does "
                                            + "not exist: %s" % value
                                             )

            if 'filter' in self.conf.logging:
                self.log_filter = self.conf.logging['filter']

            if 'format' in self.conf.logging:
                value = self.conf.logging['format'].lower()
                if value not in ('compact', 'verbose'):
                    raise ConfigurationError("Bad log format: %s" % value)
                self.log_format = value

            if 'level' in self.conf.logging:
                value = self.conf.logging['level']
                try:
                    value = getattr(logging, value.upper())
                except AttributeError:
                    raise ConfigurationError("Bad log level: %s" % value)
                self.log_level = value

            if 'size' in self.conf.logging:
                value = self.conf.logging['size']
                try:
                    value = float(value)
                except ValueError:
                    raise ConfigurationError("Bad logfile size: %s" % value)
                self.log_size = value


            if 'keep' in self.conf.logging:
                value = self.conf.logging['keep']
                try:
                    value = int(value)
                except ValueError:
                    raise ConfigurationError( "Bad number of log files to "
                                            + "keep: %s" % value
                                             )
                self.log_keep = value


        # mode
        # ====

        if 'mode' in self.conf.main:
            mode.set(self.conf.main['mode'])
            self._mode = self.conf.main['mode'] # mostly for testing


        # threads
        # =======

        if 'threads' in self.conf.main:
            threads = self.conf.main['threads']
            if isinstance(threads, basestring):
                if not threads.isdigit():
                    raise TypeError( "thread count not a positive integer: "
                                   + "'%s'" % threads
                                    )
                threads = int(threads)
                if not threads >= 1:
                    raise ValueError("thread count less than 1: '%d'" % threads)
            self.threads = threads

    #        # user
    #        # ====
    #        # Must be a valid user account on this system.
    #
    #        if WINDOWS:
    #            raise ConfigurationError("can't switch users on Windows")
    #        try:
    #            user = pwd.getpwnam(candidate)[2]
    #        except KeyError:
    #            raise ConfigurationError("bad user: '%s'" % candidate)
    #        return user

        log.debug("returning None")
