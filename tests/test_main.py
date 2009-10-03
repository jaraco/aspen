import aspen
from multiprocessing import Process

from tornado.httpclient import HTTPClient


class AspenRunning:

    def __enter__(self):
        self.proc = Process(target=aspen.main)
        self.proc.start()

    def __exit__(self, *exc):
        self.proc.terminate() # unclean!
            #TODO: bring over robust proc testing with proc mgmt (daemon, etc.)
        self.proc.join()


def test_greetings_program():
    with AspenRunning():
        client = HTTPClient()
        response = client.fetch('http://localhost:5370/')
        assert response.body == 'Greetings, program!', response.body


