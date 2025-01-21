import datetime
import sqlite3


def get_tweet_observation_counts(limit=None):
    """Get tweets ordered by number of engagement observations.

    Args:
        limit: Optional maximum number of tweets to return

    Returns:
        List of tuples with (tweet_id, username, following, observation_count, likes)
    """
    with sqlite3.connect("tweets.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT t.*, e.likes, e.captured_at, COUNT(*) as observation_count
            FROM tweets t
            LEFT JOIN engagements e ON t.tweet_id = e.tweet_id
            GROUP BY t.tweet_id
            ORDER BY observation_count DESC, e.captured_at DESC
            LIMIT ?
        """, (limit or 1000,))

        if limit:
            cursor = cursor.fetchmany(limit)
        else:
            cursor = cursor.fetchall()
        return [(row['tweet_id'], row['username'], bool(row['following']), 
                row['observation_count'], row['likes'] or 0, row['created_at'], row['captured_at']) for row in cursor]


def print_observation_stats():
    """Print statistics about tweet observation counts."""
    print("\nTweets with most observations:")
    print(f"{'Username':<20} {'Following':<10} {'Observations':<12} {'Likes/Hr'} URL")
    print("-" * 107)
    for tweet_id, username, following, count, likes, created_at, captured_at in get_tweet_observation_counts(limit=10):
        following_str = "Y" if following else "N"
        captured_time = datetime.datetime.fromisoformat(captured_at.replace('Z', '+00:00'))
        created_time = datetime.datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
        age_hours = max(0.1, (captured_time - created_time).total_seconds() / 3600)
        likes_per_hour = likes / age_hours
        url = f"https://x.com/{username}/status/{tweet_id}"
        print(f"@{username:<19} {following_str:<10} {count:<12} {likes_per_hour:>8,.0f} {url}")


def debug_user_tweets(username):
    """Show all tweets and their following status for a specific user."""
    with sqlite3.connect("tweets.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT t.tweet_id, t.username, t.following, t.text, t.created_at,
                   COUNT(*) as observation_count
            FROM tweets t
            JOIN engagements e ON t.tweet_id = e.tweet_id
            WHERE t.username = ?
            GROUP BY t.tweet_id
            ORDER BY t.created_at DESC
        """, (username,))
        rows = cursor.fetchall()

        if not rows:
            print(f"\nNo tweets found for @{username}")
            return

        print(f"\nAll tweets from @{username}:")
        print(f"{'Tweet ID':<20} {'Following':<10} {'Created At':<30} {'Observations':<12}")
        print("-" * 72)
        for row in rows:
            following_str = "Y" if row['following'] else "N"
            print(f"{row['tweet_id']:<20} {following_str:<10} {row['created_at']:<30} {row['observation_count']:<12}")
            print(f"Text: {row['text'][:100]}...")
            print("-" * 72)


if __name__ == "__main__":
    print_observation_stats()
    # debug_user_tweets("jessepollak")
