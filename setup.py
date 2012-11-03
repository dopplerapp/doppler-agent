#!/usr/bin/env python

import doppler
from setuptools import setup, find_packages

setup(
    name='doppler-agent',
    version=doppler.__version__,
    description="The server monitoring agent for doppler.com collects data about resource usage on your machines",
    author='Doppler',
    author_email='agent@doppler.io',
    url='http://doppler.io',
    license='MIT',
    scripts = ['doppler/bin/doppler-agent.py'],
    packages=find_packages(exclude=['ez_setup', 'tests']),
    include_package_data=True,
    zip_safe=False,
)