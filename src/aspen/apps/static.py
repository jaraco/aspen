"""Define a static publication application.

Use this to serve static files when you don't need the handlers.conf behavior.

"""
import logging
from os.path import exists

from aspen import configuration
from aspen.handlers.static import static as static_handler
from aspen.utils import find_default, translate


log = logging.getLogger('aspen.apps.static')

def static(environ, start_response):
    log.debug('called')
    environ['PATH_TRANSLATED'] = translate( environ['PATH_TRANSLATED']
                                          , environ['PATH_INFO']
                                           )
    fspath = find_default(configuration.defaults, environ)
    if not exists(fspath) or fspath.endswith('README.aspen'):
        start_response('404 Not Found', [])
        log.debug('responding with 404')
        return ['Resource not found.']
    log.debug('responding')
    return static_handler(environ, start_response)
