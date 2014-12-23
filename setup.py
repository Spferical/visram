#!/usr/bin/env python2
"""Setup file for Visram"""

from setuptools import setup
import visram

setup(
    name='visram',
    version=visram.__version__,
    description='Graphical RAM/CPU Visualizer',
    license='MIT',
    author='Matthew Pfeiffer',
    author_email='spferical@gmail.com',
    url='http://github.com/Spferical/visram',
    packages=['visram'],
    install_requires=['wxPython', 'matplotlib', 'psutil'],
    # can't use entry_points without it depending on all of the dependencies of
    # the requires, down to nose
    scripts=['bin/visram'],
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
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Monitoring',
        ],
    data_files=[
        ('share/applications', ['xdg/visram.desktop']),
        ('share/licenses/visram', ['LICENSE.TXT']),
    ]
)
