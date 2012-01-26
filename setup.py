import os
from setuptools import setup, find_packages

version='0.1dev'

install_requires = [
    'setuptools',
    'gevent',
    'gevent-websocket',
]

tests_require = install_requires + ['nose']

def read(f):
    return open(os.path.join(os.path.dirname(__file__), f)).read().strip()

setup(name='gevent-sockjs',
      version=version,
      description=('gevent base sockjs server'),
      long_description='\n\n'.join((read('README.md'), read('CHANGES.txt'))),
      classifiers=[
          "Intended Audience :: Developers",
          "Programming Language :: Python",
          "Programming Language :: Python :: 2.6",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: Implementation :: CPython",
          "Topic :: Internet :: WWW/HTTP",
          'Topic :: Internet :: WWW/HTTP :: WSGI'],
      author='Stephen Diehl',
      author_email='stephen.m.diehl@gmail.com',
      url='https://github.com/sdiehl/sockjs-gevent',
      license='MIT',
      packages=find_packages(),
      install_requires = install_requires,
      tests_require = tests_require,
      test_suite = 'nose.collector',
      include_package_data = True,
      zip_safe = False,
      entry_points = {
          'console_scripts': [
              'sockjs-server = gevent_sockjs.server:main',
              ],
          },
      )
