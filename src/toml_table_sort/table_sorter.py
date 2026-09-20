import re
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final, Literal

_TABLE_HEADER_PAT: Final = re.compile(rb'^[ \t]*(?:\[\[(?P<aot>.*?)\]\]|\[(?P<table>.*?)\])[ \t]*(?:#.*)?$')

_STRING_TOKENISE_PAT: Final = re.compile(rb'\"{3}|\'{3}|\"(?:[^\"\\]|\\.)*\"|\'[^\']*\'|#')


@dataclass(frozen=True, kw_only=True)
class _Header:
    path: Sequence[str]
    is_aot: bool
    lineno: int


def _scan_lines(lines: list[bytes]):
    headers: list[_Header] = []
    open_quote: Literal[b'"""', b"'''"] | None = None

    for lineno, line in enumerate(lines):
        if open_quote is not None:
            open_quote = _parse_multiline_string(line, open_quote)
            continue

        if header_match := _TABLE_HEADER_PAT.match(line):
            header = _parse_table_header(header_match, lineno)
            headers.append(header)
        else:
            open_quote = _parse_multiline_string(line, open_quote)

    return headers


def _parse_table_header(header_match: re.Match[bytes], lineno: int) -> _Header:
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
    return _Header(path=path, is_aot=is_aot, lineno=lineno)


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


@dataclass(kw_only=True)
class _Table:
    line_range: range | None = None
    children: dict[str, _Table | _Aot] = field(default_factory=dict)


@dataclass(kw_only=True)
class _Aot:
    instances: list[_Table] = field(default_factory=list)


def _sort_headers(headers: list[_Header], max_lineno: int) -> list[int]:
    root = _Table()

    # partition tables
    header_linenos = [header.lineno for header in headers]
    table_starts = [0, *header_linenos]
    table_stops = [*header_linenos, max_lineno]
    table_headers = [None, *headers]
    table_line_ranges: list[range] = []
    for start, stop, header in zip(table_starts, table_stops, table_headers, strict=True):
        line_range = range(start, stop)
        if header is None:
            root.line_range = line_range
        else:
            table_line_ranges.append(line_range)

    # build table tree
    for header, line_range in zip(headers, table_line_ranges, strict=True):
        parent = root
        for key in header.path[:-1]:
            child = parent.children.get(key)
            match child:
                case None:
                    child = _Table()
                    parent.children[key] = child
                    parent = child
                case _Table():
                    parent = child
                case _Aot():
                    parent = child.instances[-1]
                case _:
                    raise TypeError(child)

        key = header.path[-1]
        child = parent.children.get(key)
        match child:
            case None:
                if header.is_aot:
                    child = _Aot(instances=[_Table(line_range=line_range)])
                else:
                    child = _Table(line_range=line_range)
                parent.children[key] = child
            case _Table():
                if header.is_aot:
                    raise ValueError(header)
                child.line_range = line_range
            case _Aot():
                if not header.is_aot:
                    raise ValueError(header)
                child.instances.append(_Table(line_range=line_range))
            case _:
                raise TypeError(child)

    # calculate lineno mapping
    linenos = _get_table_linenos(root)
    return linenos


def _get_table_linenos(table: _Table) -> list[int]:
    linenos: list[int] = [] if table.line_range is None else list(table.line_range)
    linenos.extend(_get_children_linenos(table))
    return linenos


def _get_children_linenos(table: _Table) -> list[int]:
    linenos: list[int] = []
    keys = sorted(key for key in table.children)
    for key in keys:
        child = table.children.get(key)
        match child:
            case _Table():
                lns = _get_table_linenos(child)
                linenos.extend(lns)
            case _Aot():
                lns = _get_aot_linenos(child)
                linenos.extend(lns)
            case _:
                raise TypeError(child)
    return linenos


def _get_aot_linenos(aot: _Aot) -> list[int]:
    linenos: list[int] = []
    for instance in aot.instances:
        lns = _get_table_linenos(instance)
        linenos.extend(lns)
    return linenos


def sort_tables(toml: bytes, /) -> bytes:
    if not toml:
        return b''

    newline = re.search(rb'\r\n|(?<!\r)\n', toml)
    newline = newline.group() if newline else b'\n'

    # `splitlines` drops final new line
    lines = toml.split(sep=newline)

    headers = _scan_lines(lines)
    if headers:
        linenos = _sort_headers(headers, len(lines))
    else:
        linenos = list(range(len(lines)))

    toml = newline.join(lines[ln] for ln in linenos)
    toml = toml.rstrip(newline)
    toml += newline
    return toml
