import logging

from aspen import colon, utils
from aspen.exceptions import *


log = logging.getLogger('aspen.apps.pub')

SPACE = ' '
TAB = '\t'
DEFAULT_HANDLERS_CONF = """\

    catch_all   aspen.rules:catch_all

    [aspen.handlers.static:wsgi]
      catch_all

"""


class Handler(object):
    """Represent a function that knows how to obey the rules.

    Some optimization ideas:

      - cache the results of match()
      - evaluate the expression after each rule is added, exit early if False
      - um, write it in C? :)
      - index this in dewey

    """

    handle = None # the actual callable we are tracking
    _rules = None # a list containing the rules
    _funcs = None # a mapping of rulenames to rulefuncs
    _name = '' # the name of the callable

    def __init__(self, rulefuncs, handle):
        """Takes a mapping of rulename to rulefunc, and a WSGI callable.
        """
        self._funcs = rulefuncs
        self.handle = handle

    def __str__(self):
        return "<%s>" % repr(self.handle)
    __repr__ = __str__

    def __eq__(self, other):
        """This is mostly here to ease testing.
        """
        try:
            assert utils.cmp_routines(self.handle, other.handle)
            assert self._rules == other._rules
            assert sorted(self._funcs.keys()) == sorted(other._funcs.keys())
            for k,v in self._funcs.items():
                assert utils.cmp_routines(v, other._funcs[k])
            return True
        except AssertionError:
            return False


    def add(self, rule, lineno):
        """Given a rule string, add it to the rules for this handler.

        The rules are stored in self._rules, the first item of which is a
        two-tuple: (rulename, predicate); subsequent items are three-tuples:
        (boolean, rulename, predicate).

            boolean -- one of 'and', 'or', 'and not'. Any NOT in the conf file
                       becomes 'and not' here.

            rulename -- a name defined in the first (anonymous) section of
                        handlers.conf; maps to a rule callable in self._funcs

            predicate -- a string that is meaningful to the rule callable

        lineno is for error handling.

        """

        # Tokenize and get the boolean
        # ============================

        if self._rules is None:                 # no rules yet
            self._rules = []
            parts = rule.split(None, 1)
            if len(parts) not in (1, 2):
                msg = "need one or two tokens in '%s'" % rule
                raise HandlersConfError(msg, lineno)
            parts.reverse()
            boolean = None
        else:                                   # we have at least one rule
            parts = rule.split(None, 2)
            if len(parts) not in (2,3):
                msg = "need two or three tokens in '%s'" % rule
                raise HandlersConfError(msg, lineno)

            parts.reverse()
            orig = parts.pop()
            boolean = orig.lower()
            if boolean not in ('and', 'or', 'not'):
                msg = "bad boolean '%s' in '%s'" % (orig, rule)
                raise HandlersConfError(msg, lineno)
            boolean = (boolean == 'not') and 'and not' or boolean


        # Get the rulename and predicate
        # ==============================

        rulename = parts.pop()
        if rulename not in self._funcs:
            msg = "no rule named '%s'" % rulename
            raise HandlersConfError(msg, lineno)
        predicate = parts and parts.pop() or None
        assert len(parts) == 0 # for good measure


        # Package up and store
        # ====================

        if boolean is None:
            _rule = (rulename, predicate)
        else:
            _rule = (boolean, rulename, predicate)

        if _rule in self._rules:
            log.info("duplicate handlers rule: %s [line %d]" % (rule, lineno))
        else:
            self._rules.append(_rule)


    def match(self, pathname):
        """Given a full pathname, return a boolean.

        I thought of allowing rules to return arbitrary values that would then
        be passed along to the handlers. Basically this was to support routes-
        style regular expression matching, but that is an application use case,
        and handlers are specifically not for applications but publications.

        """
        if not self._rules: # None or []
            raise HandlerError, "no rules to match"

        rulename, predicate = self._rules[0]                    # first
        expressions = [str(self._funcs[rulename](pathname, predicate))]

        for boolean, rulename, predicate in self._rules[1:]:    # subsequent
            result = bool(self._funcs[rulename](pathname, predicate))
            expressions.append('%s %s' % (boolean, result))

        expression = ' '.join(expressions)
        return eval(expression) # e.g.: True or False and not True


def load_handlers():
    """Return a list of Handler instances.
    """

    # Find a config file to parse.
    # ============================

    user_conf = False
    if aspen.paths.__ is not None:
        path = join(aspen.paths.__, 'etc', 'handlers.conf')
        if isfile(path):
            user_conf = True

    if user_conf:
        fp = open(path)
        fpname = fp.name
    else:
        log.info("No handlers configured; using defaults.")
        fp = cStringIO.StringIO(DEFAULT_HANDLERS_CONF)
        fpname = '<default>'


    # We have a config file; proceed.
    # ===============================
    # The conditions in the loop below are not in the order found in the
    # file, but are in the order necessary for correct processing.

    rulefuncs = {} # a mapping of function names to rule functions
    handlers = [] # a list of Handler objects
    handler = None # the Handler we are currently processing
    lineno = 0

    for line in fp:
        lineno += 1
        line = utils.clean(line)
        if not line:                            # blank line
            continue
        elif line.startswith('['):              # new section
            if not line.endswith(']'):
                raise HandlersConfError("missing end-bracket", lineno)
            if not rulefuncs:
                raise HandlersConfError("no rules specified yet", lineno)
            name = line[1:-1]
            obj = colon.colonize(name, fpname, lineno)
            if inspect.isclass(obj):
                obj = obj(self) #### @@: PRETTY CLEVER, CHAD!!!!!!!
            if not callable(obj):
                msg = "'%s' is not callable" % name
                raise HandlersConfError(msg, lineno)
            handler = Handler(rulefuncs, obj)
            handlers.append(handler)
            continue
        elif handler is None:                   # anonymous section
            if (SPACE not in line) and (TAB not in line):
                msg = "malformed line (no whitespace): '%s'" % line
                raise HandlersConfError(msg, lineno)
            rulename, name = line.split(None, 1)
            obj = colon.colonize(name, fpname, lineno)
            if not callable(obj):
                msg = "'%s' is not callable" % name
                raise HandlersConfError(msg, lineno)
            rulefuncs[rulename] = obj
        else:                                   # named section
            handler.add(line, lineno)

    return handlers



def get_handler(self, pathname):
    """Given a full pathname, return the first matching handler.
    """
    for handler in aspen.configuration.handlers:
        if handler.match(pathname):
            return handler

    log.warn("No handler found for filesystem path '%s'" % pathname)
    raise HandlerError("No handler found.")


    # Translate the request to the filesystem.
    # ========================================

    hide = False
    fspath = translate(self.configuration.paths.docroot, environ['PATH_INFO'])
    environ['PATH_TRANSLATED'] = fspath


    elif not exists(fspath):                            # 404 NOT FOUND
        start_response('404 Not Found', [])
        response = ['Resource not found.']


    # Dispatch to a handler.
    # ======================

    response = check_trailing_slash(environ, start_response)
    if response is None: # no redirection
        fspath = find_default(self.configuration.defaults, fspath)
        environ['PATH_TRANSLATED'] = fspath
        handler = self.get_handler(fspath)
        response = handler.handle(environ, start_response) # WSGI

