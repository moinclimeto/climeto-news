import time
import random
import json
import requests
from datetime import datetime
from linkedin_api import Linkedin

# ==========================================
# 🛑 SETUP INSTRUCTIONS:
# 1. Install required library: 
#    pip install linkedin-api
# 1. Open LinkedIn in your browser and log in
# 2. Open Developer Tools (F12) -> Application -> Cookies -> https://www.linkedin.com
# 3. Copy the values of 'li_at' and 'JSESSIONID' and paste them below:
# ==========================================
from database import SessionLocal, Setting, Post
import hashlib

# Load cookies from DB
db = SessionLocal()
try:
    li_at_setting = db.query(Setting).filter(Setting.key == 'linkedin_li_at').first()
    jsession_setting = db.query(Setting).filter(Setting.key == 'linkedin_jsessionid').first()
    
    LINKEDIN_LI_AT = li_at_setting.value if li_at_setting else "paste_your_li_at_cookie_here"
    LINKEDIN_JSESSIONID = jsession_setting.value if jsession_setting else "paste_your_JSESSIONID_here"
finally:
    db.close()

# Keywords aapke domain se related hain, sath me 'India' add kiya hai filter ke liye
KEYWORDS = [
    "Extended Producer Responsibility India",
    "EPR India",
    "Plastic Waste India",
    "Battery Waste India",
    "E-Waste India"
]

def extract_urn_id(urn):
    # urn format: urn:li:fsd_profile:ACoAAGdAIk...
    if not urn: return None
    parts = urn.split(':')
    if len(parts) > 3:
        return parts[-1]
    return None

def fetch_linkedin_data(api, keyword):
    print(f"🔍 Searching LinkedIn for Top Companies for: {keyword}...")
    final_posts = []
    try:
        # Step 1: Search for entities (Companies) related to the keyword
        results = api.search({'keywords': keyword}, limit=5)
        
        for res in results:
            urn = res.get('entityUrn', '')
            title = res.get('title', {}).get('text', 'Unknown')
            desc = res.get('primarySubtitle', {}).get('text', '')
            
            # Step 2: Fetch their latest posts/updates
            # Note: We skip Profiles because linkedin-api's get_profile_posts is currently broken (KeyError: 'message')
            if 'fsd_company' in urn:
                print(f"  🏢 Fetching updates for Company: {title}")
                company_urn = res.get('navigationUrl', '').split('company/')
                if len(company_urn) > 1:
                    company_id = company_urn[1].split('?')[0].strip('/')
                    try:
                        updates = api.get_company_updates(company_id, max_results=3)
                        # Extract clean text from the complex JSON
                        clean_updates = []
                        if updates:
                            for update in updates:
                                try:
                                    text = update.get('value', {}).get('com.linkedin.voyager.feed.render.UpdateV2', {}).get('commentary', {}).get('text', {}).get('text', '')
                                    if text: clean_updates.append(text)
                                except:
                                    pass
                        
                        if clean_updates:
                            final_posts.append({
                                "type": "Company",
                                "name": title,
                                "bio": desc,
                                "latest_posts": clean_updates
                            })
                    except Exception as e:
                        print(f"    ⚠️ Could not fetch updates for {title}: {e}")

        return final_posts
    except Exception as e:
        print(f"⚠️ Error fetching {keyword}: {e}")
        return None

def main():
    if LINKEDIN_LI_AT == "paste_your_li_at_cookie_here":
        print("❌ Please update LINKEDIN_LI_AT and LINKEDIN_JSESSIONID in the script first!")
        return

    print("⏳ Logging into LinkedIn using cookies...")
    try:
        # Convert dictionary to a requests CookieJar to avoid AttributeError
        cookie_jar = requests.cookies.cookiejar_from_dict({
            'li_at': LINKEDIN_LI_AT, 
            'JSESSIONID': LINKEDIN_JSESSIONID.strip('"') # Strip quotes if any
        })

        # Authenticate using cookies
        api = Linkedin('', '', cookies=cookie_jar)
        print("✅ Successfully logged in!")
    except Exception as e:
        print(f"❌ Failed to login: {e}")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_filename = "linkedin_report_latest.json"
    
    print(f"🚀 Starting LinkedIn Monitor. Results will be saved to {output_filename}\n")
    
    all_data = {}
    
    for keyword in KEYWORDS:
        data = fetch_linkedin_data(api, keyword)
        if data:
            all_data[keyword] = data
            print(f"✅ Found {len(data)} records for '{keyword}'")
        else:
            print(f"❌ No records found for '{keyword}'")
        
        # Adding a random sleep delay is EXTREMELY IMPORTANT for LinkedIn to prevent account ban
        delay = random.randint(25, 45)
        print(f"⏳ Sleeping for {delay} seconds to avoid LinkedIn blocking...")
        time.sleep(delay)
            
    db = SessionLocal()
    try:
        seen_ids = set()
        for keyword, data in all_data.items():
            if not isinstance(data, list):
                continue
            for item in data:
                company = item.get("name")
                bio = item.get("bio")
                for text in item.get("latest_posts", []):
                    post_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
                    
                    if post_hash in seen_ids:
                        continue
                    
                    if db.query(Post).filter(Post.post_id == post_hash).first():
                        continue
                        
                    new_post = Post(
                        platform="linkedin",
                        keyword=keyword,
                        post_id=post_hash,
                        author_name=company,
                        author_handle=bio,
                        text=text,
                        created_at=datetime.utcnow()
                    )
                    db.add(new_post)
                    seen_ids.add(post_hash)
        db.commit()
        print(f"\n✅ Done! LinkedIn posts successfully saved to database")
    except Exception as e:
        print(f"❌ Error saving to DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
