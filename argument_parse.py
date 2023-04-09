import argparse
import sys


class ArgumentParser:
    """Class for parsing arguments from command line"""

    def __init__(self):
        self.parser = argparse.ArgumentParser(prog='Interpret XML',
                                              description='Interprets XML code made by parse.php'
                                                          ' and outputs the result to stdout',
                                              epilog='(Jan Kalenda 2023)', add_help=False)
        self.parser.add_argument('--source', nargs="?", type=str, help='Source file')
        self.parser.add_argument('--input', nargs="?", type=str, help='Input file')
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
            print("Error: Argument --help cannot be used with any other argument", file=sys.stderr)
            sys.exit(10)

        if args.source is None and args.input is None:
            self.parser.print_help()
            print("\nError: At least one of the arguments --source or --input must be present", file=sys.stderr)
            sys.exit(10)
        return args
