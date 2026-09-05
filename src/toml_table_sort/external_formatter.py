import sys
from collections.abc import Mapping, Sequence
from subprocess import DEVNULL, PIPE, run
from typing import Literal, overload


@overload
def run_formatter(
    args: Sequence[str],
    *,
    stdio: Literal[False] = False,
    env: Mapping[str, str] | None = None,
) -> None: ...


@overload
def run_formatter(
    args: Sequence[str],
    *,
    stdio: Literal[True] = True,
    env: Mapping[str, str] | None = None,
) -> bytes: ...


def run_formatter(
    args: Sequence[str],
    *,
    stdio: bool = False,
    env: Mapping[str, str] | None = None,
) -> bytes | None:
    if stdio:
        stdin = None
        stdout = PIPE
    else:
        stdin = DEVNULL
        stdout = None

    process = run(
        args=args,
        stdin=stdin,
        stdout=stdout,
        shell=False,
        env=env,
        check=False,
    )

    if process.returncode:
        sys.exit(process.returncode)

    if stdio:
        return process.stdout
