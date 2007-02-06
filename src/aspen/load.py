"""Routines for loading plugin objects based on config file settings.
"""
import cStringIO
import inspect
import logging
import os
from os.path import isdir, isfile, join, realpath

from aspen import colon, utils
from aspen.exceptions import *


log = logging.getLogger('aspen.load')
clean = lambda x: x.split('#',1)[0].strip() # clears comments & whitespace
README_aspen = """\
This directory is served by the application configured on line %d of
__/etc/apps.conf. To wit:

%s

"""


SPACE = ' '
TAB = '\t'


class Mixin:

    apps = None # a list of apps, reverse-sorted by SCRIPT_NAME
    middleware = None # a list of middleware, in reverse order


    def load_plugins(self):
        """Load plugin objects and set on self.
        """
        self.apps = self.load_apps()
        self.middleware = self.load_middleware()


    # Apps
    # ====

    def load_apps(self):
        """Return a list of (URI path, WSGI application) tuples.
        """

        # Prime the pump.
        # ===============
        # Default to static, unless handlers.conf exists. Imports are lazy
        # so that configuration objects are available to static/handlers.

        from aspen.apps.static import static as default
        if self.paths.__ is not None:
            handlers_conf = join(self.paths.__, 'etc', 'handlers.conf')
            if isfile(handlers_conf):
                from aspen.apps.handlers import handlers as default
        apps = [('/', default)]


        # Find a config file to parse.
        # ============================

        try:
            if self.paths.__ is None:
                raise NotImplementedError
            path = join(self.paths.__, 'etc', 'apps.conf')
            if not isfile(path):
                raise NotImplementedError
        except NotImplementedError:
            log.info("No apps configured.")
            return apps


        # We have a config file; proceed.
        # ===============================

        fp = open(path)
        lineno = 0
        urlpaths = []

        for dirpath, dirnames, filenames in os.walk(self.paths.root):
            if 'README.aspen' not in filenames:
                continue
            os.remove(join(dirpath, 'README.aspen'))

        for line in fp:
            lineno += 1
            original = line # for README.aspen
            line = clean(line)
            if not line:                            # blank line
                continue
            else:                                   # specification

                # Perform basic validation.
                # =========================

                if (SPACE not in line) and (TAB not in line):
                    msg = "malformed line (no whitespace): '%s'" % line
                    raise AppsConfError(msg, lineno)
                urlpath, name = line.split(None, 1)
                if not urlpath.startswith('/'):
                    msg = "URL path not specified absolutely: '%s'" % urlpath
                    raise AppsConfError(msg, lineno)


                # Instantiate the app on the filesystem.
                # ======================================

                fspath = utils.translate(self.paths.root, urlpath)
                if not isdir(fspath):
                    os.makedirs(fspath)
                    log.info("created app directory '%s'"% fspath)
                readme = join(fspath, 'README.aspen')
                open(readme, 'w+').write(README_aspen % (lineno, original))


                # Determine whether we already have an app for this path.
                # =======================================================

                msg = "URL path is contested: '%s'" % urlpath
                contested = AppsConfError(msg, lineno)
                if urlpath in urlpaths:
                    raise contested
                if urlpath.endswith('/'):
                    if urlpath[:-1] in urlpaths:
                        raise contested
                elif urlpath+'/' in urlpaths:
                    raise contested
                urlpaths.append(urlpath)


                # Load the app, check it, store it.
                # =================================

                obj = colon.colonize(name, fp.name, lineno)
                if not callable(obj):
                    msg = "'%s' is not callable" % name
                    raise AppsConfError(msg, lineno)
                apps.append((urlpath, obj))

        apps.sort()
        apps.reverse()
        return apps


    # Middleware
    # ==========

    def load_middleware(self):
        """Return a list of middleware callables in reverse order.
        """

        # Find a config file to parse.
        # ============================

        default_stack = []

        try:
            if self.paths.__ is None:
                raise NotImplementedError
            path = join(self.paths.__, 'etc', 'middleware.conf')
            if not isfile(path):
                raise NotImplementedError
        except NotImplementedError:
            log.info("No middleware configured.")
            return default_stack


        # We have a config file; proceed.
        # ===============================

        fp = open(path)
        lineno = 0
        stack = []

        for line in fp:
            lineno += 1
            name = clean(line)
            if not name:                            # blank line
                continue
            else:                                   # specification
                obj = colon.colonize(name, fp.name, lineno)
                if not callable(obj):
                    msg = "'%s' is not callable" % name
                    raise MiddlewareConfError(msg, lineno)
                stack.append(obj)

        stack.reverse()
        return stack
