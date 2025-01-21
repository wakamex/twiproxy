# %%
import sqlite3
from datetime import datetime

import matplotlib.pyplot as plt
import seaborn as sns


def get_tweet_data(min_observations=5, max_age=100):
    """Get tweet data with likes and age.

    Args:
        min_observations: Minimum number of observations required for a tweet
        max_age: Maximum age in hours to include
    """
    with sqlite3.connect("tweets.db") as conn:
        query = """
            WITH tweet_counts AS (
                SELECT tweet_id, COUNT(*) as observation_count
                FROM engagements
                GROUP BY tweet_id
                HAVING COUNT(*) > ?
            )
            SELECT
                t.tweet_id,
                t.username,
                t.created_at,
                e.likes,
                e.captured_at
            FROM tweets t
            JOIN engagements e ON t.tweet_id = e.tweet_id
            JOIN tweet_counts tc ON t.tweet_id = tc.tweet_id
        """
        cursor = conn.execute(query, (min_observations,))
        results = cursor.fetchall()

        # Group by username
        tweets = {}
        for tweet_id, username, created_at, likes, captured_at in results:
            if username not in tweets:
                tweets[username] = {'ages': [], 'likes': []}

            # Parse timestamps and calculate age
            created_time = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
            captured_time = datetime.fromisoformat(captured_at.replace('Z', '+00:00'))
            age_hours = (captured_time - created_time).total_seconds() / 3600

            if age_hours < max_age:  # Filter by max age
                tweets[username]['ages'].append(age_hours)
                tweets[username]['likes'].append(likes)

        return tweets

def linear_regression(x, y):
    """Calculate linear regression parameters."""
    n = len(x)
    if n < 2:
        return 0, 0, 0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

    if denominator == 0:
        return 0, 0, 0

    slope = numerator / denominator
    intercept = mean_y - slope * mean_x

    # Calculate R-squared
    y_pred = [slope * x[i] + intercept for i in range(n)]
    ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((y[i] - mean_y) ** 2 for i in range(n))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

    return slope, intercept, r_squared

def plot_likes_vs_age():
    """Create a scatter plot of likes vs. age with linear fits."""
    tweets = get_tweet_data(min_observations=5, max_age=100)

    plt.figure(figsize=(12, 8))

    # Prepare data for seaborn
    all_ages = []
    all_likes = []
    all_usernames = []

    for username, data in tweets.items():
        all_ages.extend(data['ages'])
        all_likes.extend(data['likes'])
        all_usernames.extend([username] * len(data['ages']))

    # Plot with seaborn
    sns.scatterplot(x=all_ages, y=all_likes, hue=all_usernames, alpha=0.6, legend=False)

    # Add linear fits
    for username, data in tweets.items():
        if len(data['ages']) > 1:
            slope, intercept, r2 = linear_regression(data['ages'], data['likes'])
            plt.plot([min(data['ages']), max(data['ages'])], 
                    [slope * min(data['ages']) + intercept, slope * max(data['ages']) + intercept],
                    '--', alpha=0.8)

    plt.title('Tweet Likes vs. Age (< 100 hours)')
    plt.xlabel('Age (hours)')
    plt.ylabel('Likes')

    plt.tight_layout()
    plt.savefig('likes_vs_age.png', dpi=300)
    plt.close()

def plot_virality_distribution():
    """Create a scatter plot of virality vs number of observations."""
    tweets = get_tweet_data(min_observations=2, max_age=100)

    # Calculate virality and count observations for each tweet
    virality_data = []
    for username, data in tweets.items():
        if len(data['ages']) > 1:
            slope, _, r2 = linear_regression(data['ages'], data['likes'])
            if r2 > 0.8:  # Only include tweets with good linear fit
                virality_data.append({
                    'username': username,
                    'virality': slope,
                    'observations': len(data['ages'])
                })

    # Extract data for plotting
    viralities = [d['virality'] for d in virality_data]
    observations = [d['observations'] for d in virality_data]
    usernames = [d['username'] for d in virality_data]

    # Calculate R² between virality and number of observations
    _, _, r2 = linear_regression(observations, viralities)

    plt.figure(figsize=(12, 8))
    sns.scatterplot(x=observations, y=viralities, alpha=0.6)

    plt.title(f'Tweet Virality vs Number of Observations (R² = {r2:.3f})')
    plt.xlabel('Number of Observations')
    plt.ylabel('Virality (likes/hour)')
    plt.tight_layout()
    plt.savefig('virality_vs_observations.png', dpi=300)
    plt.close()

if __name__ == "__main__":
    plot_likes_vs_age()
    plot_virality_distribution()

# %%
