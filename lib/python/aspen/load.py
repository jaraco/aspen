"""Routines for loading plugin objects based on config file settings.
"""
import cStringIO
import inspect
import logging
import os
from os.path import isdir, isfile, join, realpath

import aspen
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

    apps = []
    urlpaths = []
    if not aspen.conf.has_section('apps'):
        return apps

    for dirpath, dirnames, filenames in os.walk(aspen.paths.root):
        if 'README.aspen' not in filenames:
            continue
        os.remove(join(dirpath, 'README.aspen'))

    for urlpath, name in aspen.conf.items('apps'):
        if not urlpath.startswith('/'):
            msg = "URL path not specified absolutely: '%s'" % urlpath
            raise ConfError(msg, lineno)


        # Instantiate the app on the filesystem.
        # ======================================

        fspath = utils.translate(aspen.paths.root, urlpath)
        if not isdir(fspath):
            os.makedirs(fspath)
            log.info("created app directory '%s'"% fspath)
        readme = join(fspath, 'README.aspen')
        open(readme, 'w+').write(README_aspen % (0, 'foo'))


        # Determine whether we already have an app for this path.
        # =======================================================

        msg = "URL path is contested: '%s'" % urlpath
        contested = ConfError(msg, 0)
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

        obj = colon.colonize(name, '[app def]', 0)
        if not callable(obj):
            msg = "'%s' is not callable" % name
            raise ConfError(msg, 0)
        apps.append((urlpath, obj))

    apps.sort()
    apps.reverse()
    return apps


def load_middleware():
    """Return a list of middleware callables in reverse order.
    """
    stack = []
    stack_def = aspen.conf.DEFAULT.get('middleware', '')
    if not stack_def:
        return stack
    for raw in stack_def.split():
        obj = colon.colonize(name, '[middleware def]', 0)
        if not callable(obj):
            msg = "'%s' is not callable" % name
            raise ConfError(msg, 0)
        stack.append(obj)
    stack.reverse()
    return stack
