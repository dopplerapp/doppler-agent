#!/usr/bin/env python

import doppler
from setuptools import setup, find_packages

setup(
    name='doppler-agent',
    version=doppler.__version__,
    description="The server monitoring agent for doppler.io collects data about resource usage on your machines",
    long_description=open('README.md').read(),
    author='Doppler',
    author_email='agent@doppler.io',
    url='http://doppler.io',
    license='MIT',
    scripts = ['doppler/bin/doppler-agent.py', 'doppler/bin/doppler-configure.py'],
    packages=find_packages(exclude=['ez_setup', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=['bugsnag'],
)