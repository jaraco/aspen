class Version(tuple):
    def __init__(self, version):
        self.raw = version
        if version == '':
            t = (0, 9)
        elif not version.startswith('HTTP/'):
            raise Response(400)
        else:
            version = version[len('HTTP/'):]
            if version not in ('0.9', '1.0', '1.1'):
                # http://w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.5.6
                raise Response(505, "We support HTTP/0.9, HTTP/1.0, and "
                                    "HTTP/1.1")
            t = [int(x) for x in version.split('.')]
        tuple.__init__(self, t) 
