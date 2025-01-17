import sqlite3


class TokenStore:
    def __init__(self, db_path="requests.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        # Create tables if they don't exist
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_token(self, key, value):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tokens (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (key, value)
            )

    def get_token(self, key):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM tokens WHERE key = ?",
                (key,)
            )
            result = cursor.fetchone()
            return result[0] if result else None

    def get_all_tokens(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT key, value FROM tokens")
            return dict(cursor.fetchall())

    def save_cookie(self, cookie_dict):
        """Save a dictionary of cookies as a single cookie string."""
        cookie_parts = []
        for key, value in cookie_dict.items():
            cookie_parts.append(f"{key}={value}")
        cookie_str = "; ".join(cookie_parts)
        self.save_token('cookie', cookie_str)

    def update_cookie(self, key, value):
        """Update a single cookie in the stored cookie string."""
        cookies = {}
        stored_cookie = self.get_token('cookie')
        if stored_cookie:
            # Parse existing cookies
            for cookie in stored_cookie.split('; '):
                if '=' in cookie:
                    k, v = cookie.split('=', 1)
                    cookies[k] = v

        # Update or add the new cookie
        cookies[key] = value

        # Save back as cookie string
        self.save_cookie(cookies)

    def get_cookie_dict(self):
        """Get stored cookies as a dictionary."""
        cookies = {}
        stored_cookie = self.get_token('cookie')
        if stored_cookie:
            for cookie in stored_cookie.split('; '):
                if '=' in cookie:
                    key, value = cookie.split('=', 1)
                    cookies[key] = value
        return cookies
