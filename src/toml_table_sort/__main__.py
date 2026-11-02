import sys

from .cli import main as cli_main


def main():
    cli_main()


if __name__ == '__main__':
    sys.tracebacklimit = 0
    main()
