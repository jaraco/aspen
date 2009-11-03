import os

from tornado.web import HTTPError, RequestHandler


class SimpleHandler(RequestHandler):
    """This is a bare bones handler. It naively serves files from ./www/.
    """

    def get(self):
        docroot = os.path.join(self.application.configuration.root, 'www')
        fspath = os.path.join(docroot, self.request.path[1:])
        if os.path.isdir(fspath):
            fspath = os.path.join(fspath, 'index.html')
        if os.path.isfile(fspath):
            self.write(open(fspath).read())
        else:
            raise HTTPError(404)

    post = put = delete = head = get

