import sys
from argparse import OPTIONAL, ArgumentParser, Namespace, RawDescriptionHelpFormatter
from collections.abc import Sequence
from typing import Final, Literal, LiteralString, Protocol

from .version import NAME, VERSION

_TAPLO_CLI: Final[LiteralString] = 'taplo'


class _Args(Protocol):
    input: str
    output: str | None
    force: bool
    newline: Literal['LF', 'CRLF']
    formatter: str | None
    no_formatter: bool
    taplo: bool
    option: list[tuple[str, str]] | None
    formatter_args: list[str] | None


class ArgvParser:
    def __init__(self):
        self._parser = ArgvParser._get_arg_parser()

    def parse_argv(
        self,
        argv: Sequence[str] | None = None,
        *,
        start: int = 1,
    ) -> Namespace:
        if argv is None:
            argv = sys.argv

        argv = argv[start:]

        if '--' in argv:
            sep_idx = argv.index('--')
            formatter_args = list(argv[sep_idx + 1 :])
        else:
            sep_idx = len(argv)
            formatter_args = None

        args: _Args = self._parser.parse_args(argv[:sep_idx])  # type: ignore
        args.formatter_args = formatter_args

        self._set_defaults(args)

        self._check_constraints(args)

        return args  # type: ignore

    def _set_defaults(self, args: _Args) -> None:
        if args.output is None:
            args.output = args.input

        if args.formatter is None and not args.no_formatter:
            args.formatter = _TAPLO_CLI
            args.taplo = True

    def _check_constraints(self, args: _Args) -> None:
        if args.input == '-' and not (args.output is None or args.output == '-'):
            self._parser.error('argument output: required to be stdout when argument input is stdin')

        if args.input != '-' and args.output is None and not args.force:
            self._parser.error('argument --force: required when argument output is not specified')

        if args.no_formatter and args.taplo:
            self._parser.error('argument --taplo: not allowed with argument --no-formatter')

        if not args.taplo and args.option is not None:
            self._parser.error('argument --option: not allowed without argument --taplo')

        if args.no_formatter and args.formatter_args is not None:
            self._parser.error('argument external-formatter-args: not allowed with argument --no-formatter')

        if args.taplo and args.formatter_args is not None:
            self._parser.error('argument external-formatter-args: not allowed with argument --taplo')

    @staticmethod
    def _get_arg_parser() -> ArgumentParser:
        parser = ArgumentParser(
            usage='%(prog)s input [output] [options] [-- <external-formatter-args>...]',
            epilog='\n  -- args...\t\tpass these arguments to the external formatter; mutually exclusive with --taplo\n',
            formatter_class=RawDescriptionHelpFormatter,
            allow_abbrev=False,
        )

        parser.add_argument(
            '--version',
            action='version',
            version=f'{NAME} v{VERSION}',
        )

        parser.add_argument(
            'input',
            help='read from this TOML file, or - for stdin',
        )

        parser.add_argument(
            'output',
            nargs=OPTIONAL,
            help='write to this TOML file (default: input); mutually exclusive with stdin',
        )

        parser.add_argument(
            '-f',
            '--force',
            action='store_true',
            help='allow to overwrite existing files',
        )

        parser.add_argument(
            '--newline',
            default='LF',
            choices=['LF', 'CRLF'],
            help='specify the line endings of output (default: LF)',
        )

        formatter_group = parser.add_mutually_exclusive_group()
        formatter_group.add_argument(
            '--formatter',
            default=None,
            help='specify the external formatter (default: taplo)',
        )
        formatter_group.add_argument(
            '--no-formatter',
            action='store_true',
            help='skip external formatting',
        )

        parser.add_argument(
            '--taplo',
            action='store_true',
            help='use bundled taplo config (default: !--formatter && !--no-formatter)',
        )

        taplo_docs = 'https://github.com/tamasfe/taplo/blob/master/site/site/configuration/formatter-options.md'
        parser.add_argument(
            '--option',
            action='append',
            type=ArgvParser._parse_eq_sep_str,
            help=f'override taplo options; require --taplo; see {taplo_docs}',
            metavar='KEY=VALUE',
        )

        return parser

    @staticmethod
    def _parse_eq_sep_str(s: str, /) -> tuple[str, str]:
        if not s or '=' not in s:
            raise ValueError(s)
        kv = s.split('=', maxsplit=1)
        if len(kv) != 2:
            raise ValueError(s)
        k, v = kv
        if not k:
            raise ValueError(s)
        return k, v


if __name__ == '__main__':
    args = ArgvParser().parse_argv()
    print(args)
