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

from ntscraper import Nitter

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

def fetch_tweets_for_keyword(keyword):
    print(f"🔍 Searching tweets for: {keyword} in India...")
    try:
        scraper = Nitter(log_level=1, skip_instance_check=False)
        search_query = f'"{keyword}" (India OR Indian OR Delhi OR Mumbai)'
        
        # Get tweets using ntscraper
        tweets_data = scraper.get_tweets(search_query, mode='term', number=10)
        
        if tweets_data and 'tweets' in tweets_data:
            formatted_tweets = []
            for tweet in tweets_data['tweets']:
                # Format to match your expected dictionary structure
                formatted_tweets.append({
                    "id": tweet.get("link", "").split("/")[-1] if "link" in tweet else str(hash(tweet.get("text", ""))),
                    "text": tweet.get("text", ""),
                    "createdAtISO": tweet.get("date", ""),
                    "author": {
                        "name": tweet.get("user", {}).get("name", ""),
                        "screenName": tweet.get("user", {}).get("username", ""),
                        "profileImageUrl": tweet.get("user", {}).get("avatar", "")
                    },
                    "media": [{"type": "photo", "url": pic} for pic in tweet.get("pictures", [])],
                    "metrics": {
                        "likeCount": tweet.get("stats", {}).get("likes", 0),
                        "retweetCount": tweet.get("stats", {}).get("retweets", 0),
                        "replyCount": tweet.get("stats", {}).get("comments", 0)
                    }
                })
            return formatted_tweets
        return None
    except Exception as e:
        print(f"❌ Exception for {keyword}: {e}")
        return None

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_filename = "twitter_report_latest.json"
    
    print(f"🚀 Starting Twitter Monitor. Results will be saved as JSON to {output_filename}\n")
    
    all_data = {}
    
    for keyword in KEYWORDS:
        data = fetch_tweets_for_keyword(keyword)
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
