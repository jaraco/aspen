import logging
import os
import sys
from os.path import exists, isdir, isfile, join

from aspen.utils import check_trailing_slash, translate


log = logging.getLogger('aspen.website')


class Website:
    """Represent a publication, application, or hybrid website.
    """

    def __init__(self, configuration):
        self.apps = configuration.apps
        self.__ = configuration.paths.__
        self.root = configuration.paths.root


    def __call__(self, environ, start_response):
        """Main WSGI callable.
        """
        log.debug('called')


        # Translate the request to the filesystem.
        # ========================================

        fspath = translate(self.root, environ['PATH_INFO'])
        if self.__ is not None:
            if fspath.startswith(self.__): # protect magic dir
                start_response('404 Not Found', [])
                return ['Resource not found.']
        environ['PATH_TRANSLATED'] = fspath


        # Dispatch to an app.
        # ===================

        app = self.get_app(environ, start_response) # 301
        if isinstance(app, list):                           # redirection
            response = app
        elif app is None:                                   # no app found
            log.debug("No app found for '%s'" % environ['PATH_INFO'])
            start_response( "500 Internal Server Error"
                          , [('Content-Type', 'text/plain')]
                           )
            response = ["Server got itself in trouble."]
        else:                                               # app
            response = app(environ, start_response) # WSGI


        log.debug('responding')
        return response


    def get_app(self, environ, start_response):
        """Given a WSGI environ, return the first matching app.
        """

        app = None
        path = match_against = environ['PATH_INFO']
        if not match_against.endswith('/'):
            match_against += '/'

        for app_urlpath, _app in self.apps:

            # Do basic validation.
            # ====================

            if not match_against.startswith(app_urlpath):
                continue
            environ['PATH_TRANSLATED'] = translate(self.root, app_urlpath)
            if not isdir(environ['PATH_TRANSLATED']):
                start_response('404 Not Found', [])
                return ['Resource not found.']


            # Check trailing slash.
            # =====================

            if app_urlpath.endswith('/'): # "please canonicalize"
                if path == app_urlpath[:-1]:
                    response = check_trailing_slash(environ, start_response)
                    assert response is not None # sanity check
                    return response # redirect to trailing slash
                app_urlpath = app_urlpath[:-1] # trailing slash goes in
                                               # PATH_INFO, not SCRIPT_NAME

            # Update environ.
            # ===============

            environ["SCRIPT_NAME"] = app_urlpath
            environ["PATH_INFO"] = path[len(app_urlpath):]

            app = _app
            break

        return app
