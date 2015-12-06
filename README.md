#pyretrace


A python reimplementation on [Proguard][1]'s [Retrace][2], with a deobfuscation API for python.

[![PyPI version](https://badge.fury.io/py/pyretrace.svg)](https://badge.fury.io/py/pyretrace)

### Installation

	$ pip install pyretrace
	
from source:
	
	$ pip install https://github.com/EverythingMe/pyretrace.git
	
or if you're having permission issues:

	$ git clone https://github.com/EverythingMe/pyretrace.git
	cd pyretrace
	sudo pip install .
	
	
### Usage

There are two ways of using pyretrace:

1. As a command line tool:
	
		$ pyretrace -m path/to/mapping_file.txt -s path/to/stacktrace.txt
	
2. As an API module:

		import pyretrace
		
		retrace = Retrace(mapping_file_path, verbose, regex)
		deobfuscated_string = retrace.deobfuscate('my obfuscated string')
	

[1]: http://proguard.sourceforge.net/
[2]: http://proguard.sourceforge.net/index.html#manual/retrace/introduction.html