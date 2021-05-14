# Mailboat

Mailboat (Chinese name: 信舟) is a email solution for organisation. It combines MTA and MUA to reduce maintaining complixity.

## Still in developing
This project is under active developing, and should be avaliable soon.

## Contributing
Please turn to "CONTRIBUTING.md" for details.

For security issues, please send an email to maintainer, see "CONTRIBUTING.md".

## References
Mailboat uses [pdoc3](https://pdoc3.github.io/pdoc/) to generate documentation. It should automatically installed after all development dependencies installed by poetry.

Use `poetry run pdoc --html mailboat` to generate references in HTML, `poetry run pdoc --pdf mailboat` for a copy in PDF, `poetry run pdoc --html 127.0.0.1:<port> mailboat` to run a http server with automatic reloading on `<port>`.

Refer to [Pdoc3 Documentation](https://pdoc3.github.io/pdoc/doc/pdoc/) for detailed usage.

## License
GPL-3.0-or-later
