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
usage: cli.py input [output] [options] [-- <external-formatter-args>...]

positional arguments:
  input
  output

options:
  -h, --help
  -f, --force
  --formatter [FORMATTER]
  --newline {lf,crlf}
  --version
```
