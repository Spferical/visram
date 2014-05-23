#!/usr/bin/env python2
"""Setup file for Visram"""

from setuptools import setup

setup(
    name='visram',
    version='0.1.0',
    description='Graphical RAM/CPU Visualizer',
    license='MIT',
    author='Matthew Pfeiffer',
    author_email='spferical@gmail.com',
    url='http://github.com/Spferical/visram',
    packages=['visram', 'visram.tests'],
    install_requires=['wxPython', 'matplotlib', 'psutil'],
    scripts=['bin/visram'],
    test_suite='visram.tests',
    platforms=['any'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: X11 Applications',
        'Environment :: MacOS X :: Cocoa',
        'Environment :: Win32 (MS Windows)',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 2 :: Only',
        'Topic :: System :: Monitoring',
        ],
    )
