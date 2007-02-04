

from paste.deploy import loadapp
from aspen import conf

config=conf.pylons.get( 'inifile', None )

if not config:
    raise ValueError('configure me!')

pylons_app = loadapp('config:'+config)