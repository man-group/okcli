from __future__ import print_function, unicode_literals

import logging
import os
import os.path
import sys
import threading
import traceback
from collections import namedtuple
from datetime import datetime
from io import open
from random import choice
from time import time

import click
from pygments.token import Token

import okcli.packages.special as special
import sqlparse
from cli_helpers.tabular_output import TabularOutputFormatter
from prompt_toolkit import AbortAction, Application, CommandLineInterface
from prompt_toolkit.document import Document
from prompt_toolkit.enums import DEFAULT_BUFFER, EditingMode
from prompt_toolkit.filters import Always, HasFocus, IsDone
from prompt_toolkit.history import FileHistory
from prompt_toolkit.interface import AcceptAction
from prompt_toolkit.layout.processors import (ConditionalProcessor,
                                              HighlightMatchingBracketProcessor)
from prompt_toolkit.shortcuts import create_eventloop, create_prompt_layout

from .__init__ import __version__
from .clibuffer import CLIBuffer
from .clistyle import style_factory
from .clitoolbar import create_toolbar_tokens_func
from .completion_refresher import CompletionRefresher
from .config import (read_config_files, str_to_bool,
                     write_default_config)
from .encodingutils import utf8tounicode
from .key_bindings import okcli_bindings
from .lexer import OracleLexer
from .packages.special.main import NO_QUERY
from .sqlcompleter import SQLCompleter
from .sqlexecute import SQLExecute

click.disable_unicode_literals_warning = True
try:
    from urlparse import urlparse
    FileNotFoundError = OSError
except ImportError:
    from urllib.parse import urlparse


# Query tuples are used for maintaining history
Query = namedtuple('Query', ['query', 'successful', 'mutating'])

PACKAGE_ROOT = os.path.abspath(os.path.dirname(__file__))

# no-op logging handler


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


class OCli(object):

    default_prompt = '\\t \\u@\\h:\\d> '
    max_len_prompt = 45
    defaults_suffix = None

    # In order of being loaded. Files lower in list override earlier ones.
    cnf_files = [
        '~/login.conf',
    ]

    system_config_files = [
    ]

    default_config_file = os.path.join(PACKAGE_ROOT, 'okclirc')

    def __init__(self, sqlexecute=None, prompt=None,
                 logfile=None, defaults_suffix=None, defaults_file=None,
                 login_path=None, auto_vertical_output=False, warn=None,
                 okclirc="~/.okclirc"):
        self.sqlexecute = sqlexecute
        self.logfile = logfile
        self.defaults_suffix = defaults_suffix
        self.login_path = login_path

        # self.cnf_files is a class variable that stores the list of oracle
        # config files to read in at launch.
        # If defaults_file is specified then override the class variable with
        # defaults_file.
        if defaults_file:
            self.cnf_files = [defaults_file]

        # Load config.
        config_files = ([self.default_config_file] + self.system_config_files +
                        [okclirc])
        c = self.config = read_config_files(config_files)
        self.multi_line = c['main'].as_bool('multi_line')
        self.key_bindings = c['main']['key_bindings']
        special.set_timing_enabled(c['main'].as_bool('timing'))
        self.formatter = TabularOutputFormatter(
            format_name=c['main']['table_format'])
        self.syntax_style = c['main']['syntax_style']
        self.cli_style = c['colors']
        self.wider_completion_menu = c['main'].as_bool('wider_completion_menu')
        c_ddl_warning = c['main'].as_bool('ddl_warning')
        self.ddl_warning = c_ddl_warning if warn is None else warn
        self.login_path_as_host = c['main'].as_bool('login_path_as_host')

        # read from cli argument or user config file
        self.auto_vertical_output = auto_vertical_output or \
            c['main'].as_bool('auto_vertical_output')

        # Write user config if system config wasn't the last config loaded.
        if c.filename not in self.system_config_files:
            write_default_config(self.default_config_file, okclirc)

        # audit log
        if self.logfile is None and 'audit_log' in c['main']:
            try:
                self.logfile = open(os.path.expanduser(c['main']['audit_log']), 'a')
            except (IOError, OSError) as e:
                self.echo('Error: Unable to open the audit log file. Your queries will not be logged.',
                          err=True, fg='red')
                self.logfile = False

        self.completion_refresher = CompletionRefresher()

        self.logger = logging.getLogger(__name__)
        self.initialize_logging()

        prompt_cnf = self.read_my_cnf_files(self.cnf_files, ['prompt'])['prompt']
        self.prompt_format = prompt or prompt_cnf or c['main']['prompt'] or \
            self.default_prompt
        self.prompt_continuation_format = c['main']['prompt_continuation']

        self.query_history = []

        # Initialize completer.
        self.smart_completion = c['main'].as_bool('smart_completion')
        self.completer = SQLCompleter(
            self.smart_completion,
            supported_formats=self.formatter.supported_formats)
        self._completer_lock = threading.Lock()

        # Register custom special commands.
        self.register_special_commands()
        self.cli = None

    def register_special_commands(self):
        special.register_special_command(self.change_schema, 'use',
                                         'use [schema]', 'Change to a new schema.', aliases=['\\u'])
        special.register_special_command(self.change_db, 'connect',
                                         'connect [database]', 'Reconnect to the database. Optional database argument.',
                                         aliases=('\\r', ), case_sensitive=True)
        special.register_special_command(self.refresh_completions, 'refresh',
                                         'refresh', 'Refresh auto-completions.', arg_type=NO_QUERY, aliases=('\\#',))
        special.register_special_command(
            self.change_table_format, 'format', '\\T [format]',
            'Change the format used to output results (html, csv etc.).',
            aliases=('\\T',), case_sensitive=True)
        special.register_special_command(self.execute_from_file, '@', 'a [filename]',
                                         'Execute commands from file.', aliases=['\\.', 'source'])
        special.register_special_command(self.change_prompt_format, 'prompt',
                                         '\\R', 'Change prompt format.', aliases=('\\R',), case_sensitive=True)

    def change_table_format(self, arg, **_):
        try:
            self.formatter.format_name = arg
            yield (None, None, None,
                   'Changed table format to {}'.format(arg))
        except ValueError:
            msg = 'Table format {} not recognized. Allowed formats:'.format(
                arg)
            for table_type in self.formatter.supported_formats:
                msg += "\n\t{}".format(table_type)
            yield (None, None, None, msg)

    def change_db(self, arg, **_):
        if arg is None:
            self.sqlexecute.connect()
        else:
            self.sqlexecute.connect(database=arg)

        yield (None, None, None, 'You are now connected to database "%s" as '
               'user "%s"' % (self.sqlexecute.dbname, self.sqlexecute.user))

    def change_schema(self, arg, **_):
        if arg is None:
            yield (None, None, None,
                   'Specify the schema to switch to.')
        else:
            schema_name = str(arg).upper()
            self.sqlexecute.conn.current_schema = schema_name
            self.sqlexecute.dbname = schema_name
            yield (None, None, None, 'Schema updated to {}'.format(arg))

    def execute_from_file(self, arg, **_):
        if not arg:
            message = 'Missing required argument, filename.'
            return [(None, None, None, message)]
        try:
            with open(os.path.expanduser(arg), encoding='utf-8') as f:
                query = f.read()
        except IOError as e:
            return [(None, None, None, str(e))]

        if (self.ddl_warning and
                confirm_ddl_query(query) is False):
            message = 'Command execution stopped.'
            return [(None, None, None, message)]

        return self.sqlexecute.run(query)

    def change_prompt_format(self, arg, **_):
        """
        Change the prompt format.
        """
        if not arg:
            message = 'Missing required argument, format.'
            return [(None, None, None, message)]

        self.prompt_format = self.get_prompt(arg)
        return [(None, None, None, "Changed prompt format to %s" % arg)]

    def initialize_logging(self):

        log_file = self.config['main']['log_file']
        log_level = self.config['main']['log_level']
        level_map = {'CRITICAL': logging.CRITICAL,
                     'ERROR': logging.ERROR,
                     'WARNING': logging.WARNING,
                     'INFO': logging.INFO,
                     'DEBUG': logging.DEBUG
                     }

        # Disable logging if value is NONE by switching to a no-op handler
        # Set log level to a high value so it doesn't even waste cycles getting called.
        if log_level.upper() == "NONE":
            handler = NullHandler()
            log_level = "CRITICAL"
        else:
            handler = logging.FileHandler(os.path.expanduser(log_file))

        formatter = logging.Formatter(
            '%(asctime)s (%(process)d/%(threadName)s) '
            '%(name)s %(levelname)s - %(message)s')

        handler.setFormatter(formatter)

        root_logger = logging.getLogger('okcli')
        root_logger.addHandler(handler)
        root_logger.setLevel(level_map[log_level.upper()])

        logging.captureWarnings(True)

        root_logger.debug('Initializing okcli logging.')
        root_logger.debug('Log file %r.', log_file)

    def read_my_cnf_files(self, files, keys):
        """
        Reads a list of config files and merges them. The last one will win.
        :param files: list of files to read
        :param keys: list of keys to retrieve
        :returns: tuple, with None for missing keys.
        """
        cnf = read_config_files(files)

        sections = ['client']
        if self.login_path and self.login_path != 'client':
            sections.append(self.login_path)

        if self.defaults_suffix:
            sections.extend([sect + self.defaults_suffix for sect in sections])

        def get(key):
            result = None
            for sect in cnf:
                if sect in sections and key in cnf[sect]:
                    result = cnf[sect][key]
            return result

        return {x: get(x) for x in keys}

    def connect(self, database='', user='', passwd='', host=''):


        cnf = {'database': None,
               'user': None,
               'password': None,
               'host': None,
               }

        cnf = self.read_my_cnf_files(self.cnf_files, cnf.keys())

        # Fall back to config values only if user did not specify a value.

        database = database or cnf['database']
        user = user or cnf['user'] or os.getenv('USER')
        host = host or cnf['host'] or 'localhost'

        passwd = cnf['password'] or passwd
        if not passwd:
            passwd = click.prompt('Password', hide_input=True, show_default=False, type=str)

        # Assume connecting to schema with same name as user by default
        if not database:
            database = user.upper()
        # Connect to the database.
        try:
            from cx_Oracle import DatabaseError
            try:
                sqlexecute = SQLExecute(database, user, passwd, host)
            except DatabaseError as e:
                if ('invalid username/password' in str(e)):
                    passwd = click.prompt('Password', hide_input=True,
                                          show_default=False, type=str)
                    sqlexecute = SQLExecute(database, user, passwd, host)
                else:
                    raise
        except Exception as e:  # Connecting to a database could fail.
            self.logger.debug('Database connection failed', exc_info=True)
            self.echo(str(e), err=True, fg='red')
            exit(1)

        self.sqlexecute = sqlexecute

    def handle_editor_command(self, cli, document):
        """
        Editor command is any query that is prefixed by a ed. The reason for a
        while loop is because a user might edit a query multiple times.
        For eg:
        r"select * from \e"<enter> to edit it in vim, then come
        back to the prompt with the edited query "select * from
        blah where q = 'abc'\e" to edit it again.
        :param cli: CommandLineInterface
        :param document: Document
        :return: Document
        """
        # FIXME: using application.pre_run_callables like this here is not the best solution.
        # It's internal api of prompt_toolkit that may change. This was added to fix
        # https://github.com/dbcli/pgcli/issues/668. We may find a better way to do it in the future.
        saved_callables = cli.application.pre_run_callables
        while special.editor_command(document.text):
            filename = special.get_filename(document.text)
            query = (special.get_editor_query(document.text) or
                     self.get_last_query())
            sql, message = special.open_external_editor(filename, sql=query)
            if message:
                # Something went wrong. Raise an exception and bail.
                raise RuntimeError(message)
            cli.current_buffer.document = Document(sql, cursor_position=len(sql))
            cli.application.pre_run_callables = []
            document = cli.run()
            continue
        cli.application.pre_run_callables = saved_callables
        return document

    def run_cli(self):
        sqlexecute = self.sqlexecute
        logger = self.logger
        self.configure_pager()

        if self.smart_completion:
            self.refresh_completions()

        key_binding_manager = okcli_bindings()

        def prompt_tokens(cli):
            prompt = self.get_prompt(self.prompt_format)
            if self.prompt_format == self.default_prompt and len(prompt) > self.max_len_prompt:
                prompt = self.get_prompt('\\d> ')
            return [(Token.Prompt, prompt)]

        def get_continuation_tokens(cli, width):
            continuation_prompt = self.get_prompt(self.prompt_continuation_format)
            return [(Token.Continuation, ' ' * (width - len(continuation_prompt)) + continuation_prompt)]

        def one_iteration(document=None):
            if document is None:
                document = self.cli.run()

                special.set_expanded_output(False)

                try:
                    document = self.handle_editor_command(self.cli, document)
                except RuntimeError as e:
                    logger.error("sql: %r, error: %r", document.text, e)
                    logger.error("traceback: %r", traceback.format_exc())
                    self.echo(str(e), err=True, fg='red')
                    return

            if not document.text.strip():
                return

            if self.ddl_warning:
                destroy = confirm_ddl_query(document.text)
                if destroy is None:
                    pass  # Query was not destructive. Nothing to do here.
                elif destroy is True:
                    self.echo('OK')
                else:
                    self.echo('Cancelled')
                    return

            # Keep track of whether or not the query is mutating. In case
            # of a multi-statement query, the overall query is considered
            # mutating if any one of the component statements is mutating
            mutating = False

            try:
                logger.debug('sql: %r', document.text)

                special.write_tee(self.get_prompt(self.prompt_format) + document.text)
                if self.logfile:
                    self.logfile.write('\n# %s\n' % datetime.now())
                    self.logfile.write(document.text)
                    self.logfile.write('\n')

                successful = False
                start = time()
                res = sqlexecute.run(document.text)
                successful = True
                result_count = 0
                for title, cur, headers, status in res:
                    logger.debug("headers: %r", headers)
                    logger.debug("rows: %r", cur)
                    logger.debug("status: %r", status)
                    threshold = 1000
                    if (is_select(status) and
                            cur and cur.rowcount > threshold):
                        self.echo('The result set has more than {} rows.'.format(
                            threshold), fg='red')
                        if not click.confirm('Do you want to continue?'):
                            self.echo("Aborted!", err=True, fg='red')
                            break

                    if self.auto_vertical_output:
                        max_width = self.cli.output.get_size().columns
                    else:
                        max_width = None

                    formatted = self.format_output(
                        title, cur, headers, special.is_expanded_output(),
                        max_width)

                    if cur is not None:
                        status = self.sqlexecute.get_status(cur)
                    t = time() - start
                    try:
                        if result_count > 0:
                            self.echo('')
                        try:
                            self.output('\n'.join(formatted), status)
                        except KeyboardInterrupt:
                            pass
                        if special.is_timing_enabled():
                            self.echo('Time: %0.03fs' % t)
                    except KeyboardInterrupt:
                        pass

                    start = time()
                    result_count += 1
                    mutating = mutating or is_mutating(status)
                special.unset_once_if_written()
            except EOFError as e:
                raise e
            except KeyboardInterrupt:
                # get last connection id
                connection_id_to_kill = sqlexecute.connection_id
                logger.debug("connection id to kill: %r", connection_id_to_kill)
                # Restart connection to the database
                sqlexecute.connect()
                try:
                    for title, cur, headers, status in sqlexecute.run('kill %s' % connection_id_to_kill):
                        status_str = str(status).lower()
                        if status_str.find('ok') > -1:
                            logger.debug("cancelled query, connection id: %r, sql: %r",
                                         connection_id_to_kill, document.text)
                            self.echo("cancelled query", err=True, fg='red')
                except Exception as e:
                    self.echo('Encountered error while cancelling query: {}'.format(e),
                              err=True, fg='red')
            except NotImplementedError:
                self.echo('Not Yet Implemented.', fg="yellow")
            except Exception as e:
                logger.debug("Error", exc_info=True)
                if (e.args[0] in (2003, 2006, 2013)):
                    logger.debug('Attempting to reconnect.')
                    self.echo('Reconnecting...', fg='yellow')
                    try:
                        sqlexecute.connect()
                        logger.debug('Reconnected successfully.')
                        one_iteration(document)
                        return  # OK to just return, cuz the recursion call runs to the end.
                    except Exception as e:
                        logger.debug('Reconnect failed', exc_info=True)
                        self.echo(str(e), err=True, fg='red')
                        # If reconnection failed, don't proceed further.
                        return
                else:
                    logger.error("sql: %r, error: %r", document.text, e)
                    logger.error("traceback: %r", traceback.format_exc())
                    self.echo(str(e), err=True, fg='red')
            except Exception as e:
                logger.error("sql: %r, error: %r", document.text, e)
                logger.error("traceback: %r", traceback.format_exc())
                self.echo(str(e), err=True, fg='red')
            else:
                # Refresh the table names and column names if necessary.
                if need_completion_refresh(document.text):
                    self.refresh_completions(
                        reset=need_completion_reset(document.text))
            finally:
                if self.logfile is False:
                    self.echo("Warning: This query was not logged.",
                              err=True, fg='red')
            query = Query(document.text, successful, mutating)
            self.query_history.append(query)

        get_toolbar_tokens = create_toolbar_tokens_func(self.completion_refresher.is_refreshing)

        layout = create_prompt_layout(
            lexer=OracleLexer,
            multiline=True,
            get_prompt_tokens=prompt_tokens,
            get_continuation_tokens=get_continuation_tokens,
            get_bottom_toolbar_tokens=get_toolbar_tokens,
            display_completions_in_columns=self.wider_completion_menu,
            extra_input_processors=[ConditionalProcessor(
                processor=HighlightMatchingBracketProcessor(chars='[](){}'),
                filter=HasFocus(DEFAULT_BUFFER) & ~IsDone()
            )],
            reserve_space_for_menu=self.get_reserved_space()
        )
        with self._completer_lock:
            buf = CLIBuffer(always_multiline=self.multi_line, completer=self.completer,
                            history=FileHistory(os.path.expanduser(os.environ.get('okcli_HISTFILE', '~/.okcli-history'))),
                            complete_while_typing=Always(), accept_action=AcceptAction.RETURN_DOCUMENT)

            if self.key_bindings == 'vi':
                editing_mode = EditingMode.VI
            else:
                editing_mode = EditingMode.EMACS

            application = Application(style=style_factory(self.syntax_style, self.cli_style),
                                      layout=layout, buffer=buf,
                                      key_bindings_registry=key_binding_manager.registry,
                                      on_exit=AbortAction.RAISE_EXCEPTION,
                                      on_abort=AbortAction.RETRY,
                                      editing_mode=editing_mode,
                                      ignore_case=True)
            self.cli = CommandLineInterface(application=application,
                                            eventloop=create_eventloop())

        try:
            while True:
                one_iteration()
        except EOFError:
            special.close_tee()

    def log_output(self, output):
        """Log the output in the audit log, if it's enabled."""
        if self.logfile:
            self.logfile.write(utf8tounicode(output))
            self.logfile.write('\n')

    def echo(self, s, **kwargs):
        """Print a message to stdout.

        The message will be logged in the audit log, if enabled.

        All keyword arguments are passed to click.echo().

        """
        self.log_output(s)
        click.secho(s, **kwargs)

    def output_fits_on_screen(self, output, status=None):
        """Check if the given output fits on the screen."""
        size = self.cli.output.get_size()

        margin = self.get_reserved_space() + self.get_prompt(self.prompt_format).count('\n') + 1
        if special.is_timing_enabled():
            margin += 1
        if status:
            margin += 1 + status.count('\n')

        for i, line in enumerate(output.splitlines(), 1):
            if len(line) > size.columns or i > (size.rows - margin):
                return False

        return True

    def output(self, output, status=None):
        """Output text to stdout or a pager command.

        The status text is not outputted to pager or files.

        The message will be logged in the audit log, if enabled. The
        message will be written to the tee file, if enabled. The
        message will be written to the output file, if enabled.

        """
        if output:
            self.log_output(output)
            special.write_tee(output)
            special.write_once(output)

            if (self.explicit_pager or
                    (special.is_pager_enabled() and not self.output_fits_on_screen(output, status))):
                click.echo_via_pager(output)
            else:
                click.secho(output)

        if status:
            self.log_output(status)
            click.secho(status)

    def configure_pager(self):
        # Provide sane defaults for less if they are empty.
        if not os.environ.get('LESS'):
            os.environ['LESS'] = '-RXF'

        cnf = self.read_my_cnf_files(self.cnf_files, ['pager', 'skip-pager'])
        if cnf['pager']:
            special.set_pager(cnf['pager'])
            self.explicit_pager = True
        else:
            self.explicit_pager = False

        if cnf['skip-pager']:
            special.disable_pager()

    def refresh_completions(self, reset=False):
        if reset:
            with self._completer_lock:
                self.completer.reset_completions()
        self.completion_refresher.refresh(
            self.sqlexecute, self._on_completions_refreshed,
            {'smart_completion': self.smart_completion,
             'supported_formats': self.formatter.supported_formats})

        return [(None, None, None,
                 'Auto-completion refresh started in the background.')]

    def _on_completions_refreshed(self, new_completer):
        self._swap_completer_objects(new_completer)

        if self.cli:
            # After refreshing, redraw the CLI to clear the statusbar
            # "Refreshing completions..." indicator
            self.cli.request_redraw()

    def _swap_completer_objects(self, new_completer):
        """Swap the completer object in cli with the newly created completer.
        """
        with self._completer_lock:
            self.completer = new_completer
            # When okcli is first launched we call refresh_completions before
            # instantiating the cli object. So it is necessary to check if cli
            # exists before trying the replace the completer object in cli.
            if self.cli:
                self.cli.current_buffer.completer = new_completer

    def get_completions(self, text, cursor_positition):
        with self._completer_lock:
            return self.completer.get_completions(
                Document(text=text, cursor_position=cursor_positition), None)

    def get_prompt(self, string):
        sqlexecute = self.sqlexecute
        host = self.login_path if self.login_path and self.login_path_as_host else sqlexecute.host
        now = datetime.now()
        string = string.replace('\\u', sqlexecute.user or '(none)')
        string = string.replace('\\h', host or '(none)')
        string = string.replace('\\d', sqlexecute.dbname or '(none)')
        string = string.replace('\\t', sqlexecute.server_type()[0] or 'okcli')
        string = string.replace('\\n', "\n")
        string = string.replace('\\D', now.strftime('%a %b %d %H:%M:%S %Y'))
        string = string.replace('\\m', now.strftime('%M'))
        string = string.replace('\\P', now.strftime('%p'))
        string = string.replace('\\R', now.strftime('%H'))
        string = string.replace('\\r', now.strftime('%I'))
        string = string.replace('\\s', now.strftime('%S'))
        return string

    def run_query(self, query, new_line=True):
        """Runs *query*."""
        results = self.sqlexecute.run(query)
        for result in results:
            title, cur, headers, status = result
            output = self.format_output(title, cur, headers)
            for line in output:
                click.echo(line, nl=new_line)

    def format_output(self, title, cur, headers, expanded=False,
                      max_width=None):
        expanded = expanded or self.formatter.format_name == 'vertical'
        output = []

        if title:  # Only print the title if it's not None.
            output.append(title)

        if cur:
            rows = list(cur)
            formatted = self.formatter.format_output(
                rows, headers, format_name='vertical' if expanded else None)

            if (not expanded and max_width and rows and
                    content_exceeds_width(rows[0], max_width) and headers):
                formatted = self.formatter.format_output(
                    rows, headers, format_name='vertical')

            output.append(formatted)

        return output

    def get_reserved_space(self):
        """Get the number of lines to reserve for the completion menu."""
        reserved_space_ratio = .45
        max_reserved_space = 8
        _, height = click.get_terminal_size()
        return min(round(height * reserved_space_ratio), max_reserved_space)

    def get_last_query(self):
        """Get the last query executed or None."""
        return self.query_history[-1][0] if self.query_history else None


@click.command()
@click.option('-h', '--host', help='Host address of the database.')
@click.option('-u', '--user', help='User name to connect to the database.')
@click.option('-p', '--password', help='Password to connect to the database.')
@click.option('-v', '--version', is_flag=True, help='Output okcli\'s version.')
@click.option('-D', '--database', 'database', help='Database to use.')
@click.option('-R', '--prompt', 'prompt',
              help='Prompt format (Default: "{0}").'.format(
                  OCli.default_prompt))
@click.option('-l', '--logfile', type=click.File(mode='a', encoding='utf-8'),
              help='Log every query and its results to a file.')
@click.option('--okclirc', type=click.Path(), default="~/.okclirc",
              help='Location of okclirc file.')
@click.option('--auto-vertical-output', is_flag=True,
              help='Automatically switch to vertical output mode if the result is wider than the terminal width.')
@click.option('-t', '--table', is_flag=True,
              help='Display batch output in table format.')
@click.option('--csv', is_flag=True,
              help='Display batch output in CSV format.')
@click.option('--warn/--no-warn', default=None,
              help='Warn before running a destructive query.')
@click.option('--login-path', type=str,
              help='Read this path from the login file.')
@click.option('-e', '--execute', type=str,
              help='Execute command and quit.')
@click.option('-@', '--filename', type=str,
              help='Execute commands in a file.')
@click.argument('sqlplus', default='', nargs=1)
def cli(sqlplus, user, host, password, database,
        version, prompt, logfile, login_path,
        auto_vertical_output, table, csv,
        warn, execute, filename, okclirc):
    """An Oracle-DB terminal client with auto-completion and syntax highlighting.

    \b
    Examples:
      - okcli -u my_user -h my_host.com -D schema
      - okcli user/password@tns_name
      - okcli user/password@tns_name -D schema
      - okcli user/password@tns_name -e "query"
      - okcli user@tns_name -@ query_file.sql
    """

    if version:
        print('Version:', __version__)
        sys.exit(0)

    if sqlplus:
        user, password, host = parse_sqlplus_arg(sqlplus)

    okcli = OCli(prompt=prompt, logfile=logfile,
                    login_path=login_path,
                    auto_vertical_output=auto_vertical_output, warn=warn,
                    okclirc=okclirc)

    okcli.connect(database, user, password, host)

    okcli.logger.debug('Launch Params: \n'
                        '\tdatabase: %r'
                        '\tuser: %r'
                        '\thost: %r', database, user, host)

    if execute or filename:
        if csv:
            okcli.formatter.format_name = 'csv'
        elif not table:
            okcli.formatter.format_name = 'tsv'
    # --execute argument
    if execute:
        try:
            okcli.run_query(execute)
            exit(0)
        except Exception as e:
            click.secho(str(e), err=True, fg='red')
            exit(1)

    # --filename argument
    if filename:
        try:
            with open(os.path.expanduser(filename), encoding='utf-8') as f:
                query = f.read()
            okcli.run_query(query)
        except IOError as e:
            click.secho(str(e), err=True, fg='red')

    if sys.stdin.isatty():
        okcli.run_cli()
    else:
        stdin = click.get_text_stream('stdin')
        stdin_text = stdin.read()

        try:
            sys.stdin = open('/dev/tty')
        except FileNotFoundError:
            okcli.logger.warning('Unable to open TTY as stdin.')

        if (okcli.ddl_warning and
                confirm_ddl_query(stdin_text) is False):
            exit(0)
        try:
            new_line = True

            if csv:
                okcli.formatter.format_name = 'csv'
                new_line = False
            elif not table:
                okcli.formatter.format_name = 'tsv'

            okcli.run_query(stdin_text, new_line=new_line)
            exit(0)
        except Exception as e:
            click.secho(str(e), err=True, fg='red')
            exit(1)


def content_exceeds_width(row, width):
    # Account for 3 characters between each column
    separator_space = (len(row) * 3)
    # Add 2 columns for a bit of buffer
    line_len = sum([len(str(x)) for x in row]) + separator_space + 2
    return line_len > width


def need_completion_refresh(queries):
    """Determines if the completion needs a refresh by checking if the sql
    statement is an alter, create, drop or change db."""
    for query in sqlparse.split(queries):
        try:
            first_token = query.split()[0]
            if first_token.lower() in ('alter', 'create', 'use', '\\r',
                                       '\\u', 'connect', 'drop'):
                return True
        except Exception:
            return False


def need_completion_reset(queries):
    """Determines if the statement is a database switch such as 'use' or '\\u'.
    When a database is changed the existing completions must be reset before we
    start the completion refresh for the new database.
    """
    for query in sqlparse.split(queries):
        try:
            first_token = query.split()[0]
            if first_token.lower() in ('use', '\\u'):
                return True
        except Exception:
            return False


def is_mutating(status):
    """Determines if the statement is mutating based on the status."""
    if not status:
        return False

    mutating = set(['insert', 'update', 'delete', 'alter', 'create', 'drop',
                    'replace', 'truncate', 'load'])
    return status.split(None, 1)[0].lower() in mutating


def is_select(status):
    """Returns true if the first word in status is 'select'."""
    if not status:
        return False
    return status.split(None, 1)[0].lower() == 'select'


def query_starts_with(query, prefixes):
    """Check if the query starts with any item from *prefixes*."""
    prefixes = [prefix.lower() for prefix in prefixes]
    formatted_sql = sqlparse.format(query.lower(), strip_comments=True)
    return bool(formatted_sql) and formatted_sql.split()[0] in prefixes


def queries_start_with(queries, prefixes):
    """Check if any queries start with any item from *prefixes*."""
    for query in sqlparse.split(queries):
        if query and query_starts_with(query, prefixes) is True:
            return True
    return False


def is_ddl(queries):
    keywords = ('drop', 'shutdown', 'truncate', 'alter', "rename")
    return queries_start_with(queries, keywords)


def confirm_ddl_query(queries):
    """Check if the query is destructive and prompts the user to confirm.
    Returns:
    None if the query is non-destructive or we can't prompt the user.
    True if the query is destructive and the user wants to proceed.
    False if the query is destructive and the user doesn't want to proceed.
    """
    prompt_text = ("You're about to run a DDL command.\n"
                   "Do you want to proceed? (y/n)")
    if is_ddl(queries) and sys.stdin.isatty():
        return click.prompt(prompt_text, type=bool)


def parse_sqlplus_arg(database):
    """Parses an sqlplus connection string (user/passwd@host) unpacking the user, password and host.

    :param database: sqlplus-like connection string
    :return: (?user, ?password, ?host)
    :raises: ValueError
        when database is not of the form <user>/<?password>@<host>
    """
    try:
        credentials, host = database.split('@')
        if '/' in credentials:
            user, password = credentials.split('/')
        else:
            user = credentials
            password = None
        return (user, password, host)
    except ValueError:
        raise ValueError('Invalid sqlplus connection string {}: expected <user>/?<pass>@<host>'.format(database))


if __name__ == "__main__":
    cli()

