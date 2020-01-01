import logging

import sql.connection
import sql.parse

from okcli.main import OCli, parse_sqlplus_arg

_logger = logging.getLogger(__name__)
_okcli = OCli(prompt=OCli.default_prompt) 


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
    if _okcli.sqlexecute is None: 
        username, password, host  = parse_sqlplus_arg(line.strip())
        database=''
        _okcli.connect(database=database, host=host, user=username, passwd=password)
        _okcli.url = to_url(username, password, host) 

        # For convenience, print the connection alias
        print('Connected to: {}'.format(host))

    try:
        _okcli.run_cli()
    except SystemExit:
        pass

    if not _okcli.query_history:
        return

    q = _okcli.query_history[-1]
    if q.mutating:
        _logger.debug('Mutating query detected -- ignoring')
        return

    if q.successful:
        ipython = get_ipython()
        return ipython.run_cell_magic('sql', _okcli.url, q.query)

def to_url(username, password, dsn):
    return 'oracle+cx_oracle://{}:{}@{}'.format(username, password, dsn)
