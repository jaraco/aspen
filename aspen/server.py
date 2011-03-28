#!/usr/bin/env python
import Queue
import diesel
import socket
import threading
import time


# Cooperative
# ===========

def cooperate(conn):

    conn.send('SELECTED ' + data)
    conn.close()


# Blocking
# ========

queue_blocking = Queue.Queue()

def do_work(conn, addr):
    data = conn.recv(1024)
    if data.startswith('CHEESE'):
        conn.setblocking(False)
        app.hub.register(conn, cooperate)
    else:
        conn.send(data)
        conn.close()

def worker():
    while True:
        work = queue_blocking.get()
        do_work(*work)


# Server
# ======

def accept_connections():
    print "accepting connections on 5370"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 5370))
    s.listen(1)
    while 1:
        conn, addr = s.accept()
        queue_blocking.put((conn, addr))

app = None
def main():
    global app

    pool = []
    for i in range(3):
        thread = threading.Thread(None, worker)
        thread.daemon = True
        pool.append(thread)
        thread.start()
    
    master_thread = threading.Thread(None, accept_connections)
    master_thread.daemon = True
    master_thread.start()

    app = diesel.Application()
    app.add_loop(diesel.Loop(cooperate))
    app.run()


if __name__ == '__main__':
    main()

