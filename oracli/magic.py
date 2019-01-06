import logging

import sql.connection
import sql.parse

from .main import OraCli

_logger = logging.getLogger(__name__)


def load_ipython_extension(ipython):

    # This is called via the ipython command '%load_ext oracli.magic'.

    # First, load the sql magic if it isn't already loaded.
    if not ipython.find_line_magic('sql'):
        ipython.run_line_magic('load_ext', 'sql')

    # Register our own magic.
    ipython.register_magic_function(oracli_line_magic, 'line', 'oracli')


def oracli_line_magic(line):
    _logger.debug('oracli magic called: %r', line)
    parsed = sql.parse.parse(line, {})
    conn = sql.connection.Connection.get(parsed['connection'])

    try:
        # A corresponding oracli object already exists
        oracli = conn._oracli
        _logger.debug('Reusing existing oracli')
    except AttributeError:
        oracli = OraCli()
        u = conn.session.engine.url
        _logger.debug('New oracli: %r', str(u))

        oracli.connect(u.database, u.host, u.username, u.password)
        conn._oracli = oracli

    # For convenience, print the connection alias
    print('Connected: {}'.format(conn.name))

    try:
        oracli.run_cli()
    except SystemExit:
        pass

    if not oracli.query_history:
        return

    q = oracli.query_history[-1]
    if q.mutating:
        _logger.debug('Mutating query detected -- ignoring')
        return

    if q.successful:
        ipython = get_ipython()
        return ipython.run_cell_magic('sql', line, q.query)

