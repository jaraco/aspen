import sys


# Set for use in aspen.configuration.
__version__ = '~~VERSION~~'
WINDOWS = 'win32' in sys.platform


from aspen.configuration import Configuration, ConfigurationError, usage

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler




class SimplateHandler(RequestHandler):

    def get(self):
        """Serve the request by processing a simplate.
        """
        self.write('Greetings, program!')

    post = get





 
def main(argv=None):
    if argv is None:
        argv = sys.argv


    #TODO make configuration available down in simplates? E.g.:
    # config.paths.root
    try:
        configuration = Configuration(argv)
    except ConfigurationError, err:
        print >> sys.stderr, usage
        print >> sys.stderr, err.msg
        sys.exit(2)


    app = Application([('^.*$', SimplateHandler)])
    server = HTTPServer(app)
    server.listen(configuration.address[1]) #TODO what about AF_UNIX?
    loop = IOLoop.instance()
    loop.start()
