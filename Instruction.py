import sys
from xml.etree.ElementTree import Element
from typing import List

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
