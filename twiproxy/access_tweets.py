import datetime
import sqlite3
import sys
from collections import defaultdict

DEBUG = False

def get_recent_tweets(limit=100):
    """Get the most recently captured tweets.
    
    Args:
        limit: Maximum number of tweets to return (default 100)
        
    Returns:
        List of tweet dictionaries with engagement metrics and their history
    """
    with sqlite3.connect("tweets.db") as conn:
        conn.row_factory = sqlite3.Row  # This lets us access columns by name

        # Get tweets and all their engagement data in one query
        cursor = conn.execute("""
            SELECT t.*, e.likes, e.retweets, e.replies, e.views, e.captured_at
            FROM tweets t
            LEFT JOIN engagements e ON t.tweet_id = e.tweet_id
            ORDER BY e.captured_at DESC
            LIMIT ?
        """, (limit,))

        # Group the results by tweet
        tweets_data = defaultdict(lambda: {'engagement_history': []})
        current_time = datetime.datetime.now(datetime.timezone.utc)

        for row in cursor:
            tweet_id = row['tweet_id']

            if DEBUG:
                # Print all keys in row
                for key in row.keys():
                    value = row[key]
                    # iterate if value is a dict
                    if isinstance(value, dict):
                        for k2, v2 in value.items():
                            print(f"  {k2}")
                    else:
                        print(f"{key}")

            # Initialize tweet data if this is the first row for this tweet
            if 'username' not in tweets_data[tweet_id]:
                created_time = datetime.datetime.strptime(row['created_at'], "%a %b %d %H:%M:%S %z %Y")
                age_hours = max(0.1, (current_time - created_time).total_seconds() / 3600)

                tweets_data[tweet_id].update({
                    'tweet_id': tweet_id,
                    'username': row['username'],
                    'name': row['name'],
                    'text': row['text'],
                    'created_at': row['created_at'],
                    'age_hours': round(age_hours, 1),
                    'following': bool(row['following'])
                })

            # Parse the captured_at timestamp and calculate rates
            if row['captured_at'] is not None:
                captured_time = datetime.datetime.fromisoformat(row['captured_at'].replace('Z', '+00:00'))
                created_time = datetime.datetime.strptime(row['created_at'], "%a %b %d %H:%M:%S %z %Y")
                age_hours = max(0.1, (captured_time - created_time).total_seconds() / 3600)

                # Update current engagement (will end up with the latest due to ORDER BY)
                tweets_data[tweet_id]['current_engagement'] = {
                    'likes': row['likes'] or 0,
                    'retweets': row['retweets'] or 0,
                    'replies': row['replies'] or 0,
                    'views': row['views'] or 0,
                    'captured_at': row['captured_at']
                }
            else:
                # No engagement data yet, use zeros
                tweets_data[tweet_id]['current_engagement'] = {
                    'likes': 0,
                    'retweets': 0,
                    'replies': 0,
                    'views': 0,
                    'captured_at': None
                }

        return list(tweets_data.values())


def print_tweet(tweet):
    """Print a formatted tweet with its engagement metrics and history."""
    eng = tweet['current_engagement']
    likes_per_hour = eng['likes'] / tweet['age_hours']
    print(f"@{tweet['username']} ({tweet['name']}) - {likes_per_hour:,.0f} likes/h (Followed={tweet['following']})")
    # print(f"Tweet ID: {tweet['tweet_id']}")
    print(f"Tweet: {tweet['text']}")
    # print(f"Age: {tweet['age_hours']} hours")

if __name__ == '__main__':
    # Get limit argument if it's passed in
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 100

    # Get tweets
    tweets = get_recent_tweets(limit=limit)
    for tweet in tweets:
        print('-' * 80)
        print_tweet(tweet)
