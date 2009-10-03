
def test_aspen():
    import aspen
    assert aspen.__version__ == '~~VERSION~~'

def test_pycurl():
    import pycurl
    assert pycurl.version_info()[1] == '7.19.6'

def test_tornado():
    import tornado
    #TODO http://github.com/facebook/tornado/issues/#issue/22
    assert not hasattr(tornado, '__version__') 
