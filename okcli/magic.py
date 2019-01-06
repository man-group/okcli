import logging

import sql.connection
import sql.parse

from .main import OCli

_logger = logging.getLogger(__name__)


def load_ipython_extension(ipython):

    # This is called via the ipython command '%load_ext okcli.magic'.

    # First, load the sql magic if it isn't already loaded.
    if not ipython.find_line_magic('sql'):
        ipython.run_line_magic('load_ext', 'sql')

    # Register our own magic.
    ipython.register_magic_function(okcli_line_magic, 'line', 'okcli')


def okcli_line_magic(line):
    _logger.debug('okcli magic called: %r', line)
    parsed = sql.parse.parse(line, {})
    conn = sql.connection.Connection.get(parsed['connection'])

    try:
        # A corresponding okcli object already exists
        okcli = conn._okcli
        _logger.debug('Reusing existing okcli')
    except AttributeError:
        okcli = OCli()
        u = conn.session.engine.url
        _logger.debug('New okcli: %r', str(u))

        okcli.connect(u.database, u.host, u.username, u.password)
        conn._okcli = okcli

    # For convenience, print the connection alias
    print('Connected: {}'.format(conn.name))

    try:
        okcli.run_cli()
    except SystemExit:
        pass

    if not okcli.query_history:
        return

    q = okcli.query_history[-1]
    if q.mutating:
        _logger.debug('Mutating query detected -- ignoring')
        return

    if q.successful:
        ipython = get_ipython()
        return ipython.run_cell_magic('sql', line, q.query)

