# Macaboo

**Macaboo** is a small Python utility for macOS that mirrors any running GUI
application to a browser window. It captures screenshots of an application's
frontmost window and exposes them via a lightweight web server. The page also
forwards mouse and keyboard events back to the application so you can interact
with it remotely.

## Features

- Discover running applications and choose one interactively
- Live screenshot streaming via a local HTTP server
- Mouse clicks, scrolling and key presses sent from the browser
- Simple command line interface available as `macaboo`

## Requirements

- macOS 10.15 or later
- Python 3.9+
- `pyobjc-framework-Quartz` and `pyobjc-framework-Cocoa`
- `aiohttp`, `opencv-python` and `numpy`

## Installation

Once published on PyPI the package can be installed with pip:

```bash
python -m pip install macaboo
```

The `macaboo` command will then be available on your PATH. If you are working
from a clone of the repository you can install an editable copy instead:

```bash
python -m pip install -e .
```

## Quick start

Run `macaboo` with no arguments to select an application from the list of running
processes. The default web server listens on port `6222`:

```bash
macaboo
# open http://localhost:6222 in your browser
```

You can provide the application name directly or change the port:

```bash
macaboo "Safari" --port 7000
```

When the browser is open you can click, scroll and type in the screenshot just as
if you were using the application locally.

## Development

The project is packaged with a standard `pyproject.toml`. After cloning, install
the dependencies and an editable build:

```bash
python -m pip install -e .
```

On macOS this will also fetch the PyObjC and OpenCV libraries required for
runtime operation.

The source code and issue tracker live on [GitHub](https://github.com/quartzjer/macaboo).

## License

This project is licensed under the Apache 2.0 license. See the
[LICENSE](LICENSE) file for details.
