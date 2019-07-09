from __future__ import print_function

import sys


class MappingReader():
    def __init__(self, mapping_file):
        self.mapping_file = mapping_file

    def pump(self, mapping_processor):

        reader = open(self.mapping_file, 'r')

        try:
            class_name = None

            # Read the subsequent class mappings and class member mappings.
            while True:
                line = reader.readline()

                if not line:
                    break

                line = line.strip()

                # The distinction between a class mapping and a class
                # member mapping is the initial whitespace.
                if line.endswith(':'):
                    # Process the class mapping and remember the class's
                    # old name.
                    class_name = self.process_class_mapping(line, mapping_processor)
                elif class_name is not None:
                    # Process the class member mapping, in the context of the
                    # current old class name.
                    self.process_class_member_mapping(class_name, line, mapping_processor)

        except Exception as ex:
            print('Can\'t process mapping file (%s)' % ex)
            sys.exit(1)
        finally:
            reader.close()

    @staticmethod
    def process_class_mapping(line, mapping_processor):

        # See if we can parse "___ -> ___:", containing the original
        # class name and the new class name.
        arrow_index = line.find('->')
        if arrow_index < 0:
            return None

        colon_index = line.find(':', arrow_index + 2)
        if colon_index < 0:
            return None

        # Extract the elements.
        class_name = line[0: arrow_index].strip()
        new_class_name = line[arrow_index + 2: colon_index].strip()

        # Process this class name mapping.
        interested = mapping_processor.process_class_mapping(class_name, new_class_name)

        if interested:
            return class_name
        else:
            return None

    @staticmethod
    def process_class_member_mapping(class_name, line, mapping_processor):
        # See if we can parse "___:___:___ ___(___) -> ___",
        # containing the optional line numbers, the return type, the original
        # field/method name, optional arguments, and the new field/method name.

        colon_index1 = line.find(':')
        colon_index2 = -1 if colon_index1 < 0 else line.find(':', colon_index1 + 1)
        space_index = line.find(' ', colon_index2 + 2)
        argument_index1 = line.find('(', space_index + 1)
        argument_index2 = -1 if argument_index1 < 0 else line.find(')', argument_index1 + 1)
        arrow_index = line.find('->', max(space_index, argument_index2) + 1)

        if space_index < 0 or arrow_index < 0:
            return

        # Extract the elements.
        type = line[colon_index2 + 1: space_index].strip()
        name = line[space_index + 1: argument_index1 if argument_index1 >= 0 else arrow_index].strip()
        new_name = line[arrow_index + 2: len(line)].strip()

        # Process this class member mapping.
        if len(type) > 0 and \
           len(name) > 0 and \
           len(new_name) > 0:

            # Is it a field or a method?
            if argument_index2 < 0:
                mapping_processor.process_field_mapping(class_name, type, name, new_name)
            else:
                first_line_number = 0
                last_line_number = 0

                if colon_index2 > 0:
                    first_line_number = int(line[0: colon_index1].strip())
                    last_line_number = int(line[colon_index1 + 1: colon_index2].strip())

                arguments = line[argument_index1 + 1: argument_index2].strip()

                mapping_processor.process_method_mapping(class_name,
                                                         first_line_number,
                                                         last_line_number,
                                                         type,
                                                         name,
                                                         arguments,
                                                         new_name)
