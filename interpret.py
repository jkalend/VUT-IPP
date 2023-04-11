import sys
import re
from typing import Dict, Callable, List, Tuple, Any

from XMLParser import XMLParser
from Instruction import Instruction
from Variable import Variable
from Frame import Frame
from Error_enum import Error


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
        return value.lower() == 'true'

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
            Error.exit(Error.Invalid_XML_structure, f"bad int value {value}")

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
            Error.exit(Error.Invalid_XML_structure, f"bad float value {value}")

    def __get_labels(self) -> Dict[str, Instruction]:
        """Yields dictionary of labels

        :return: dictionary of labels
        """
        labels = {}
        for instruction in self.instructions:
            if instruction.opcode == 'LABEL':
                label = instruction.args[0].text
                labels[label] = instruction if label not in labels else Error.exit(Error.Semantic_error)
        return labels

    @staticmethod
    def __parse_string(string: str) -> str:
        """Parses string from IPPcode23 format

        :param string: string to be parsed
        :return: parsed string
        """
        return re.sub(r'\\(\d{3})', lambda x: chr(int(x.group(1))), string) if string is not None else ''

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
            "CLEARS": self.__clears,
            "ADD": self.__add,
            "ADDS": self.__adds,
            "SUB": self.__sub,
            "SUBS": self.__subs,
            "MUL": self.__mul,
            "MULS": self.__muls,
            "IDIV": self.__idiv,
            "IDIVS": self.__idivs,
            "DIV": self.__div,
            "DIVS": self.__divs,
            "LT": self.__lt,
            "LTS": self.__lts,
            "GT": self.__gt,
            "GTS": self.__gts,
            "EQ": self.__eq,
            "EQS": self.__eqs,
            "AND": self.__and,
            "ANDS": self.__ands,
            "OR": self.__or,
            "ORS": self.__ors,
            "NOT": self.__not,
            "NOTS": self.__nots,
            "INT2CHAR": self.__int2char,
            "INT2CHARS": self.__int2chars,
            "INT2FLOAT": self.__int2float,
            "INT2FLOATS": self.__int2floats,
            "FLOAT2INT": self.__float2int,
            "FLOAT2INTS": self.__float2ints,
            "STRI2INT": self.__stri2int,
            "STRI2INTS": self.__stri2ints,
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
            "JUMPIFEQS": self.__jumpifeqs,
            "JUMPIFNEQ": self.__jumpifneq,
            "JUMPIFNEQS": self.__jumpifneqs,
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
                Error.exit(Error.Frame_not_found, "LF not defined")
            return self.frame_stack[-1]
        if frame == 'TF':
            if self.temporary_frame is None:
                Error.exit(Error.Frame_not_found, "TF not defined")
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
        #limit = {"s": "string", "i": "int", "b": "bool", "n": "nil", "f": "float"}[options] if len(options) == 1 else ""
        limit = []
        for i in options:
            limit.append({"s": "string", "i": "int", "b": "bool", "n": "nil", "f": "float", "t": "type"}[i])
        start = 0 if first else 1
        if dest:
            if instruction.args[0].attrib['type'] != 'var' or len(instruction.args[0].text.split('@')) != 2:
                Error.exit(Error.Invalid_type, "Wrong destination variable")
            destination = \
                self.__get_frame(instruction.args[0].text.split('@')[0]).\
                get(instruction.args[0].text.split('@')[1]) if instruction.args[0].attrib['type'] == 'var' \
                else Error.exit(Error.Invalid_type, "Wrong destination variable")

        for i in instruction.args[start:]:
            if i.attrib['type'] == 'var' and not take_type:
                var = var if (var := self.__get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])).type != "" \
                    else Error.exit(Error.Missing_value, "Variable not initialized")
                arg.append(var) if var.type in limit else Error.exit(Error.Invalid_type, "Wrong type")
            elif i.attrib['type'] == 'var' and take_type:
                var = var if (var := self.__get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])) \
                    else Error.exit(Error.Missing_value, "Variable not initialized")
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
            elif i.attrib['type'] == 'type' and 't' in options and i.text in ['int', 'string', 'bool', 'float']:
                arg.append(Variable(value=i.text, type='type'))
            else:
                Error.exit(Error.Invalid_type, "Wrong type")
        return (destination, arg) if dest else arg

    def __get_args_stack(self,
                         count: int = 0,
                         options: str = "") -> List[Variable]:
        limits = []
        for i in options:
            limits.append({"s": "string", "i": "int", "b": "bool", "n": "nil", "f": "float"}[i])

        args = []

        for i in range(count):
            var = self.data_stack.pop() if len(self.data_stack) > 0 else\
                Error.exit(Error.Missing_value, "Stack is empty")

            if var.type in limits or "" in limits:
                args.insert(0, var)
            else:
                Error.exit(Error.Invalid_type, "Wrong type")
        return args

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
        self.frame_stack.append(self.temporary_frame) if self.temporary_frame is not None else\
            Error.exit(Error.Frame_not_found, "TF not defined")
        self.temporary_frame = None

    def __popframe(self, instruction: Instruction) -> None:
        """Pops frame from frame stack and sets it as temporary frame

        Exits with 55 if frame stack is empty
        """
        self.temporary_frame = self.frame_stack.pop() if len(self.frame_stack) > 0 else\
            Error.exit(Error.Frame_not_found, "Frame stack is empty")

    def __defvar(self, instruction: Instruction) -> None:
        """Defines variable in a frame"""
        var = instruction.args[0].text.split('@')
        if instruction.args[0].attrib['type'] != 'var' or len(var) != 2:
            Error.exit(Error.Invalid_type, "Wrong type of a variable")
        self.__get_frame(var[0]).add(var[1]) if len(var) == 2 else\
            Error.exit(Error.Semantic_error, "Wrong variable name")

    def __call(self, instruction: Instruction) -> None:
        """Stores current instruction and jumps to label

        Exits with 52 if label is not defined
        """
        label = instruction.args[0].text
        self.call_stack.append(self.current) if label in self.labels else\
            Error.exit(Error.Semantic_error, "Label not found")
        self.current = iter(self.instructions[self.labels[label].index:])

    def __return(self, instruction: Instruction) -> None:
        """Returns to instruction stored in call stack

        Exits with 56 if call stack is empty
        """
        self.current = self.call_stack.pop() if len(self.call_stack) > 0 else\
            Error.exit(Error.Missing_value, "Call stack is empty")

    def __pushs(self, instruction: Instruction) -> None:
        """Pushes value onto data stack

        Exits with 56 if variable is not defined
        """
        pushed = self.__instruction_args(instruction, "isbnf", first=True)[0]
        self.data_stack.append(Variable(value=pushed.value, type=pushed.type))

    def __pops(self, instruction: Instruction) -> None:
        """Pops value from data stack and stores it in variable

        Exits with 56 if data stack is empty
        """
        dest, _ = self.__instruction_args(instruction, "", dest=True)
        popped = self.data_stack.pop() if len(self.data_stack) > 0 else\
            Error.exit(Error.Missing_value, "Stack is empty")
        dest.value, dest.type = popped.value, popped.type

    def __clears(self, instruction: Instruction) -> None:
        """Clears data stack"""
        self.data_stack.clear()

    def __add(self, instruction: Instruction) -> None:
        """Adds two values and stores them in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "if", dest=True)
        if arg[0].type != arg[1].type:
            Error.exit(Error.Invalid_type, "Wrong type combination")
        dest.value, dest.type = arg[0].value + arg[1].value, self.__get_type(arg[0].type, arg[1].type)

    def __adds(self, instruction: Instruction) -> None:
        """Adds two values from the stack and stores them in the data stack

        Exits with 53 if types are not compatible
        """
        arg = self.__get_args_stack(2, "if")
        if arg[0].type != arg[1].type:
            Error.exit(Error.Invalid_type, "Wrong type combination")
        arg[0].value, arg[0].type = arg[0].value + arg[1].value, self.__get_type(arg[0].type, arg[1].type)
        self.data_stack.append(arg[0])

    def __sub(self, instruction: Instruction) -> None:
        """Subtracts two values and stores them in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "if", dest=True)
        if arg[0].type != arg[1].type:
            Error.exit(Error.Invalid_type, "Wrong type combination")
        dest.value, dest.type = arg[0].value - arg[1].value, self.__get_type(arg[0].type, arg[1].type)

    def __subs(self, instruction: Instruction) -> None:
        """Subtracts two values from the stack and stores them in the data stack

        Exits with 53 if types are not compatible
        """
        arg = self.__get_args_stack(2, "if")
        if arg[0].type != arg[1].type:
            Error.exit(Error.Invalid_type, "Wrong type combination")
        arg[0].value, arg[0].type = arg[0].value - arg[1].value, self.__get_type(arg[0].type, arg[1].type)
        self.data_stack.append(arg[0])

    def __mul(self, instruction: Instruction) -> None:
        """Multiplies two values and stores them in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "if", dest=True)
        if arg[0].type != arg[1].type:
            Error.exit(Error.Invalid_type, "Wrong type combination")
        dest.value, dest.type = arg[0].value * arg[1].value, self.__get_type(arg[0].type, arg[1].type)

    def __muls(self, instruction: Instruction) -> None:
        """Multiplies two values from stack and stores them in the data stack

        Exits with 53 if types are not compatible
        """
        arg = self.__get_args_stack(2, "if")
        if arg[0].type != arg[1].type:
            Error.exit(Error.Invalid_type, "Wrong type combination")
        arg[0].value, arg[0].type = arg[0].value * arg[1].value, self.__get_type(arg[0].type, arg[1].type)
        self.data_stack.append(arg[0])

    def __div(self, instruction: Instruction) -> None:
        """Divides two values and stores them in variable

        Exits with 53 if types are not compatible
        Exits with 57 if dividing by zero
        """
        dest, arg = self.__instruction_args(instruction, "if", dest=True)
        if arg[0].type != arg[1].type:
            Error.exit(Error.Invalid_type, "Wrong type combination")
        dest.value = arg[0].value / arg[1].value if arg[1].value != 0 else\
            Error.exit(Error.Invalid_value, "Dividing by zero")
        dest.type = 'float'

    def __divs(self, instruction: Instruction) -> None:
        """Divides two values from stack and stores them in the data stack

        Exits with 53 if types are not compatible
        Exits with 57 if dividing by zero
        """
        arg = self.__get_args_stack(2, "if")
        if arg[0].type != arg[1].type:
            Error.exit(Error.Invalid_type, "Wrong type combination")
        arg[0].value = arg[0].value / arg[1].value if arg[1].value != 0 else\
            Error.exit(Error.Invalid_value, "Dividing by zero")
        arg[0].type = 'float'
        self.data_stack.append(arg[0])

    def __idiv(self, instruction: Instruction) -> None:
        """Divides two values and stores them in variable

        Exits with 53 if types are not compatible
        Exits with 57 if dividing by zero
        """
        dest, arg = self.__instruction_args(instruction, "i", dest=True)
        dest.value = arg[0].value // arg[1].value if arg[1].value != 0 else\
            Error.exit(Error.Invalid_value, "Dividing by zero")
        dest.type = 'int'

    def __idivs(self, instruction: Instruction) -> None:
        """Divides two values from stack and stores them in the data stack

        Exits with 53 if types are not compatible
        Exits with 57 if dividing by zero
        """
        arg = self.__get_args_stack(2, "i")
        arg[0].value = arg[0].value // arg[1].value if arg[1].value != 0 else\
            Error.exit(Error.Invalid_value, "Dividing by zero")
        arg[0].type = 'int'
        self.data_stack.append(arg[0])

    def __lt(self, instruction: Instruction) -> None:
        """Compares whether arg1 is lesser than arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "ibsf", dest=True)
        if arg[0].type == arg[1].type and arg[0].type == 'nil':
            Error.exit(Error.Invalid_type, "Wrong type combination")
        dest.value = arg[0].value < arg[1].value if arg[0].type == arg[1].type else\
            Error.exit(Error.Invalid_type, "Wrong type combination")
        dest.type = 'bool'

    def __lts(self, instruction: Instruction) -> None:
        """Compares whether arg1 is lesser than arg2 and stores result in the data stack

        Exits with 53 if types are not compatible
        """
        arg = self.__get_args_stack(2, "ibsf")
        if arg[0].type == arg[1].type and arg[0].type == 'nil':
            Error.exit(Error.Invalid_type, "Wrong type combination")
        arg[0].value = arg[0].value < arg[1].value if arg[0].type == arg[1].type else\
            Error.exit(Error.Invalid_type, "Wrong type combination")
        arg[0].type = 'bool'
        self.data_stack.append(arg[0])

    def __gt(self, instruction: Instruction) -> None:
        """Compares whether arg1 is greater than arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "ibsf", dest=True)
        if arg[0].type == arg[1].type and arg[0].type == 'nil':
            Error.exit(Error.Invalid_type, "Wrong type combination")
        dest.value = arg[0].value > arg[1].value if arg[0].type == arg[1].type else\
            Error.exit(Error.Invalid_type, "Wrong type combination")
        dest.type = 'bool'

    def __gts(self, instruction: Instruction) -> None:
        """Compares whether arg1 is greater than arg2 and stores result in the data stack

        Exits with 53 if types are not compatible
        """
        arg = self.__get_args_stack(2, "ibsf")
        if arg[0].type == arg[1].type and arg[0].type == 'nil':
            Error.exit(Error.Invalid_type, "Wrong type combination")
        arg[0].value = arg[0].value > arg[1].value if arg[0].type == arg[1].type else\
            Error.exit(Error.Invalid_type, "Wrong type combination")
        arg[0].type = 'bool'
        self.data_stack.append(arg[0])

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

        dest.value = arg[0].value == arg[1].value if arg[0].type == arg[1].type else\
            Error.exit(Error.Invalid_type, "Wrong type combination")

    def __eqs(self, instruction: Instruction) -> None:
        """Compares whether arg1 and arg2 are equal and stores result in the data stack

        Exits with 53 if types are not compatible
        """
        arg = self.__get_args_stack(2, "ibsnf")
        if arg[0].type == 'nil' and arg[1].type == 'nil':
            arg[0].value = True
            arg[0].type = 'bool'
            self.data_stack.append(arg[0])
            return
        if arg[0].type == 'nil' or arg[1].type == 'nil':
            arg[0].value = False
            arg[0].type = 'bool'
            self.data_stack.append(arg[0])
            return

        arg[0].value = arg[0].value == arg[1].value if arg[0].type == arg[1].type else\
            Error.exit(Error.Invalid_type, "Wrong type combination")
        arg[0].type = 'bool'
        self.data_stack.append(arg[0])

    def __and(self, instruction: Instruction) -> None:
        """Performs logical and on arg1 and arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "b", dest=True)
        dest.value, dest.type = arg[0].value and arg[1].value, "bool"

    def __ands(self, instruction: Instruction) -> None:
        """Performs logical and on arg1 and arg2 and stores result in the data stack

        Exits with 53 if types are not compatible
        """
        arg = self.__get_args_stack(2, "b")
        arg[0].value, arg[0].type = arg[0].value and arg[1].value, "bool"
        self.data_stack.append(arg[0])

    def __or(self, instruction: Instruction) -> None:
        """Performs logical or on arg1 and arg2 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "b", dest=True)
        dest.value, dest.type = arg[0].value or arg[1].value, "bool"

    def __ors(self, instruction: Instruction) -> None:
        """Performs logical or on arg1 and arg2 and stores result in the data stack

        Exits with 53 if types are not compatible
        """
        arg = self.__get_args_stack(2, "b")
        arg[0].value, arg[0].type = arg[0].value or arg[1].value, "bool"
        self.data_stack.append(arg[0])

    def __not(self, instruction: Instruction) -> None:
        """Performs logical not on arg1 and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "b", dest=True)
        dest.value, dest.type = not arg[0].value, "bool"

    def __nots(self, instruction: Instruction) -> None:
        """Performs logical not on arg1 and stores result in the data stack

        Exits with 53 if types are not compatible
        """
        arg = self.__get_args_stack(1, "b")
        arg[0].value = not arg[0].value
        self.data_stack.append(arg[0])

    def __int2char(self, instruction: Instruction) -> None:
        """Converts int to char and stores result in variable

        Exits with 53 if types are not compatible
        Exits with 58 if int is not in range of chr()
        """
        dest, arg = self.__instruction_args(instruction, "i", dest=True)

        if arg[0].value < 0 or arg[0].value > 1114111:
            Error.exit(Error.Bad_string_operation, "Int is not in range of chr()")

        dest.value, dest.type = chr(arg[0].value), "string"

    def __int2chars(self, instruction: Instruction) -> None:
        """Converts int to char and stores result in the data stack

        Exits with 53 if types are not compatible
        Exits with 58 if int is not in range of chr()
        """
        arg = self.__get_args_stack(1, "i")
        if arg[0].value < 0 or arg[0].value > 1114111:
            Error.exit(Error.Bad_string_operation, "Int is not in range of chr()")
        arg[0].value, arg[0].type = chr(arg[0].value), "string"
        self.data_stack.append(arg[0])

    def __float2int(self, instruction: Instruction) -> None:
        """Converts float to int and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "f", dest=True)
        if arg[0].type != 'float':
            Error.exit(Error.Invalid_type, "Wrong type combination")

        dest.value, dest.type = int(arg[0].value), "int"

    def __float2ints(self, instruction: Instruction) -> None:
        """Converts float to int and stores result in the data stack

        Exits with 53 if types are not compatible
        """
        arg = self.__get_args_stack(1, "f")
        if arg[0].type != 'float':
            Error.exit(Error.Invalid_type, "Wrong type combination")

        arg[0].value, arg[0].type = int(arg[0].value), "int"
        self.data_stack.append(arg[0])

    def __int2float(self, instruction: Instruction) -> None:
        """Converts int to float and stores result in variable

        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "i", dest=True)
        if arg[0].type != 'int':
            Error.exit(Error.Invalid_type, "Wrong type combination")

        dest.value, dest.type = float(arg[0].value), "float"

    def __int2floats(self, instruction: Instruction) -> None:
        """Converts int to float and stores result in the data stack

        Exits with 53 if types are not compatible
        """
        arg = self.__get_args_stack(2, "i")
        if arg[1].type != 'int':
            Error.exit(Error.Invalid_type, "Wrong type combination")

        arg[0].value, arg[0].type = float(arg[1].value), "float"
        self.data_stack.append(arg[0])

    def __stri2int(self, instruction: Instruction) -> None:
        """Converts char to int and stores result in variable

        Exits with 53 if types are not compatible
        Exits with 58 if index is out of range or char is not in range of ord()
        """
        dest, arg = self.__instruction_args(instruction, "is", dest=True)
        if arg[0].type != 'string' or arg[1].type != 'int':
            Error.exit(Error.Invalid_type, "Wrong type combination")

        if arg[1].value < 0 or arg[1].value >= len(arg[0].value):
            Error.exit(Error.Bad_string_operation, "Index is out of range")

        dest.value, dest.type = ord(arg[0].value[arg[1].value]), 'int'

    def __stri2ints(self, instruction: Instruction) -> None:
        """Converts char to int and stores result in the data stack

        Exits with 53 if types are not compatible
        Exits with 58 if index is out of range or char is not in range of ord()
        """
        arg = self.__get_args_stack(2, "is")
        if arg[0].type != 'string' or arg[1].type != 'int':
            Error.exit(Error.Invalid_type, "Wrong type combination")

        if arg[1].value < 0 or arg[1].value >= len(arg[0].value):
            Error.exit(Error.Bad_string_operation, "Index is out of range")

        arg[0].value, arg[0].type = ord(arg[0].value[arg[1].value]), 'int'
        self.data_stack.append(arg[0])

    def __read(self, instruction: Instruction) -> None:
        """Reads input from stdin and stores it in variable"""
        dest, type = self.__instruction_args(instruction, "isbnft", dest=True, take_type=True)

        if type[0].name != '':
            Error.exit(Error.Invalid_XML_structure, "Wrong type combination")

        dest = self.__get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        in_data = self.__process_input()
        if in_data == "nil":
            dest.value, dest.type = "nil", "nil"
        elif type[0].value == 'int':
            dest.value = self.__int(in_data.strip(), read=True)
            dest.type = 'int' if dest.value != "nil" else 'nil'
        elif type[0].value == 'bool':
            dest.value, dest.type = self.__process_bool(in_data.strip()), 'bool'
        elif type[0].value == 'string':
            dest.value, dest.type = self.__parse_string(in_data.strip()), 'string'
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
            Error.exit(Error.Invalid_type, "Wrong type combination")

        if arg[1].value < 0 or arg[1].value >= len(arg[0].value):
            Error.exit(Error.Bad_string_operation, "Index is out of range")

        dest.value, dest.type = arg[0].value[arg[1].value], 'string'

    def __setchar(self, instruction: Instruction) -> None:
        """Sets character in string at given index to given character

        Exits with 58 if index is out of bounds
        Exits with 53 if types are not compatible
        """
        dest, arg = self.__instruction_args(instruction, "is", dest=True)
        if dest.type == '':
            Error.exit(Error.Missing_value, "Variable is not initialized")
        if arg[0].type != 'int' or arg[1].type != 'string' or dest.type != 'string':
            Error.exit(Error.Invalid_type, "Wrong type combination")

        if len(arg[1].value) == 0 or arg[0].value < 0 or arg[0].value >= len(dest.value):
            Error.exit(Error.Bad_string_operation, "Index is out of range")

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
            Error.exit(Error.Semantic_error, "Label does not exist")
        self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])

    def __jumpifeq(self, instruction: Instruction) -> None:
        """Jumps to label if values are equal

        Exits with 52 if label does not exist
        Exits with 53 if types are not compatible
        """
        if instruction.args[0].text not in self.labels:
            Error.exit(Error.Semantic_error, "Label does not exist")
        arg = self.__instruction_args(instruction, "isbnf")

        if arg[0].type == arg[1].type:
            if arg[0].value == arg[1].value:
                self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])
        elif arg[0].type == 'nil' or arg[1].type == 'nil':
            pass
        else:
            Error.exit(Error.Invalid_type, "Wrong type combination")

    def __jumpifeqs(self, instruction: Instruction) -> None:
        """Jumps to label if values from stack are equal

        Exits with 52 if label does not exist
        Exits with 53 if types are not compatible
        """
        if instruction.args[0].text not in self.labels:
            Error.exit(Error.Semantic_error, "Label does not exist")
        arg = self.__get_args_stack(2, "isbnf")

        if arg[0].type == arg[1].type:
            if arg[0].value == arg[1].value:
                self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])
        elif arg[0].type == 'nil' or arg[1].type == 'nil':
            pass
        else:
            Error.exit(Error.Invalid_type, "Wrong type combination")

    def __jumpifneq(self, instruction: Instruction) -> None:
        """Jumps to label if values are not equal

        Exits with 52 if label does not exist
        Exits with 53 if types are not compatible
        """
        if instruction.args[0].text not in self.labels:
            Error.exit(Error.Semantic_error, "Label does not exist")
        arg = self.__instruction_args(instruction, "isbnf")

        if arg[0].type == arg[1].type:
            if arg[0].value != arg[1].value:
                self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])
        elif arg[0].type == 'nil' or arg[1].type == 'nil':
            self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])
        else:
            Error.exit(Error.Invalid_type, "Wrong type combination")

    def __jumpifneqs(self, instruction: Instruction) -> None:
        """Jumps to label if values from stack are not equal

        Exits with 52 if label does not exist
        Exits with 53 if types are not compatible
        """
        if instruction.args[0].text not in self.labels:
            Error.exit(Error.Semantic_error, "Label does not exist")
        arg = self.__get_args_stack(2, "isbnf")

        if arg[0].type == arg[1].type:
            if arg[0].value != arg[1].value:
                self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])
        elif arg[0].type == 'nil' or arg[1].type == 'nil':
            self.current = iter(self.instructions[self.labels[instruction.args[0].text].index:])
        else:
            Error.exit(Error.Invalid_type, "Wrong type combination")

    def __exit(self, instruction: Instruction) -> None:
        """Exits program

        Exits with 57 if value is not in range 0-49
        """
        arg = self.__instruction_args(instruction, "i", first=True)
        sys.exit(arg[0].value) if 0 <= arg[0].value <= 49 else Error.exit(Error.Invalid_value, "Exit code out of range")

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
