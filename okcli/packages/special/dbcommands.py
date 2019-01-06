import logging
import os
import platform

from okcli import __version__
from okcli.packages.special import iocommands
from okcli.packages.special.utils import format_uptime

from .main import PARSED_QUERY, RAW_QUERY, special_command

log = logging.getLogger(__name__)


DATABASES_QUERY = '''select distinct(owner) from all_tables'''
TABLES_QUERY = '''select distinct(table_name) from all_tab_cols where owner=upper(:1) '''
VERSION_QUERY = '''select * from V$VERSION'''
VERSION_COMMENT_QUERY = '''select * from V$VERSION'''
USERS_QUERY = '''select username from all_users'''
FUNCTIONS_QUERY = '''select object_name from ALL_OBJECTS where owner=:1 and object_type in ('FUNCTION','PROCEDURE')'''
ALL_TABLE_COLUMNS_QUERY = '''select table_name, column_name from all_tab_cols where owner=:1'''
COLUMNS_QUERY = '''select column_name, data_type, data_length, nullable from all_tab_cols where owner=:1 and table_name=:2 '''
CONNECTION_ID_QUERY = '''select sys_context('USERENV', 'SID') from dual'''
CURRENT_SCHEMA_QUERY = '''select sys_context('USERENV', 'CURRENT_SCHEMA') from dual'''
PRIMARY_KEY_QUERY = '''select  column_name as PRIMARY_KEY_COLUMNS from all_constraints ac inner join all_cons_columns acc on ac.table_name=acc.table_name and acc.constraint_name=ac.constraint_name where ac.table_name=:1 and ac.owner=:2 and ac.constraint_type='P' '''
FOREIGN_KEY_QUERY = '''SELECT ACC2.COLUMN_NAME, concat(ACC.TABLE_NAME, concat('.', ACC.COLUMN_NAME )) as FOREIGN_KEY_CONSTRAINT
   FROM (SELECT TABLE_NAME, CONSTRAINT_NAME, R_CONSTRAINT_NAME, CONSTRAINT_TYPE FROM ALL_CONSTRAINTS) AC,
        (SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME FROM ALL_CONS_COLUMNS) ACC,
        (SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME FROM ALL_CONS_COLUMNS) ACC2
   WHERE AC.R_CONSTRAINT_NAME = ACC.CONSTRAINT_NAME
     AND AC.CONSTRAINT_NAME = ACC2.CONSTRAINT_NAME
     AND AC.constraint_type = 'R' and AC.TABLE_NAME=:1
   ORDER BY 1,2'''

def _fetch_all(cursor, sql_query, params):
    """Execute a query fetch all of the results.

    Paramters
    ---------
    cursor: `cx_Oracle.Cursor`
    sql_query: `str`
    params: `tuple`

    Returns
    -------
    list[tuple]
    Rows and headers.
    """
    log.debug(sql_query)
    cursor.execute(sql_query, params)
    rows = cursor.fetchall()
    status = ''

    if cursor.description:
        headers = [x[0] for x in cursor.description]
        return [(None, rows, headers, status)]
        
    else:
        return [(None, None, None, '')]



def _resolve_table(cur, table_desc):
    """Find out the connection's current schema.
    
    Parameters
    ----------
    cur: `cx_Oracle.Cursor`
    table_desc: `str`

    Returns
    -------
    (str, str)
    Current schema and table-name.
    """

    table_desc = table_desc.upper()
    table_tokens = table_desc.split('.', 1)

    if len(table_tokens) == 2:
        return table_tokens  # schema and table

    # get the current schema
    log.debug(CURRENT_SCHEMA_QUERY)
    cur.execute(CURRENT_SCHEMA_QUERY)
    current_schema = cur.fetchall()[0][0]

    return current_schema, table_desc


@special_command('describe', 'desc[+] [schema.table]', 'describe table.',
                 arg_type=PARSED_QUERY, case_sensitive=False, aliases=['desc'])
def describe(cur, arg, arg_type=PARSED_QUERY, verbose=True):
    """Special command for show column-named and types for a  given table.

    Returns
    -------
    generator[tuple]
    Table description, primary-keys and foreign keys.
    """
    schema, table = _resolve_table(cur, arg)
    
    description = _fetch_all(cur, COLUMNS_QUERY, (schema, table))[0]
    yield description
    primary_key = _fetch_all(cur, PRIMARY_KEY_QUERY, (table, schema))[0]
    yield primary_key
    foreign_keys = _fetch_all(cur, FOREIGN_KEY_QUERY, (table, ))[0]
    yield foreign_keys
    raise StopIteration


@special_command('show [schema]', 'show [schema]', 'List all the visible tables in schema.', arg_type=PARSED_QUERY, case_sensitive=False, aliases=['show'])
def describe(cur, arg, arg_type=PARSED_QUERY, verbose=True):
    """Special command for show all the tables in a given schema.

    Returns
    -------
    list[tuple]
    table names in schema.

    """
    return _fetch_all(cur, TABLES_QUERY, (arg,))


@special_command('list', '\\l', 'List databases.', arg_type=RAW_QUERY, case_sensitive=True)
def list_databases(cur, **_):
    """Special command for show all the schemas that the user can read.

    Returns
    -------
    list[tuple]
    schema names available to user.

    """
    return _fetch_all(cur, DATABASES_QUERY, ())


def status(cur, **_):
    query = 'SHOW GLOBAL STATUS;'
    log.debug(query)
    cur.execute(query)
    status = dict(cur.fetchall())

    query = 'SHOW GLOBAL VARIABLES;'
    log.debug(query)
    cur.execute(query)
    variables = dict(cur.fetchall())

    # Create output buffers.
    title = []
    output = []
    footer = []

    title.append('--------------')

    # Output the okcli client information.
    implementation = platform.python_implementation()
    version = platform.python_version()
    client_info = []
    client_info.append('okcli {0},'.format(__version__))
    client_info.append('running on {0} {1}'.format(implementation, version))
    title.append(' '.join(client_info) + '\n')

    # Build the output that will be displayed as a table.
    output.append(('Connection id:', cur.connection.thread_id()))

    query = 'SELECT DATABASE(), USER();'
    log.debug(query)
    cur.execute(query)
    db, user = cur.fetchone()
    if db is None:
        db = ''

    output.append(('Current database:', db))
    output.append(('Current user:', user))

    if iocommands.is_pager_enabled():
        if 'PAGER' in os.environ:
            pager = os.environ['PAGER']
        else:
            pager = 'System default'
    else:
        pager = 'stdout'
    output.append(('Current pager:', pager))

    output.append(('Server version:', '{0} {1}'.format(
        variables['version'], variables['version_comment'])))
    output.append(('Protocol version:', variables['protocol_version']))

    if 'unix' in cur.connection.host_info.lower():
        host_info = cur.connection.host_info
    else:
        host_info = '{0} via TCP/IP'.format(cur.connection.host)

    output.append(('Connection:', host_info))

    query = ('SELECT @@character_set_server, @@character_set_database, '
             '@@character_set_client, @@character_set_connection LIMIT 1;')
    log.debug(query)
    cur.execute(query)
    charset = cur.fetchone()
    output.append(('Server characterset:', charset[0]))
    output.append(('Db characterset:', charset[1]))
    output.append(('Client characterset:', charset[2]))
    output.append(('Conn. characterset:', charset[3]))

    if not 'TCP/IP' in host_info:
        output.append(('UNIX socket:', variables['socket']))

    output.append(('Uptime:', format_uptime(status['Uptime'])))

    # Print the current server statistics.
    stats = []
    stats.append('Connections: {0}'.format(status['Threads_connected']))
    stats.append('Queries: {0}'.format(status['Queries']))
    stats.append('Slow queries: {0}'.format(status['Slow_queries']))
    stats.append('Opens: {0}'.format(status['Opened_tables']))
    stats.append('Flush tables: {0}'.format(status['Flush_commands']))
    stats.append('Open tables: {0}'.format(status['Open_tables']))
    queries_per_second = int(status['Queries']) / int(status['Uptime'])
    stats.append('Queries per second avg: {:.3f}'.format(queries_per_second))
    stats = '  '.join(stats)
    footer.append('\n' + stats)

    footer.append('--------------')
    return [('\n'.join(title), output, '', '\n'.join(footer))]

