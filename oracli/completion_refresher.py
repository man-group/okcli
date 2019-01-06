import threading
from collections import OrderedDict

from .packages.special.main import COMMANDS
from .sqlcompleter import SQLCompleter
from .sqlexecute import SQLExecute


class CompletionRefresher(object):

    refreshers = OrderedDict()

    def __init__(self):
        self._completer_thread = None
        self._restart_refresh = threading.Event()

    def refresh(self, executor, callbacks, completer_options=None):
        """Creates a SQLCompleter object and populates it with the relevant
        completion suggestions in a background thread.

        executor - SQLExecute object, used to extract the credentials to connect
                   to the database.
        callbacks - A function or a list of functions to call after the thread
                    has completed the refresh. The newly created completion
                    object will be passed in as an argument to each callback.
        completer_options - dict of options to pass to SQLCompleter.

        """
        completer_options = completer_options or {}

        if self.is_refreshing():
            self._restart_refresh.set()
            return [(None, None, None, 'Auto-completion refresh restarted.')]
        else:
            self._completer_thread = threading.Thread(
                target=self._bg_refresh,
                args=(executor, callbacks, completer_options),
                name='completion_refresh')
            self._completer_thread.setDaemon(True)
            self._completer_thread.start()
            return [(None, None, None,
                     'Auto-completion refresh started in the background.')]

    def is_refreshing(self):
        return self._completer_thread and self._completer_thread.is_alive()

    def _bg_refresh(self, sqlexecute, callbacks, completer_options):
        completer = SQLCompleter(**completer_options)

        # Create a new pgexecute method to popoulate the completions.
        e = sqlexecute
        executor = SQLExecute(e.dbname, e.user, e.password, e.host)

        # If callbacks is a single function then push it into a list.
        if callable(callbacks):
            callbacks = [callbacks]

        while True:
            for refresher in self.refreshers.values():
                refresher(completer, executor)
                if self._restart_refresh.is_set():
                    self._restart_refresh.clear()
                    break
            else:
                # Break out of while loop if the for loop finishes natually
                # without hitting the break statement.
                break

            # Start over the refresh from the beginning if the for loop hit the
            # break statement.
            continue

        for callback in callbacks:
            callback(completer)


def refresher(name, refreshers=CompletionRefresher.refreshers):
    """Decorator to add the decorated function to the dictionary of
    refreshers. Any function decorated with a @refresher will be executed as
    part of the completion refresh routine."""
    def wrapper(wrapped):
        refreshers[name] = wrapped
        return wrapped
    return wrapper


@refresher('databases')
def refresh_databases(completer, executor):
    completer.extend_database_names(executor.databases())


@refresher('schemata')
def refresh_schemata(completer, executor):
    completer.set_dbname(executor.dbname)
    completer.extend_schemata(completer.databases)


@refresher('tables')
def refresh_tables(completer, executor):
    for schema in completer.databases:
        tables = executor.tables(schema)
        completer.extend_relations(tables, kind='tables', schema=schema)
        columns = executor.table_columns(schema)
        completer.extend_columns(columns, kind='tables', schema=schema)


@refresher('users')
def refresh_users(completer, executor):
    completer.extend_users(executor.users())

# todo separate views from tables
# @refresher('views')
# def refresh_views(completer, executor):
#     completer.extend_relations(executor.views(), kind='views')
#     completer.extend_columns(executor.view_columns(), kind='views')


@refresher('functions')
def refresh_functions(completer, executor):
    for schema in completer.databases:
        completer.extend_functions(executor.functions(schema), schema)


@refresher('special_commands')
def refresh_special(completer, executor):
    completer.extend_special_commands(COMMANDS.keys())

