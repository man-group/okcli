import pytest

import okcli.sqlexecute
from utils import HOST, PASSWORD, SCHEMA, USER, db_connection


@pytest.yield_fixture(scope="function")
def connection():
    connection = db_connection()
    yield connection
    connection.close()


@pytest.fixture
def cursor(connection):
    with connection.cursor() as cur:
        return cur


@pytest.fixture
def executor(connection):
    return okcli.sqlexecute.SQLExecute(database=SCHEMA, user=USER,
                                        host=HOST, password=PASSWORD)

