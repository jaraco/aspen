#static
from aspen.handlers import *


class _Static( object ):
    __metaclass__= cache.CacherClass

    # Any wsgi wep app must be a callable that accepts \
    #at least environ dict and start_response callable and
    #its result must be iterable

    # However, python class objects  are callables, because, by default,
    #type metaclass has __call__ defined; therefore, if the class object
    #itself has __iter__ and its __init__ accepts the same arguments (i.e., environ
    #and start_response), one can employ class object as wsgi.

    # Indeed, _Static callable (which happens to be a class) accepts environ, start_response;
    #when one calls _Static, it results in an iterable (that happens to be its instance), just
    #as was required by the wsgi spec.

    # One has to note that this is a pretty common praxis. See, e.g., the PEP333
    #itself, http://www.python.org/dev/peps/pep-0333/ and
    #Colubrid source code: http://wsgiarea.pocoo.org/colubrid/
    
       
    
    def __init__( self, environ, start_response, **kw): 
        self.__env = environ
        self.__sr = start_response
        assert isfile(environ['PATH_TRANSLATED'])
        
    def __iter__( self ):
        key = self.__env['PATH_TRANSLATED']
        ims = self.__env.get('HTTP_IF_MODIFIED_SINCE', '')
        status='200 OK'
        stats = os.stat(key)
        mtime = stats[stat.ST_MTIME]
        size = stats[stat.ST_SIZE]
        content_type = mimetypes.guess_type(key)[0] or 'text/plain'
        if mode.stprod:
            if ims:
                mod_since = rfc822.parsedate(ims)
                last_modified = time.gmtime(mtime)
                if last_modified[:6] <= mod_since[:6]:
                    status = '304 Not Modified'
        headers = []
        headers.append(('Last-Modified', rfc822.formatdate(mtime)))
        headers.append(('Content-Type', content_type))
        headers.append(('Content-Length', str(size)))
        self.__sr(status, headers)
        if status == '304 Not Modified':
            yield []
        else:
            yield self._fc[key]

_cache = None

def static( environ, start_response ):
    global _cache
    if _cahce is None:        
        _cache = cahce.FileCache( max_size=aspen.conf.cache.get('max_size',128), mode='rb' )
    return _Static(environ, start_response, cahcer=_cache)