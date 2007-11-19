import aspen
from aspen.apps.pub.handlers.static import wsgi as static_handler
from aspen.utils import find_default, translate


def wsgi(environ, start_response):
    """This makes the static handler available as a full-blown application.
    """
    fspath = translate(aspen.paths.docroot, environ['PATH_INFO'])
    fspath = find_default(aspen.server.configuration.defaults, fspath)
    environ['PATH_TRANSLATED'] = fspath
    return static_handler(environ, start_response)
