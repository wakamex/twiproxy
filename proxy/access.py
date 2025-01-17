import datetime
import json
import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect("requests.db")
cursor = conn.cursor()

# First print all URLs to see what we have
print("Available URLs:")
cursor.execute("SELECT DISTINCT url FROM requests ORDER BY url")
for (url,) in cursor.fetchall():
    print(f"URL: {url}")
print("\n" + "="*80 + "\n")

# Fetch the last 100 requests
cursor.execute("SELECT timestamp, url, method, status, body FROM requests ORDER BY timestamp DESC LIMIT 100")
data = cursor.fetchall()

NUM_TO_DISPLAY = 100
DEBUG=False

# Get current time with timezone
current_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5)))

def extract_tweet_info(tweet_data, current_time):
    try:
        result = tweet_data['tweet_results']['result']
        if 'tweet' in result:
            result = result['tweet']
            
        # Get user info
        user = result['core']['user_results']['result']['legacy']
        username = user.get('screen_name', '')
        name = user.get('name', '')

        # Get tweet text and timestamp
        if 'legacy' in result:
            text = result['legacy'].get('full_text', '')
            created_at = result['legacy'].get('created_at', '')
            # Get engagement metrics
            favorite_count = int(result['legacy'].get('favorite_count', 0))
            retweet_count = int(result['legacy'].get('retweet_count', 0))
            reply_count = int(result['legacy'].get('reply_count', 0))
            view_count = int(result.get('views', {}).get('count', 0))
        elif 'note_tweet' in result:
            text = result['note_tweet']['note_tweet_results']['result']['text']
            created_at = result.get('created_at', '')
            favorite_count = retweet_count = reply_count = view_count = 0
        else:
            return None

        # Calculate tweet age in hours using provided current time
        if created_at:
            tweet_time = datetime.datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
            age_hours = max(0.1, (current_time - tweet_time).total_seconds() / 3600)  # Avoid division by zero
        else:
            age_hours = 0

        return {
            'username': username,
            'name': name,
            'text': text,
            'created_at': created_at,
            'age_hours': round(age_hours, 1),
            'likes': favorite_count,
            'retweets': retweet_count,
            'replies': reply_count,
            'views': view_count,
            'engagement_per_hour': {
                'likes': round(favorite_count / age_hours, 1),
                'retweets': round(retweet_count / age_hours, 1),
                'replies': round(reply_count / age_hours, 1),
                'views': round(view_count / age_hours, 1)
            }
        }
    except (KeyError, TypeError) as e:
        print(f"Error extracting tweet info: {str(e)}")
        return None

def parse_body(body_json, current_time):
    """Parse the timeline body JSON and extract tweet information.

    Args:
        body_json: The parsed JSON body from the response
        current_time: Current datetime with timezone for age calculations

    Returns:
        List of dictionaries containing tweet information
    """
    tweets = []
    try:
        if 'data' in body_json and 'home' in body_json['data']:
            timeline = body_json['data']['home']['home_timeline_urt']
            for instruction in timeline.get('instructions', []):
                if instruction['type'] == 'TimelineAddEntries':
                    for entry in instruction['entries']:
                        if 'content' in entry and 'itemContent' in entry['content']:
                            tweet_data = entry['content']['itemContent']
                            if DEBUG:
                                print("\nTweet data structure:")
                                print(json.dumps(tweet_data, indent=2))
                            if tweet_data['itemType'] == 'TimelineTweet':
                                tweet_info = extract_tweet_info(tweet_data, current_time)
                                if tweet_info:
                                    tweet_info['tweet_id'] = tweet_data['tweet_results']['result'].get('rest_id')
                                    tweets.append(tweet_info)
    except Exception as e:
        print(f"\nError parsing timeline: {str(e)}")
    return tweets

num_display=0
for row in data:
    # Only show timeline-related requests
    if 'HomeTimeline' not in row[1]:
        continue

    print("=" * 80)
    print(f"Time: {row[0]}")
    print(f"URL: {row[1]}")
    print(f"Method: {row[2]}")
    print(f"Status: {row[3]}")

    # For timeline requests, extract tweets
    if row[4]:
        try:
            body_json = json.loads(row[4])
            tweets = parse_body(body_json, current_time)
            for tweet in tweets:
                print(f"\n@{tweet['username']} ({tweet['name']})")
                if tweet['tweet_id']:
                    print(f"Tweet ID: {tweet['tweet_id']}")
                print(f"Tweet: {tweet['text'][:500]}")
                print(f"Age: {tweet['age_hours']} hours")
                print(f"Total engagement: {tweet['likes']} likes, {tweet['retweets']} retweets, {tweet['replies']} replies, {tweet['views']} views")
                print(f"Engagement per hour: {tweet['engagement_per_hour']['likes']} likes/h, {tweet['engagement_per_hour']['retweets']} retweets/h, {tweet['engagement_per_hour']['replies']} replies/h, {tweet['engagement_per_hour']['views']} views/h")
        except Exception as e:
            print(f"\nError parsing timeline: {str(e)}")
            print("Raw body preview:")
            print(row[4][:500])
    else:
        print("\nBody: [No Body]")

    print()

    num_display += 1
    if num_display >= NUM_TO_DISPLAY:
        break
