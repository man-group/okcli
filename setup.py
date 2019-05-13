#!/usr/bin/env python

import ast
import sys
import re

from setuptools import find_packages, setup

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('okcli/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

description = 'A CLI for Oracle DB Database with auto-completion and syntax highlighting.'

def get_long_description():
    with open('README.md', 'r') as f:
        return f.read()


def get_requirements():
    with open('requirements.txt', 'r') as f:
        return f.read().splitlines()


setup(
    name='okcli',
    version=version,
    author='Man AHL Technology',
    author_email='ManAHLTech@ahl.com',
    url='https://github.com/manahl/okcli',
    packages=find_packages(),
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    install_requires=get_requirements(),
    include_package_data=True,
    entry_points={
        'console_scripts': ['okcli = okcli.main:cli'],
    },
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: SQL',
        'Topic :: Database',
        'Topic :: Database :: Front-Ends',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Python Modules',
],
)

