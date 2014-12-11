pyretrace
=========

A python reimplementation on [Proguard][1]'s [Retrace][2], with a deobfuscation API for python.

	pyretrace -m path/to/mapping_file.txt -s path/to/stacktrace.txt


Installation
------------

	pip install https://github.com/EverythingMe/pyretrace.git
	
or if you're having permission issues

	git clone https://github.com/EverythingMe/pyretrace.git
	cd pyretrace
	pip install .
	
	
Usage
-----

	retrace = Retrace(mapping_file_path, verbose, regex, stacktrace_file_path)
	deobfuscated_string = retrace.deobfuscate('my obfuscated string')
	

[1]: http://proguard.sourceforge.net/
[2]: http://proguard.sourceforge.net/index.html#manual/retrace/introduction.html