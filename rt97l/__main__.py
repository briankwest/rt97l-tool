"""Entry point for rt97l-tool."""

import sys


def main():
    from rt97l.app import RT97LApp

    app = RT97LApp()
    app.run()


if __name__ == "__main__":
    main()
