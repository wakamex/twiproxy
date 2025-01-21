import datetime
import json
import sqlite3


def debug_log(message):
    """Write a message to proxy.log."""
    with open('proxy.log', 'a', encoding='utf-8') as log:
        log.write(str(message) + '\n')

DEBUG = False  # Enable debug mode for better logging

# Get current time with timezone
current_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5)))

# Connect to the SQLite database
conn = sqlite3.connect("requests.db")
cursor = conn.cursor()

NUM_TO_DISPLAY = 100

# First print all URLs to see what we have
debug_log("Available URLs:")
cursor.execute("SELECT DISTINCT url FROM requests ORDER BY url")
for (url,) in cursor.fetchall():
    debug_log(f"URL: {url}")
debug_log("\n" + "="*80 + "\n")

# Fetch the last 100 requests
cursor.execute("SELECT timestamp, url, method, status, body FROM requests ORDER BY timestamp DESC LIMIT 100")
data = cursor.fetchall()

def extract_tweet_info(tweet_data, current_time):
    try:
        result = tweet_data['tweet_results']['result']
        if 'tweet' in result:
            result = result['tweet']

        # Get user info
        user = result['core']['user_results']['result']['legacy']
        username = user.get('screen_name', '')
        name = user.get('name', '')
        following = user.get('following', False)

        if DEBUG:
            debug_log(f"\nFollowing status for @{username}:")
            debug_log(f"Raw user data: {json.dumps(user, indent=2)}")
            debug_log(f"Following: {following}")

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
            },
            'following': following
        }
    except (KeyError, TypeError) as e:
        debug_log(f"Error extracting tweet info: {str(e)}")
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
                                debug_log("\nTweet data structure:")
                                debug_log(json.dumps(tweet_data, indent=2))
                            if tweet_data['itemType'] == 'TimelineTweet':
                                tweet_info = extract_tweet_info(tweet_data, current_time)
                                if tweet_info:
                                    tweet_info['tweet_id'] = tweet_data['tweet_results']['result'].get('rest_id')
                                    tweets.append(tweet_info)
    except Exception as e:
        debug_log(f"\nError parsing timeline: {str(e)}")
    return tweets

num_display=0
for row in data:
    # Only show timeline-related requests
    if 'HomeTimeline' not in row[1]:
        continue

    debug_log("=" * 80)
    debug_log(f"Time: {row[0]}")
    debug_log(f"URL: {row[1]}")
    debug_log(f"Method: {row[2]}")
    debug_log(f"Status: {row[3]}")

    # For timeline requests, extract tweets
    if row[4]:
        try:
            body_json = json.loads(row[4])
            tweets = parse_body(body_json, current_time)
            for tweet in tweets:
                debug_log(f"\n@{tweet['username']} ({tweet['name']})")
                if tweet['tweet_id']:
                    debug_log(f"Tweet ID: {tweet['tweet_id']}")
                debug_log(f"Tweet: {tweet['text'][:500]}")
                debug_log(f"Age: {tweet['age_hours']} hours")
                debug_log(f"Total engagement: {tweet['likes']} likes, {tweet['retweets']} retweets, {tweet['replies']} replies, {tweet['views']} views")
                debug_log(f"Engagement per hour: {tweet['engagement_per_hour']['likes']} likes/h, {tweet['engagement_per_hour']['retweets']} retweets/h, {tweet['engagement_per_hour']['replies']} replies/h, {tweet['engagement_per_hour']['views']} views/h")
                debug_log(f"Following: {tweet['following']}")
        except Exception as e:
            debug_log(f"\nError parsing timeline: {str(e)}")
            debug_log("Raw body preview:")
            debug_log(row[4][:500])
    else:
        debug_log("\nBody: [No Body]")

    debug_log("")

    num_display += 1
    if num_display >= NUM_TO_DISPLAY:
        break
