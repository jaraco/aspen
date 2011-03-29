#!/usr/bin/env python
import socket
import string
import sys
import threading
import time
import random


def gentokens():
    yield "baby"
    yield "adam"
    while True:
        yield ''.join(random.sample(string.lowercase, 10))
tokens = gentokens()

def hit(expected):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', 5370))
    s.send(expected)
    actual = s.recv(1024)
    s.close()
    assert actual == expected, actual
    print actual

def loop():
    while True:
        token = tokens.next()
        hit(token)
        time.sleep(random.random())

def main():
    for i in range(3):
        t = threading.Thread(None, loop)
        t.daemon = True
        t.start()

    while True:
        time.sleep(1)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        hit(' '.join(sys.argv[1:]))
    else:
        try:
            main()
        except KeyboardInterrupt:
            pass

