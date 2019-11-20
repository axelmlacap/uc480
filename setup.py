# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(name='uc480',
      version='0.1',
      description='OCT Control',
      url='',
      author='Axel Lacapmesure',
      author_email='axel.lacapmesure@fi.uba.ar',
      license='',
      packages=find_packages(),
      #      install_requires=[
      #          'pyueye',
      #          'numpy',
      #          'lantzdev[full]',
      #          'enum',
      #          'numpy'
      #      ],
      zip_safe=False, install_requires=['lantz', 'numpy'])