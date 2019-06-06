#!/usr/bin/env python

import ast
import sys
import re

from setuptools import find_packages, setup

import okcli
version = okcli.__version__

description = 'A CLI for Oracle DB Database with auto-completion and syntax highlighting.'

def get_long_description():
    with open('README.md', 'r') as f:
        return f.read()


setup(
    name='okcli',
    version=version,
    author='Man AHL Technology',
    author_email='ManAHLTech@ahl.com',
    url='https://github.com/manahl/okcli',
    packages=find_packages(),
    description=description,
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    install_requires=[
        'cx_Oracle',
        'cli_helpers >= 0.1.0,<=0.2.3',
        'click >= 4.1',
        'Pygments >= 1.6',
        'prompt_toolkit==1.0.14',
        'sqlparse>=0.2.2,<0.3.0',
        'configobj >= 5.0.5',
        'pytest',
        'mock',
        ],
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

