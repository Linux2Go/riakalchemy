#!/usr/bin/python

from setuptools import setup

setup(
    name='riakalchemy',
    version='0.1a3',
    description='Object Mapper for Riak',
    author='Soren Hansen',
    license='LGPL',
    author_email='soren@linux2go.dk',
    url='https://launchpad.net/riakalchemy',
    packages=['riakalchemy'],
    install_requires=['riak'],
    test_suite = 'nose.collector',
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
