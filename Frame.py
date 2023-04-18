# IPP 2023 project 2
# Author: Jan Kalenda
# Login: xkalen07

from Variable import Variable

from Error_enum import Error

class Frame:
    """Class for simulating frame"""

    def __init__(self):
        self.frame = {}

    def get(self, id: str) -> Variable:
        """Returns variable with given id

        :param id: id of variable
        :return: variable with given id
        """
        return self.frame[id] if id in self.frame.keys() else\
            Error.exit(Error.Nonexistent_variable, f"variable {id} not found")

    def add(self, var: str) -> None:
        """Adds variable to frame

        :param var: variable to add
        """
        self.frame[var] = Variable(name=var) if var not in self.frame.keys() else\
            Error.exit(Error.Semantic_error, f"variable {var} already exists")
