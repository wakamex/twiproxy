# TwiProxy

A proxy server for Twitter/X.

## Setup

```bash
# Create a new virtual environment with Python 3.12
rm -rf .venv
uv venv .venv -p 3.12

# Activate the virtual environment
source .venv/bin/activate

# Install the package in editable mode
uv pip install -e .

# Run the proxy server
uv run mitmdump --mode regular@8082 -s proxy/run.py
```

## Running Chrome with the Proxy

Modify `run_chrome.sh` to point to the chrome profile you want to use:

```bash
export HTTP_PROXY="http://127.0.0.1:8082"
export HTTPS_PROXY="http://127.0.0.1:8082"
google-chrome \
    --user-data-dir="$HOME/.config/google-chrome" \
    --profile-directory="Profile 10" \
    --disable-quic
```

Then run it with:
```bash
chmod +x run_chrome.sh
./run_chrome.sh
```
