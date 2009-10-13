"""Module for loading objects specified in colon notation.

NB: The Aspen version had better error handling (filename, lineno reporting).

"""
import os
import string


class ColonizeError(StandardError):
    pass

class ColonizeBadColonsError(ColonizeError): pass
class ColonizeBadObjectError(ColonizeError): pass
class ColonizeBadModuleError(ColonizeError): pass


INITIAL = '_' + string.letters
INNER = INITIAL + string.digits
def is_valid_identifier(s):
    """Given a string of length > 0, return a boolean.

        >>> is_valid_identifier('.svn')
        False
        >>> is_valid_identifier('svn')
        True
        >>> is_valid_identifier('_svn')
        True
        >>> is_valid_identifier('__svn')
        True
        >>> is_valid_identifier('123')
        False
        >>> is_valid_identifier('r123')
        True

    """
    try:
        assert s[0] in INITIAL
        assert False not in [x in INNER for x in s]
        return True
    except AssertionError:
        return False


def colonize(name):
    """Given a name in colon notation and some error helpers, return an object.

    The format of name is a subset of setuptools entry_point format: a
    dotted module name, followed by a colon and a dotted identifier naming
    an object within the module.

    """

    if name.count(':') != 1:
        msg = "'%s' is not valid colon notation" % name
        raise ColonizeBadColonsError(msg)

    #modname, objname = name.rsplit(':', 1) -- no rsplit < Python 2.4
    idx = name.rfind(":")
    modname = name[:idx]
    objname = name[idx+1:]

    for _name in modname.split('.'):
        if not is_valid_identifier(_name):
            msg = ( "'%s' is not valid colon notation: " % name
                  + "bad module name '%s'" % _name
                   )
            raise ColonizeBadModuleError(msg)

    exec 'import %s as obj' % modname # may raise ImportError

    for _name in objname.split('.'):
        if not is_valid_identifier(_name):
            msg = ( "'%s' is not valid colon notation: " % name
                  + "bad object name '%s'" % _name
                   )
            raise ColonizeBadObjectError(msg)
        obj = getattr(obj, _name) # may raise AttributeError
    return obj
