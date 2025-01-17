"""Grok API Flow Analysis Module.

This module analyzes the flow of Grok API calls to understand the sequence, timing, and relationships
between different API endpoints.

Main API Endpoints:
- add_response.json: Generates Grok responses
- CreateGrokConversation: Creates new conversations
- GrokHome: Home interface

Feature Flags:
- analyze_button_fetch_trends
- analyze_post_followups
- share_attachment
- image_annotation

GraphQL Operations:
- TweetDetail: Gets tweet information
- TweetResultByRestId: Retrieves tweet by ID
- UserTweets: Gets user timeline
- ExploreSidebar: Gets explore page content
- BroadcastQuery: Gets broadcast information
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class ApiCall:
    """Represent a single API call in the Grok flow."""

    url: str
    timestamp: datetime
    request_id: str
    response_id: Optional[str]
    conversation_id: Optional[str]
    tweet_id: Optional[str]

class GrokFlow:
    """Analyze the sequence and relationships of Grok API calls."""

    def __init__(self, db_path: str = "/code/proxy/requests.db"):
        self.db_path = db_path
        self.calls: List[ApiCall] = []
        self.conversation_map: Dict[str, List[str]] = {}
        self.tweet_map: Dict[str, List[str]] = {}

    def load_calls(self, time_window: Optional[int] = None) -> None:
        """Load API calls from the database within an optional time window (in seconds).
        
        Args:
            time_window: Optional number of seconds to look back
        """
        base_query = """
            SELECT url, timestamp, 
                   ROWID as request_id,
                   NULL as response_id,
                   CASE 
                       WHEN json_valid(body) THEN json_extract(body, '$.conversation_id')
                       ELSE NULL
                   END as conversation_id,
                   CASE 
                       WHEN json_valid(body) THEN json_extract(body, '$.tweet_id')
                       ELSE NULL
                   END as tweet_id
            FROM requests 
            WHERE url LIKE '%grok%'
            AND status = 200
        """

        if time_window:
            query = base_query + f" AND timestamp > datetime('now', '-{time_window} seconds')"
        else:
            query = base_query

        query += " ORDER BY timestamp DESC"

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for row in cursor.execute(query):
                    try:
                        call = ApiCall(
                            url=row[0],
                            timestamp=datetime.fromisoformat(row[1].replace('Z', '+00:00')),
                            request_id=str(row[2]),
                            response_id=str(row[3]) if row[3] else None,
                            conversation_id=str(row[4]) if row[4] else None,
                            tweet_id=str(row[5]) if row[5] else None
                        )
                        self.calls.append(call)
                    except Exception as e:
                        print(f"Error processing row {row[2]}: {e}")
                        continue
        except Exception as e:
            print(f"Database error: {e}")

    def analyze_timing(self) -> List[Tuple[str, float]]:
        """Analyze timing between different types of API calls.

        Returns:
            List of (call_type, avg_time) tuples
        """
        timings: Dict[str, List[float]] = {}

        for i in range(len(self.calls) - 1):
            current = self.calls[i]
            next_call = self.calls[i + 1]

            # Extract call type from URL
            current_type = self._get_call_type(current.url)
            if current_type:
                delta = (next_call.timestamp - current.timestamp).total_seconds()
                if current_type not in timings:
                    timings[current_type] = []
                timings[current_type].append(delta)

        return [(call_type, sum(times)/len(times)) 
                for call_type, times in timings.items()]

    def analyze_conversation_flow(self) -> Dict[str, List[str]]:
        """Analyze the flow of API calls within conversations.

        Returns:
            Dictionary mapping conversation IDs to lists of API call types
        """
        flows: Dict[str, List[str]] = {}

        for call in self.calls:
            if call.conversation_id:
                conv_id = call.conversation_id
                if conv_id not in flows:
                    flows[conv_id] = []
                call_type = self._get_call_type(call.url)
                if call_type:
                    flows[conv_id].append(call_type)

        return flows

    def get_feature_flags(self) -> Dict[str, bool]:
        """Extract Grok feature flags from GraphQL queries.

        Returns:
            Dictionary of feature flag names and their values
        """
        flags: Dict[str, bool] = {}

        for call in self.calls:
            if "graphql" in call.url:
                # Look for feature flags in URL parameters
                flag_markers = [
                    "grok_analyze_button_fetch_trends_enabled",
                    "grok_analyze_post_followups_enabled",
                    "grok_share_attachment_enabled",
                    "grok_image_annotation_enabled"
                ]

                for marker in flag_markers:
                    if marker in call.url:
                        # Extract value after marker
                        value = call.url.split(marker + "%22%3A")[1].split("%")[0]
                        flags[marker] = value.lower() == "true"

        return flags

    def analyze_explore_content(self) -> Dict[str, List[Dict]]:
        """Analyze content returned by the ExploreSidebar endpoint.
        
        Returns:
            Dictionary with events and trends
        """
        content = {
            'events': [],
            'trends': []
        }

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                query = """
                    SELECT body 
                    FROM requests 
                    WHERE url LIKE '%ExploreSidebar%' 
                    AND status = 200 
                    AND json_valid(body)
                    ORDER BY timestamp DESC
                    LIMIT 1
                """

                row = cursor.execute(query).fetchone()
                if row and row[0]:
                    data = json.loads(row[0])
                    if 'data' in data and 'explore_sidebar' in data['data']:
                        sidebar = data['data']['explore_sidebar']
                        if 'timeline' in sidebar:
                            for instruction in sidebar['timeline'].get('instructions', []):
                                if instruction.get('type') == 'TimelineAddEntries':
                                    for entry in instruction.get('entries', []):
                                        content_data = entry.get('content', {})
                                        if content_data.get('entryType') == 'TimelineTimelineModule':
                                            for item in content_data.get('items', []):
                                                item_content = item.get('item', {}).get('itemContent', {})

                                                # Event summaries
                                                if item_content.get('itemType') == 'TimelineEventSummary':
                                                    event = {
                                                        'title': item_content.get('title', ''),
                                                        'time': item_content.get('timeString', ''),
                                                        'media_url': item_content.get('image', {}).get('url', '')
                                                    }
                                                    content['events'].append(event)

                                                # Trending topics
                                                elif item_content.get('itemType') == 'TimelineTrend':
                                                    trend = {
                                                        'name': item_content.get('name', ''),
                                                        'context': item_content.get('trend_metadata', {}).get('domain_context', ''),
                                                        'description': item_content.get('trend_metadata', {}).get('meta_description', '')
                                                    }
                                                    content['trends'].append(trend)
        except Exception as e:
            print(f"Error analyzing explore content: {e}")

        return content

    @staticmethod
    def _get_call_type(url: str) -> Optional[str]:
        """Extract the type of API call from the URL."""
        if "add_response.json" in url:
            return "add_response"
        elif "CreateGrokConversation" in url:
            return "create_conversation"
        elif "GrokHome" in url:
            return "home"
        elif "TweetDetail" in url:
            return "tweet_detail"
        elif "TweetResultByRestId" in url:
            return "tweet_by_id"
        elif "UserTweets" in url:
            return "user_tweets"
        elif "ExploreSidebar" in url:
            return "explore"
        elif "BroadcastQuery" in url:
            return "broadcast"
        return None

def main():
    """Run the Grok API flow analysis."""
    flow = GrokFlow()

    # Load calls from the last hour
    flow.load_calls(time_window=3600)

    # Analyze timing between calls
    print("\nAPI Call Timing Analysis:")
    print("=" * 50)
    for call_type, avg_time in flow.analyze_timing():
        print(f"{call_type:20s}: {avg_time:.2f}s average")

    # Analyze conversation flows
    print("\nConversation Flow Analysis:")
    print("=" * 50)
    for conv_id, call_types in flow.analyze_conversation_flow().items():
        print(f"\nConversation {conv_id}:")
        for i, call_type in enumerate(call_types, 1):
            print(f"{i}. {call_type}")

    # Get feature flags
    print("\nGrok Feature Flags:")
    print("=" * 50)
    for flag, enabled in flow.get_feature_flags().items():
        print(f"{flag}: {'Enabled' if enabled else 'Disabled'}")

    # Analyze explore content
    print("\nExplore Content Analysis:")
    print("=" * 50)
    content = flow.analyze_explore_content()
    print("Events:")
    for event in content['events']:
        print(f"Title: {event['title']}")
        print(f"Time: {event['time']}")
        print(f"Media URL: {event['media_url']}")
        print()
    print("Trends:")
    for trend in content['trends']:
        print(f"Name: {trend['name']}")
        print(f"Context: {trend['context']}")
        print(f"Description: {trend['description']}")
        print()

if __name__ == '__main__':
    main()
