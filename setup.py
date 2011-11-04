#!/usr/bin/python

from setuptools import setup

setup(
    name='riakalchemy',
    version='0.1a2',
    description='Object Mapper for Riak',
    author='Soren Hansen',
    license='LGPL',
    author_email='soren@linux2go.dk',
    url='https://launchpad.net/riakalchemy',
    packages=['riakalchemy'],
    install_requires=['riak'],
    classifiers = [
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: '
        'GNU Library or Lesser General Public License (LGPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
