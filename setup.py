from setuptools import setup, find_packages
from os import path

pwd = lambda f: path.join(path.abspath(path.dirname(__file__)), f)

setup(
    name='pyretrace',
    description=open(pwd('README.md')).read(),
    entry_points={
        'console_scripts': ['pyretrace = pyretrace:main']
    },
    author='EverythingMe',
    version='0.1',
    packages=find_packages(),
)