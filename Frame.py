import sys
from Variable import Variable

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
