import datetime
import sqlite3


def get_recent_tweets(limit=100):
    """Get the most recently captured tweets.
    
    Args:
        limit: Maximum number of tweets to return (default 100)
        
    Returns:
        List of tweet dictionaries with engagement metrics
    """
    with sqlite3.connect("tweets.db") as conn:
        conn.row_factory = sqlite3.Row  # This lets us access columns by name
        cursor = conn.execute("""
            SELECT * FROM tweets 
            ORDER BY captured_at DESC 
            LIMIT ?
        """, (limit,))
        
        tweets = []
        current_time = datetime.datetime.now(datetime.timezone.utc)
        
        for row in cursor:
            # Calculate age and engagement rates
            created_time = datetime.datetime.strptime(row['created_at'], "%a %b %d %H:%M:%S %z %Y")
            age_hours = max(0.1, (current_time - created_time).total_seconds() / 3600)
            
            tweets.append({
                'tweet_id': row['tweet_id'],
                'username': row['username'],
                'name': row['name'],
                'text': row['text'],
                'created_at': row['created_at'],
                'age_hours': round(age_hours, 1),
                'likes': row['likes'],
                'retweets': row['retweets'],
                'replies': row['replies'],
                'views': row['views'],
                'engagement_per_hour': {
                    'likes': round(row['likes'] / age_hours, 1),
                    'retweets': round(row['retweets'] / age_hours, 1),
                    'replies': round(row['replies'] / age_hours, 1),
                    'views': round(row['views'] / age_hours, 1)
                }
            })
    
    return tweets

def print_tweet(tweet):
    """Print a formatted tweet with its engagement metrics."""
    print(f"\n@{tweet['username']} ({tweet['name']})")
    print(f"Tweet ID: {tweet['tweet_id']}")
    print(f"Tweet: {tweet['text'][:500]}")
    print(f"Age: {tweet['age_hours']} hours")
    print(f"Total engagement: {tweet['likes']} likes, {tweet['retweets']} retweets, {tweet['replies']} replies, {tweet['views']} views")
    print(f"Engagement per hour: {tweet['engagement_per_hour']['likes']} likes/h, "
          f"{tweet['engagement_per_hour']['retweets']} retweets/h, "
          f"{tweet['engagement_per_hour']['replies']} replies/h, "
          f"{tweet['engagement_per_hour']['views']} views/h")

if __name__ == '__main__':
    # Example usage
    tweets = get_recent_tweets()
    for tweet in tweets:
        print_tweet(tweet)
        print('-' * 80)
