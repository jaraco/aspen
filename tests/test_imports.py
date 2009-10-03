
def test_aspen():
    import aspen
    expected = '~~VERSION~~' 
    actual = aspen.__version__
    assert actual == expected, actual

def test_pycurl():
    import pycurl
    expected = '7.19.6' #TODO rather stringent, no?
    actual = pycurl.version_info()[1]
    assert actual == expected, actual

def test_tornado():
    import tornado
    #TODO http://github.com/facebook/tornado/issues/#issue/22
    assert not hasattr(tornado, '__version__') 
