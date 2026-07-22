import subprocess
import time
import os
import yaml
import json
from datetime import datetime

# Fix PATH for docker exec to find pipx installations
os.environ["PATH"] = f"/root/.local/bin:{os.environ.get('PATH', '')}"

from database import SessionLocal, Setting

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

import os
from tweety import Twitter

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

def fetch_tweets_for_keyword(keyword, app):
    print(f"🔍 Searching tweets for: {keyword} in India...")
    try:
        search_query = f'"{keyword}" (India OR Indian OR Delhi OR Mumbai)'
        
        # Search using Tweety-ns
        tweets = app.search(search_query, pages=1)
        
        formatted_tweets = []
        for tweet in tweets:
            formatted_tweets.append({
                "id": str(tweet.id),
                "text": tweet.text,
                "createdAtISO": str(tweet.created_on),
                "author": {
                    "name": tweet.author.name if tweet.author else "",
                    "screenName": tweet.author.username if tweet.author else "",
                    "profileImageUrl": tweet.author.profile_image_url_https if tweet.author else ""
                },
                "media": [{"type": "photo", "url": pic.media_url_https} for pic in tweet.media if pic.type == "photo"],
                "metrics": {
                    "likeCount": tweet.likes,
                    "retweetCount": tweet.retweet_counts,
                    "replyCount": tweet.replies
                }
            })
        return formatted_tweets
    except Exception as e:
        print(f"❌ Exception for {keyword}: {e}")
        return None

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_filename = "twitter_report_latest.json"
    
    print(f"🚀 Starting Twitter Monitor. Results will be saved as JSON to {output_filename}\n")
    
    # Initialize Tweety and start session using your configured cookies
    app = Twitter("session")
    auth_token = os.environ.get("TWITTER_AUTH_TOKEN")
    ct0 = os.environ.get("TWITTER_CT0")
    
    if auth_token and ct0:
        # Load cookies explicitly
        app.load_cookies(f"auth_token={auth_token}; ct0={ct0}")
    else:
        print("⚠️ Warning: No TWITTER_AUTH_TOKEN or TWITTER_CT0 found. Search might fail or be limited.")

    all_data = {}
    
    for keyword in KEYWORDS:
        data = fetch_tweets_for_keyword(keyword, app)
        if data:
            all_data[keyword] = data
            print(f"✅ Found {len(data) if isinstance(data, list) else 'some'} records for {keyword}")
        
        # Har search ke baad wait
        time.sleep(3) 
            
    from database import SessionLocal, Post
    
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
                    dt = datetime.fromisoformat(tweet.get("createdAtISO", "").replace("Z", "+00:00"))
                except:
                    dt = datetime.utcnow()
                    
                author = tweet.get("author", {})
                new_post = Post(
                    platform="twitter",
                    keyword=keyword,
                    post_id=str(tweet.get("id")),
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
