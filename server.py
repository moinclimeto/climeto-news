import os
import subprocess
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from database import SessionLocal, Post, Setting

app = FastAPI(title="Agent Reach Dashboard")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API Models
class SettingUpdate(BaseModel):
    key: str
    value: str

class SettingsRequest(BaseModel):
    settings: List[SettingUpdate]

# --- API Routes ---

@app.get("/api/posts")
def get_posts(platform: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Post).order_by(Post.created_at.desc())
    if platform:
        query = query.filter(Post.platform == platform)
    
    posts = query.limit(200).all()
    
    # Format to match the frontend expectations
    results = []
    for p in posts:
        if p.platform == 'twitter':
            results.append({
                "id": p.post_id,
                "platform": "twitter",
                "text": p.text,
                "author": {
                    "name": p.author_name,
                    "screenName": p.author_handle,
                    "profileImageUrl": p.author_avatar
                },
                "metrics": p.metrics or {},
                "media": [{"type": "photo", "url": p.media_url}] if p.media_url else [],
                "createdAtISO": p.created_at.isoformat() if p.created_at else None
            })
        elif p.platform == 'youtube':
            results.append({
                "id": p.post_id,
                "platform": "youtube",
                "text": p.text,
                "author": {
                    "name": p.author_name,
                    "channelUrl": p.author_handle,
                    "profileImageUrl": p.author_avatar
                },
                "metrics": p.metrics or {},
                "media": [{"type": "photo", "url": p.media_url}] if p.media_url else [],
                "createdAtISO": p.created_at.isoformat() if p.created_at else None
            })
        else: # linkedin
            results.append({
                "id": p.post_id,
                "platform": "linkedin",
                "companyName": p.author_name,
                "bio": p.author_handle,
                "text": p.text
            })
            
    return {"data": results}

@app.post("/api/settings")
def save_settings(request: SettingsRequest, db: Session = Depends(get_db)):
    for setting in request.settings:
        db_setting = db.query(Setting).filter(Setting.key == setting.key).first()
        if db_setting:
            db_setting.value = setting.value
        else:
            db_setting = Setting(key=setting.key, value=setting.value)
            db.add(db_setting)
            
        # If it's twitter cookies, also configure it in agent-reach CLI
        if setting.key == 'twitter_auth_token':
            auth_token = setting.value
            ct0 = next((s.value for s in request.settings if s.key == 'twitter_ct0'), "")
            if auth_token and ct0:
                # Update CLI config
                try:
                    subprocess.run(["agent-reach", "configure", "twitter-cookies", auth_token, ct0], check=False)
                except:
                    pass

    db.commit()
    return {"message": "Settings saved successfully"}

@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}

def run_fetch_scripts():
    print("Background Task: Running fetch_tweets.py")
    subprocess.run(["python", "fetch_tweets.py"])
    print("Background Task: Running fetch_linkedin_india.py")
    subprocess.run(["python", "fetch_linkedin_india.py"])
    print("Background Task: Running fetch_youtube.py")
    subprocess.run(["python", "fetch_youtube.py"])

@app.post("/api/fetch")
def trigger_fetch(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_fetch_scripts)
    return {"message": "Fetch started in background. The UI will update as data flows into the database."}

# --- Static File Serving ---

@app.get("/")
def serve_index():
    return FileResponse("index.html")

@app.get("/styles.css")
def serve_css():
    return FileResponse("styles.css")

@app.get("/app.js")
def serve_js():
    return FileResponse("app.js")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
