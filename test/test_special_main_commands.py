import okcli.packages.special.main  as mod
import pytest

@pytest.mark.parametrize('sql', [
    "exec my_proc",
    "exec my_proc(); ",
    "exec my_proc()",
    "exec my_proc ()   ",
])
def test_sql_to_stored_proc_cursor_no_args(sql):
    assert mod._sql_to_stored_proc_cursor_args(sql) == ('my_proc', ())

@pytest.mark.parametrize(['sql', 'expected'], [
    ["exec my_proc(123);", ('my_proc', (123, ))],
    ["exec my_proc('arg_name');", ('my_proc', ('arg_name',))],
    ["exec my_schema.my_proc('some', 'thing', 123)", ('my_schema.my_proc', ('some', 'thing', 123))],
])
def test_sql_to_stored_proc_cursor_args_with_args(sql, expected):
    assert mod._sql_to_stored_proc_cursor_args(sql) == expected


@pytest.mark.parametrize('sql', [
    'exec',
    'execblah',
    '',
    'exe',
    'exe 12dc'
    ])
def test_sql_to_stored_proc_cursor_args_raises(sql):
    with pytest.raises(ValueError):
        mod._sql_to_stored_proc_cursor_args(sql)
