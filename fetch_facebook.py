import os
import time
import random
from datetime import datetime
from facebook_scraper import get_posts
from database import SessionLocal, Post, Setting

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

# Facebook-scraper requires actual Page usernames to work properly, not generic search strings
FACEBOOK_PAGES = [
    "moefcc",              # Ministry of Environment, Forest and Climate Change
    "GreenpeaceIndia",     # Greenpeace India
    "wwfindia",            # WWF India
    "UNEnvironment",       # UN Environment
    "sustainability.zero"  # General Sustainability Page
]

def main():
    print(f"🚀 Starting Facebook Monitor...\n")
    
    db = SessionLocal()
    
    # Query Facebook cookies from database settings
    c_user_setting = db.query(Setting).filter(Setting.key == 'fb_c_user').first()
    xs_setting = db.query(Setting).filter(Setting.key == 'fb_xs').first()
    
    c_user = c_user_setting.value if c_user_setting else None
    xs = xs_setting.value if xs_setting else None
    
    if not c_user or not xs:
        print("⚠️ Facebook cookies (fb_c_user, fb_xs) not configured in UI Settings.")
        print("Facebook actively blocks anonymous scraping. Skipping Facebook fetch.")
        db.close()
        return

    cookies_dict = {
        "c_user": c_user,
        "xs": xs
    }

    # Facebook bohot jaldi block karta hai. Hum randomly 2-3 FB Pages uthayenge.
    selected_pages = random.sample(FACEBOOK_PAGES, min(3, len(FACEBOOK_PAGES)))
    
    all_data = {}
    for page in selected_pages:
        print(f"🔍 Fetching posts from Facebook Page: @{page}...")
        try:
            # options={comments: False} makes it lighter and safer
            posts = get_posts(page, pages=3, cookies=cookies_dict, options={"comments": False})
            data = list(posts)
            if data:
                all_data[page] = data
                print(f"✅ Found {len(data)} posts from @{page}")
        except Exception as e:
            print(f"❌ Exception fetching from @{page}: {e}")
            
        # Human behavior mimic karne ke liye 15 se 25 seconds ka random wait
        sleep_time = random.randint(15, 25)
        print(f"⏳ Wait for {sleep_time}s to avoid ban...")
        time.sleep(sleep_time)
            
    try:
        seen_ids = set()
        for page, data in all_data.items():
            for post in data:
                post_id = f"fb_{post.get('post_id')}"
                if post_id in seen_ids:
                    continue
                existing_post = db.query(Post).filter(Post.post_id == post_id).first()
                if existing_post:
                    existing_post.fetched_at = datetime.utcnow()
                    continue
                
                dt = post.get('time', datetime.utcnow())
                text = post.get('text', '')[:1000]
                if post.get('post_url'):
                    text += f"\n\n{post.get('post_url')}"
                
                # Assign a random keyword from the main list so it fits the schema
                assigned_keyword = random.choice(KEYWORDS)
                
                new_post = Post(
                    platform="facebook",
                    keyword=assigned_keyword,
                    post_id=post_id,
                    author_name=post.get('username', 'Facebook User'),
                    author_handle=post.get('username', ''),
                    author_avatar=post.get('user_image', ''),
                    text=text,
                    media_url=post.get('image', ''),
                    metrics={"likes": post.get('likes', 0), "comments": post.get('comments', 0)},
                    created_at=dt 
                )
                db.add(new_post)
                seen_ids.add(post_id)
        db.commit()
        print(f"\n✅ Done! Facebook posts successfully saved to database")
    except Exception as e:
        print(f"❌ Error saving to DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
