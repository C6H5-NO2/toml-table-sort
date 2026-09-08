import re
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Literal

_TABLE_HEADER_PAT: Final = re.compile(rb'^[ \t]*(?:\[\[(?P<aot>.*?)\]\]|\[(?P<table>.*?)\])[ \t]*(?:#.*)?$')

_STRING_TOKENISE_PAT: Final = re.compile(rb'\"{3}|\'{3}|\"(?:[^\"\\]|\\.)*\"|\'[^\']*\'|#')


@dataclass(frozen=True, kw_only=True)
class _Table:
    path: Sequence[str]
    is_aot: bool
    start_lineno: int


def _scan_lines(lines: list[bytes]):
    tables: list[_Table] = []
    open_quote: Literal[b'"""', b"'''"] | None = None

    for lineno, line in enumerate(lines):
        if open_quote is not None:
            open_quote = _parse_multiline_string(line, open_quote)
            continue

        if header_match := _TABLE_HEADER_PAT.match(line):
            table = _parse_table_header(header_match, lineno)
            tables.append(table)
        else:
            open_quote = _parse_multiline_string(line, open_quote)

    return tables


def _parse_table_header(header_match: re.Match[bytes], lineno: int) -> _Table:
    is_aot = header_match.group('aot') is not None
    name = header_match.group('aot') if is_aot else header_match.group('table')
    if not name:
        raise ValueError(lineno)
    try:
        value = tomllib.loads(f'[{name.decode()}]')
    except tomllib.TOMLDecodeError:
        raise ValueError(lineno)
    path: list[str] = []
    while value:
        key, value = next(iter(value.items()))
        path.append(key)
    return _Table(path=path, is_aot=is_aot, start_lineno=lineno)


def _parse_multiline_string(
    line: bytes,
    open_quote: Literal[b'"""', b"'''"] | None,
) -> Literal[b'"""', b"'''"] | None:
    for token_match in _STRING_TOKENISE_PAT.finditer(line):
        token = token_match.group()
        if open_quote is not None:
            if token == open_quote:
                open_quote = None
            continue
        match token:
            case b'"""' | b"'''":
                open_quote = token
            case b'#':
                break
    return open_quote


def sort_tables(toml: bytes, /) -> bytes:
    if not toml:
        return b''

    newline = re.search(rb'\r\n|(?<!\r)\n', toml)
    newline = newline.group() if newline else b'\n'

    # `splitlines` drops final new line
    lines = toml.split(sep=newline)

    tables = _scan_lines(lines)
    if tables:
        # todo: implement this
        raise NotImplementedError()
    else:
        lineno = list(range(len(lines)))

    toml = newline.join(lines[no] for no in lineno)
    toml = toml.rstrip(newline)
    toml += newline
    return toml
