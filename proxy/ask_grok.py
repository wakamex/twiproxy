"""Script for interacting with Grok's API to analyze tweets and retrieve conversation details.

API Flow:
    The complete flow for generating a Grok response involves these API calls:
    1. CreateGrokConversation: Creates a new conversation for analysis
       - Endpoint: /graphql/vvC5uy7pWWHXS2aDi1FZeA/CreateGrokConversation
       - Required headers:
           * authorization: Bearer token for authentication
           * x-csrf-token: Must match the ct0 cookie value
           * cookie: Contains essential auth tokens (ct0, auth_token, twid)
       - Request data: Not needed (empty POST request works)
       - Returns a conversation_id for subsequent calls
       - Average response time: ~0.3s
       
    2. add_response.json: Generates the Grok response
       - Endpoint: grok.x.com/2/grok/add_response.json
       - Required headers: Same as CreateGrokConversation
       - Request data:
           * responses[0].message: The prompt to send to Grok
           * responses[0].sender: 1 (required, request times out without it)
           * conversationId: ID from step 1
       - Response format: Multiple newline-separated JSON objects
           1. First object: Contains userChatItemId and agentChatItemId
           2. Subsequent objects: Contain actual response content
       - Average response time: ~0.3s

Authentication:
    Both endpoints require:
    - auth_token cookie: For user authentication
    - ct0 cookie: CSRF token that must match x-csrf-token header
    - x-csrf-token header: Must match ct0 cookie value
    - Authorization header: Bearer token

ID Relationships:
    1. Chat Item IDs:
        - Each message pair has a userChatItemId and agentChatItemId
        - agentChatItemId is always userChatItemId + 1
        Example:
            User: 1880083944181223424
            Agent: 1880083944181223425
"""

import base64
import json
import os
import sys

import requests

import proxy.tokens

TIMEOUT = 60
DEBUG = False

def load_tokens():
    """Load tokens from the database."""
    store = proxy.tokens.TokenStore()
    tokens = store.get_all_tokens()
    if not tokens:
        print("Error: No tokens found. Please make a request to Grok first.")
        sys.exit(1)
    return tokens

def generate_transaction_id():
    """Generate a transaction ID similar to those used by x.com.
    
    Returns a URL-safe base64 encoded string of 64 characters, matching Twitter's format:
    - Uses URL-safe encoding (- and _ instead of + and /)
    - No padding characters (=)
    - 64 characters in length
    """
    random_bytes = os.urandom(48)  # 48 bytes gives ~64 chars in base64
    return base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip("=")

def create_conversation(tokens):
    """Create a new Grok conversation.
    
    Args:
        tokens (dict): Authentication tokens from get_tokens()
    
    Returns:
        str: Conversation ID for subsequent API calls
    """
    url = "https://x.com/i/api/graphql/vvC5uy7pWWHXS2aDi1FZeA/CreateGrokConversation"

    # Match header order and casing from successful request
    headers = {
        'authorization': tokens['authorization'],
        'x-csrf-token': tokens['x-csrf-token'],
        'cookie': tokens['cookie'],
    }

    # Debug print request details
    if DEBUG:
        print("\nRequest URL:", url)
        print("\nRequest Headers:")
        for key, value in headers.items():
            print(f"{key}: {value}")

    response = requests.post(url, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()

    try:
        # First get the conversation ID from initial response
        result = response.json()
        if DEBUG:
            print("Initial response:", result)
        conversation_id = result['data']['create_grok_conversation']['conversation_id']
        if DEBUG:
            print(f"Got conversation ID: {conversation_id}")
        return conversation_id

    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error parsing response: {e}")
        print(f"Response content: {response.text}")
        raise

def ask_grok(tweet_id: str) -> dict:
    """Ask Grok to analyze a tweet.
    
    Args:
        tweet_id: ID of the tweet to analyze
        
    Returns:
        Dictionary containing Grok's response
    """
    # First create a conversation
    tokens = load_tokens()
    conversation_id = create_conversation(tokens)

    # Then get Grok's response
    url = "https://grok.x.com/2/grok/add_response.json"

    # Match header order and casing from successful request
    headers = {
        'authorization': tokens['authorization'],
        'x-csrf-token': tokens['x-csrf-token'],
        'cookie': tokens['cookie'],
    }

    tweet_url = f"https://x.com/{tweet_id}"

    data = {
        "responses": [
            {
                "message": f"Is this fake news? {tweet_url}\nRate it 100 for fake news and 0 for very factual. Respond in the following format:\nScore: [0-100]\nReason:",
                "sender": 1
            }
        ],
        "conversationId": conversation_id
    }

    # Debug print request details
    if DEBUG:
        print("\nRequest URL:", url)
        print("\nRequest Headers:")
        for key, value in headers.items():
            print(f"{key}: {value}")
        print("\nRequest Data:")
        print(json.dumps(data, indent=2))

    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=TIMEOUT)
    response.raise_for_status()

    try:
        # Split response into individual JSON objects
        json_objects = [obj for obj in response.text.split('\n') if obj.strip()]

        # Get chat IDs from first response
        first_response = json.loads(json_objects[0]) 
        user_chat_item_id = first_response.get('userChatItemId')
        agent_chat_item_id = first_response.get('agentChatItemId')

        if not user_chat_item_id or not agent_chat_item_id:
            print("Failed to retrieve chat IDs")
            print("Response:", first_response)
            return {
                'status': 'error',
                'message': 'Failed to retrieve chat IDs'
            }

        # The subsequent responses will contain the actual content
        message = ""
        for json_obj in json_objects[1:]:
            try:
                response_data = json.loads(json_obj)
                if 'result' in response_data:
                    result = response_data['result']
                    if 'message' in result:
                        message += result['message']
                        print(result['message'], end='')
            except json.JSONDecodeError as e:
                print(f"Error parsing response object: {e}")
                print(f"Object: {json_obj}")
                continue

        # Return success with conversation details
        return {
            'status': 'success',
            'conversation_id': conversation_id,
            'user_chat_item_id': user_chat_item_id,
            'agent_chat_item_id': agent_chat_item_id,
            'message': message
        }

    except Exception as e:
        print(f"Error processing response: {e}")
        print(f"Response content: {response.text}")
        return {
            'status': 'error',
            'message': str(e)
        }

def main():
    if len(sys.argv) != 2:
        print("Usage: python ask_grok.py <tweet_id>")
        sys.exit(1)

    tweet_id = sys.argv[1]
    result = ask_grok(tweet_id)
    if result['status'] == 'success':
        if DEBUG:
            print("Conversation ID:", result.get('conversation_id', 'Not found'))
            print("User Chat Item ID:", result.get('user_chat_item_id', 'Not found'))
            print("Agent Chat Item ID:", result.get('agent_chat_item_id', 'Not found'))
        print(result['message'])
    else:
        print("Failed to retrieve IDs")

if __name__ == "__main__":
    main()
