import time
import os
import yaml
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

from database import SessionLocal, Setting, Post

def load_twitter_cookies():
    # Load from DB if available
    try:
        db = SessionLocal()
        auth_token = db.query(Setting).filter(Setting.key == 'twitter_auth_token').first()
        ct0 = db.query(Setting).filter(Setting.key == 'twitter_ct0').first()
        if auth_token and ct0 and auth_token.value and ct0.value:
            os.environ["TWITTER_AUTH_TOKEN"] = auth_token.value
            os.environ["TWITTER_CT0"] = ct0.value
        db.close()
    except Exception as e:
        pass

    # Fallback to config file if still missing
    if not os.environ.get("TWITTER_AUTH_TOKEN"):
        CONFIG_FILE = "/root/.agent-reach/config.yaml"
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = yaml.safe_load(f)
                    os.environ["TWITTER_AUTH_TOKEN"] = config.get("twitter_auth_token", "")
                    os.environ["TWITTER_CT0"] = config.get("twitter_ct0", "")
            except Exception as e:
                print(f"⚠️ Could not load Agent Reach config: {e}")

load_twitter_cookies()

# Aapke saare keywords yahan hain
KEYWORDS = [
    "Extended Producer Responsibility",
    "EPR India",
    "Plastic Waste",
    "Battery Waste",
    "E-Waste",
    "Tyre Waste",
    "Used Oil",
    "CPCB",
    "SPCB",
    "ESG",
    "Carbon Credits",
    "Sustainability",
    "Circular Economy",
    "Waste Management Rules",
    "Recycling",
    "Hazardous Waste",
    "PWM Rules",
    "BMW Rules",
    "Solid Waste Rules",
    "Environmental Compliance",
    "Climate Tech"
]

def parse_graphql_timeline(json_data):
    formatted_tweets = []
    try:
        instructions = json_data.get('data', {}).get('search_by_raw_query', {}).get('search_timeline', {}).get('timeline', {}).get('instructions', [])
        for instruction in instructions:
            if instruction.get('type') == 'TimelineAddEntries':
                for entry in instruction.get('entries', []):
                    item_content = entry.get('content', {}).get('itemContent', {})
                    if item_content.get('itemType') == 'TimelineTweet':
                        tweet_result = item_content.get('tweet_results', {}).get('result', {})
                        if 'tweet' in tweet_result:
                            tweet_result = tweet_result['tweet']
                        
                        legacy = tweet_result.get('legacy', {})
                        core = tweet_result.get('core', {}).get('user_results', {}).get('result', {}).get('legacy', {})
                        
                        if not legacy:
                            continue
                            
                        # Extract media if any
                        media_urls = []
                        if 'extended_entities' in legacy and 'media' in legacy['extended_entities']:
                            for m in legacy['extended_entities']['media']:
                                if m.get('type') == 'photo':
                                    media_urls.append({"type": "photo", "url": m.get('media_url_https')})
                        
                        formatted_tweets.append({
                            "id": tweet_result.get('rest_id', ""),
                            "text": legacy.get('full_text', ""),
                            "createdAtISO": legacy.get('created_at', ""),
                            "author": {
                                "name": core.get('name', ""),
                                "screenName": core.get('screen_name', ""),
                                "profileImageUrl": core.get('profile_image_url_https', "")
                            },
                            "media": media_urls,
                            "metrics": {
                                "likeCount": legacy.get('favorite_count', 0),
                                "retweetCount": legacy.get('retweet_count', 0),
                                "replyCount": legacy.get('reply_count', 0)
                            }
                        })
    except Exception as e:
        print(f"Error parsing timeline: {e}")
    return formatted_tweets

def fetch_tweets_for_keywords(keywords):
    all_data = {}
    auth_token = os.environ.get("TWITTER_AUTH_TOKEN")
    ct0 = os.environ.get("TWITTER_CT0")
    
    if not auth_token or not ct0:
        print("⚠️ Warning: No TWITTER_AUTH_TOKEN or TWITTER_CT0 found.")
        return all_data

    print(f"🚀 Starting Playwright headless browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        context.add_cookies([
            {'name': 'auth_token', 'value': auth_token, 'domain': '.x.com', 'path': '/'},
            {'name': 'ct0', 'value': ct0, 'domain': '.x.com', 'path': '/'}
        ])
        
        page = context.new_page()
        
        for keyword in keywords:
            print(f"🔍 Searching tweets for: {keyword} in India...")
            captured_tweets = []
            
            def handle_response(response):
                if "SearchTimeline" in response.url and response.request.method == "GET":
                    try:
                        data = response.json()
                        tweets = parse_graphql_timeline(data)
                        if tweets:
                            captured_tweets.extend(tweets)
                    except:
                        pass
                        
            # Add listener for this search
            page.on("response", handle_response)
            
            try:
                search_query = f'"{keyword}" (India OR Indian OR Delhi OR Mumbai)'
                search_url = f"https://x.com/search?q={search_query}&src=typed_query&f=live"
                page.goto(search_url)
                
                # Wait for the timeline to load by waiting for a tweet cell, or timeout after 10s
                page.wait_for_selector('article[data-testid="tweet"]', timeout=10000)
                
                # Scroll down a bit to trigger any pending data loads
                page.mouse.wheel(0, 1000)
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Exception for {keyword}: (Timeout or no tweets found)")
                
            # Clean up the listener so it doesn't duplicate for the next keyword
            page.remove_listener("response", handle_response)
            
            if captured_tweets:
                all_data[keyword] = captured_tweets
                print(f"✅ Found {len(captured_tweets)} records for {keyword}")
            else:
                print(f"⚠️ No records captured for {keyword}")
                
            time.sleep(3)
            
        browser.close()
        
    return all_data

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_filename = "twitter_report_latest.json"
    
    print(f"🚀 Starting Twitter Monitor with Playwright Interception.\n")
    
    all_data = fetch_tweets_for_keywords(KEYWORDS)
            
    db = SessionLocal()
    try:
        seen_ids = set()
        for keyword, data in all_data.items():
            if not isinstance(data, list):
                continue
            for tweet in data:
                post_id = str(tweet.get("id"))
                if post_id in seen_ids:
                    continue
                existing_post = db.query(Post).filter(Post.post_id == post_id).first()
                if existing_post:
                    existing_post.fetched_at = datetime.utcnow()
                    continue
                
                media_url = ""
                if tweet.get("media"):
                    for m in tweet["media"]:
                        if m.get("type") == "photo":
                            media_url = m.get("url")
                            break
                            
                try:
                    dt_str = tweet.get("createdAtISO", "").replace("Z", "+00:00")
                    # Twitter string: "Thu Jun 22 12:00:00 +0000 2023"
                    if '+0000' in dt_str:
                        dt = datetime.strptime(dt_str, "%a %b %d %H:%M:%S %z %Y").replace(tzinfo=None)
                    else:
                        dt = datetime.fromisoformat(dt_str)
                except Exception as e:
                    dt = datetime.utcnow()
                    
                author = tweet.get("author", {})
                new_post = Post(
                    platform="twitter",
                    keyword=keyword,
                    post_id=post_id,
                    author_name=author.get("name"),
                    author_handle=author.get("screenName"),
                    author_avatar=author.get("profileImageUrl"),
                    text=tweet.get("text"),
                    media_url=media_url,
                    metrics=tweet.get("metrics"),
                    created_at=dt
                )
                db.add(new_post)
                seen_ids.add(post_id)
        db.commit()
        print(f"\n✅ Done! Tweets successfully saved to database")
    except Exception as e:
        print(f"❌ Error saving to DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
