# -*- coding: utf-8 -*-
from setuptools import setup

setup(name='uc480',
      version='0.1',
      description='uc480 (Thorlabs DCx, IDS uEye) cameras control, user-end oriented.',
      url='',
      author='Axel Lacapmesure',
      author_email='axel.lacapmesure@fi.uba.ar',
      license='',
      packages=['uc480'],
      install_requires=[
          'pyueye',
          'numpy',
          'lantzdev[full]',
          'enum'
      ],
      zip_safe=False)