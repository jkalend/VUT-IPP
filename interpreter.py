import sys
import xml.etree.ElementTree as ET
import argparse
import re
from typing import Generator, Dict, Type, Callable, List
from xml.etree.ElementTree import Element


class ArgumentParser:
    """Class for parsing arguments from command line"""
    def __init__(self):
        self.parser = argparse.ArgumentParser(prog='Interpret XML',
                                              description='Interprets XML code made by parse.php'
                                                          ' and outputs the result to stdout',
                                              epilog='At least one of the arguments --source or --input must be present'
                                                     ' (Jan Kalenda 2023)',
                                              add_help=False
                                              )
        self.parser.add_argument('--source', nargs="?", type=str, help='Source file')
        self.parser.add_argument('--input', nargs="?", type=str, help='Input file')
        self.parser.add_argument('--help', action='help', help='Prints this help')

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
        self.root = self.parse()

    def parse(self) -> ET.Element:
        """Parses XML file

        :return: root of XML file
        """
        if self.args.source is None:
            root = ET.fromstring(self._load_xml())
        else:
            try:
                root = ET.parse(self.args.source).getroot()
            except ET.ParseError:
                print("Error: XML file is not valid")
                exit(31)
        return root

    def _load_xml(self) -> str:
        """Loads XML file from stdin

        :return: XML file as string
        """
        xml_file = sys.stdin.read()
        return xml_file

    def get_input(self) -> str:
        """Returns input file

        :return: input file or None
        """
        if self.args.input is not None:
            return self.args.input
        return None

    def get_instructions(self) -> Generator[Element, None, None]:
        """Yields instructions from XML file

        :return: iterator of instructions
        """
        return self.root.iter("instruction")

    def get_instruction(self, tag: str) -> Element:
        """Returns instruction with given tag

        :param: tag: tag of instruction
        :return: instruction with given tag
        """
        return self.root.find("instruction[@opcode='{}']".format(tag))

    def get_args(self, instruction: Element) -> Generator[Element, None, None]:
        """Yields arguments of given instruction

        :param instruction: instruction
        :return: iterator of arguments
        """
        return instruction.iter('arg')


class Instruction:
    """Class for storing instruction"""
    def __init__(self, instruction):
        self.instruction = instruction
        self.opcode = instruction.attrib['opcode']
        self.args = self._get_args(instruction)
        self.index = int(instruction.attrib['order']) - 1

    def _get_args(self, instruction: Element) -> List[Element]:
        """Returns arguments of given instruction

        :param instruction: instruction
        :return: list of arguments
        """
        if int(instruction.attrib['order']) < 1:
            exit(32)

        args = []
        for arg in ['arg1', 'arg2', 'arg3']:
            arg = instruction.find(arg)
            if arg is not None:
                args.append(arg)
        return args


class Variable:
    """Class for storing variable"""
    def __init__(self, var=None, value=None, type=""):
        self.name = var
        self.value = value
        self.type = type


class Frame:
    """Class for simulating frame"""
    def __init__(self):
        self.frame = {}

    def get(self, id) -> Variable:
        """Returns variable with given id

        :param id: id of variable
        :return: variable with given id
        """
        if id in self.frame:
            return self.frame[id]
        exit(54)

    def add(self, var) -> None:
        """Adds variable to frame

        :param var: variable to add
        """
        self.frame[var] = Variable(var=var)



class Interpret:
    """Class for interpreting IPPcode23 code"""
    def __init__(self):
        self.xml = XMLParser()
        self.instructions = [Instruction(instruction) for instruction in self.xml.get_instructions()]
        self.labels = self._get_labels()
        self.input = self.xml.get_input()
        self.operations = self._init_operations()
        self.temporary_frame = None
        self.frame_stack = []
        self.global_frame = Frame()
        self.current = iter(self.instructions)
        self.call_stack = []
        self.data_stack = []

    def run(self) -> None:
        """Runs the program"""
        try:
            while True:
                instruction = next(self.current)
                self.operations[instruction.opcode](instruction)
        except StopIteration:
            exit(0)

    def process_input(self) -> str:
        """Processes input

        :return: input as string
        """
        if self.input is not None:
            with open(self.input, 'r') as file:
                in_data = file.read()
                if in_data == '':
                    return "nil"
                return in_data
        else:
            try:
                in_data = input()
                return in_data
            except EOFError:
                return "nil"

    def process_output(self, var: Variable) -> None:
        """Processes output

        :param var: variable to be printed
        """
        if var.type == 'string':
            print(self.parse_string(var.value), end='')
        elif var.type == 'int':
            print(var.value, end='')
        elif var.type == 'bool':
            if var.value:
                print('true', end='')
            else:
                print('false', end='')
        elif var.type == 'nil':
            print('', end='')

    def __process_bool(self, value: str) -> bool:
        """Processes bool value

        :param value: value to be processed
        :return: processed value as bool
        """
        if value == 'true':
            return True
        else:
            return False

    def int(self, value: str) -> int:
        """Processes int value

        :param value: value to be processed
        :return: processed value as int
        """
        if value.startswith("0x"):
            return int(value, 16)
        elif value.startswith("0o"):
            return int(value, 8)
        else:
            try:
                return int(value)
            except ValueError:
                exit(32)

    def _get_labels(self) -> Dict[str, Instruction]:
        """Yields dictionary of labels

        :return: dictionary of labels
        """
        labels = {}
        for instruction in self.instructions:
            if instruction.opcode == 'LABEL':
                label = instruction.args[0].text
                if label in labels:
                    exit(52)
                labels[label] = instruction
        return labels

    def parse_string(self, string: str) -> str:
        """Parses string from IPPcode23 format

        :param string: string to be parsed
        :return: parsed string
        """
        while re.match(r'.*\\[0-9]{3}.*', string):
            string = re.sub(r'\\([0-9]{3})', lambda x: chr(int(x.group(1))), string)
        return string

    def _init_operations(self) -> Dict[str, Callable]:
        """Initializes dictionary of operations

        :return: dictionary of operations
        """
        return {
            "MOVE": self.move,
            "CREATEFRAME": self.createframe,
            "PUSHFRAME": self.pushframe,
            "POPFRAME": self.popframe,
            "DEFVAR": self.defvar,
            "CALL": self.call,
            "RETURN": self.return_,
            "PUSHS": self.pushs,
            "POPS": self.pops,
            "ADD": self.add,
            "SUB": self.sub,
            "MUL": self.mul,
            "IDIV": self.idiv,
            "LT": self.lt,
            "GT": self.gt,
            "EQ": self.eq,
            "AND": self.and_,
            "OR": self.or_,
            "NOT": self.not_,
            "INT2CHAR": self.int2char,
            "STRI2INT": self.stri2int,
            "READ": self.read,
            "WRITE": self.write,
            "CONCAT": self.concat,
            "STRLEN": self.strlen,
            "GETCHAR": self.getchar,
            "SETCHAR": self.setchar,
            "TYPE": self.type,
            "LABEL": self.label,
            "JUMP": self.jump,
            "JUMPIFEQ": self.jumpifeq,
            "JUMPIFNEQ": self.jumpifneq,
            "EXIT": self.exit,
            "DPRINT": self.dprint,
            "BREAK": self.break_,
        }

    def _get_frame(self, frame: str) -> Frame:
        """Yields frame based on frame tag

        exits with 55 if frame is not defined

        :param frame: frame tag
        :return: frame object
        """
        if frame == 'GF':
            return self.global_frame
        elif frame == 'LF':
            if len(self.frame_stack) == 0:
                sys.exit(55)
            return self.frame_stack[-1]
        elif frame == 'TF':
            if self.temporary_frame is None:
                sys.exit(55)
            return self.temporary_frame

    def move(self, instruction: Instruction) -> None:
        """Moves value into a variable

        Exits with 56 if variable is not defined

        :param instruction: MOVE instruction to be processed
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = instruction.args[1]
        if arg.attrib['type'] == 'var':
            var = self._get_frame(arg.text.split('@')[0]).get(arg.text.split('@')[1])
            if var.value is None:
                exit(56)
            dest.value = var.value
            dest.type = var.type
        elif arg.attrib['type'] == 'int':
            dest.value = self.int(arg.text)
            dest.type = 'int'
        elif arg.attrib['type'] == 'bool':
            dest.value = arg.text == 'true'
            dest.type = 'bool'
        elif arg.attrib['type'] == 'string':
            dest.value = self.parse_string(arg.text)
            dest.type = 'string'
        elif arg.attrib['type'] == 'nil':
            dest.value = "nil"
            dest.type = 'nil'
        else:
            exit(53)

    def createframe(self, instruction: Instruction) -> None:
        """Creates temporary frame"""
        self.temporary_frame = Frame()

    def pushframe(self, instruction: Instruction) -> None:
        """Pushes temporary frame into frame stack

        Exits with 55 if temporary frame is not defined
        """
        if self.temporary_frame is None:
            exit(55)
        self.frame_stack.append(self.temporary_frame)
        self.temporary_frame = None

    def popframe(self, instruction: Instruction) -> None:
        """Pops frame from frame stack and sets it as temporary frame

        Exits with 55 if frame stack is empty
        """
        if len(self.frame_stack) == 0:
            exit(55)
        self.temporary_frame = self.frame_stack.pop()

    def defvar(self, instruction: Instruction) -> None:
        """Defines variable in a frame"""
        var = instruction.args[0].text.split('@')
        self._get_frame(var[0]).add(var[1])

    def call(self, instruction: Instruction) -> None:
        """Stores current instruction and jumps to label

        Exits with 52 if label is not defined
        """
        label = instruction.args[0].text
        if label not in self.labels:
            exit(52)
        self.call_stack.append(self.current)
        self.current = iter(self.instructions[self.labels[label].index:])

    def return_(self, instruction: Instruction) -> None:
        """Returns to instruction stored in call stack

        Exits with 56 if call stack is empty
        """
        if len(self.call_stack) == 0:
            exit(56)
        self.current = self.call_stack.pop()

    def pushs(self, instruction: Instruction) -> None:
        """Pushes value onto data stack

        Exits with 56 if variable is not defined
        """
        arg = instruction.args[0].attrib['type']
        if arg == 'var':
            var = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
            self.data_stack.append(var) if var.type != "" else exit(56)
        elif arg == 'int':
            self.data_stack.append(Variable(value=self.int(instruction.args[0].text), type='int'))
        elif arg == 'bool':
            self.data_stack.append(Variable(value=self.__process_bool(instruction.args[0].text), type='bool'))
        elif arg == 'string':
            self.data_stack.append(Variable(value=self.parse_string(instruction.args[0].text), type='string'))
        elif arg == 'nil':
            self.data_stack.append(Variable(value="nil", type='nil'))
        else:
            exit(53)

    def pops(self, instruction: Instruction) -> None:
        """Pops value from data stack and stores it in variable

        Exits with 56 if data stack is empty
        """
        var = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        if len(self.data_stack) == 0:
            exit(56)

        popped = self.data_stack.pop()
        var.value = popped.value
        var.type = popped.type

    def add(self, instruction: Instruction) -> None:
        """Adds two values and stores them in variable

        Exits with 53 if types are not compatible
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = self.instruction_args(instruction, "i")

        dest.value = arg[0].value + arg[1].value
        dest.type = 'int'

    def sub(self, instruction: Instruction) -> None:
        """Subtracts two values and stores them in variable

        Exits with 53 if types are not compatible
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = self.instruction_args(instruction, "i")

        dest.value = arg[0].value - arg[1].value
        dest.type = 'int'

    def mul(self, instruction: Instruction) -> None:
        """Multiplies two values and stores them in variable

        Exits with 53 if types are not compatible
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = self.instruction_args(instruction, "i")

        dest.value = arg[0].value * arg[1].value
        dest.type = 'int'

    def idiv(self, instruction: Instruction) -> None:
        """Divides two values and stores them in variable

        Exits with 53 if types are not compatible
        Exits with 57 if dividing by zero
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = self.instruction_args(instruction, "i")

        if arg[1].value == 0:
            exit(57)

        dest.value = arg[0].value // arg[1].value
        dest.type = 'int'

    def lt(self, instruction: Instruction) -> None:
        """Compares whether arg1 is lesser than arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = self.instruction_args(instruction, "ibs")

        if arg[0].type != arg[1].type:
            exit(53)

        dest.value = True if arg[0].value < arg[1].value else False
        dest.type = 'bool'

    def gt(self, instruction: Instruction) -> None:
        """Compares whether arg1 is greater than arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = self.instruction_args(instruction, "ibs")

        if arg[0].type != arg[1].type:
            exit(53)

        dest.value = True if arg[0].value > arg[1].value else False
        dest.type = 'bool'

    def eq(self, instruction: Instruction) -> None:
        """Compares whether arg1 and arg2 are equal and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = self.instruction_args(instruction, "ibsn")

        if arg[0].type == 'nil' and arg[1].type == 'nil':
            dest.value = True
            dest.type = 'bool'
            return
        elif arg[0].type == 'nil' or arg[1].type == 'nil':
            dest.value = False
            dest.type = 'bool'
            return

        if arg[0].type != arg[1].type:
            exit(53)

        dest.value = True if arg[0].value == arg[1].value else False
        dest.type = 'bool'

    def and_(self, instruction: Instruction) -> None:
        """Performs logical and on arg1 and arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = self.instruction_args(instruction, "b")

        dest.value = arg[0].value and arg[1].value
        dest.type = 'bool'

    def or_(self, instruction: Instruction) -> None:
        """Performs logical or on arg1 and arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = self.instruction_args(instruction, "b")

        dest.value = arg[0].value or arg[1].value
        dest.type = 'bool'

    def not_(self, instruction: Instruction) -> None:
        """Performs logical not on arg1 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = self.instruction_args(instruction, "b")

        dest.value = not arg[0].value
        dest.type = 'bool'

    def int2char(self, instruction: Instruction) -> None:
        """Converts int to char and stores result in variable

        Exits with 53 if types are not compatible
        Exits with 58 if int is not in range of chr()
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = self.instruction_args(instruction, "i")

        try:
            dest.value = chr(arg[0].value)
            dest.type = 'string'
            return
        except ValueError:
            exit(58)

    def stri2int(self, instruction: Instruction) -> None:
        """Converts char to int and stores result in variable

        Exits with 53 if types are not compatible
        Exits with 58 if index is out of range or char is not in range of ord()
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        if instruction.args[1].attrib['type'] == 'var':
            var = self._get_frame(instruction.args[1].text.split('@')[0]).get(instruction.args[1].text.split('@')[1])
            arg.append(var) if var.type == "string" else exit(53)
        elif instruction.args[1].attrib['type'] == 'string':
            arg.append(Variable(value=self.parse_string(instruction.args[1].text), type='string'))
        else:
            exit(53)

        if instruction.args[2].attrib['type'] == 'var':
            var = self._get_frame(instruction.args[2].text.split('@')[0]).get(instruction.args[2].text.split('@')[1])
            arg.append(var) if var.type == "int" else exit(53)
        elif instruction.args[2].attrib['type'] == 'int':
            arg.append(Variable(value=self.int(instruction.args[2].text), type='int'))
        else:
            exit(53)

        try:
            dest.value = ord(arg[0].value[arg[1].value])
            dest.type = 'int'
            return
        except ValueError:
            exit(58)

    def read(self, instruction: Instruction) -> None:
        """Reads input from stdin and stores it in variable"""
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        in_data = self.process_input()
        if in_data == "nil":
            dest.value = "nil"
            dest.type = "nil"
        elif instruction.args[1].text == 'int':
            try:
                dest.value = self.int(in_data)
                dest.type = 'int'
                return
            except ValueError:
                dest.value = "nil"
                dest.type = "nil"
                return
        elif instruction.args[1].text == 'bool':
            dest.value = self.__process_bool(in_data)
            dest.type = 'bool'
        elif instruction.args[1].text == 'string':
            dest.value = self.parse_string(in_data)
            dest.type = 'string'

    def write(self, instruction: Instruction) -> None:
        """Writes value of variable to stdout"""
        arg = self.instruction_args(instruction, "isbn", first=True)
        for var in arg:
            self.process_output(var)

    def concat(self, instruction: Instruction) -> None:
        """Concatenates two strings and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = self.instruction_args(instruction, "s")

        dest.value = arg[0].value + arg[1].value
        dest.type = 'string'

    def strlen(self, instruction: Instruction) -> None:
        """Gets length of string and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = self.instruction_args(instruction, "s")

        dest.value = len(arg[0].value)
        dest.type = 'int'

    def getchar(self, instruction: Instruction) -> None:
        """Gets character from string at given index and stores it in variable

        Exits with 58 if index is out of bounds
        Exits with 53 if types are not compatible
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        if instruction.args[1].attrib['type'] == 'var':
            var = self._get_frame(instruction.args[1].text.split('@')[0]).get(instruction.args[1].text.split('@')[1])
            arg.append(var) if var.type == "string" else exit(53)
        elif instruction.args[1].attrib['type'] == 'string':
            arg.append(Variable(value=self.parse_string(instruction.args[1].text), type='string'))
        else:
            exit(53)

        if instruction.args[2].attrib['type'] == 'var':
            var = self._get_frame(instruction.args[2].text.split('@')[0]).get(instruction.args[2].text.split('@')[1])
            arg.append(var) if var.type == "int" else exit(53)
        elif instruction.args[2].attrib['type'] == 'int':
            arg.append(Variable(value=self.int(instruction.args[2].text), type='int'))
        else:
            exit(53)

        try:
            dest.value = arg[0].value[arg[1].value]
            dest.type = 'string'
            return
        except IndexError:
            exit(58)

    def setchar(self, instruction: Instruction) -> None:
        """Sets character in string at given index to given character

        Exits with 58 if index is out of bounds
        Exits with 53 if types are not compatible
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        if dest.type != 'string':
            exit(53)
        arg = []
        if instruction.args[1].attrib['type'] == 'var':
            var = self._get_frame(instruction.args[1].text.split('@')[0]).get(instruction.args[1].text.split('@')[1])
            arg.append(var) if var.type == "int" else exit(53)
        elif instruction.args[1].attrib['type'] == 'int':
            arg.append(Variable(value=self.int(instruction.args[1].text), type='int'))
        else:
            exit(53)

        if instruction.args[2].attrib['type'] == 'var':
            var = self._get_frame(instruction.args[2].text.split('@')[0]).get(instruction.args[2].text.split('@')[1])
            arg.append(var) if var.type == "string" else exit(53)
        elif instruction.args[2].attrib['type'] == 'string':
            arg.append(Variable(value=self.parse_string(instruction.args[2].text), type='string'))
        else:
            exit(53)

        try:
            dest.value[arg[1].value] = arg[2].value[0]
            dest.type = 'string'
            return
        except IndexError:
            exit(58)

    def type(self, instruction: Instruction) -> None:
        """Gets type of variable and stores it in variable

        Exits with 53 if types are not compatible
        """
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = self.instruction_args(instruction, "isbn")

        dest.value = arg[0].type
        dest.type = 'string'

    def label(self, instruction: Instruction) -> None:
        """Creates label"""
        pass

    def jump(self, instruction: Instruction) -> None:
        """Jumps to label

        Exits with 52 if label does not exist
        """
        if instruction.args[0].text not in self.labels:
            exit(52)
        self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])

    def jumpifeq(self, instruction: Instruction) -> None:
        """Jumps to label if values are equal

        Exits with 52 if label does not exist
        Exits with 53 if types are not compatible
        """
        if instruction.args[0].text not in self.labels:
            exit(52)
        arg = self.instruction_args(instruction, "isbn")

        if arg[0].type == arg[1].type:
            if arg[0].value == arg[1].value:
                self.current = iter(self.instructions[self.labels[instruction.args[0].text]:])
        elif arg[0].type == 'nil' or arg[1].type == 'nil':
            pass
        else:
            exit(53)

    def jumpifneq(self, instruction: Instruction) -> None:
        """Jumps to label if values are not equal

        Exits with 52 if label does not exist
        Exits with 53 if types are not compatible
        """
        if instruction.args[0].text not in self.labels:
            exit(52)
        arg = self.instruction_args(instruction, "isbn")

        if arg[0].type == arg[1].type:
            if arg[0].value != arg[1].value:
                self.current = iter(self.instructions[self.labels[instruction.args[0].text]:])
        elif arg[0].type == 'nil' or arg[1].type == 'nil':
            self.current = iter(self.instructions[self.labels[instruction.args[0].text]:])
        else:
            exit(53)

    def exit(self, instruction: Instruction) -> None:
        """Exits program

        Exits with 57 if value is not in range 0-49
        """
        arg = self.instruction_args(instruction, "i")

        if arg[0].value < 0 or arg[0].value > 49:
            exit(57)

        exit(arg[0].value)

    def dprint(self, instruction: Instruction) -> None:
        """Prints value to stderr"""
        arg = self.instruction_args(instruction, "isbn", first=True)
        print(arg[0].value, file=sys.stderr)

    def break_(self, instruction: Instruction) -> None:
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

    def instruction_args(self, instruction: Instruction, options: str = "", first=False) -> List[Variable]:
        """Returns list of arguments for instruction

        Exits with 53 if type is not compatible
        :param instruction: instruction
        :param options: string of types (string, int, bool, nil) as isbn
        :param first: if first argument should be accounted for
        :return: list of arguments
        """
        arg = []
        limit = {"s": "string", "i": "int", "b": "bool", "n": "nil"}[options] if len(options) == 1 else ""
        start = 0 if first else 1

        for i in instruction.args[start:]:
            if i.attrib['type'] == 'var':
                var = self._get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])
                arg.append(var) if var.type != limit else exit(56)
            elif i.attrib['type'] == 'string' and 's' in options:
                arg.append(Variable(value=self.parse_string(i.text), type='string'))
            elif i.attrib['type'] == 'int' and 'i' in options:
                arg.append(Variable(value=self.int(i.text), type='int'))
            elif i.attrib['type'] == 'bool' and 'b' in options:
                arg.append(Variable(value=self.__process_bool(i.text), type='bool'))
            elif i.attrib['type'] == 'nil' and 'n' in options:
                arg.append(Variable(value=i.text, type='nil'))
            else:
                exit(53)
        return arg


if __name__ == '__main__':
    Interpret().run()
