import sys
import xml.etree.ElementTree as ET
import argparse
import re
from dataclasses import dataclass
from typing import Generator, Dict, Callable, List, Tuple, TextIO
from xml.etree.ElementTree import Element
from interpret import XMLParser, ArgumentParser, Instruction

xml = XMLParser()

instructions = [Instruction(i) for i in xml.get_instructions()]
instructions.sort(key=lambda x: x.index)
for i in instructions:
    print(i.index + 1)
