from __future__ import print_function

import argparse
import re
import sys

from pyretrace.reader import MappingReader


STACK_TRACE_EXPRESSION = "(?:.*?\\bat\\s+%c\\.%m\\s*\\(.*?(?::%l)?\\)\\s*)|(?:(?:.*?[:\"]\\s+)?%c(?::.*)?)"

REGEX_CLASS = "\\b(?:[A-Za-z0-9_$]+\\.)*[A-Za-z0-9_$]+\\b"
REGEX_CLASS_SLASH = "\\b(?:[A-Za-z0-9_$]+/)*[A-Za-z0-9_$]+\\b"
REGEX_LINE_NUMBER = "\\b[0-9]+\\b"
REGEX_TYPE = REGEX_CLASS + "(?:\\[\\])*"
REGEX_MEMBER = "<?\\b[A-Za-z0-9_$]+\\b>?"
REGEX_ARGUMENTS = "(?:" + REGEX_TYPE + "(?:\\s*,\\s*" + REGEX_TYPE + ")*)?"


class Retrace():
    def __init__(self, mapping_file, verbose=False, regular_expression=STACK_TRACE_EXPRESSION, stacktrace_file=None):
        self.regular_expression = regular_expression
        self.verbose = verbose
        self.mapping_file = mapping_file
        self.stacktrace_file = stacktrace_file

        self.class_map = dict()
        self.class_field_map = dict()
        self.class_method_map = dict()

        self.options = {
            'c': REGEX_CLASS,
            'C': REGEX_CLASS_SLASH,
            'l': REGEX_LINE_NUMBER,
            't': REGEX_TYPE,
            'f': REGEX_MEMBER,
            'm': REGEX_MEMBER,
            'a': REGEX_ARGUMENTS
        }

        # Read the mapping file.
        mapping_reader = MappingReader(self.mapping_file)
        mapping_reader.pump(self)

        expression_buffer = ''
        self.expression_types = list(range(32))
        self.expression_type_count = 0

        index = 0
        while True:
            next_index = self.regular_expression.find('%', index)
            if next_index < 0 or \
               next_index is (len(self.regular_expression) - 1) or \
               self.expression_type_count is len(self.expression_types):
                break

            expression_buffer += self.regular_expression[index: next_index]
            expression_buffer += '('

            expression_type = self.regular_expression[next_index + 1]

            expression_buffer += self.options[expression_type]
            expression_buffer += ')'

            self.expression_types[self.expression_type_count] = expression_type
            self.expression_type_count += 1

            index = next_index + 2

        expression_buffer += self.regular_expression[index: len(self.regular_expression)]

        self.pattern = re.compile(expression_buffer)

    def execute(self):
        """
        Will start looping over stacktrace_file or sys.stdin, deobfuscating line by line
        """

        # Open the stack trace file.
        if self.stacktrace_file:
            reader = open(self.stacktrace_file, 'r')
        else:
            reader = sys.stdin

        while True:
            line = reader.readline()
            if not line:
                break

            print(self.deobfuscate(line, False))

    def deobfuscate_class(self, line):
        return self.original_class_name(line, False)

    def deobfuscate(self, line, simple_name):
        """Return a deobfuscated version of the given line
        :rtype: str
        """

        # Try to match it against the regular expression.
        matcher = self.pattern.match(line)

        if matcher:
            line_number = 0
            type = None
            arguments = None

            for expression_type_index in range(0, self.expression_type_count):
                start_index = matcher.start(expression_type_index + 1)
                if start_index >= 0:
                    # match = line.split(' ')[expression_type_index]
                    match = matcher.group(expression_type_index + 1)

                    expression_type = self.expression_types[expression_type_index]

                    if expression_type == 'c':
                        class_name = self.original_class_name(match, simple_name)
                    elif expression_type == 'C':
                        class_name = self.original_class_name(external_class_name(match), simple_name)
                    elif expression_type == 'l':
                        line_number = int(match)
                    elif expression_type == 't':
                        type = self.original_type(match)
                    elif expression_type == 'a':
                        arguments = self.original_arguments(match)


            # Deconstruct the input line and reconstruct the output
            # line. Also collect any additional output lines for this
            # line.

            line_index = 0
            out_line = ''
            extra_outlines = []

            for expression_type_index in range(0, self.expression_type_count):
                start_index = matcher.start(expression_type_index + 1)
                if start_index >= 0:
                    end_index = matcher.end(expression_type_index + 1)
                    match = matcher.group(expression_type_index + 1)

                    # Copy a literal piece of the input line.
                    out_line += line[line_index: start_index]
                    # Copy a matched and translated piece of the input line.
                    expression_type = self.expression_types[expression_type_index]

                    if expression_type == 'c':
                        class_name = self.original_class_name(match, simple_name)
                        out_line += class_name
                    elif expression_type == 'C':
                        class_name = self.original_class_name(external_class_name(match), simple_name)
                        out_line += external_class_name(match)
                    elif expression_type == 'l':
                        line_number = int(match)
                        out_line += match
                    elif expression_type == 't':
                        type = self.original_type(match)
                        out_line += type
                    elif expression_type == 'f':
                        out_line += self.original_field_name(class_name,
                                                             match,
                                                             type,
                                                             out_line,
                                                             extra_outlines)
                    elif expression_type == 'm':
                        out_line += self.original_method_name(class_name,
                                                              match,
                                                              line_number,
                                                              type,
                                                              arguments,
                                                              out_line,
                                                              extra_outlines)
                    elif expression_type == 'a':
                        arguments = self.original_arguments(match)
                        out_line += arguments

                    # Skip the original element whose processed version
                    # has just been appended.
                    line_index = end_index

            # Copy the last literal piece of the input line.
            out_line += line[line_index: len(line)]

            # Print out the processed line.
            output = out_line.strip()

            for extra_line_index in range(0, len(extra_outlines)):
                output += extra_line_index

            return output
        else:
            # The line didn't match the regular expression.
            # Print out the original line.
            return line

    def original_field_name(self, class_name, obfuscated_field_name, type, out_line, extra_outlines):
        """Finds the original field name(s), appending the first one to the out
        line, and any additional alternatives to the extra lines.
        """
        extra_indent = -1

        # class name -> obfuscated field names
        field_map = self.class_field_map.get(class_name)
        if field_map:
            # Obfuscated filed names -> fields.
            field_set = field_map.get(obfuscated_field_name)
            if field_set:
                # Find all matching fields.
                for field_info in field_set:
                    if field_info.matches(type):
                        # Is this the first matching field?
                        if extra_indent < 0:
                            extra_indent = len(out_line)

                            # Append the first original name.
                            if self.verbose:
                                out_line += field_info.type + ' '
                            out_line += field_info.original_name
                        else:
                            extra_buffer = ''
                            for counter in range(0, extra_indent):
                                # Create an additional line with the proper indentation
                                extra_buffer += ' '

                                # Append the alternative name
                                if self.verbose:
                                    extra_buffer += field_info.type + ' '
                                extra_buffer += field_info.original_name

                                # Store the additional line.
                                extra_outlines.append(extra_buffer)

        # Just append the obfuscated name if we haven't found any matching fields.
        if extra_indent < 0:
            return obfuscated_field_name
        else:
            return ''

    def original_method_name(self, class_name, obfuscated_method_name, line_number, type, arguments, out_line, extra_outlines):
        extra_indent = -1
        original_method_name = ''

        # Class name -> obfuscated method names.
        method_map = self.class_method_map.get(class_name)
        if method_map:
            # Obfuscated method names -> methods.
            method_set = method_map.get(obfuscated_method_name)
            if method_set:
                # Find all matching methods.
                for method_info in method_set:
                    if method_info.matches(line_number, type, arguments):
                        # Is this the first matching method?
                        if extra_indent < 0:
                            extra_indent = len(out_line)

                            # Append the first original name.
                            if self.verbose:
                                original_method_name += method_info.type + ' '
                            original_method_name += method_info.original_name

                            if self.verbose:
                                original_method_name = '%s(%s)' % (out_line, method_info.arguments)
                        else:
                            extra_buffer = ''
                            for counter in range(0, extra_indent):
                                extra_buffer += ' '

                                # Append the alternative name.
                                if self.verbose:
                                    extra_buffer += method_info.type + ' '
                                extra_buffer += method_info.original_name

                                if self.verbose:
                                    extra_buffer += '%s(%s)' % (extra_buffer, method_info.arguments)

                                    # Store the additional line.
                                    extra_outlines.append(extra_buffer)

        # Just append the obfuscated name if we haven't found any matching methods.
        if extra_indent < 0:
            original_method_name += obfuscated_method_name

        return original_method_name

    def original_arguments(self, obfuscated_arguments):
        """
        Returns the original argument types.
        """

        original_arguments = ''

        start_index = 0
        while True:
            end_index = obfuscated_arguments.index(',', start_index)
            if end_index < 0:
                break

            original_arguments += self.original_type(obfuscated_arguments[start_index, end_index]) + ','
            start_index = end_index + 1

        original_arguments += self.original_type(obfuscated_arguments[start_index])
        return original_arguments

    def original_type(self, obfuscated_type):
        index = obfuscated_type.find('[')

        if index >= 0:
            return self.original_class_name(obfuscated_type[0, index]) + obfuscated_type[index, len(obfuscated_type)]
        else:
            return self.original_class_name(obfuscated_type)

    def original_class_name(self, obfuscated_class_name, simple_name):
        """
        Returns the original class name.
        """

        original_class_name = self.class_map.get(obfuscated_class_name)

        if original_class_name:
            if simple_name:
                original_class_name = original_class_name[original_class_name.rfind('.') + 1: len(original_class_name)]
            return original_class_name
        else:
            return obfuscated_class_name

    def process_class_mapping(self, class_name, new_class_name):
        """
        Implementations for MappingProcessor.
        """

        # Obfuscated class name -> original class name.
        self.class_map[new_class_name] = class_name

        return True

    def process_field_mapping(self, class_name, field_type, field_name, new_field_name):
        # Original class name -> obfuscated field names.
        field_map = self.class_field_map.get(class_name)
        if not field_map:
            field_map = dict()
            self.class_field_map[class_name] = field_map

        # Obfuscated field name -> fields.
        field_set = field_map.get(new_field_name)
        if not field_set:
            field_set = set()
            field_map[new_field_name] = field_set

        # Add the field information.
        field_set.add(FieldInfo(field_type, field_name))

    def process_method_mapping(self,
                               class_name,
                               first_line_number,
                               last_line_number,
                               method_return_type,
                               method_name,
                               method_arguments,
                               new_method_name):

        # Original class name -> obfuscated method names.
        method_map = self.class_method_map.get(class_name)
        if not method_map:
            method_map = dict()
            self.class_method_map[class_name] = method_map

        # Obfuscated method name -> methods.
        method_set = method_map.get(new_method_name)
        if not method_set:
            method_set = set()
            method_map[new_method_name] = method_set

        # Add the method information.
        method_set.add(MethodInfo(first_line_number,
                                  last_line_number,
                                  method_return_type,
                                  method_arguments,
                                  method_name))


class FieldInfo():
    """
    a field record
    """
    def __init__(self, type, original_name):
        self.type = type
        self.original_name = original_name

    def matches(self, type):
        return type is None or type is self.type


class MethodInfo():
    """
    A Method record
    """

    def __init__(self, first_line_number, last_line_number, type, arguments, original_name):
        self.first_line_number = first_line_number
        self.last_line_number = last_line_number
        self.type = type
        self.arguments = arguments
        self.original_name = original_name

    def matches(self, line_number, type, arguments):
        return (line_number == 0 or (
            self.first_line_number <= line_number and line_number <= self.last_line_number) or self.last_line_number == 0) and \
               (type is None or type == self.type) and \
               (arguments is None or arguments == self.arguments)


CLASS_PACKAGE_SEPARATOR = '.'
JAVA_PACKAGE_SEPARATOR = '/'


def external_class_name(internal_class_name):
    """
    Converts an external class name into an internal class name.
    @param externalClassName the external class name, e.g. "<code>java.lang.Object</code>"
    @return the internal class name,  e.g. "<code>java/lang/Object</code>".
    """

    return internal_class_name.replace(JAVA_PACKAGE_SEPARATOR, CLASS_PACKAGE_SEPARATOR)


def parse_args():
    parser = argparse.ArgumentParser(description='Filter logcat by package name')
    parser.add_argument("--regex", "-r", dest="regex", default=STACK_TRACE_EXPRESSION,
                        help="regex to match upon")
    parser.add_argument("--verbose", "-v", action="store_true", dest="verbose", default=False,
                        help="print verbose log")
    parser.add_argument("--mapping", "-m", dest="mapping_file", default=None, required=True,
                        help="mapping file to deobfuscate against")
    parser.add_argument("--stacktrace", "-s", dest="stacktrace_file", default=None,
                        help="stack trace to deobfuscate. If none provided, Retrace will deobfuscate standard input")

    options = parser.parse_args()

    return options


def main():
    options = parse_args()
    retrace = Retrace(options.mapping_file, options.verbose, options.regex, options.stacktrace_file)
    retrace.execute()


if __name__ == "__main__":
    main()
