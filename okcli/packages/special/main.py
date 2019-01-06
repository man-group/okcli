import logging
import re
from collections import namedtuple

log = logging.getLogger(__name__)

NO_QUERY = 0
PARSED_QUERY = 1
RAW_QUERY = 2
STORED_PROC_STMT =3

SpecialCommand = namedtuple('SpecialCommand',
                            ['handler', 'command', 'shortcut', 'description', 'arg_type', 'hidden',
                             'case_sensitive'])
COMMANDS = {}

STORED_PROC_REGEX = '\s*exec\s+([\w,.]+)(\(.*\))?\s*;?\s*'

class CommandNotFound(Exception):
    pass


def parse_special_command(sql):
    command, _, arg = sql.partition(' ')
    verbose = '+' in command
    command = command.strip().replace('+', '')
    return (command, verbose, arg.strip())


def special_command(command, shortcut, description, arg_type=PARSED_QUERY,
                    hidden=False, case_sensitive=False, aliases=()):
    def wrapper(wrapped):
        register_special_command(wrapped, command, shortcut, description,
                                 arg_type, hidden, case_sensitive, aliases)
        return wrapped
    return wrapper


def register_special_command(handler, command, shortcut, description,
                             arg_type=PARSED_QUERY, hidden=False, case_sensitive=False, aliases=()):
    cmd = command.lower() if not case_sensitive else command
    COMMANDS[cmd] = SpecialCommand(handler, command, shortcut, description,
                                   arg_type, hidden, case_sensitive)
    for alias in aliases:
        cmd = alias.lower() if not case_sensitive else alias
        COMMANDS[cmd] = SpecialCommand(handler, command, shortcut, description,
                                       arg_type, case_sensitive=case_sensitive,
                                       hidden=True)


def execute(cur, sql):
    """Execute a special command and return the results. If the special command
    is not supported a KeyError will be raised.
    """
    command, verbose, arg = parse_special_command(sql)

    if (command not in COMMANDS) and (command.lower() not in COMMANDS):
        raise CommandNotFound

    try:
        special_cmd = COMMANDS[command]
    except KeyError:
        special_cmd = COMMANDS[command.lower()]
        if special_cmd.case_sensitive:
            raise CommandNotFound('Command not found: %s' % command)
    # "help <SQL KEYWORD> is a special case. We want built-in help, not
    # okcli help here.
    if command == 'help' and arg:
        return show_keyword_help(cur=cur, arg=arg)
    if special_cmd.arg_type == STORED_PROC_STMT:
        return execute_stored_proc(cur, sql)
    if special_cmd.arg_type == NO_QUERY:
        return special_cmd.handler()
    elif special_cmd.arg_type == PARSED_QUERY:
        return special_cmd.handler(cur=cur, arg=arg, verbose=verbose)
    elif special_cmd.arg_type == RAW_QUERY:
        return special_cmd.handler(cur=cur, query=sql)


def _sql_to_stored_proc_cursor_args(sql):
    """Convert a sql statement that calls a  stored-proc into the 
    arguments for cx_Oracle.

    eg. "exec my_schema.my_stored_proc(arg1, 'arg2')"
    ->
    (my_schema.my_stored_proc, (arg1, 'arg2'))

    Paramters
    ---------
    sql: `str`
    
    Returns
    -------
    (str, tuple)
        The stored-proc name and its args.
    """
    match = re.match(STORED_PROC_REGEX, sql)
    if match is None:
        raise ValueError('Invalid stored-proc command "{}"'.format(sql))
    # get the name
    name_start, name_end = match.span(1)
    stored_proc_name = sql[name_start: name_end]

    # get the params if there are any
    has_args = match.span(2) != (-1, -1)
    if has_args:
        args_start, args_end = match.span(2)
        args_s = sql[args_start: args_end]
        stored_proc_params = eval(args_s)
        if not isinstance(stored_proc_params, tuple):
            stored_proc_params = (stored_proc_params,)
    else:
        stored_proc_params = ()

    return stored_proc_name, stored_proc_params


@special_command('exec', 'exec stored_proc_name(args)', description='Execute a stored-procedure.', arg_type=STORED_PROC_STMT)
def execute_stored_proc(cursor, sql):
    """Execute a stored-procedure.
    
    Parameters
    ----------
    cursor: `OracleCursor`
    sql: `str`
        stored-proc sql statement.
    """
    stored_proc_name, stored_proc_args = _sql_to_stored_proc_cursor_args(sql)
    status = cursor.callproc(stored_proc_name, parameters=stored_proc_args)
    status = '\n'.join(status)
    return [(None, None, None, status)]


@special_command('help', '\\?', 'Show this help.', arg_type=NO_QUERY, aliases=('\\?', '?'))
def show_help():  # All the parameters are ignored.
    headers = ['Command', 'Shortcut', 'Description']
    result = []

    for _, value in sorted(COMMANDS.items()):
        if not value.hidden:
            result.append((value.command, value.shortcut, value.description))
    return [(None, result, headers, None)]


def show_keyword_help(cur, arg):
    """
    Call the built-in "show <command>", to display help for an SQL keyword.
    :param cur: cursor
    :param arg: string
    :return: list
    """
    keyword = arg.strip('"').strip("'")
    query = "help '{0}'".format(keyword)
    log.debug(query)
    cur.execute(query)
    if cur.description and cur.rowcount > 0:
        headers = [x[0] for x in cur.description]
        return [(None, cur, headers, '')]
    else:
        return [(None, None, None, 'No help found for {0}.'.format(keyword))]


@special_command('exit', '\\q', 'Exit.', arg_type=NO_QUERY, aliases=('\\q', ))
@special_command('quit', '\\q', 'Quit.', arg_type=NO_QUERY)
def quit(*_args):
    raise EOFError

@special_command('ed', 'ed [filename]', 'Edit command with editor (uses $EDITOR).',
                 arg_type=NO_QUERY, case_sensitive=True)
def stub():
    raise NotImplementedError


