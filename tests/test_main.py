from multiprocessing import Process

import aspen
from tornado.httpclient import HTTPClient


class AspenRunning:

    def __enter__(self):
        #TODO can't use Process here, because it is not designed for tweaking
        # cli args. So we call aspen.main with nosetext -sx args and Conf 
        # breaks.
        self.proc = Process(target=aspen.main)
        self.proc.start()

    def __exit__(self, *exc):
        self.proc.terminate() # unclean!
            #TODO: bring over robust proc testing with proc mgmt (daemon, etc.)
            # would be swell to update that for multiprocessing?
            # nah, leave it with subprocess for usage on < 2.6
        self.proc.join()


def test_greetings_program():
    with AspenRunning():
        client = HTTPClient()
        response = client.fetch('http://localhost:5370/')
        assert response.body == 'Greetings, program!', response.body


