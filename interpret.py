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
                                              epilog='At least one of the arguments --source or --input must be present'
                                                     ' (Jan Kalenda 2023)'
                                              )
        self.parser.add_argument('--source', nargs="?", type=str, help='Source file')
        self.parser.add_argument('--input', nargs="?", type=str, help='Input file')

    def parse(self) -> argparse.Namespace:
        """Parses arguments from command line

        :return: parsed arguments
        """
        args = self.parser.parse_args()
        if args.source is None and args.input is None:
            self.parser.error('At least one of the arguments --source or --input must be present')
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
        except (ET.ParseError, FileNotFoundError):
            print("Error: XML file is not valid", file=sys.stderr)
            sys.exit(31)

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
        if instruction.attrib["opcode"] not in ["MOVE", "CREATEFRAME", "PUSHFRAME", "POPFRAME", "DEFVAR", "CALL",
                                                "RETURN", "PUSHS", "POPS", "ADD", "SUB", "MUL", "IDIV", "LT", "GT",
                                                "EQ", "AND", "OR", "NOT", "INT2CHAR", "STRI2INT", "READ", "WRITE",
                                                "CONCAT", "STRLEN", "GETCHAR", "SETCHAR", "TYPE", "LABEL", "JUMP",
                                                "JUMPIFEQ", "JUMPIFNEQ", "EXIT", "DPRINT", "BREAK"]:
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
        if instruction.attrib["opcode"] in ["MOVE", "INT2CHAR", "STRLEN", "TYPE", "NOT", "READ"]:
            if len(instruction) != 2:
                print(f"wrong arg count on instruction {instruction.tag}", file=sys.stderr)
                sys.exit(32)
        if instruction.attrib["opcode"] in ["ADD", "SUB", "MUL", "IDIV", "LT", "GT", "EQ", "AND", "OR", "STRI2INT",
                                            "CONCAT", "GETCHAR", "SETCHAR", "JUMPIFEQ", "JUMPIFNEQ"]:
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
            try:
                indexes.append(int(arg.tag[3:]))
            except ValueError:
                print(f"bad arg tag {arg.tag}", file=sys.stderr)
                sys.exit(32)
            if not arg.tag.startswith("arg"):
                print(f"bad arg tag {arg.tag}", file=sys.stderr)
                sys.exit(32)
            if "type" not in arg.attrib:
                print(f"type missing for arg {arg.tag}", file=sys.stderr)
                sys.exit(32)
            if arg.attrib["type"] not in ["var", "symb", "label", "type", "nil", "int", "bool", "string"]:
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
        self.frame[var] = Variable(name=var)


class Interpret:
    """Class for interpreting IPPcode23 code"""

    def __init__(self):
        self.xml = XMLParser()
        self.instructions = list(self.xml.get_instructions())
        self.instructions.sort(key=lambda x: int(x.attrib['order']))
        self.instructions = [Instruction(instr, index) for index, instr in enumerate(self.instructions)]

        self.labels = self._get_labels()
        self.input = self.xml.get_input()
        self.operations = self._init_operations()
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

    def _process_input(self) -> str:
        """Processes input

        :return: input as string
        """
        if self.input is not None:
            return in_data if (in_data := self.input.readline()) != '' else "nil"

        try:
            return input()
        except EOFError:
            return "nil"

    def _process_output(self, var: Variable) -> None:
        """Processes output

        :param var: variable to be printed
        """
        if var.type == 'string':
            print(self._parse_string(var.value), end='')
        elif var.type == 'int':
            print(var.value, end='')
        elif var.type == 'bool':
            print('true', end='') if var.value else print('false', end='')
        elif var.type == 'nil':
            print('', end='')

    @staticmethod
    def _process_bool(value: str) -> bool:
        """Processes bool value

        :param value: value to be processed
        :return: processed value as bool
        """
        return True if value == 'true' else False

    @staticmethod
    def _int(value: str) -> int:
        """Processes int value

        :param value: value to be processed
        :return: processed value as int
        """
        if re.match(r'^[+-]?0[Xx]', value):
            return int(value, 16)
        if re.match(r'^[+-]?0[Oo]?', value):
            return int(value, 8)
        else:
            try:
                return int(value)
            except ValueError:
                print(f"bad int value {value}", file=sys.stderr)
                sys.exit(32)

    def _get_labels(self) -> Dict[str, Instruction]:
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
    def _parse_string(string: str) -> str:
        """Parses string from IPPcode23 format

        :param string: string to be parsed
        :return: parsed string
        """
        return re.sub(r'\\(\d{3})', lambda x: chr(int(x.group(1))), string.strip())

    def _init_operations(self) -> Dict[str, Callable]:
        """Initializes dictionary of operations

        :return: dictionary of operations
        """
        return {
            "MOVE": self._move,
            "CREATEFRAME": self._createframe,
            "PUSHFRAME": self._pushframe,
            "POPFRAME": self._popframe,
            "DEFVAR": self._defvar,
            "CALL": self._call,
            "RETURN": self._return,
            "PUSHS": self._pushs,
            "POPS": self._pops,
            "ADD": self._add,
            "SUB": self._sub,
            "MUL": self._mul,
            "IDIV": self._idiv,
            "LT": self._lt,
            "GT": self._gt,
            "EQ": self._eq,
            "AND": self._and,
            "OR": self._or,
            "NOT": self._not,
            "INT2CHAR": self._int2char,
            "STRI2INT": self._stri2int,
            "READ": self._read,
            "WRITE": self._write,
            "CONCAT": self._concat,
            "STRLEN": self._strlen,
            "GETCHAR": self._getchar,
            "SETCHAR": self._setchar,
            "TYPE": self._type,
            "LABEL": self._label,
            "JUMP": self._jump,
            "JUMPIFEQ": self._jumpifeq,
            "JUMPIFNEQ": self._jumpifneq,
            "EXIT": self._exit,
            "DPRINT": self._dprint,
            "BREAK": self._break,
        }

    def _get_frame(self, frame: str) -> Frame:
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

    def _instruction_args(self, instruction: Instruction,
                          options: str = "",
                          first=False,
                          dest=False,
                          take_type=False) -> Tuple[Variable, List[Variable]]:
        """Returns list of arguments for instruction

        Exits with 53 if type is not compatible
        :param instruction: instruction
        :param options: string of types (int, string, bool, nil) as isbn
        :param first: if first argument should be accounted for
        :param dest: destination variable should be accounted for, returns tuple
        :param take_type: if type is being checked
        :return: list of arguments or tuple when dest is True
        """
        arg = []
        limit = {"s": "string", "i": "int", "b": "bool", "n": "nil"}[options] if len(options) == 1 else ""
        start = 0 if first else 1
        if dest:
            destination = \
                self._get_frame(instruction.args[0].text.split('@')[0]).\
                get(instruction.args[0].text.split('@')[1]) if instruction.args[0].attrib['type'] == 'var' \
                else sys.exit(53)

        for i in instruction.args[start:]:
            if i.attrib['type'] == 'var' and not take_type:
                var = var if (var := self._get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])).type != "" \
                    else sys.exit(56)
                arg.append(var) if limit in (var.type, "") else sys.exit(53)
            elif i.attrib['type'] == 'var' and take_type:
                var = var if (var := self._get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])) \
                    else sys.exit(56)
                arg.append(var)
            elif i.attrib['type'] == 'string' and 's' in options:
                arg.append(Variable(value=self._parse_string(i.text), type='string'))
            elif i.attrib['type'] == 'int' and 'i' in options:
                arg.append(Variable(value=self._int(i.text), type='int'))
            elif i.attrib['type'] == 'bool' and 'b' in options:
                arg.append(Variable(value=self._process_bool(i.text), type='bool'))
            elif i.attrib['type'] == 'nil' and 'n' in options:
                arg.append(Variable(value=i.text, type='nil'))
            else:
                sys.exit(53)
        return (destination, arg) if dest else arg

    def _move(self, instruction: Instruction) -> None:
        """Moves value into a variable

        Exits with 56 if variable is not defined

        :param instruction: MOVE instruction to be processed
        """
        if instruction.args[0].attrib['type'] != 'var':
            sys.exit(53)
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = instruction.args[1]
        if arg.attrib['type'] == 'var':
            var = var if (var := self._get_frame(arg.text.split('@')[0]).get(arg.text.split('@')[1])).type != ""\
                else sys.exit(56)
            dest.value, dest.type = var.value, var.type
        elif arg.attrib['type'] == 'int':
            dest.value, dest.type = self._int(arg.text), 'int'
        elif arg.attrib['type'] == 'bool':
            dest.value, dest.type = self._process_bool(arg.text), 'bool'
        elif arg.attrib['type'] == 'string':
            dest.value, dest.type = self._parse_string(arg.text), 'string'
        elif arg.attrib['type'] == 'nil':
            dest.value, dest.type = 'nil', 'nil'
        else:
            sys.exit(53)

    def _createframe(self, instruction: Instruction) -> None:
        """Creates temporary frame"""
        self.temporary_frame = Frame()

    def _pushframe(self, instruction: Instruction) -> None:
        """Pushes temporary frame into frame stack

        Exits with 55 if temporary frame is not defined
        """
        self.frame_stack.append(self.temporary_frame) if self.temporary_frame is not None else sys.exit(55)
        self.temporary_frame = None

    def _popframe(self, instruction: Instruction) -> None:
        """Pops frame from frame stack and sets it as temporary frame

        Exits with 55 if frame stack is empty
        """
        self.temporary_frame = self.frame_stack.pop() if len(self.frame_stack) > 0 else sys.exit(55)

    def _defvar(self, instruction: Instruction) -> None:
        """Defines variable in a frame"""
        var = instruction.args[0].text.split('@')
        if instruction.args[0].attrib['type'] != 'var':
            sys.exit(53)
        self._get_frame(var[0]).add(var[1]) if len(var) == 2 else sys.exit(52)

    def _call(self, instruction: Instruction) -> None:
        """Stores current instruction and jumps to label

        Exits with 52 if label is not defined
        """
        label = instruction.args[0].text
        if label not in self.labels:
            sys.exit(52)
        self.call_stack.append(self.current)
        self.current = iter(self.instructions[self.labels[label].index:])

    def _return(self, instruction: Instruction) -> None:
        """Returns to instruction stored in call stack

        Exits with 56 if call stack is empty
        """
        self.current = self.call_stack.pop() if len(self.call_stack) > 0 else sys.exit(56)

    def _pushs(self, instruction: Instruction) -> None:
        """Pushes value onto data stack

        Exits with 56 if variable is not defined
        """
        self.data_stack.append(self._instruction_args(instruction, "isbn", first=True)[0])

    def _pops(self, instruction: Instruction) -> None:
        """Pops value from data stack and stores it in variable

        Exits with 56 if data stack is empty
        """
        dest, _ = self._instruction_args(instruction, "", dest=True)
        popped = self.data_stack.pop() if len(self.data_stack) > 0 else sys.exit(56)
        dest.value, dest.type = popped.value, popped.type

    def _add(self, instruction: Instruction) -> None:
        """Adds two values and stores them in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self._instruction_args(instruction, "i", dest=True)
        dest.value, dest.type = arg[0].value + arg[1].value, 'int'

    def _sub(self, instruction: Instruction) -> None:
        """Subtracts two values and stores them in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self._instruction_args(instruction, "i", dest=True)
        dest.value, dest.type = arg[0].value - arg[1].value, 'int'

    def _mul(self, instruction: Instruction) -> None:
        """Multiplies two values and stores them in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self._instruction_args(instruction, "i", dest=True)
        dest.value, dest.type = arg[0].value * arg[1].value, 'int'

    def _idiv(self, instruction: Instruction) -> None:
        """Divides two values and stores them in variable

        Exits with 53 if types are not compatible
        Exits with 57 if dividing by zero
        """
        dest, arg = self._instruction_args(instruction, "i", dest=True)
        dest.value = arg[0].value // arg[1].value if arg[1].value != 0 else sys.exit(57)
        dest.type = 'int'

    def _lt(self, instruction: Instruction) -> None:
        """Compares whether arg1 is lesser than arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self._instruction_args(instruction, "ibs", dest=True)
        dest.value = arg[0].value < arg[1].value if arg[0].type == arg[1].type else sys.exit(53)
        dest.type = 'bool'

    def _gt(self, instruction: Instruction) -> None:
        """Compares whether arg1 is greater than arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self._instruction_args(instruction, "ibs", dest=True)
        dest.value = arg[0].value > arg[1].value if arg[0].type == arg[1].type else sys.exit(53)
        dest.type = 'bool'

    def _eq(self, instruction: Instruction) -> None:
        """Compares whether arg1 and arg2 are equal and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self._instruction_args(instruction, "ibsn", dest=True)
        dest.type = 'bool'

        if arg[0].type == 'nil' and arg[1].type == 'nil':
            dest.value = True
            return
        if arg[0].type == 'nil' or arg[1].type == 'nil':
            dest.value = False
            return

        dest.value = arg[0].value == arg[1].value if arg[0].type == arg[1].type else sys.exit(53)

    def _and(self, instruction: Instruction) -> None:
        """Performs logical and on arg1 and arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self._instruction_args(instruction, "b", dest=True)
        dest.value, dest.type = arg[0].value and arg[1].value, "bool"

    def _or(self, instruction: Instruction) -> None:
        """Performs logical or on arg1 and arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self._instruction_args(instruction, "b", dest=True)
        dest.value, dest.type = arg[0].value or arg[1].value, "bool"

    def _not(self, instruction: Instruction) -> None:
        """Performs logical not on arg1 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self._instruction_args(instruction, "b", dest=True)
        dest.value, dest.type = not arg[0].value, "bool"

    def _int2char(self, instruction: Instruction) -> None:
        """Converts int to char and stores result in variable

        Exits with 53 if types are not compatible
        Exits with 58 if int is not in range of chr()
        """
        dest, arg = self._instruction_args(instruction, "i", dest=True)

        try:
            dest.value, dest.type = chr(arg[0].value), "string"
        except ValueError:
            sys.exit(58)

    def _stri2int(self, instruction: Instruction) -> None:
        """Converts char to int and stores result in variable

        Exits with 53 if types are not compatible
        Exits with 58 if index is out of range or char is not in range of ord()
        """
        if instruction.args[0].attrib['type'] != 'var':
            sys.exit(53)

        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        if instruction.args[1].attrib['type'] == 'var':
            var = self._get_frame(instruction.args[1].text.split('@')[0]).get(instruction.args[1].text.split('@')[1])
            arg.append(var) if var.type == "string" else sys.exit(53)
        elif instruction.args[1].attrib['type'] == 'string':
            arg.append(Variable(value=self._parse_string(instruction.args[1].text), type='string'))
        else:
            sys.exit(53)

        if instruction.args[2].attrib['type'] == 'var':
            var = self._get_frame(instruction.args[2].text.split('@')[0]).get(instruction.args[2].text.split('@')[1])
            arg.append(var) if var.type == "int" else sys.exit(53)
        elif instruction.args[2].attrib['type'] == 'int':
            arg.append(Variable(value=self._int(instruction.args[2].text), type='int'))
        else:
            sys.exit(53)

        try:
            dest.value, dest.type = ord(arg[0].value[arg[1].value]), 'int'
        except ValueError:
            sys.exit(58)

    def _read(self, instruction: Instruction) -> None:
        """Reads input from stdin and stores it in variable"""
        if instruction.args[0].attrib['type'] != 'var':
            sys.exit(53)

        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        in_data = self._process_input()
        if in_data == "nil":
            dest.value, dest.type = "nil", "nil"
        elif instruction.args[1].text == 'int':
            try:
                dest.value, dest.type = self._int(in_data), "int"
            except ValueError:
                dest.value, dest.type = "nil", "nil"
        elif instruction.args[1].text == 'bool':
            dest.value, dest.type = self._process_bool(in_data), 'bool'
        elif instruction.args[1].text == 'string':
            dest.value, dest.type = self._parse_string(in_data), 'string'

    def _write(self, instruction: Instruction) -> None:
        """Writes value of variable to stdout"""
        for var in self._instruction_args(instruction, "isbn", first=True):
            self._process_output(var)

    def _concat(self, instruction: Instruction) -> None:
        """Concatenates two strings and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self._instruction_args(instruction, "s", dest=True)
        dest.value, dest.type = arg[0].value + arg[1].value, "string"

    def _strlen(self, instruction: Instruction) -> None:
        """Gets length of string and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self._instruction_args(instruction, "s", dest=True)
        dest.value, dest.type = len(arg[0].value), "int"

    def _getchar(self, instruction: Instruction) -> None:
        """Gets character from string at given index and stores it in variable

        Exits with 58 if index is out of bounds
        Exits with 53 if types are not compatible
        """
        if instruction.args[0].attrib['type'] != 'var':
            sys.exit(53)

        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        if instruction.args[1].attrib['type'] == 'var':
            var = self._get_frame(instruction.args[1].text.split('@')[0]).get(instruction.args[1].text.split('@')[1])
            arg.append(var) if var.type == "string" else sys.exit(53)
        elif instruction.args[1].attrib['type'] == 'string':
            arg.append(Variable(value=self._parse_string(instruction.args[1].text), type='string'))
        else:
            sys.exit(53)

        if instruction.args[2].attrib['type'] == 'var':
            var = self._get_frame(instruction.args[2].text.split('@')[0]).get(instruction.args[2].text.split('@')[1])
            arg.append(var) if var.type == "int" else sys.exit(53)
        elif instruction.args[2].attrib['type'] == 'int':
            arg.append(Variable(value=self._int(instruction.args[2].text), type='int'))
        else:
            sys.exit(53)

        try:
            dest.value, dest.type = arg[0].value[arg[1].value], 'string'
        except IndexError:
            sys.exit(58)

    def _setchar(self, instruction: Instruction) -> None:
        """Sets character in string at given index to given character

        Exits with 58 if index is out of bounds
        Exits with 53 if types are not compatible
        """
        if instruction.args[0].attrib['type'] != 'var':
            sys.exit(53)

        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])     
        if dest.type != 'string':
            sys.exit(53)
        arg = []
        if instruction.args[1].attrib['type'] == 'var':
            var = self._get_frame(instruction.args[1].text.split('@')[0]).get(instruction.args[1].text.split('@')[1])
            arg.append(var) if var.type == "int" else sys.exit(53)
        elif instruction.args[1].attrib['type'] == 'int':
            arg.append(Variable(value=self._int(instruction.args[1].text), type='int'))
        else:
            sys.exit(53)

        if instruction.args[2].attrib['type'] == 'var':
            var = self._get_frame(instruction.args[2].text.split('@')[0]).get(instruction.args[2].text.split('@')[1])
            arg.append(var) if var.type == "string" else sys.exit(53)
        elif instruction.args[2].attrib['type'] == 'string':
            arg.append(Variable(value=self._parse_string(instruction.args[2].text), type='string'))
        else:
            sys.exit(53)

        try:
            dest.value =\
                "".join(list(dest.value)[:arg[0].value] + [arg[1].value[0]] + list(dest.value)[arg[0].value+1:])
            dest.type = 'string'
        except IndexError:
            sys.exit(58)

    def _type(self, instruction: Instruction) -> None:
        """Gets type of variable and stores it in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self._instruction_args(instruction, "isbn", dest=True, take_type=True)
        dest.value, dest.type = arg[0].type, "string"

    def _label(self, instruction: Instruction) -> None:
        """Creates label"""

    def _jump(self, instruction: Instruction) -> None:
        """Jumps to label

        Exits with 52 if label does not exist
        """
        if instruction.args[0].text not in self.labels:
            sys.exit(52)
        self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])

    def _jumpifeq(self, instruction: Instruction) -> None:
        """Jumps to label if values are equal

        Exits with 52 if label does not exist
        Exits with 53 if types are not compatible
        """
        if instruction.args[0].text not in self.labels:
            sys.exit(52)
        arg = self._instruction_args(instruction, "isbn")

        if arg[0].type == arg[1].type:
            if arg[0].value == arg[1].value:
                self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])
        elif arg[0].type == 'nil' or arg[1].type == 'nil':
            pass
        else:
            sys.exit(53)

    def _jumpifneq(self, instruction: Instruction) -> None:
        """Jumps to label if values are not equal

        Exits with 52 if label does not exist
        Exits with 53 if types are not compatible
        """
        if instruction.args[0].text not in self.labels:
            sys.exit(52)
        arg = self._instruction_args(instruction, "isbn")

        if arg[0].type == arg[1].type:
            if arg[0].value != arg[1].value:
                self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])
        elif arg[0].type == 'nil' or arg[1].type == 'nil':
            self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])
        else:
            sys.exit(53)

    def _exit(self, instruction: Instruction) -> None:
        """Exits program

        Exits with 57 if value is not in range 0-49
        """
        arg = self._instruction_args(instruction, "i", first=True)
        sys.exit(arg[0].value) if 0 <= arg[0].value <= 49 else sys.exit(57)

    def _dprint(self, instruction: Instruction) -> None:
        """Prints value to stderr"""
        print(self._instruction_args(instruction, "isbn", first=True)[0].value, file=sys.stderr)

    def _break(self, instruction: Instruction) -> None:
        """Prints debug information"""
        print('BREAK', file=sys.stderr)
        print('Current instruction', instruction.instruction.attrib['order'], file=sys.stderr)
        print('GF', file=sys.stderr)
        for i in self.global_frame.frame:
            print(i.name, i.value, i.type, file=sys.stderr)
        print('LF', file=sys.stderr)
        if len(self.frame_stack) != 0:
            for i in self._get_frame('LF').frame:
                print(i.name, i.value, i.type, file=sys.stderr)
        print('TF', file=sys.stderr)
        if self.temporary_frame is not None:
            for i in self.temporary_frame.frame:
                print(i.name, i.value, i.type, file=sys.stderr)


if __name__ == '__main__':
    Interpret().run()
