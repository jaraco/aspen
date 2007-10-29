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

SPACE = ' '
TAB = '\t'
README_aspen = """\
This directory is served by the application configured on line %d of
__/etc/apps.conf. To wit:

%s

"""

def load_apps():
    """Return a list of (URI path, WSGI application) tuples.
    """

    # Find a config file to parse.
    # ============================

    apps = []

    try:
        if aspen.paths.__ is None:
            raise NotImplementedError
        path = join(aspen.paths.__, 'etc', 'apps.conf')
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

    for dirpath, dirnames, filenames in os.walk(aspen.paths.root):
        if 'README.aspen' not in filenames:
            continue
        os.remove(join(dirpath, 'README.aspen'))

    for line in fp:
        lineno += 1
        original = line # for README.aspen
        line = utils.clean(line)
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

            fspath = utils.translate(aspen.paths.root, urlpath)
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


def load_middleware():
    """Return a list of middleware callables in reverse order.
    """

    # Find a config file to parse.
    # ============================

    default_stack = []

    try:
        if aspen.paths.__ is None:
            raise NotImplementedError
        path = join(aspen.paths.__, 'etc', 'middleware.conf')
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
        name = utils.clean(line)
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
