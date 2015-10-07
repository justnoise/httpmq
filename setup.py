from setuptools import setup

setup(name='httpmq',
      version='0.1',
      description='A simple HTTP message queue',
      url='http://github.com/justnoise/httpmq/',
      author='Brendan Cox',
      author_email='justnoise@gmail.com',
      license='MIT',
      packages=['httpmq'],
      install_requires=[
          "twisted",
          "monocle",
          "pyOpenSSL",
          "daemon",
          "requests"
      ],
      zip_safe=False)
