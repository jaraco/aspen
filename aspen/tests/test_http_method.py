from aspen.http.method import Method


def test_method_is_uppercased():
    actual = Method('foo')
    import pdb; pdb.set_trace()
    expected = u"FOO"
    assert actual == expected, actual
