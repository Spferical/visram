#!/usr/bin/env python2

from distutils.core import setup

setup(name='visram',
      version='0.1.0',
      description='Graphical RAM/CPU Visualizer',
      license='MIT',
      author='Matthew Pfeiffer',
      author_email='spferical@gmail.com',
      url='http://github.com/Spferical/visram',
      packages=['visram', 'visram.test'],
      scripts=['bin/visram'],
      platforms=['any'],
     )
