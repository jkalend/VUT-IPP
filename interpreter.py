import sys
import xml.etree.ElementTree as ET
import argparse


class ArgumentParser:
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

    def parse(self):
        args = self.parser.parse_args()
        if args.source is None and args.input is None:
            self.parser.error('At least one of the arguments --source or --input must be present')
        return args


class XMLParser:
    def __init__(self):
        self.args = ArgumentParser().parse()
        self.root = self.parse()

    def parse(self):
        if self.args.source is None:
            root = ET.fromstring(self._load_xml())
        else:
            try:
                root = ET.parse(self.args.source).getroot()
            except ET.ParseError:
                print("Error: XML file is not valid")
                exit(31)
        return root

    def _load_xml(self):
        xml_file = sys.stdin.read()
        return xml_file

    def get_input(self):
        if self.args.input is not None:
            return self.args.input
        return None

    def get_instructions(self):
        return self.root.iter("instruction")

    def get_instruction(self, tag):
        return self.root.find("instruction[@opcode='{}']".format(tag))

    def get_args(self, instruction):
        return instruction.iter('arg')


class Interpret:
    def __init__(self):
        self.xml = XMLParser()
        self.instructions = [Instruction(instruction) for instruction in self.xml.get_instructions()]
        self.labels = self._get_labels()
        self.variables = self._get_vars() #likely not needed
        self.input = self.xml.get_input()
        self.operations = self._init_operations()
        self.temporary_frame = None
        self.frame_stack = []
        self.global_frame = Frame()
        self.current = self.instructions[0]
        self.call_stack = []
        self.data_stack = []

    def _get_labels(self):
        labels = {}
        for instruction in self.instructions:
            if instruction.opcode == 'LABEL':
                label = instruction.args[0].text
                labels[label] = instruction
        return labels

    def _get_vars(self):
        vars = {}
        for instruction in self.instructions:
            if instruction.opcode == 'DEFVAR':
                var = instruction.args[0].text
                vars[var] = None
        return vars

    def _init_operations(self):
        return {}

    def _get_frame(self, frame):
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

    def _get_arg(self, instruction, arg):
        arg = instruction.find(arg)
        if arg is not None:
            return arg.text
        return None

    def _get_arg_types(self, instruction):
        arg_types = []
        for arg in instruction.args:
            arg_type = arg.attrib['type']
            if arg_type is not None:
                arg_types.append(arg_type)
        return arg_types

    def _check_args(self, instruction, arg_types):
        args = self._get_arg_types(instruction)
        if len(args) != len(arg_types):
            return False
        for arg, arg_type in zip(args, arg_types):
            if arg != arg_type:
                return False
        return True

    def move(self, instruction):
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = instruction.args[1]
        if arg.attrib['type'] == 'var':
            var = self._get_frame(arg.text.split('@')[0]).get(arg.text.split('@')[1])
            if var.value is None:
                exit(56)
            dest.value = var.value
            dest.type = var.type
        elif arg.attrib['type'] == 'int':
            dest.value = int(arg.text.split('@')[0])
            dest.type = 'int'
        elif arg.attrib['type'] == 'bool':
            dest.value = arg.text.split('@')[0] == 'true'
            dest.type = 'bool'
        elif arg.attrib['type'] == 'string':
            dest.value = arg.text.split('@')[0]
            dest.type = 'string'
        elif arg.attrib['type'] == 'nil':
            dest.value = "nil"
            dest.type = 'nil'
        else:
            exit(53)

    def createframe(self, instruction):
        self.temporary_frame = Frame()

    def pushframe(self, instruction):
        if self.temporary_frame is None:
            exit(55)
        self.frame_stack.append(self.temporary_frame)
        self.temporary_frame = None

    def popframe(self, instruction):
        if len(self.frame_stack) == 0:
            exit(55)
        self.temporary_frame = self.frame_stack.pop()

    def defvar(self, instruction):
        var = instruction.args[0].text.split('@')
        self._get_frame(var[0]).add(var[1])

    def call(self, instruction):
        label = instruction.args[0].text
        if label not in self.labels:
            exit(52)
        self.call_stack.append(self.current)
        self.current = self.labels[label]

    def return_(self, instruction):
        if len(self.call_stack) == 0:
            exit(56)
        self.current = self.call_stack.pop()

    def pushs(self, instruction):
        arg = instruction.args[0].attrib['type']
        if arg == 'var':
            var = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
            self.data_stack.append(var)
        elif arg == 'int':
            self.data_stack.append(Variable(value=int(instruction.args[0].text.split('@')[1]), type='int'))
        elif arg == 'bool':
            self.data_stack.append(Variable(value=instruction.args[0].text.split('@')[1] == 'true', type='bool'))
        elif arg == 'string':
            self.data_stack.append(Variable(value=instruction.args[0].text.split('@')[1], type='string'))
        elif arg == 'nil':
            self.data_stack.append(Variable(value="nil", type='nil'))
        else:
            exit(53)

    def pops(self, instruction):
        var = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        if len(self.data_stack) == 0:
            exit(56)

        popped = self.data_stack.pop()
        var.value = popped.value
        var.type = popped.type


    def add(self, instruction):
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        for i in instruction.args[1:]:
            if i.attrib['type'] == 'var':
                var = self._get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])
                arg.append(var) if var.type == "int" else exit(56)
            elif i.attrib['type'] == 'int':
                arg.append(Variable(value=int(i.text.split('@')[1]), type='int'))
            else:
                exit(53)

        dest.value = arg[0].value + arg[1].value
        dest.type = 'int'
        return dest.value

    def sub(self, instruction):
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        for i in instruction.args[1:]:
            if i.attrib['type'] == 'var':
                var = self._get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])
                arg.append(var) if var.type == "int" else exit(56)
            elif i.attrib['type'] == 'int':
                arg.append(Variable(value=int(i.text.split('@')[1]), type='int'))
            else:
                exit(53)

        dest.value = arg[0].value - arg[1].value
        dest.type = 'int'
        return dest.value

    def mul(self, instruction):
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        for i in instruction.args[1:]:
            if i.attrib['type'] == 'var':
                var = self._get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])
                arg.append(var) if var.type == "int" else exit(56)
            elif i.attrib['type'] == 'int':
                arg.append(Variable(value=int(i.text.split('@')[1]), type='int'))
            else:
                exit(53)

        dest.value = arg[0].value * arg[1].value
        dest.type = 'int'
        return dest.value

    def idiv(self, instruction):
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        for i in instruction.args[1:]:
            if i.attrib['type'] == 'var':
                var = self._get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])
                arg.append(var) if var.type == "int" else exit(56)
            elif i.attrib['type'] == 'int':
                arg.append(Variable(value=int(i.text.split('@')[1]), type='int'))
            else:
                exit(53)

        if arg[1].value == 0:
            exit(57)

        dest.value = arg[0].value // arg[1].value
        dest.type = 'int'
        return dest.value

    def lt(self, instruction):
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        for i in instruction.args[1:]:
            if i.attrib['type'] == 'var':
                var = self._get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])
                arg.append(var) if var.value is not None else exit(56)
            elif i.attrib['type'] == 'int':
                arg.append(Variable(value=int(i.text.split('@')[1]), type='int'))
            elif i.attrib['type'] == 'bool':
                arg.append(Variable(value=bool(i.text.split('@')[1]), type='bool'))
            elif i.attrib['type'] == 'string':
                arg.append(Variable(value=str(i.text.split('@')[1]), type='string'))
            else:
                exit(53)

        if arg[0].type != arg[1].type:
            exit(53)

        dest.value = True if arg[0].value < arg[1].value else False
        dest.type = 'bool'
        return dest.value

    def gt(self, instruction):
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        for i in instruction.args[1:]:
            if i.attrib['type'] == 'var':
                var = self._get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])
                arg.append(var) if var.value is not None else exit(56)
            elif i.attrib['type'] == 'int':
                arg.append(Variable(value=int(i.text.split('@')[1]), type='int'))
            elif i.attrib['type'] == 'bool':
                arg.append(Variable(value=bool(i.text.split('@')[1]), type='bool'))
            elif i.attrib['type'] == 'string':
                arg.append(Variable(value=str(i.text.split('@')[1]), type='string'))
            else:
                exit(53)

        if arg[0].type != arg[1].type:
            exit(53)

        dest.value = True if arg[0].value > arg[1].value else False
        dest.type = 'bool'
        return dest.value

    def eq(self, instruction):
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        for i in instruction.args[1:]:
            if i.attrib['type'] == 'var':
                var = self._get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])
                arg.append(var) if var.value is not None else exit(56)
            elif i.attrib['type'] == 'int':
                arg.append(Variable(value=int(i.text.split('@')[1]), type='int'))
            elif i.attrib['type'] == 'bool':
                arg.append(Variable(value=bool(i.text.split('@')[1]), type='bool'))
            elif i.attrib['type'] == 'string':
                arg.append(Variable(value=str(i.text.split('@')[1]), type='string'))
            elif i.attrib['type'] == 'nil':
                arg.append(Variable(value="nil", type='nil'))
            else:
                exit(53)

        if arg[0].type == 'nil' and arg[1].type == 'nil':
            dest.value = True
            dest.type = 'bool'
            return dest.value
        elif arg[0].type == 'nil' or arg[1].type == 'nil':
            dest.value = False
            dest.type = 'bool'
            return dest.value

        if arg[0].type != arg[1].type:
            exit(53)

        dest.value = True if arg[0].value == arg[1].value else False
        dest.type = 'bool'
        return dest.value

    def and_(self, instruction):
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        for i in instruction.args[1:]:
            if i.attrib['type'] == 'var':
                var = self._get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])
                arg.append(var) if var.type == "bool" else exit(56)
            elif i.attrib['type'] == 'bool':
                arg.append(Variable(value=bool(i.text.split('@')[1]), type='bool'))
            else:
                exit(53)

        dest.value = arg[0].value and arg[1].value
        dest.type = 'bool'
        return dest.value

    def or_(self, instruction):
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        for i in instruction.args[1:]:
            if i.attrib['type'] == 'var':
                var = self._get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])
                arg.append(var) if var.type == "bool" else exit(56)
            elif i.attrib['type'] == 'bool':
                arg.append(Variable(value=bool(i.text.split('@')[1]), type='bool'))
            else:
                exit(53)

        dest.value = arg[0].value or arg[1].value
        dest.type = 'bool'
        return dest.value

    def not_(self, instruction):
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        for i in instruction.args[1:]:
            if i.attrib['type'] == 'var':
                var = self._get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])
                arg.append(var) if var.type == "bool" else exit(56)
            elif i.attrib['type'] == 'bool':
                arg.append(Variable(value=bool(i.text.split('@')[1]), type='bool'))
            else:
                exit(53)

        dest.value = not arg[0].value
        dest.type = 'bool'
        return dest.value

    def int2char(self, instruction):
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        for i in instruction.args[1:]:
            if i.attrib['type'] == 'var':
                var = self._get_frame(i.text.split('@')[0]).get(i.text.split('@')[1])
                arg.append(var) if var.type == "int" else exit(53)
            elif i.attrib['type'] == 'int':
                arg.append(Variable(value=int(i.text.split('@')[1]), type='int'))
            else:
                exit(53)

        try:
            dest.value = chr(arg[0].value)
            dest.type = 'string'
            return dest.value
        except ValueError:
            exit(58)

    def stri2int(self, instruction):
        dest = self._get_frame(instruction.args[0].text.split('@')[0]).get(instruction.args[0].text.split('@')[1])
        arg = []
        if instruction.args[1].attrib['type'] == 'var':
            var = self._get_frame(instruction.args[1].text.split('@')[0]).get(instruction.args[1].text.split('@')[1])
            arg.append(var) if var.type == "string" else exit(53)
        elif instruction.args[1].attrib['type'] == 'string':
            arg.append(Variable(value=instruction.args[1].text.split('@')[1], type='string'))
        else:
            exit(53)

        if instruction.args[2].attrib['type'] == 'var':
            var = self._get_frame(instruction.args[2].text.split('@')[0]).get(instruction.args[2].text.split('@')[1])
            arg.append(var) if var.type == "int" else exit(53)
        elif instruction.args[2].attrib['type'] == 'int':
            arg.append(Variable(value=int(instruction.args[2].text.split('@')[1]), type='int'))
        else:
            exit(53)

        try:
            dest.value = ord(arg[0].value[arg[1].value])
            dest.type = 'int'
            return dest.value
        except ValueError:
            exit(58)


class Instruction:
    def __init__(self, instruction):
        self.instruction = instruction
        self.opcode = instruction.attrib['opcode']
        self.args = self._get_args(instruction)

    def _get_arg(self, instruction, arg):
        arg = instruction.find(arg)
        if arg is not None:
            return arg

    def _get_args(self, instruction):
        args = []
        for arg in ['arg1', 'arg2', 'arg3']:
            arg = instruction.find(arg)
            if arg is not None:
                args.append(arg)
        return args

    def _get_arg_types(self, instruction):
        arg_types = []
        for arg in ['arg1', 'arg2', 'arg3']:
            arg_type = instruction.find(arg)
            if arg_type is not None:
                arg_types.append(arg_type.attrib['type'])
        return arg_types

    def _check_args(self, instruction, arg_types):
        args = self._get_arg_types(instruction)
        if len(args) != len(arg_types):
            return False
        for arg, arg_type in zip(args, arg_types):
            if arg != arg_type:
                return False
        return True

    def _check_arg(self, instruction, arg, arg_type):
        args = self._get_arg_types(instruction)
        if len(args) != 1:
            return False
        if args[0] != arg_type:
            return False
        return True


class Frame:
    def __init__(self):
        self.frame = {}

    def get(self, id):
        if id in self.frame:
            return self.frame[id]
        exit(54)

    def add(self, var):  # done by defvar
        self.frame[var] = Variable(var=var)


class Variable:
    def __init__(self, var=None, value=None, type=""):
        self.name = var
        self.value = value
        self.type = type


def main():
    args = ArgumentParser().parse()
    inter = Interpret()
    print(inter.instructions[0].args[0].attrib['type'])


if __name__ == '__main__':
    main()
