import argparse
import sys

from Error_enum import Error


class ArgumentParser:
    """Class for parsing arguments from command line"""

    def __init__(self):
        self.parser = argparse.ArgumentParser(prog='Interpret XML',
                                              description='Interprets XML code made by parse.php'
                                                          ' and outputs the result to stdout',
                                              epilog='(Jan Kalenda 2023)', add_help=False)
        self.parser.add_argument('--source', nargs="*", type=str, help='Source file')
        self.parser.add_argument('--input', nargs="*", type=str, help='Input file')
        self.parser.add_argument('--help', action="store_true", help='Prints this help')

    def parse(self) -> argparse.Namespace:
        """Parses arguments from command line

        :return: parsed arguments
        """
        args = self.parser.parse_args()
        if args.help and args.source is None and args.input is None:
            self.parser.print_help()
            sys.exit(0)
        elif args.help and (args.source is not None or args.input is not None):
            Error.exit(Error.Missing_parameter, "Argument --help cannot be used with any other argument")

        if args.source is not None and len(args.source) > 1:
            Error.exit(Error.Missing_parameter, "Argument --source can be used only once")
        elif args.input is not None and len(args.input) > 1:
            Error.exit(Error.Missing_parameter, "Argument --input can be used only once")

        if args.source is None and args.input is None:
            self.parser.print_help()
            Error.exit(Error.Missing_parameter, "At least one of the arguments --source or --input must be present")
        return args
