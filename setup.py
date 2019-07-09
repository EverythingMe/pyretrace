from setuptools import setup, find_packages
from os import path

pwd = lambda f: path.join(path.abspath(path.dirname(__file__)), f)

setup(
    name='pyretrace',
    description="A python reimplementation on Proguard's Retrace, with a deobfuscation API for python.",
    entry_points={
        'console_scripts': ['pyretrace = pyretrace:main']
    },
    author='Rotem Mizrachi-Meidan',
    author_email='rotem@everything.me',
    url='http://github.com/EverythingMe/pyretrace',
    version='0.3',
    packages=find_packages(),
)
