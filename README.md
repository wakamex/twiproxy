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

## See most common tweets

```bash
.venv/bin/python twiproxy/query_tweets.py

Tweets with most observations:
Username             Following  Observations Likes/Hr URL
-----------------------------------------------------------------------------------------------------------
@jessepollak         Y          16                 35 https://x.com/jessepollak/status/1881395849063972913
@PendleIntern        Y          16                  1 https://x.com/PendleIntern/status/1881530247553966186
@0xAneri             Y          15                 34 https://x.com/0xAneri/status/1881749679429554220
@FigoETH             N          14                 65 https://x.com/FigoETH/status/1881781941810405797
@iamDCinvestor       Y          11                 92 https://x.com/iamDCinvestor/status/1881734502864556072
@optimizoor          N          11                229 https://x.com/optimizoor/status/1881783025677303887
@jessepollak         Y          7                   0 https://x.com/jessepollak/status/1881751042934919239
@futur3_cannibal     N          6               4,337 https://x.com/futur3_cannibal/status/1881573635191939530
@AdrianoFeria        N          6                  17 https://x.com/AdrianoFeria/status/1881697866860679611
@LordGrimdark        N          6                 390 https://x.com/LordGrimdark/status/1881752437813584217
```