import sys
from argparse import OPTIONAL, ArgumentParser, Namespace, RawDescriptionHelpFormatter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from os.path import abspath, exists, isfile, samefile
from shutil import copyfile
from typing import Final, Literal, LiteralString, Protocol

from .external_formatter import run_formatter
from .table_sorter import sort_tables
from .version import NAME, VERSION

_MAX_READ_SIZE: Final[int] = 1 << 22

_TAPLO_CLI: Final[LiteralString] = 'taplo'

_DEFAULT_TAPLO_OPTIONS: Final[Sequence[tuple[str, str]]] = [
    ('align_comments', 'false'),
    ('array_auto_collapse', 'false'),
    ('compact_arrays', 'false'),
    ('reorder_keys', 'true'),
    ('reorder_arrays', 'false'),
    ('reorder_inline_tables', 'true'),
]


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

        if args.input != '-' and (args.output is None or args.output == args.input) and not args.force:
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


@dataclass(frozen=True, kw_only=True)
class CliArgs:
    input: str | Literal[0]
    output: str | Literal[1]
    force: bool
    formatter: str | None
    formatter_args: Sequence[str] | None
    formatter_env: Mapping[str, str] | None
    newline: Literal['\n', '\r\n']

    def __init__(
        self,
        *,
        input: str,
        output: str | None = None,
        force: bool = False,
        newline: Literal['LF', 'CRLF'] = 'LF',
        formatter: str | None = None,
        no_formatter: bool = False,
        taplo: bool = False,
        option: Sequence[tuple[str, str]] | None = None,
        formatter_args: Sequence[str] | None = None,
        formatter_env: Mapping[str, str] | None = None,
    ):
        if input == '-':
            object.__setattr__(self, 'input', 0)
            object.__setattr__(self, 'output', 1)
        else:
            object.__setattr__(self, 'input', input)
            output = self._get_output(input, output, force)
            object.__setattr__(self, 'output', output)

        object.__setattr__(self, 'force', force)

        if no_formatter:
            formatter = None
            formatter_args = None
            formatter_env = None
        elif taplo:
            if not formatter:
                formatter = _TAPLO_CLI
            if not formatter_args:
                formatter_args = self._get_taplo_args(
                    option if option else [],
                    '-' if self.output == 1 else self.output,
                )
            if not formatter_env:
                formatter_env = self._get_taplo_env()
        object.__setattr__(self, 'formatter', formatter)
        object.__setattr__(self, 'formatter_args', formatter_args)
        object.__setattr__(self, 'formatter_env', formatter_env)

        match newline:
            case 'CRLF':
                newline: str = '\r\n'
            case _:
                newline: str = '\n'
        object.__setattr__(self, 'newline', newline)

    @staticmethod
    def _get_output(
        input: str,
        output: str | None,
        force: bool,
    ) -> str:
        if not input or not isfile(input):
            raise FileNotFoundError(input)

        if not input.endswith('.toml'):
            raise TypeError(input)

        if output:
            if exists(output):
                if isfile(output):
                    if not force:
                        raise FileExistsError(output)
                else:
                    raise IsADirectoryError(output)
        else:
            output = input
            if not force:
                raise FileExistsError(output)

        return output

    @staticmethod
    def _get_taplo_args(
        option: Sequence[tuple[str, str]],
        file: str,
    ) -> list[str]:
        args = [
            'format',
            '--no-auto-config',
        ]
        options = dict([*_DEFAULT_TAPLO_OPTIONS, *option])
        for k, v in options.items():
            args.append('--option')
            args.append(f'{k}={v}')
        if file != '-':
            file = abspath(file)
        args.append(file)
        return args

    @staticmethod
    def _get_taplo_env() -> dict[str, str]:
        return {
            'RUST_LOG': 'error',
        }


def parse_cli_args() -> CliArgs:
    parser = ArgvParser()
    args = parser.parse_argv()
    args = CliArgs(**vars(args))
    return args


def main():
    parser = ArgvParser()
    args = parser.parse_argv()
    taplo = bool(args.taplo)
    args = CliArgs(**vars(args))
    stdio = args.input == 0

    if not stdio and taplo:
        if not exists(args.output) or not samefile(args.input, args.output):
            copyfile(args.input, args.output)  # type: ignore

    if args.formatter:
        formatter_args = [args.formatter]
        if args.formatter_args:
            formatter_args.extend(args.formatter_args)
        stdout = run_formatter(
            args=formatter_args,
            stdio=stdio,
            env=args.formatter_env,
        )

    if stdio:
        if args.formatter:
            toml: bytes = stdout  # type: ignore
        else:
            if 'buffer' in dir(sys.stdin):
                toml = sys.stdin.buffer.read(_MAX_READ_SIZE)
            else:
                toml = sys.stdin.read(_MAX_READ_SIZE).encode()
    else:
        if taplo:
            file = args.output
        else:
            file = args.input
        with open(file, 'rb') as fp:
            toml = fp.read(_MAX_READ_SIZE)

    toml = sort_tables(toml)

    if stdio:
        if 'buffer' in dir(sys.stdout):
            sys.stdout.buffer.write(toml)
        else:
            sys.stdout.write(toml.decode())
    else:
        with open(args.output, 'wb') as fp:
            fp.write(toml)


if __name__ == '__main__':
    sys.tracebacklimit = 0
    main()
