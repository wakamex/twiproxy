import sqlite3


def get_tweet_observation_counts(limit=None):
    """Get tweets ordered by number of engagement observations.

    Args:
        limit: Optional maximum number of tweets to return

    Returns:
        List of tuples with (tweet_id, username, observation_count)
    """
    with sqlite3.connect("tweets.db") as conn:
        query = """
            SELECT t.tweet_id, t.username,
                   COUNT(e.captured_at) as observation_count
            FROM tweets t
            LEFT JOIN engagements e ON t.tweet_id = e.tweet_id
            GROUP BY t.tweet_id
            ORDER BY observation_count DESC
        """
        if limit:
            query += f" LIMIT {limit}"

        cursor = conn.execute(query)
        return cursor.fetchall()


def print_observation_stats():
    """Print statistics about tweet observation counts."""
    tweets = get_tweet_observation_counts()

    print(f"\nFound {len(tweets)} tweets")
    print("\nTweet - Observations")
    print("-" * 30)

    for tweet_id, username, count in tweets[:10]:
        combined_id = f"{username}/{tweet_id}"
        print(f"{combined_id:<40} - {count}")


if __name__ == "__main__":
    print_observation_stats()
