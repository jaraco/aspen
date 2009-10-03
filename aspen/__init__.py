from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler


__version__ = '~~VERSION~~'



class SimplateHandler(RequestHandler):

    def get(self):
        """Serve the request by processing a simplate.
        """
        self.write('Greetings, program!')

    post = get

 
def main():
    app = Application([('^.*$', SimplateHandler)])
    server = HTTPServer(app)
    server.listen(5370)
    loop = IOLoop.instance()
    loop.start()
