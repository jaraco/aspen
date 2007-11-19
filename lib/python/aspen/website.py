import logging
import os
from os.path import basename, exists, isdir, isfile, join, realpath

import aspen
from aspen import colon, mode, utils
from aspen.exceptions import HandlerError
from aspen.configuration import ConfigurationError
from aspen.utils import check_trailing_slash, find_default, translate


log = logging.getLogger('aspen.website')


class Website:
    """Represent a website.

    A website is composed of WSGI callables mounted at various paths in the site
    hierarchy. We don't use CherryPyWSGIServer's mounting mechanism because we
    want some extra spice (middleware, slash semantics).

    """

    def __init__(self, server):
        """Takes a Server instance.
        """

        # Remember some things.
        # =====================

        self.server = server
        self.configuration = server.configuration
        self.apps = self.load_apps()


        # Wrap ourself in middleware.
        # ===========================

        wrapped = self.wsgi
        for middleware in self.load_middleware():
            wrapped = middleware(wrapped)
        self.wrapped = wrapped

        log.debug("returning None")


    def __call__(self, environ, start_response):
        """Main WSGI callable, to be called from the outside world.
        """
        response = self.wrapped(environ, start_response)
        log.debug("returning %s" % response)
        return response


    def wsgi(self, environ, start_response):
        """Base WSGI callable, to be wrapped by middleware.
        """
        app = self.get_app(environ, start_response) # 301
        if isinstance(app, list):                   # redirection
            response = app
        elif app is None:                           # no apps configured!
            start_response('500', [('Content-Type', 'text/plain')])
            response = ['No apps mounted.']
        else:
            response = app(environ, start_response) # WSGI
        log.debug("returning %s" % response)
        return response


    def load_middleware(self):
        """Return a list of middleware callables in reverse order.
        """
        stack = []
        stack_def = self.configuration.conf.DEFAULT.get('middleware', '')
        if not stack_def:
            return stack
        for raw in stack_def.split():
            obj = colon.colonize(name, '[middleware def]', 0)
            if not callable(obj):
                msg = "'%s' is not callable" % name
                raise ConfigurationError(msg)
            stack.append(obj)
        stack.reverse()
        log.debug("returning %s" % stack)
        return stack


    def load_apps(self):
        """Return a list of (URI path, WSGI application) tuples.
        """

        apps = []
        urlpaths = []
        if not aspen.conf.has_section('apps'):
            return apps

        for dirpath, dirnames, filenames in os.walk(aspen.paths.docroot):
            if 'README.aspen' not in filenames:
                continue
            os.remove(join(dirpath, 'README.aspen'))

        for urlpath, name in aspen.conf.items('apps'):
            if not urlpath.startswith('/'):
                msg = "URL path not specified absolutely: '%s'" % urlpath
                raise ConfigurationError(msg, lineno)


            # Determine whether we already have an app for this path.
            # =======================================================

            msg = "URL path is contested: '%s'" % urlpath
            contested = ConfigurationError(msg)
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
                raise ConfigurationError(msg)
            apps.append((urlpath, obj))

        apps.sort()
        apps.reverse()
        log.debug("returning %s" % apps)
        return apps


    def get_app(self, environ, start_response):
        """Given a WSGI environ, return the first matching app.
        """

        app = None
        path = match_against = environ['PATH_INFO']
        if not match_against.endswith('/'):
            match_against += '/'

        for app_urlpath, _app in self.apps:

            # Match?
            # ======

            if not match_against.startswith(app_urlpath):
                continue # No.


            # Check trailing slash.
            # =====================

            if app_urlpath.endswith('/'): # "slash please"
                if path == app_urlpath[:-1]: # redirect to trailing slash
                    environ['PATH_INFO'] += '/'
                    new_url = full_url(environ)
                    start_response( '301 Moved Permanently'
                                  , [('Location', new_url)]
                                   )
                    return ['Resource moved to: ' + new_url]
                app_urlpath = app_urlpath[:-1] # trailing slash goes in
                                               # PATH_INFO, not SCRIPT_NAME

            # Update environ.
            # ===============

            environ["SCRIPT_NAME"] = app_urlpath
            environ["PATH_INFO"] = path[len(app_urlpath):]

            app = _app
            break

        log.debug("returning %s" % app)
        return app
