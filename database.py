import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Use SQLite for local dev if DATABASE_URL is not set (Render will provide it)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./agent_reach.db")

# SQLAlchemy requires 'postgresql://' instead of 'postgres://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), index=True) # 'twitter' or 'linkedin'
    keyword = Column(String(255), index=True)
    post_id = Column(String(255), unique=True, index=True) # Unique ID from platform
    author_name = Column(String(255))
    author_handle = Column(String(255))
    author_avatar = Column(Text)
    text = Column(Text)
    media_url = Column(Text)
    metrics = Column(JSON) # likes, retweets, etc.
    created_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"
    
    key = Column(String(255), primary_key=True, index=True)
    value = Column(Text)

# Create tables
Base.metadata.create_all(bind=engine)
