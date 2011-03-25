class Method(unicode):
    def __init__(self, bytes):
        """Given a bytestring, save that to raw and store uppercased unicode.
        """
        import pdb; pdb.set_trace()
        #assert type(bytes) is str, TypeError("Method only takes an ASCII "
        #                                     "bytestring")
        self.raw = bytes
        super(Method, self).__init__('FOO')
        #unicode.__init__(self, 'FOO') # self.raw.decode('ASCII').upper())
