"""Define a handler that interprets files as Python scripts, with caching.

WARNING: EXPERIMENTAL

"""
from aspen import cache


class _PyScript(object):
    __metaclass__ = cache.CacherClass
    # to be done

def pyscript(environ, start_response):
    raise NotImplementedError # NOT WORKING YET!
    _c = cache.ModuleCache(max_size=128) #@@ MUST talk with config!!!
    return _PyScript(environ, start_response, cacher=_c)
