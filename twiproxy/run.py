import datetime
import json
import os
import sqlite3

from mitmproxy import http

import twiproxy.tokens
from twiproxy.access_direct import parse_body


def init_db():
    """Initialize the databases."""
    # Initialize requests database
    with sqlite3.connect("requests.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                method TEXT,
                url TEXT,
                status INTEGER,
                headers TEXT,
                body TEXT
            )
        """)

    # Initialize tweets database
    with sqlite3.connect("tweets.db") as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS tweets (
            tweet_id TEXT PRIMARY KEY,
            username TEXT,
            name TEXT,
            text TEXT,
            created_at TEXT,
            likes INTEGER,
            retweets INTEGER,
            replies INTEGER,
            views INTEGER,
            captured_at TEXT
        )
        """)

DEBUG = False  # Enable debug mode for better logging

def load_inject_script():
    script_path = os.path.join(os.path.dirname(__file__), 'inject.js')
    with open(script_path, 'r', encoding='utf-8') as f:
        return f.read()

def parse_cookies(cookie_str):
    """Parse cookie string into a dictionary."""
    cookie_dict = {}
    if not cookie_str:
        return cookie_dict

    pairs = cookie_str.split(';')
    for pair in pairs:
        if '=' in pair:
            name, value = pair.split('=', 1)
            cookie_dict[name.strip()] = value.strip()

    return cookie_dict

def debug_log(message):
    """Write a message to proxy.log if DEBUG is True."""
    if DEBUG:
        with open('proxy.log', 'a', encoding='utf-8') as log:
            log.write(message + '\n')

def save_tokens(headers, token_store):
    debug_log(f"\nHeaders: {dict(headers)}")

    # Convert headers to case-insensitive dict
    headers_lower = {k.lower(): v for k, v in headers.items()}
    debug_log(f"Headers lower: {headers_lower}")

    # Save each token if present
    if 'authorization' in headers_lower:
        token_store.save_token('authorization', headers_lower['authorization'])
        debug_log("Found authorization")

    if 'cookie' in headers_lower:
        cookie_dict = parse_cookies(headers_lower['cookie'])
        debug_log(f"Parsed cookies: {cookie_dict}")

        # Save cookie if it has all required authentication tokens
        required_cookies = {'auth_token', 'ct0', 'gt'}
        if all(cookie in cookie_dict for cookie in required_cookies):
            token_store.save_cookie(cookie_dict)
            debug_log(f"Found cookie with all required tokens: {', '.join(required_cookies)}")
            debug_log(f"gt value: {cookie_dict['gt']}")
        else:
            missing = required_cookies - set(cookie_dict.keys())
            debug_log(f"Missing required cookies: {', '.join(missing)}")
            debug_log(f"Found cookies: {', '.join(cookie_dict.keys())}")

    if 'x-csrf-token' in headers_lower:
        token_store.save_token('x-csrf-token', headers_lower['x-csrf-token'])
        debug_log("Found x-csrf-token")

    if 'x-client-uuid' in headers_lower:
        token_store.save_token('x-client-uuid', headers_lower['x-client-uuid'])
        debug_log(f"Found x-client-uuid: {headers_lower['x-client-uuid']}")

def save_tweets(tweets, captured_at):
    """Save tweets to the tweets database.

    Args:
        tweets: List of tweet dictionaries from parse_body
        captured_at: Timestamp when tweets were captured
    """
    with sqlite3.connect("tweets.db") as conn:
        for tweet in tweets:
            conn.execute("""
                INSERT OR REPLACE INTO tweets (
                    tweet_id, username, name, text, created_at,
                    likes, retweets, replies, views, captured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tweet.get('tweet_id'),
                tweet.get('username'),
                tweet.get('name'),
                tweet.get('text'),
                tweet.get('created_at'),
                tweet.get('likes', 0),
                tweet.get('retweets', 0),
                tweet.get('replies', 0),
                tweet.get('views', 0),
                captured_at
            ))
        conn.commit()

def response(flow: http.HTTPFlow) -> None:
    """Handle responses from Twitter."""
    init_db()  # Ensure tables exist
    token_store = twiproxy.tokens.TokenStore()  # Initialize token store

    if flow.response and flow.response.headers:
        debug_log(f"\nResponse Headers: {dict(flow.response.headers)}")

        # Look for Set-Cookie headers and parse them
        if 'set-cookie' in flow.response.headers:
            cookies = flow.response.headers.get_all('set-cookie')
            debug_log(f"Found Set-Cookie headers: {cookies}")

            # Parse each Set-Cookie header
            for cookie in cookies:
                if cookie:
                    # Split on first '=' to get name and value
                    parts = cookie.split('=', 1)
                    if len(parts) == 2:
                        name = parts[0]
                        value = parts[1].split(';')[0]  # Get value before any attributes
                        name = name.strip()
                        if name == 'gt':
                            token_store.update_cookie('gt', value)
                            debug_log(f"Added gt cookie to tokens: {value}")

        # Log all requests and responses
        log_request(flow)

def request(flow: http.HTTPFlow) -> None:
    """Handle requests to Twitter."""
    init_db()  # Ensure tables exist
    token_store = twiproxy.tokens.TokenStore()  # Initialize token store

    if flow.request and flow.request.headers:
        save_tokens(flow.request.headers, token_store)

def log_request(flow):
    """Log request and response details."""
    debug_log('\n' + '=' * 80)
    debug_log(f"URL: {flow.request.url}")
    debug_log(f"Method: {flow.request.method}")
    debug_log(f"Status: {flow.response.status_code if flow.response else 'No response'}")

    if flow.request.headers:
        debug_log("\nRequest Headers:")
        for name, value in flow.request.headers.items():
            debug_log(f"{name}: {value}")

    if flow.response and flow.response.headers:
        debug_log("\nResponse Headers:")
        for name, value in flow.response.headers.items():
            debug_log(f"{name}: {value}")

    if flow.response and flow.response.content:
        try:
            body = flow.response.content.decode('utf-8')
            debug_log(body)

            # Store in requests table
            with sqlite3.connect("requests.db") as conn:
                conn.execute(
                    "INSERT INTO requests (method, url, status, headers, body) VALUES (?, ?, ?, ?, ?)",
                    (flow.request.method, flow.request.url, flow.response.status_code,
                     json.dumps(dict(flow.request.headers)), body)
                )
                conn.commit()

            # Parse and store tweets if this is a timeline response
            if 'HomeTimeline' in flow.request.url:
                try:
                    body_json = json.loads(body)
                    current_time = datetime.datetime.now(datetime.timezone.utc)
                    tweets = parse_body(body_json, current_time)
                    if tweets:
                        save_tweets(tweets, current_time.isoformat())
                except Exception as e:
                    debug_log(f"Error parsing tweets: {str(e)}")

        except UnicodeDecodeError:
            debug_log("[Binary content]")

def done():
    """Call this when the script shuts down."""
