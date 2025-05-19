# Macaboo

Macaboo is a small command-line utility written in Python for macOS. It lets you
pick a running GUI application and capture a screenshot of its first on-screen
window.

## Features

- Lists all running GUI applications
- Prompts you to select which app to capture
- Saves a PNG image of the selected application's window

## Requirements

- macOS 10.15 or later
- Python 3.9 or newer
- PyObjC libraries (`pyobjc-framework-Quartz`, `pyobjc-framework-Cocoa`)

## Installation

Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa
```

## Usage

Run the tool directly after installing the package:

```bash
python -m macaboo
```

You can optionally specify an output filename:

```bash
macaboo --output screenshot.png
```

## License

This project is licensed under the Apache 2.0 License. See the
[LICENSE](LICENSE) file for details.
