import os
import re

files = [
    "fetch_tweets.py",
    "fetch_linkedin_india.py",
    "fetch_youtube.py",
    "fetch_news.py",
    "fetch_reddit.py",
    "fetch_facebook.py"
]

for file in files:
    if not os.path.exists(file):
        continue
    with open(file, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"if db\.query\(Post\)\.filter\(Post\.post_id == post_id\)\.first\(\):\s+continue"
    replacement = """existing_post = db.query(Post).filter(Post.post_id == post_id).first()
                if existing_post:
                    from datetime import datetime
                    existing_post.fetched_at = datetime.utcnow()
                    continue"""
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        with open(file, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {file}")
