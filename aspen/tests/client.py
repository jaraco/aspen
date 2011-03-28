#!/usr/bin/env python
import socket
import sys


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('localhost', 5370))
s.send(" ".join(sys.argv[1:]))
data = s.recv(1024)
s.close()
print 'Received', repr(data)
