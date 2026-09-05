# toml-table-sort

🚧 WIP 🚧

`toml-table-sort` alphabetically sorts [TOML](https://toml.io/) tables. It acts as a post processing step after other formatters for a more consistent formatting of TOML files. The default formatter is [Taplo](https://github.com/tamasfe/taplo), and it can be configured to others.

Anyway, [TOML is sh\*t](https://hitchdev.com/strictyaml/why-not/toml/). Avoid it if you can.


## Example

Input:
```toml
[TODO]
```

Output:
```toml
[TODO]
```


## Usage

```
usage: python -m toml_table_sort.cli input [output] [options] [-- <external-formatter-args>...]

positional arguments:
  input                 read from this TOML file, or - for stdin
  output                write to this TOML file (default: input); mutually exclusive with stdin

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -f, --force           allow to overwrite existing files
  --newline {LF,CRLF}   specify the line endings of output (default: LF)
  --formatter FORMATTER
                        specify the external formatter (default: taplo)
  --no-formatter        skip external formatting
  --taplo               use bundled taplo config (default: !--formatter && !--no-formatter)
  --option KEY=VALUE    override taplo options; require --taplo; see
                        https://github.com/tamasfe/taplo/blob/master/site/site/configuration/formatter-options.md

  -- args...            pass these arguments to the external formatter; mutually exclusive with --taplo
```
