import datetime
import sqlite3
from collections import defaultdict


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
                    'age_hours': round(age_hours, 1)
                })

            # Parse the captured_at timestamp and calculate rates
            captured_time = datetime.datetime.fromisoformat(row['captured_at'].replace('Z', '+00:00'))
            created_time = datetime.datetime.strptime(row['created_at'], "%a %b %d %H:%M:%S %z %Y")
            age_hours = max(0.1, (captured_time - created_time).total_seconds() / 3600)

            engagement_point = {
                'age_hours': round(age_hours, 1),
                'timestamp': row['captured_at'],
                'total_engagement': {
                    'likes': row['likes'],
                    'retweets': row['retweets'],
                    'replies': row['replies'],
                    'views': row['views']
                },
                'rates': {
                    'likes': round(row['likes'] / age_hours, 1),
                    'retweets': round(row['retweets'] / age_hours, 1),
                    'replies': round(row['replies'] / age_hours, 1),
                    'views': round(row['views'] / age_hours, 1)
                }
            }

            tweets_data[tweet_id]['engagement_history'].append(engagement_point)

            # Update current engagement (will end up with the latest due to ORDER BY)
            tweets_data[tweet_id]['current_engagement'] = {
                'likes': row['likes'],
                'retweets': row['retweets'],
                'replies': row['replies'],
                'views': row['views'],
                'captured_at': row['captured_at']
            }

        return list(tweets_data.values())


def print_tweet(tweet):
    """Print a formatted tweet with its engagement metrics and history."""
    print(f"\n@{tweet['username']} ({tweet['name']})")
    print(f"Tweet ID: {tweet['tweet_id']}")
    print(f"Tweet: {tweet['text'][:500]}")
    print(f"Age: {tweet['age_hours']} hours")

    eng = tweet['current_engagement']
    print(f"\nCurrent engagement (as of {eng['captured_at']}):")
    print(f"  {eng['likes']} likes, {eng['retweets']} retweets, {eng['replies']} replies, {eng['views']} views")

    if tweet['engagement_history']:
        print("\nEngagement rates over time:")
        for point in tweet['engagement_history']:
            print(f"\nAt {point['timestamp']} (age: {point['age_hours']}h):")
            print(f"  Total: {point['total_engagement']['likes']} likes, {point['total_engagement']['retweets']} retweets")
            print(f"  Rates: {point['rates']['likes']} likes/h, {point['rates']['retweets']} retweets/h")
            print(f"         {point['rates']['replies']} replies/h, {point['rates']['views']} views/h")


if __name__ == '__main__':
    # Example usage
    tweets = get_recent_tweets()
    for tweet in tweets:
        print_tweet(tweet)
        print('-' * 80)
