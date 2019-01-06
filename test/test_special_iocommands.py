# coding: utf-8
import os
import stat
import tempfile

import pytest

import okcli.packages.special
from okcli.packages.special.main import CommandNotFound
from utils import db_connection, dbtest


def test_set_get_pager():
    okcli.packages.special.set_pager_enabled(True)
    assert okcli.packages.special.is_pager_enabled()
    okcli.packages.special.set_pager_enabled(False)
    assert not okcli.packages.special.is_pager_enabled()
    okcli.packages.special.set_pager('less')
    assert os.environ['PAGER'] == "less"
    okcli.packages.special.set_pager(False)
    assert os.environ['PAGER'] == "less"
    del os.environ['PAGER']
    okcli.packages.special.set_pager(False)
    okcli.packages.special.disable_pager()
    assert not okcli.packages.special.is_pager_enabled()


def test_set_get_timing():
    okcli.packages.special.set_timing_enabled(True)
    assert okcli.packages.special.is_timing_enabled()
    okcli.packages.special.set_timing_enabled(False)
    assert not okcli.packages.special.is_timing_enabled()


def test_set_get_expanded_output():
    okcli.packages.special.set_expanded_output(True)
    assert okcli.packages.special.is_expanded_output()
    okcli.packages.special.set_expanded_output(False)
    assert not okcli.packages.special.is_expanded_output()


def test_editor_command():
    assert okcli.packages.special.editor_command(r'ed hello')
    assert not okcli.packages.special.editor_command(r'hello')

    assert okcli.packages.special.get_filename(r'ed filename') == "filename"

    os.environ['EDITOR'] = 'true'
    okcli.packages.special.open_external_editor(r'select 1') == "select 1"


def test_spool_command():
    okcli.packages.special.write_tee(u"hello world")  # write without file set
    with tempfile.NamedTemporaryFile() as f:
        okcli.packages.special.execute(None, u"spool " + f.name)
        okcli.packages.special.write_tee(u"hello world")
        assert f.read() == b"hello world"

        okcli.packages.special.execute(None, u"spool -o " + f.name)
        okcli.packages.special.write_tee(u"hello world")
        f.seek(0)
        assert f.read() == b"hello world"

        okcli.packages.special.execute(None, u"nospool")
        okcli.packages.special.write_tee(u"hello world")
        f.seek(0)
        assert f.read() == b"hello world"


def test_tee_command_error():
    with pytest.raises(TypeError):
        okcli.packages.special.execute(None, 'tee')

    with pytest.raises(OSError):
        with tempfile.NamedTemporaryFile() as f:
            os.chmod(f.name, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
            okcli.packages.special.execute(None, 'tee {}'.format(f.name))


@dbtest
def test_favorite_query():
    with db_connection().cursor() as cur:
        query = u'select "✔"'
        okcli.packages.special.execute(cur, u'\\fs check {0}'.format(query))
        assert next(okcli.packages.special.execute(
            cur, u'\\f check'))[0] == "> " + query


def test_once_command():
    with pytest.raises(TypeError):
        okcli.packages.special.execute(None, u"\once")

    okcli.packages.special.execute(None, u"\once /proc/access-denied")
    with pytest.raises(OSError):
        okcli.packages.special.write_once(u"hello world")

    okcli.packages.special.write_once(u"hello world")  # write without file set
    with tempfile.NamedTemporaryFile() as f:
        okcli.packages.special.execute(None, u"\once " + f.name)
        okcli.packages.special.write_once(u"hello world")
        assert f.read() == b"hello world\n"

        okcli.packages.special.execute(None, u"\once -o " + f.name)
        okcli.packages.special.write_once(u"hello world")
        f.seek(0)
        assert f.read() == b"hello world\n"

