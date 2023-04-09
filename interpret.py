import sys
import xml.etree.ElementTree as ET
import argparse
import re
from dataclasses import dataclass
from typing import Generator, Dict, Callable, List, Tuple, TextIO, Any
from xml.etree.ElementTree import Element


class ArgumentParser:
    """Class for parsing arguments from command line"""

    def __init__(self):
        self.parser = argparse.ArgumentParser(prog='Interpret XML',
                                              description='Interprets XML code made by parse.php'
                                                          ' and outputs the result to stdout',
                                              epilog='(Jan Kalenda 2023)', add_help=False)
        self.parser.add_argument('--source', nargs="?", type=str, help='Source file')
        self.parser.add_argument('--input', nargs="?", type=str, help='Input file')
        self.parser.add_argument('--help', action="store_true", help='Prints this help')

    def parse(self) -> argparse.Namespace:
        """Parses arguments from command line

        :return: parsed arguments
        """
        args = self.parser.parse_args()
        if args.help and args.source is None and args.input is None:
            self.parser.print_help()
            sys.exit(0)
        elif args.help and (args.source is not None or args.input is not None):
            print("Error: Argument --help cannot be used with any other argument", file=sys.stderr)
            sys.exit(10)

        if args.source is None and args.input is None:
            self.parser.print_help()
            print("\nError: At least one of the arguments --source or --input must be present", file=sys.stderr)
            sys.exit(10)
        return args


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
            return ET.parse(self.args.source).getroot()
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
                                                "RETURN", "PUSHS", "POPS", "ADD", "SUB", "MUL", "IDIV", "LT", "GT",
                                                "EQ", "AND", "OR", "NOT", "INT2CHAR", "STRI2INT", "READ", "WRITE",
                                                "CONCAT", "STRLEN", "GETCHAR", "SETCHAR", "TYPE", "LABEL", "JUMP",
                                                "JUMPIFEQ", "JUMPIFNEQ", "EXIT", "DPRINT", "BREAK", "INT2FLOAT",
                                                "FLOAT2INT", "DIV"]:
            print("opcode bad", file=sys.stderr)
            sys.exit(32)
        if instruction.attrib["opcode"] in ["CREATEFRAME", "PUSHFRAME", "POPFRAME", "RETURN", "BREAK"]:
            if len(instruction) > 0:
                print(f"wrong arg count on instruction {instruction.tag}", file=sys.stderr)
                sys.exit(32)
        if instruction.attrib["opcode"] in ["CALL", "LABEL", "JUMP", "PUSHS", "EXIT",
                                            "DPRINT", "WRITE", "DEFVAR", "POPS"]:
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
        return open(self.args.input) if self.args.input is not None else None

    def get_instructions(self) -> Generator[Element, None, None]:
        """Yields instructions from XML file

        :return: iterator of instructions
        """
        self._check_xml()
        return self.root.iter("instruction")


class Instruction:
    """Class for storing instruction"""

    def __init__(self, instruction, index):
        self.instruction = instruction
        self.opcode = instruction.attrib['opcode']
        self.args = self._get_args(instruction)
        self.index = index

    @staticmethod
    def _get_args(instruction: Element) -> List[Element]:
        """Returns arguments of given instruction

        :param instruction: instruction
        :return: list of arguments
        """
        if int(instruction.attrib['order']) < 1:
            sys.exit(32)

        instruction = list(instruction)
        instruction.sort(key=lambda x: int(x.tag[3:]))

        return list(instruction)


@dataclass
class Variable:
    """Class for storing variable"""

    value: Any = None
    name: str = ""
    type: str = ""


class Frame:
    """Class for simulating frame"""

    def __init__(self):
        self.frame = {}

    def get(self, id: str) -> Variable:
        """Returns variable with given id

        :param id: id of variable
        :return: variable with given id
        """
        return self.frame[id] if id in self.frame.keys() else sys.exit(54)

    def add(self, var: str) -> None:
        """Adds variable to frame

        :param var: variable to add
        """
        self.frame[var] = Variable(name=var) if var not in self.frame.keys() else sys.exit(52)


class Interpret:
    """Class for interpreting IPPcode23 code"""

    def __init__(self):
        self.xml = XMLParser()
        self.instructions = list(self.xml.get_instructions())
        self.instructions.sort(key=lambda x: int(x.attrib['order']))
        self.instructions = [Instruction(instr, index) for index, instr in enumerate(self.instructions)]

        self.labels = self.__get_labels()
        self.input = self.xml.get_input()
        self.operations = self.__init_operations()
        self.temporary_frame = None
        self.frame_stack = []
        self.global_frame = Frame()
        self.call_stack = []
        self.data_stack = []

        self.current = iter(self.instructions)

    def run(self) -> None:
        """Runs the program"""
        try:
            while True:
                instruction = next(self.current)
                self.operations[instruction.opcode](instruction)
        except StopIteration:
            return

    def __process_input(self) -> str:
        """Processes input

        :return: input as string
        """
        if self.input is not None:
            return in_data if (in_data := self.input.readline()) != '' else "nil"

        try:
            return input()
        except EOFError:
            return "nil"

    def __process_output(self, var: Variable) -> None:
        """Processes output

        :param var: variable to be printed
        """
        if var.type == 'string':
            print(self.__parse_string(var.value), end='')
        elif var.type == 'int':
            print(var.value, end='')
        elif var.type == 'bool':
            print('true', end='') if var.value else print('false', end='')
        elif var.type == 'nil':
            print('', end='')
        elif var.type == 'float':
            print(var.value.hex(), end='')

    @staticmethod
    def __process_bool(value: str) -> bool | str:
        """Processes bool value

        :param value: value to be processed
        :return: processed value as bool, "nil" on bad value when reading
        """
        return True if value == 'true' else False

    @staticmethod
    def __int(value: str, read: bool = False) -> int | str:
        """Processes int value

        :param value: value to be processed
        :param read: if True, return "nil" on bad value
        :return: processed value as int, "nil" on bad value when reading
        """
        if re.match(r'^[+-]?0[Xx][a-fA-F0-9]+$', value):
            return int(value, 16)
        elif re.match(r'^[+-]?0[Oo]?[0-7]+$', value):
            return int(value, 8)
        elif re.match(r'^[+-]?\d+$', value):
            return int(value, 10)
        elif read:
            return "nil"
        else:
            print(f"bad int value {value}", file=sys.stderr)
            sys.exit(32)

    @staticmethod
    def __float(value: str, read: bool = False) -> float | str:
        """Processes float value

        :param value: value to be processed
        :param read: if True, return "nil" on bad value
        :return: processed value as float
        """
        if re.match(r'^[+-]?(\d*[.])?\d*$', value):
            return float(value)
        elif re.match(r'^[+-]?0[Xx][a-fA-F0-9]+$', value):
            return float.fromhex(value)
        elif re.match(r'^[+-]?\d+$', value):
            return float(value)
        elif re.match(r'^[+-]?(0[xX])?[01]\.?[0-9a-fA-F]*([pP][+-]?\d+)?$', value):
            return float.fromhex(value)
        elif read:
            return "nil"
        else:
            print(f"bad float value {value}", file=sys.stderr)
            sys.exit(32)

    def __get_labels(self) -> Dict[str, Instruction]:
        """Yields dictionary of labels

        :return: dictionary of labels
        """
        labels = {}
        for instruction in self.instructions:
            if instruction.opcode == 'LABEL':
                label = instruction.args[0].text
                labels[label] = instruction if label not in labels else sys.exit(52)
        return labels

    @staticmethod
    def __parse_string(string: str) -> str:
        """Parses string from IPPcode23 format

        :param string: string to be parsed
        :return: parsed string
        """
        return re.sub(r'\\(\d{3})', lambda x: chr(int(x.group(1))), string.replace("\n", ""))

    @staticmethod
    def __get_type(A: Any, B: Any) -> str:
        """Returns resulting type of an operation on 2 variables

        :param A: first variable
        :param B: second variable
        :return: resulting type of variables
        """
        if A == B:
            return A
        elif A == 'float' or B == 'float':
            return 'float'

    def __init_operations(self) -> Dict[str, Callable]:
        """Initializes dictionary of operations

        :return: dictionary of operations
        """
        return {
            "MOVE": self.__move,
            "CREATEFRAME": self.__createframe,
            "PUSHFRAME": self.__pushframe,
            "POPFRAME": self.__popframe,
            "DEFVAR": self.__defvar,
            "CALL": self.__call,
            "RETURN": self.__return,
            "PUSHS": self.__pushs,
            "POPS": self.__pops,
            "ADD": self.__add,
            "SUB": self.__sub,
            "MUL": self.__mul,
            "IDIV": self.__idiv,
            "DIV": self.__div,
            "LT": self.__lt,
            "GT": self.__gt,
            "EQ": self.__eq,
            "AND": self.__and,
            "OR": self.__or,
            "NOT": self.__not,
            "INT2CHAR": self.___int2char,
            "INT2FLOAT": self.__int2float,
            "FLOAT2INT": self.__float2int,
            "STRI2INT": self.__stri2int,
            "READ": self.__read,
            "WRITE": self.__write,
            "CONCAT": self.__concat,
            "STRLEN": self.__strlen,
            "GETCHAR": self.__getchar,
            "SETCHAR": self.__setchar,
            "TYPE": self.__type,
            "LABEL": self.__label,
            "JUMP": self.__jump,
            "JUMPIFEQ": self.__jumpifeq,
            "JUMPIFNEQ": self.__jumpifneq,
            "EXIT": self.__exit,
            "DPRINT": self.__dprint,
            "BREAK": self.__break,
        }

    def __get_frame(self, frame: str) -> Frame:
        """Yields frame based on frame tag

        exits with 55 if frame is not defined

        :param frame: frame tag
        :return: frame object
        """
        if frame == 'GF':
            return self.global_frame
        if frame == 'LF':
            if len(self.frame_stack) == 0:
                sys.exit(55)
            return self.frame_stack[-1]
        if frame == 'TF':
            if self.temporary_frame is None:
                sys.exit(55)
            return self.temporary_frame

    def __instruction_args(self, instruction: Instruction,
                          options: str = "",
                          first=False,
                          dest=False,
                          take_type=False) -> Tuple[Variable, List[Variable]]:
        """Returns list of arguments for instruction

        Exits with 53 if type is not compatible
        :param instruction: instruction
        :param options: string of types (int, string, bool, nil, float, type) as isbnft
        :param first: if first argument should be accounted for
        :param dest: destination variable should be accounted for, returns tuple
        :param take_type: if type is being checked
        :return: list of arguments or tuple when dest is True
        """
        arg = []
        limit = {"s": "string", "i": "int", "b": "bool", "n": "nil", "f": "float"}[options] if len(options) == 1 else ""
        start = 0 if first else 1
        if dest:
            if instruction.args[0].attrib['type'] != 'var' or len(instruction.args[0].text.split('@')) != 2:
                sys.exit(53)
            destination = \
                self.__get_frame(instruction.args[0].text.split('@')[0]).\
                get(instruction.args[0].text.split('@')[1]) if instruction.args[0].attrib['type'] == 'var' \
                else sys.exit(53)

        for i in instruction.args[start:]:
            if i.attrib['type'] == 'var' and not take_type:
                var = var if (var := self.__get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])).type != "" \
                    else sys.exit(56)
                arg.append(var) if limit in (var.type, "") else sys.exit(53)
            elif i.attrib['type'] == 'var' and take_type:
                var = var if (var := self.__get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])) \
                    else sys.exit(56)
                arg.append(var)
            elif i.attrib['type'] == 'string' and 's' in options:
                arg.append(Variable(value=self.__parse_string(i.text), type='string'))
            elif i.attrib['type'] == 'int' and 'i' in options:
                arg.append(Variable(value=self.__int(i.text), type='int'))
            elif i.attrib['type'] == 'bool' and 'b' in options:
                arg.append(Variable(value=self.__process_bool(i.text), type='bool'))
            elif i.attrib['type'] == 'nil' and 'n' in options:
                arg.append(Variable(value=i.text, type='nil'))
            elif i.attrib['type'] == 'float' and 'f' in options:
                arg.append(Variable(value=self.__float(i.text), type='float'))
            elif i.attrib['type'] == 'type' and 't' in options:
                arg.append(Variable(value=i.text, type='type'))
            else:
                sys.exit(53)
        return (destination, arg) if dest else arg

    def __move(self, instruction: Instruction) -> None:
        """Moves value into a variable

        Exits with 56 if variable is not defined

        :param instruction: MOVE instruction to be processed
        """
        dest, arg = self.__instruction_args(instruction, "isbnf", dest=True)
        dest.value, dest.type = arg[0].value, arg[0].type

    def __createframe(self, instruction: Instruction) -> None:
        """Creates temporary frame"""
        self.temporary_frame = Frame()

    def __pushframe(self, instruction: Instruction) -> None:
        """Pushes temporary frame into frame stack

        Exits with 55 if temporary frame is not defined
        """
        self.frame_stack.append(self.temporary_frame) if self.temporary_frame is not None else sys.exit(55)
        self.temporary_frame = None

    def __popframe(self, instruction: Instruction) -> None:
        """Pops frame from frame stack and sets it as temporary frame

        Exits with 55 if frame stack is empty
        """
        self.temporary_frame = self.frame_stack.pop() if len(self.frame_stack) > 0 else sys.exit(55)

    def __defvar(self, instruction: Instruction) -> None:
        """Defines variable in a frame"""
        var = instruction.args[0].text.split('@')
        if instruction.args[0].attrib['type'] != 'var' or len(var) != 2:
            sys.exit(53)
        self.__get_frame(var[0]).add(var[1]) if len(var) == 2 else sys.exit(52)

    def __call(self, instruction: Instruction) -> None:
        """Stores current instruction and jumps to label

        Exits with 52 if label is not defined
        """
        label = instruction.args[0].text
        self.call_stack.append(self.current) if label in self.labels else sys.exit(52)
        self.current = iter(self.instructions[self.labels[label].index:])

    def __return(self, instruction: Instruction) -> None:
        """Returns to instruction stored in call stack

        Exits with 56 if call stack is empty
        """
        self.current = self.call_stack.pop() if len(self.call_stack) > 0 else sys.exit(56)

    def __pushs(self, instruction: Instruction) -> None:
        """Pushes value onto data stack

        Exits with 56 if variable is not defined
        """
        self.data_stack.append(self.__instruction_args(instruction, "isbnf", first=True)[0])

    def __pops(self, instruction: Instruction) -> None:
        """Pops value from data stack and stores it in variable

        Exits with 56 if data stack is empty
        """
        dest, _ = self.__instruction_args(instruction, "", dest=True)
        popped = self.data_stack.pop() if len(self.data_stack) > 0 else sys.exit(56)
        dest.value, dest.type = popped.value, popped.type

    def __add(self, instruction: Instruction) -> None:
        """Adds two values and stores them in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "if", dest=True)
        dest.value, dest.type = arg[0].value + arg[1].value, self.__get_type(arg[0].type, arg[1].type)

    def __sub(self, instruction: Instruction) -> None:
        """Subtracts two values and stores them in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "if", dest=True)
        dest.value, dest.type = arg[0].value - arg[1].value, self.__get_type(arg[0].type, arg[1].type)

    def __mul(self, instruction: Instruction) -> None:
        """Multiplies two values and stores them in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "if", dest=True)
        dest.value, dest.type = arg[0].value * arg[1].value, self.__get_type(arg[0].type, arg[1].type)

    def __div(self, instruction: Instruction) -> None:
        """Divides two values and stores them in variable

        Exits with 53 if types are not compatible
        Exits with 57 if dividing by zero
        """
        dest, arg = self.__instruction_args(instruction, "if", dest=True)
        dest.value = arg[0].value / arg[1].value if arg[1].value != 0 else sys.exit(57)
        dest.type = 'float'

    def __idiv(self, instruction: Instruction) -> None:
        """Divides two values and stores them in variable

        Exits with 53 if types are not compatible
        Exits with 57 if dividing by zero
        """
        dest, arg = self.__instruction_args(instruction, "i", dest=True)
        dest.value = arg[0].value // arg[1].value if arg[1].value != 0 else sys.exit(57)
        dest.type = 'int'

    def __lt(self, instruction: Instruction) -> None:
        """Compares whether arg1 is lesser than arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "ibsf", dest=True)
        dest.value = arg[0].value < arg[1].value if arg[0].type == arg[1].type else sys.exit(53)
        dest.type = 'bool'

    def __gt(self, instruction: Instruction) -> None:
        """Compares whether arg1 is greater than arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "ibsf", dest=True)
        dest.value = arg[0].value > arg[1].value if arg[0].type == arg[1].type else sys.exit(53)
        dest.type = 'bool'

    def __eq(self, instruction: Instruction) -> None:
        """Compares whether arg1 and arg2 are equal and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "ibsnf", dest=True)
        dest.type = 'bool'

        if arg[0].type == 'nil' and arg[1].type == 'nil':
            dest.value = True
            return
        if arg[0].type == 'nil' or arg[1].type == 'nil':
            dest.value = False
            return

        dest.value = arg[0].value == arg[1].value if arg[0].type == arg[1].type else sys.exit(53)

    def __and(self, instruction: Instruction) -> None:
        """Performs logical and on arg1 and arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "b", dest=True)
        dest.value, dest.type = arg[0].value and arg[1].value, "bool"

    def __or(self, instruction: Instruction) -> None:
        """Performs logical or on arg1 and arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "b", dest=True)
        dest.value, dest.type = arg[0].value or arg[1].value, "bool"

    def __not(self, instruction: Instruction) -> None:
        """Performs logical not on arg1 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "b", dest=True)
        dest.value, dest.type = not arg[0].value, "bool"

    def ___int2char(self, instruction: Instruction) -> None:
        """Converts int to char and stores result in variable

        Exits with 53 if types are not compatible
        Exits with 58 if int is not in range of chr()
        """
        dest, arg = self.__instruction_args(instruction, "i", dest=True)

        dest.value, dest.type = \
            chr(arg[0].value), "string" if arg[0].value < 0 or arg[0].value > 1114111 else sys.exit(58)

    def __float2int(self, instruction: Instruction) -> None:
        """Converts float to int and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "f", dest=True)
        if arg[0].type != 'float':
            sys.exit(53)

        dest.value, dest.type = int(arg[0].value), "int"

    def __int2float(self, instruction: Instruction) -> None:
        """Converts int to float and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "i", dest=True)
        if arg[0].type != 'int':
            sys.exit(53)

        dest.value, dest.type = float(arg[0].value), "float"

    def __stri2int(self, instruction: Instruction) -> None:
        """Converts char to int and stores result in variable

        Exits with 53 if types are not compatible
        Exits with 58 if index is out of range or char is not in range of ord()
        """
        if instruction.args[0].attrib['type'] != 'var':
            sys.exit(53)

        dest, arg = self.__instruction_args(instruction, "is", dest=True)
        if arg[0].type != 'string' or arg[1].type != 'int':
            sys.exit(53)

        if arg[1].value < 0 or arg[1].value >= len(arg[0].value):
            sys.exit(58)

        dest.value, dest.type = ord(arg[0].value[arg[1].value]), 'int'

    def __read(self, instruction: Instruction) -> None:
        """Reads input from stdin and stores it in variable"""
        dest, type = self.__instruction_args(instruction, "it", dest=True)

        dest = self.__get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        in_data = self.__process_input()
        if in_data == "nil":
            dest.value, dest.type = "nil", "nil"
        elif type[0].value == 'int':
            dest.value = self.__int(in_data.strip(), read=True)
            dest.type = 'int' if dest.value != "nil" else 'nil'
        elif type[0].value == 'bool':
            dest.value, dest.type = self.__process_bool(in_data), 'bool'
        elif type[0].value == 'string':
            dest.value, dest.type = self.__parse_string(in_data), 'string'
        elif type[0].value == 'float':
            dest.value = self.__float(in_data.strip(), read=True)
            dest.type = 'float' if dest.value != "nil" else 'nil'

    def __write(self, instruction: Instruction) -> None:
        """Writes value of variable to stdout"""
        for var in self.__instruction_args(instruction, "isbnf", first=True):
            self.__process_output(var)

    def __concat(self, instruction: Instruction) -> None:
        """Concatenates two strings and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "s", dest=True)
        dest.value, dest.type = arg[0].value + arg[1].value, "string"

    def __strlen(self, instruction: Instruction) -> None:
        """Gets length of string and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "s", dest=True)
        dest.value, dest.type = len(arg[0].value), "int"

    def __getchar(self, instruction: Instruction) -> None:
        """Gets character from string at given index and stores it in variable

        Exits with 58 if index is out of bounds
        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "si", dest=True)

        if arg[0].type != 'string' or arg[1].type != 'int':
            sys.exit(53)

        if arg[1].value < 0 or arg[1].value >= len(arg[0].value):
            sys.exit(58)

        dest.value, dest.type = arg[0].value[arg[1].value], 'string'

    def __setchar(self, instruction: Instruction) -> None:
        """Sets character in string at given index to given character

        Exits with 58 if index is out of bounds
        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "is", dest=True)
        if dest.type != 'string' or arg[0].type != 'int' or arg[1].type != 'string':
            sys.exit(53)

        if len(arg[1].value) == 0 or arg[0].value < 0 or arg[0].value >= len(dest.value):
            sys.exit(58)

        dest.value = \
            "".join(list(dest.value)[:arg[0].value] + [arg[1].value[0]] + list(dest.value)[arg[0].value + 1:])
        dest.type = 'string'

    def __type(self, instruction: Instruction) -> None:
        """Gets type of variable and stores it in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "isbnf", dest=True, take_type=True)
        dest.value, dest.type = arg[0].type, "string"

    def __label(self, instruction: Instruction) -> None:
        """Creates label"""

    def __jump(self, instruction: Instruction) -> None:
        """Jumps to label

        Exits with 52 if label does not exist
        """
        if instruction.args[0].text not in self.labels:
            sys.exit(52)
        self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])

    def __jumpifeq(self, instruction: Instruction) -> None:
        """Jumps to label if values are equal

        Exits with 52 if label does not exist
        Exits with 53 if types are not compatible
        """
        if instruction.args[0].text not in self.labels:
            sys.exit(52)
        arg = self.__instruction_args(instruction, "isbnf")

        if arg[0].type == arg[1].type:
            if arg[0].value == arg[1].value:
                self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])
        elif arg[0].type == 'nil' or arg[1].type == 'nil':
            pass
        else:
            sys.exit(53)

    def __jumpifneq(self, instruction: Instruction) -> None:
        """Jumps to label if values are not equal

        Exits with 52 if label does not exist
        Exits with 53 if types are not compatible
        """
        if instruction.args[0].text not in self.labels:
            sys.exit(52)
        arg = self.__instruction_args(instruction, "isbnf")

        if arg[0].type == arg[1].type:
            if arg[0].value != arg[1].value:
                self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])
        elif arg[0].type == 'nil' or arg[1].type == 'nil':
            self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])
        else:
            sys.exit(53)

    def __exit(self, instruction: Instruction) -> None:
        """Exits program

        Exits with 57 if value is not in range 0-49
        """
        arg = self.__instruction_args(instruction, "i", first=True)
        sys.exit(arg[0].value) if 0 <= arg[0].value <= 49 else sys.exit(57)

    def __dprint(self, instruction: Instruction) -> None:
        """Prints value to stderr"""
        print(self.__instruction_args(instruction, "isbnf", first=True)[0].value, file=sys.stderr)

    def __break(self, instruction: Instruction) -> None:
        """Prints debug information"""
        print('BREAK', file=sys.stderr)
        print('Current instruction', instruction.instruction.attrib['order'], file=sys.stderr)
        print('GF', file=sys.stderr)
        for i in self.global_frame.frame:
            print(i.name, i.value, i.type, file=sys.stderr)
        print('LF', file=sys.stderr)
        if len(self.frame_stack) != 0:
            for i in self.__get_frame('LF').frame:
                print(i.name, i.value, i.type, file=sys.stderr)
        print('TF', file=sys.stderr)
        if self.temporary_frame is not None:
            for i in self.temporary_frame.frame:
                print(i.name, i.value, i.type, file=sys.stderr)


if __name__ == '__main__':
    Interpret().run()
