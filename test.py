import sys
import xml.etree.ElementTree as ET
import argparse
import re
from dataclasses import dataclass
from typing import Generator, Dict, Callable, List, Tuple, TextIO
from xml.etree.ElementTree import Element
from interpret import XMLParser, ArgumentParser

xml = XMLParser().root
for i in xml:
    print(i.tag)


#print(xml.attrib)
