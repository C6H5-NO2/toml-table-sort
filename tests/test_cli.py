"""Tests for CLI file-argument validation in toml_table_sort.cli."""

import sys

import pytest

from toml_table_sort.cli import main


def run_cli(monkeypatch, capsys, argv):
    """Run main() with the given argv, capturing the SystemExit code."""
    monkeypatch.setattr(sys, "argv", ["toml-table-sort", *argv])
    with pytest.raises(SystemExit) as exc_info:
        main()
    return exc_info.value.code, capsys.readouterr()


def test_missing_input_file_is_usage_error(monkeypatch, capsys):
    """A missing input file exits 2 with a clean message, not a traceback."""
    code, captured = run_cli(monkeypatch, capsys, ["missing.toml", "--force", "--no-formatter"])
    assert code == 2
    assert "Traceback" not in captured.err
    assert "missing.toml" in captured.err


def test_non_toml_input_file_is_usage_error(monkeypatch, capsys, tmp_path):
    """A non-TOML input file exits 2 with a clean message."""
    not_toml = tmp_path / "notes.txt"
    not_toml.write_text("just text\n")
    code, captured = run_cli(monkeypatch, capsys, [str(not_toml), "--force", "--no-formatter"])
    assert code == 2
    assert "Traceback" not in captured.err
    assert str(not_toml) in captured.err


def test_existing_output_without_force_is_usage_error(monkeypatch, capsys, tmp_path):
    """An existing output file without --force exits 2 with a clean message."""
    input_file = tmp_path / "in.toml"
    input_file.write_text("[b]\n[a]\n")
    output_file = tmp_path / "out.toml"
    output_file.write_text("[b]\n[a]\n")
    code, captured = run_cli(
        monkeypatch, capsys, [str(input_file), str(output_file), "--no-formatter"]
    )
    assert code == 2
    assert "Traceback" not in captured.err
    assert str(output_file) in captured.err


def test_valid_input_sorts_without_error(monkeypatch, capsys, tmp_path):
    """A valid TOML file still sorts in place and exits cleanly."""
    input_file = tmp_path / "in.toml"
    input_file.write_text("[b]\n[a]\n")
    monkeypatch.setattr(sys, "argv", ["toml-table-sort", str(input_file), "--force", "--no-formatter"])
    assert main() is None
    out, err = capsys.readouterr()
    assert err == ""
    assert "[a]" in input_file.read_text().splitlines()[0]
