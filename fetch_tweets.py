import asyncio
import os
import yaml
import json
import time
from datetime import datetime

# Fix PATH for docker exec to find pipx installations
os.environ["PATH"] = f"/root/.local/bin:{os.environ.get('PATH', '')}"

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

from twscrape import API, gather

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

async def fetch_tweets_for_keyword(keyword, api: API):
    print(f"🔍 Searching tweets for: {keyword} in India...")
    try:
        search_query = f'"{keyword}" (India OR Indian OR Delhi OR Mumbai)'
        
        # Search using twscrape
        tweets = await gather(api.search(search_query, limit=20))
        
        formatted_tweets = []
        for tweet in tweets:
            formatted_tweets.append({
                "id": str(tweet.id),
                "text": tweet.rawContent,
                "createdAtISO": str(tweet.date),
                "author": {
                    "name": tweet.user.displayname if tweet.user else "",
                    "screenName": tweet.user.username if tweet.user else "",
                    "profileImageUrl": tweet.user.profileImageUrl if tweet.user else ""
                },
                "media": [{"type": "photo", "url": pic.url} for pic in tweet.media.photos] if getattr(tweet.media, 'photos', None) else [],
                "metrics": {
                    "likeCount": tweet.likeCount,
                    "retweetCount": tweet.retweetCount,
                    "replyCount": tweet.replyCount
                }
            })
        return formatted_tweets
    except Exception as e:
        print(f"❌ Exception for {keyword}: {e}")
        return None

async def main():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_filename = "twitter_report_latest.json"
    
    print(f"🚀 Starting Twitter Monitor. Results will be saved as JSON to {output_filename}\n")
    
    api = API()
    auth_token = os.environ.get("TWITTER_AUTH_TOKEN")
    ct0 = os.environ.get("TWITTER_CT0")
    
    if auth_token and ct0:
        # Ensure account is added
        accounts = await api.pool.accounts_info()
        if not any(a.get("username") == "app_account" for a in accounts):
            cookies_str = f"auth_token={auth_token}; ct0={ct0}"
            await api.pool.add_account("app_account", "password", "email@test.com", "email_password", cookies=cookies_str)
            await api.pool.login_all()
    else:
        print("⚠️ Warning: No TWITTER_AUTH_TOKEN or TWITTER_CT0 found. Search might fail or be limited.")

    all_data = {}
    
    for keyword in KEYWORDS:
        data = await fetch_tweets_for_keyword(keyword, api)
        if data:
            all_data[keyword] = data
            print(f"✅ Found {len(data) if isinstance(data, list) else 'some'} records for {keyword}")
        
        # Har search ke baad wait
        await asyncio.sleep(3) 
            
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
    asyncio.run(main())
