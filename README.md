# Macaboo

Macaboo is a command-line tool written in Python for macOS. It allows you to select
an application window and stream just that app to a web page.

## Features

- Choose a target application by name or window title
- Stream the selected window to a web browser using MJPEG
- Lightweight server for local streaming

## Requirements

- macOS 10.15 or later
- Python 3.9 or newer
- Homebrew for installing dependencies
- `ffmpeg` (install with `brew install ffmpeg`)

## Installation

Clone the repository and install Python dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install pyobjc-framework-Quartz Pillow aiohttp
```

## Usage

Run the CLI and specify the application you want to stream:

```bash
python macaboo.py --app "Safari" --port 8080
```

Then open `http://localhost:8080` in your web browser to view the stream.

## How It Works

`macaboo.py` uses the Quartz APIs (via PyObjC) to capture frames from the chosen
application window. Frames are encoded as JPEG and served over HTTP using
`aiohttp`. The result is an MJPEG stream that you can view in any modern browser.

## License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE)
file for details.
