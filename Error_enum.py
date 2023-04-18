# IPP 2023 project 2
# Author: Jan Kalenda
# Login: xkalen07

from enum import IntEnum
import sys


class Error(IntEnum):
    Missing_parameter = 10
    Cant_open_file = 11
    Cant_write_file = 12
    Invalid_XML = 31
    Invalid_XML_structure = 32
    Semantic_error = 52
    Invalid_type = 53
    Nonexistent_variable = 54
    Frame_not_found = 55
    Missing_value = 56
    Invalid_value = 57
    Bad_string_operation = 58

    @staticmethod
    def exit(value: int, description: str = ""):
        print("Error: " + description, file=sys.stderr) if description != "" else None
        sys.exit(value)
