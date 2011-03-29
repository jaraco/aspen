#!/usr/bin/env python
import sys
import socket
import threading
import time
from Queue import Queue as ThreadQueue

import diesel


def parse_request():
    #rest = receive(9)
    #print rest
    print "HELP!!!"
    yield



# Cooperative
# ===========

def cooperate(data, conn, addr):
    print "now recv the rest of %s" % data
    conn.setblocking(False)
    print "cooperating?"
    c = diesel.Connection(conn, addr)
    print "still cooperating?"
    loop = diesel.Loop(parse_request, addr)
    print "*still* cooperating?"
    loop.connection_stack.append(c)
    print "cooperating now?"
    app.add_loop(loop)


# Blocking
# ========

#thread_queue = ThreadQueue()
#
#def do_work(conn, addr):
#    print "trying to do work"
#    data = conn.recv(1024)
#    print "processing %s" % data
#    if data[0] in 'aeiouy':
#        print "trying to cooperate"
#        cooperate(data, conn, addr)
#    else:
#        conn.send(data)
#        conn.close()
#
#def worker():
#    while True:
#        id = threading.current_thread().ident
#        print "%d trying to find work" % id
#        work = thread_queue.get()
#        print "%d found work" % id
#        do_work(*work)


# Server
# ======

def accept_connections():
    def _thrash():
        print "accepting connections on 5370"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 5370))
        sock.listen(1)
        while True:
            print "trying to accept a connection"
            conn, addr = sock.accept()
            data = conn.recv(1)
            print "sending %s work to cooperate" % data
            cooperate(data, conn, addr)
            #thread_queue.put((conn, addr))
    try:
        _thrash()
    except:
        import traceback
        traceback.print_exc()
        print 0
        for i in range(20):
            sys.stdout.write("\rrestarting in %2d" % (20 - i))
            sys.stdout.flush()
            time.sleep(1)
        raise SystemExit

app = None
def main():
    global app

    #pool = []
    #for i in range(1):
    #    thread = threading.Thread(None, worker)
    #    thread.daemon = True
    #    pool.append(thread)
    #    thread.start()
    
    master_thread = threading.Thread(None, accept_connections)
    master_thread.daemon = True
    master_thread.start()
    
    app = diesel.Application()
    app.run()


if __name__ == '__main__':
    main()

