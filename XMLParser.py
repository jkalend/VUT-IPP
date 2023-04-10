import sys
import xml.etree.ElementTree as ET
from typing import Generator, TextIO
from xml.etree.ElementTree import Element

from argument_parse import ArgumentParser


class XMLParser:
    """Class for parsing XML file"""

    def __init__(self):
        self.args = ArgumentParser().parse()
        self.root = self._parse()
        self.orders = []

    def _parse(self) -> ET.Element:
        """Parses XML file

        :return: root of XML file
        """
        if self.args.source is None:
            try:
                return ET.fromstring(self._load_xml())
            except ET.ParseError:
                print("Error: XML file is not valid", file=sys.stderr)
                sys.exit(31)

        try:
            return ET.parse(self.args.source[0]).getroot()
        except ET.ParseError:
            print("Error: XML file is not valid", file=sys.stderr)
            sys.exit(31)
        except FileNotFoundError:
            print("Error: XML file not found", file=sys.stderr)
            sys.exit(11)

    @staticmethod
    def _load_xml() -> str:
        """Loads XML file from stdin

        :return: XML file as string
        """
        return sys.stdin.read()

    def _check_xml(self) -> None:
        """Checks XML file for validity"""
        self._check_root()
        for i in self.root:
            self._check_instructions(i)
            self._check_args(i)

    def _check_root(self) -> None:
        """Checks root of XML file for validity"""
        for i in self.root.attrib:
            if i not in ["name", "description", "language"]:
                print("bad attribute for program", file=sys.stderr)
                sys.exit(32)

        if "language" not in self.root.attrib or self.root.attrib["language"].lower() != "ippcode23":
            print("language bad", file=sys.stderr)
            sys.exit(32)

    def _check_instructions(self, instruction: Element) -> None:
        """Checks instructions for validity

        :param instruction: instruction to check
        """
        if instruction.tag != "instruction":
            print("instr bad", file=sys.stderr)
            sys.exit(32)
        if "order" not in instruction.attrib or "opcode" not in instruction.attrib:
            print("order/opcode missing", file=sys.stderr)
            sys.exit(32)
        if not instruction.attrib["order"].isdigit() or int(instruction.attrib["order"]) < 0:
            print("order not digit or negative", file=sys.stderr)
            sys.exit(32)

        instruction.attrib["opcode"] = instruction.attrib["opcode"].upper()

        if instruction.attrib["opcode"] not in ["MOVE", "CREATEFRAME", "PUSHFRAME", "POPFRAME", "DEFVAR", "CALL",
                                                "RETURN", "PUSHS", "POPS", "ADD", "ADDS", "SUB", "SUBS", "MUL", "MULS",
                                                "IDIV", "IDIVS", "LT", "LTS", "GT", "GTS", "EQ", "EQS", "AND", "ANDS",
                                                "OR", "ORS", "NOT", "NOTS", "INT2CHAR", "STRI2INT", "INT2CHARS",
                                                "STRI2INTS", "READ", "WRITE", "CONCAT", "STRLEN", "GETCHAR", "SETCHAR",
                                                "TYPE", "LABEL", "JUMP", "JUMPIFEQ", "JUMPIFNEQ", "JUMPIFEQS",
                                                "JUMPIFNEQS", "EXIT", "DPRINT", "BREAK", "INT2FLOAT", "INT2FLOATS",
                                                "FLOAT2INT", "FLOAT2INTS", "DIV", "DIVS", "CLEARS"]:
            print("opcode bad", file=sys.stderr)
            sys.exit(32)
        if instruction.attrib["opcode"] in ["CREATEFRAME", "PUSHFRAME", "POPFRAME", "RETURN", "BREAK", "ADDS", "SUBS",
                                            "MULS", "IDIVS", "LTS", "GTS", "EQS", "ANDS", "ORS", "NOTS", "INT2CHARS",
                                            "STRI2INTS", "INT2FLOATS", "FLOAT2INTS", "DIVS", "CLEARS"]:
            if len(instruction) > 0:
                print(f"wrong arg count on instruction {instruction.tag}", file=sys.stderr)
                sys.exit(32)
        if instruction.attrib["opcode"] in ["CALL", "LABEL", "JUMP", "PUSHS", "EXIT", "DPRINT",
                                            "WRITE", "DEFVAR", "POPS", "JUMPIFEQS", "JUMPIFNEQS"]:
            if len(instruction) != 1:
                print(f"wrong arg count on instruction {instruction.tag}", file=sys.stderr)
                sys.exit(32)
        if instruction.attrib["opcode"] in ["MOVE", "INT2CHAR", "STRLEN", "TYPE",
                                            "NOT", "READ", "INT2FLOAT", "FLOAT2INT"]:
            if len(instruction) != 2:
                print(f"wrong arg count on instruction {instruction.tag}", file=sys.stderr)
                sys.exit(32)
        if instruction.attrib["opcode"] in ["ADD", "SUB", "MUL", "IDIV", "DIV", "LT", "GT", "EQ", "AND", "OR",
                                            "STRI2INT", "CONCAT", "GETCHAR", "SETCHAR", "JUMPIFEQ", "JUMPIFNEQ"]:
            if len(instruction) != 3:
                print(f"wrong arg count on instruction {instruction.tag}", file=sys.stderr)
                sys.exit(32)
        if instruction.attrib["order"] in self.orders:
            print(f"order {instruction.attrib['order']} already used", file=sys.stderr)
            sys.exit(32)
        self.orders.append(instruction.attrib["order"])

    @staticmethod
    def _check_args(instruction: Element) -> None:
        """Checks arguments for validity

        :param instruction: instruction to check
        """
        indexes = []

        for arg in instruction:
            if len(arg.tag) < 4 or not arg.tag[3:].isnumeric() or not arg.tag.startswith("arg"):
                print(f"bad arg tag {arg.tag}", file=sys.stderr)
                sys.exit(32)

            indexes.append(int(arg.tag[3:]))

            if "type" not in arg.attrib:
                print(f"type missing for arg {arg.tag}", file=sys.stderr)
                sys.exit(32)
            if arg.attrib["type"] not in ["var", "label", "nil", "int", "bool", "string", "type", "float"]:
                print(f"type bad for arg {arg.tag}", file=sys.stderr)
                sys.exit(32)
            if arg.text is None:
                print(f"text missing for arg {arg.tag}", file=sys.stderr)
                sys.exit(32)

        for i in range(1, len(indexes) + 1):
            if i not in indexes:
                print(f"arg {i} missing", file=sys.stderr)
                sys.exit(32)

    def get_input(self) -> TextIO:
        """Returns input file

        :return: input file or None
        """
        return open(self.args.input[0]) if self.args.input is not None else None

    def get_instructions(self) -> Generator[Element, None, None]:
        """Yields instructions from XML file

        :return: iterator of instructions
        """
        self._check_xml()
        return self.root.iter("instruction")
