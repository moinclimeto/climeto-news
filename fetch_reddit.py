import os
import time
import praw
from datetime import datetime
from database import SessionLocal, Post

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

def main():
    print(f"🚀 Starting Reddit Monitor...\n")
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("⚠️ REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET not found in environment variables.")
        print("Reddit requires authentication. Skipping Reddit fetch for now.")
        return

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent="agent-reach:v1.0 (by /u/agent-reach)"
    )
    
    all_data = {}
    for keyword in KEYWORDS:
        print(f"🔍 Searching Reddit for: {keyword} India...")
        try:
            search_query = f'{keyword} India'
            posts = reddit.subreddit("all").search(search_query, limit=10)
            data = list(posts)
            if data:
                all_data[keyword] = data
                print(f"✅ Found {len(data)} posts for {keyword}")
        except Exception as e:
            print(f"❌ Exception fetching {keyword}: {e}")
            
        time.sleep(2)
            
    db = SessionLocal()
    try:
        seen_ids = set()
        for keyword, data in all_data.items():
            for post in data:
                post_id = f"rdt_{post.id}"
                if post_id in seen_ids:
                    continue
                existing_post = db.query(Post).filter(Post.post_id == post_id).first()
                if existing_post:
                    from datetime import datetime
                    existing_post.fetched_at = datetime.utcnow()
                    continue
                
                dt = datetime.utcfromtimestamp(post.created_utc)
                text = f"**{post.title}**\n{post.selftext[:500]}{'...' if len(post.selftext) > 500 else ''}\n\nhttps://reddit.com{post.permalink}"
                
                author_name = post.author.name if post.author else "deleted"
                
                new_post = Post(
                    platform="reddit",
                    keyword=keyword,
                    post_id=post_id,
                    author_name=author_name,
                    author_handle=f"/u/{author_name}",
                    author_avatar="",
                    text=text,
                    media_url=post.url if post.url and (post.url.endswith('.jpg') or post.url.endswith('.png')) else "",
                    metrics={"score": post.score, "comments": post.num_comments},
                    created_at=dt 
                )
                db.add(new_post)
                seen_ids.add(post_id)
        db.commit()
        print(f"\n✅ Done! Reddit posts successfully saved to database")
    except Exception as e:
        print(f"❌ Error saving to DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
