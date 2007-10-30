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
import os
import socket
import sys
import optparse
import ConfigParser
from os.path import join, isdir, isfile, realpath

from aspen import mode


log = logging.getLogger('aspen.configuration')
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
# Does this look ugly to anyone else? I guess it works.

def callback_address(option, opt, value, parser_):
    """Must be a valid AF_INET or AF_UNIX address.
    """
    address, sockfam = validate_address(value)
    parser_.values.address = address
    parser_.values.sockfam = sockfam
    parser_.values.have_address = True


#def callback_log_level(option, opt, value, parser_):
#    """
#    """
#    try:
#        level = getattr(logging, value.upper())
#    except AttributeError:
#        msg = "Bad log level: %s" % value
#        raise optparse.OptionValueError(msg)
#    parser_.values.log_level = level


def callback_root(option, opt, value, parser_):
    """Expand the root directory path and make sure the directory exists.
    """
    value = realpath(value)
    if not isdir(value):
        msg = "%s does not point to a directory" % value
        raise optparse.OptionValueError(msg)
    parser_.values.root = value


def callback_mode(option, opt, value, parser_):
    """Indicate that we have a mode from the command line.
    """
    parser_.values.mode = value
    parser_.values.have_mode= True


usage = "aspen [options] [start,stop,&c.]; --help for more"
optparser = optparse.OptionParser(usage=usage)

optparser.add_option( "-a", "--address"
                    , action="callback"
                    , callback=callback_address
                    , default=('0.0.0.0', 8080)
                    , dest="address"
                    , help="the IP or Unix address to bind to [:8080]"
                    , type='string'
                     )
#optparser.add_option( "-l", "--log_filter"
#                    , default=''
#                    , dest="log_filter"
#                    , help="a subsystem filter for logging []"
#                    , type='string'
#                     )
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
optparser.add_option( "-r", "--root"
                    , action="callback"
                    , callback=callback_root
                    , default=os.getcwd()
                    , dest="root"
                    , help="the root publishing directory [.]"
                    , type='string'
                     )
#optparser.add_option( "-v", "--log_level"
#                    , action="callback"
#                    , callback=callback_log_level
#                    , choices=[ 'notset', 'debug', 'info', 'warning', 'error'
#                              , 'critical'
#                               ]
#                    , default='info'
#                    , dest="log_level"
#                    , help=( "the level below which messages will be stiffled "
#                           + "[warning]"
#                            )
#                    , type='choice'
#                     )


class Paths(dict, AttrMixin):
    """Junkdrawer for a few paths we like to keep around (key & attr access)
    """

    def __init__(self, root):
        """Takes the website's filesystem root.

            root        website's filesystem root
            aspen_conf  <root>/aspen.conf; <root>/etc/aspen.conf
            etc         <root>/etc
            lib         if etc is not None, lib/python{x.y}
            pkg                        ..., lib/python/site-packages
            plat                       ..., lib/plat-<foo>

        All but <root> can be None. If lib, pkg and plat are not None, they are
        added to sys.path.

        """
        self.root = root


        # aspen_conf & etc
        # ================

        aspen_conf = join(self.root, 'aspen.conf')
        has_aspen_conf = isfile(aspen_conf)
        etc_aspen_conf = join(self.root, 'etc', 'aspen.conf')
        has_etc_aspen_conf = isfile(etc_aspen_conf)
        if has_aspen_conf and has_etc_aspen_conf:
            raise ConfigurationError( "Only one of aspen.conf and "
                                    + "etc/aspen.conf may be present."
                                     )

        self.etc = None
        self.aspen_conf = None
        if has_aspen_conf:
            self.aspen_conf = aspen_conf
        elif has_etc_aspen_conf:
            self.etc = join(self.root, 'etc')
            self.aspen_conf = etc_aspen_conf


        # PYTHONPATH additions
        # ====================

        if self.etc is None:
            self.lib = None
            self.pkg = None
            self.plat = None
        else:
            lib = join(self.root, 'lib', 'python')
            if isdir(lib):
                self.lib = lib
                sys.path.insert(0, lib)
            else:
                lib = join(self.root, 'lib', 'python'+sys.version[:3])
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

        self.address = ('', 8080)
        self.command = 'runfg'
        self.daemon = False
        self.defaults = ('index.html', 'index.htm')
        self.http_version = '1.1'
        self.sockfam = socket.AF_INET
        self.threads = 10
        self._mode = 'development'


        # Update
        # ======

        self.update_from_environment()
        self.update_from_command_line()
        self.update_from_conf_file()


    # Updates
    # =======

    def update_from_environment(self):
        """Given a Configuration object, update it from the environment.
        """
        self._mode = mode.get() # mostly for testing


    def update_from_command_line(self):
        """Given a Configuration object, update it from the command line.
        """
        opts, args = optparser.parse_args(self.argv)
        paths = Paths(opts.root)                # default handled by optparse

        self.optparser = optparser
        self.opts = opts
        self.args = args
        self.paths = paths


        # command/daemon
        # ==============

        command = args and args[1] or 'runfg'
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
            self.address = address
            self.sockfam = sockfam


        # mode
        # ====
        # This can also be set in the environment and in the conf file.

        if getattr(opts, 'have_mode', False):
            mode.set(opts.mode)
            self._mode = opts.mode # mostly for testing


    def update_from_conf_file(self):
        """Given a Configuration object, update it from the aspen.conf file.
        """

        if self.paths.aspen_conf is None:
            self.conf = ConfFile()
            return
        self.conf = ConfFile(self.paths.aspen_conf)


        # address
        # =======

        if 'address' in self.conf.DEFAULT:
            address, sockfam = validate_address(self.conf.DEFAULT['address'])
            self.address = address
            self.sockfam = sockfam


        # defaults
        # ========

        if 'defaults' in self.conf.DEFAULT:
            defaults = self.conf.DEFAULT['defaults']
            if isinstance(defaults, basestring):
                if ',' in defaults:
                    defaults = [d.strip() for d in defaults.split(',')]
                else:
                    defaults = defaults.split()
            self.defaults = tuple(defaults)


        # http_version
        # ============

        if 'http_version' in self.conf.DEFAULT:
            http_version = self.conf.DEFAULT['http_version']
            if http_version not in ('1.0', '1.1'):
                raise TypeError( "http_version must be 1.0 or 1.1, "
                               + "not '%s'" % http_version
                                )
            self.http_version = http_version


        # mode
        # ====

        if 'mode' in self.conf.DEFAULT:
            mode.set(self.conf.DEFAULT['mode'])
            self._mode = self.conf.DEFAULT['mode'] # mostly for testing


        # threads
        # =======

        if threads in self.conf.DEFAULT:
            threads = self.conf.DEFAULT['threads']
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


        # Logging
        # =======
        # When run in the foreground, always log to stdout/stderr; otherwise,
        # always log to __/var/log/error.log.x, rotating per megabyte.
        #
        # Currently we just support throttling from the command line based on
        # subsystem and level.


    #        #logging.basicConfig(format=FORMAT)
    #
    #        handler = logging.StreamHandler()
    #        handler.addFilter(logging.Filter(self.opts.log_filter))
    #        form = logging.Formatter(logging.BASIC_FORMAT)
    #        handler.setFormatter(form)
    #        logging.root.addHandler(handler)
    #        logging.root.setLevel(self.opts.log_level)
    #        log.debug("logging configured")
