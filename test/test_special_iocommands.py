# coding: utf-8
import os
import stat
import tempfile

import pytest

import oracli.packages.special
from oracli.packages.special.main import CommandNotFound
from utils import db_connection, dbtest


def test_set_get_pager():
    oracli.packages.special.set_pager_enabled(True)
    assert oracli.packages.special.is_pager_enabled()
    oracli.packages.special.set_pager_enabled(False)
    assert not oracli.packages.special.is_pager_enabled()
    oracli.packages.special.set_pager('less')
    assert os.environ['PAGER'] == "less"
    oracli.packages.special.set_pager(False)
    assert os.environ['PAGER'] == "less"
    del os.environ['PAGER']
    oracli.packages.special.set_pager(False)
    oracli.packages.special.disable_pager()
    assert not oracli.packages.special.is_pager_enabled()


def test_set_get_timing():
    oracli.packages.special.set_timing_enabled(True)
    assert oracli.packages.special.is_timing_enabled()
    oracli.packages.special.set_timing_enabled(False)
    assert not oracli.packages.special.is_timing_enabled()


def test_set_get_expanded_output():
    oracli.packages.special.set_expanded_output(True)
    assert oracli.packages.special.is_expanded_output()
    oracli.packages.special.set_expanded_output(False)
    assert not oracli.packages.special.is_expanded_output()


def test_editor_command():
    assert oracli.packages.special.editor_command(r'ed hello')
    assert not oracli.packages.special.editor_command(r'hello')

    assert oracli.packages.special.get_filename(r'ed filename') == "filename"

    os.environ['EDITOR'] = 'true'
    oracli.packages.special.open_external_editor(r'select 1') == "select 1"


def test_spool_command():
    oracli.packages.special.write_tee(u"hello world")  # write without file set
    with tempfile.NamedTemporaryFile() as f:
        oracli.packages.special.execute(None, u"spool " + f.name)
        oracli.packages.special.write_tee(u"hello world")
        assert f.read() == b"hello world"

        oracli.packages.special.execute(None, u"spool -o " + f.name)
        oracli.packages.special.write_tee(u"hello world")
        f.seek(0)
        assert f.read() == b"hello world"

        oracli.packages.special.execute(None, u"nospool")
        oracli.packages.special.write_tee(u"hello world")
        f.seek(0)
        assert f.read() == b"hello world"


def test_tee_command_error():
    with pytest.raises(TypeError):
        oracli.packages.special.execute(None, 'tee')

    with pytest.raises(OSError):
        with tempfile.NamedTemporaryFile() as f:
            os.chmod(f.name, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
            oracli.packages.special.execute(None, 'tee {}'.format(f.name))


@dbtest
def test_favorite_query():
    with db_connection().cursor() as cur:
        query = u'select "✔"'
        oracli.packages.special.execute(cur, u'\\fs check {0}'.format(query))
        assert next(oracli.packages.special.execute(
            cur, u'\\f check'))[0] == "> " + query


def test_once_command():
    with pytest.raises(TypeError):
        oracli.packages.special.execute(None, u"\once")

    oracli.packages.special.execute(None, u"\once /proc/access-denied")
    with pytest.raises(OSError):
        oracli.packages.special.write_once(u"hello world")

    oracli.packages.special.write_once(u"hello world")  # write without file set
    with tempfile.NamedTemporaryFile() as f:
        oracli.packages.special.execute(None, u"\once " + f.name)
        oracli.packages.special.write_once(u"hello world")
        assert f.read() == b"hello world\n"

        oracli.packages.special.execute(None, u"\once -o " + f.name)
        oracli.packages.special.write_once(u"hello world")
        f.seek(0)
        assert f.read() == b"hello world\n"

