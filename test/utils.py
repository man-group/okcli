from os import getenv

import pytest

from okcli.main import special

PASSWORD = getenv('PYTEST_PASSWORD')
USER = getenv('PYTEST_USER')
HOST = getenv('PYTEST_HOST')
SCHEMA = getenv('PYTEST_SCHEMA')
CHARSET = getenv('PYTEST_CHARSET', 'utf8')


def db_connection(dbname=SCHEMA):
    import cx_Oracle
    conn = cx_Oracle.connect(user=USER, password=PASSWORD, dsn=HOST)
    conn.current_schema = dbname
    conn.autocommit = True
    return conn


try:
    db_connection()
    CAN_CONNECT_TO_DB = True
except Exception as e:
    CAN_CONNECT_TO_DB = False

dbtest = pytest.mark.skipif(
    not CAN_CONNECT_TO_DB,
    reason="Need an Oracle-DB instance")


def run(executor, sql, rows_as_list=True):
    """Return string output for the sql to be run."""
    result = []

    for title, rows, headers, status in executor.run(sql):
        rows = list(rows) if (rows_as_list and rows) else rows
        result.append({'title': title, 'rows': rows, 'headers': headers,
                       'status': status})

    return result


def set_expanded_output(is_expanded):
    """Pass-through for the tests."""
    return special.set_expanded_output(is_expanded)


def is_expanded_output():
    """Pass-through for the tests."""
    return special.is_expanded_output()

