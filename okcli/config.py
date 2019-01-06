from __future__ import print_function

import logging
import os
import shutil
import struct
import sys
import six
from io import BytesIO, TextIOWrapper
from os.path import exists

from configobj import ConfigObj, ConfigObjError


logger = logging.getLogger(__name__)


def log(logger, level, message):
    """Logs message to stderr if logging isn't initialized."""

    if logger.parent.name != 'root':
        logger.log(level, message)
    else:
        print(message, file=sys.stderr)


def read_config_file(f):
    """Read a config file."""

    if isinstance(f, six.string_types):
        f = os.path.expanduser(f)

    try:
        config = ConfigObj(f, interpolation=False, encoding='utf8')
    except ConfigObjError as e:
        log(logger, logging.ERROR, "Unable to parse line {0} of config file "
            "'{1}'.".format(e.line_number, f))
        log(logger, logging.ERROR, "Using successfully parsed config values.")
        return e.config
    except (IOError, OSError) as e:
        log(logger, logging.WARNING, "You don't have permission to read "
            "config file '{0}'.".format(e.filename))
        return None

    return config


def read_config_files(files):
    """Read and merge a list of config files."""

    config = ConfigObj()

    for _file in files:
        _config = read_config_file(_file)
        if bool(_config) is True:
            config.merge(_config)
            config.filename = _config.filename

    return config


def write_default_config(source, destination, overwrite=False):
    destination = os.path.expanduser(destination)
    if not overwrite and exists(destination):
        return

    shutil.copyfile(source, destination)


def str_to_bool(s):
    """Convert a string value to its corresponding boolean value."""
    if isinstance(s, bool):
        return s
    elif not isinstance(s, six.string_types):
        raise TypeError('argument must be a string')

    true_values = ('true', 'on', '1')
    false_values = ('false', 'off', '0')

    if s.lower() in true_values:
        return True
    elif s.lower() in false_values:
        return False
    else:
        raise ValueError('not a recognized boolean value: %s'.format(s))


def _remove_pad(line):
    """Remove the pad from the *line*."""
    pad_length = ord(line[-1:])
    try:
        # Determine pad length.
        pad_length = ord(line[-1:])
    except TypeError:
        # ord() was unable to get the value of the byte.
        logger.warning('Unable to remove pad.')
        return False

    if pad_length > len(line) or len(set(line[-pad_length:])) != 1:
        # Pad length should be less than or equal to the length of the
        # plaintext. The pad should have a single unqiue byte.
        logger.warning('Invalid pad found in login path file.')
        return False

    return line[:-pad_length]

