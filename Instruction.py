from xml.etree.ElementTree import Element
from typing import List

from Error_enum import Error

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
            Error.exit(Error.Invalid_XML_structure, f"invalid order {instruction.attrib['order']}")

        instruction = sorted(instruction, key=lambda x: int(x.tag[3:]))

        return list(instruction)
