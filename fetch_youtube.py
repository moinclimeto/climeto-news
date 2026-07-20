import time
import os
import json
import re
from datetime import datetime, timedelta
from youtubesearchpython import VideosSearch
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

def parse_relative_time(time_str):
    if not time_str:
        return datetime.utcnow()
    
    match = re.search(r'(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago', time_str.lower())
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        
        if unit == 'second':
            delta = timedelta(seconds=amount)
        elif unit == 'minute':
            delta = timedelta(minutes=amount)
        elif unit == 'hour':
            delta = timedelta(hours=amount)
        elif unit == 'day':
            delta = timedelta(days=amount)
        elif unit == 'week':
            delta = timedelta(weeks=amount)
        elif unit == 'month':
            delta = timedelta(days=amount * 30)
        elif unit == 'year':
            delta = timedelta(days=amount * 365)
        else:
            delta = timedelta(0)
            
        return datetime.utcnow() - delta
    return datetime.utcnow()

def fetch_youtube_for_keyword(keyword):
    print(f"🔍 Searching YouTube videos for: {keyword} in India...")
    try:
        search_query = f'{keyword} India'
        videosSearch = VideosSearch(search_query, limit=10)
        result = videosSearch.result()
        return result.get('result', [])
    except Exception as e:
        print(f"❌ Exception fetching {keyword}: {e}")
        return []

def main():
    print(f"🚀 Starting YouTube Monitor...\n")
    
    all_data = {}
    for keyword in KEYWORDS:
        data = fetch_youtube_for_keyword(keyword)
        if data:
            all_data[keyword] = data
            print(f"✅ Found {len(data)} videos for {keyword}")
        
        time.sleep(2) 
            
    db = SessionLocal()
    try:
        seen_ids = set()
        for keyword, data in all_data.items():
            if not isinstance(data, list):
                continue
            for video in data:
                post_id = f"yt_{video.get('id')}"
                if post_id in seen_ids:
                    continue
                existing_post = db.query(Post).filter(Post.post_id == post_id).first()
                if existing_post:
                    existing_post.fetched_at = datetime.utcnow()
                    continue
                
                thumbnails = video.get('thumbnails', [])
                media_url = thumbnails[0]['url'] if thumbnails else ""
                
                channel = video.get('channel', {})
                view_count = video.get('viewCount', {}).get('short', '0 views')
                
                text = f"{video.get('title', '')} \n{video.get('link', '')}"
                
                published_time = video.get('publishedTime', '')
                created_at = parse_relative_time(published_time)
                
                new_post = Post(
                    platform="youtube",
                    keyword=keyword,
                    post_id=post_id,
                    author_name=channel.get('name', 'Unknown'),
                    author_handle=channel.get('link', ''),
                    author_avatar=channel.get('thumbnails', [{'url': ''}])[0].get('url', ''),
                    text=text,
                    media_url=media_url,
                    metrics={"views": view_count},
                    created_at=created_at
                )
                db.add(new_post)
                seen_ids.add(post_id)
        db.commit()
        print(f"\n✅ Done! YouTube videos successfully saved to database")
    except Exception as e:
        print(f"❌ Error saving to DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
