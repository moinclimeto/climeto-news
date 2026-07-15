import subprocess
import time
import os
import yaml
import json
from datetime import datetime

# Fix PATH for docker exec to find pipx installations
os.environ["PATH"] = f"/root/.local/bin:{os.environ.get('PATH', '')}"

# Load twitter cookies from Agent Reach config
CONFIG_FILE = "/root/.agent-reach/config.yaml"
try:
    with open(CONFIG_FILE, "r") as f:
        config = yaml.safe_load(f)
        os.environ["TWITTER_AUTH_TOKEN"] = config.get("twitter_auth_token", "")
        os.environ["TWITTER_CT0"] = config.get("twitter_ct0", "")
except Exception as e:
    print(f"⚠️ Could not load Agent Reach config: {e}")

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
        # Append 'India' to the search query to restrict results
        search_query = f'"{keyword}" (India OR Indian OR Delhi OR Mumbai)'
        result = subprocess.run(
            ["twitter", "search", search_query], 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            # The CLI returns YAML text, so we parse it to a dictionary
            try:
                parsed_yaml = yaml.safe_load(result.stdout)
                # The actual tweets are under the "data" key
                if isinstance(parsed_yaml, dict) and "data" in parsed_yaml:
                    return parsed_yaml["data"]
                return parsed_yaml
            except Exception as parse_error:
                print(f"⚠️ Error parsing YAML for {keyword}: {parse_error}")
                return None
        else:
            print(f"⚠️ Error fetching {keyword}: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
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
                if db.query(Post).filter(Post.post_id == post_id).first():
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
