import time
import feedparser
from datetime import datetime
from database import SessionLocal, Post
from email.utils import parsedate_to_datetime

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

def fetch_news_for_keyword(keyword):
    print(f"📰 Searching Google News for: {keyword} India...")
    try:
        url = f"https://news.google.com/rss/search?q={keyword.replace(' ', '+')}+India"
        feed = feedparser.parse(url)
        return feed.entries[:10]
    except Exception as e:
        print(f"❌ Exception fetching {keyword}: {e}")
        return []

def main():
    print(f"🚀 Starting News Monitor...\n")
    
    all_data = {}
    for keyword in KEYWORDS:
        data = fetch_news_for_keyword(keyword)
        if data:
            all_data[keyword] = data
            print(f"✅ Found {len(data)} articles for {keyword}")
        
        time.sleep(1)
            
    db = SessionLocal()
    try:
        seen_ids = set()
        for keyword, data in all_data.items():
            for entry in data:
                post_id = f"news_{entry.get('id', entry.get('link', ''))}"
                if post_id in seen_ids:
                    continue
                existing_post = db.query(Post).filter(Post.post_id == post_id).first()
                if existing_post:
                    from datetime import datetime
                    existing_post.fetched_at = datetime.utcnow()
                    continue
                
                try:
                    dt = parsedate_to_datetime(entry.get('published', ''))
                except:
                    dt = datetime.utcnow()
                
                text = f"{entry.get('title', '')}\n\n{entry.get('link', '')}"
                
                new_post = Post(
                    platform="news",
                    keyword=keyword,
                    post_id=post_id,
                    author_name=entry.get('source', {}).get('title', 'Google News'),
                    author_handle=entry.get('link', ''),
                    author_avatar="",
                    text=text,
                    media_url="",
                    metrics={},
                    created_at=dt 
                )
                db.add(new_post)
                seen_ids.add(post_id)
        db.commit()
        print(f"\n✅ Done! News articles successfully saved to database")
    except Exception as e:
        print(f"❌ Error saving to DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
