import asyncio
import os
import yaml
from twscrape import API, gather

async def main():
    print("Testing twscrape...")
    api = API()
    
    CONFIG_FILE = "/root/.agent-reach/config.yaml"
    auth_token = ""
    ct0 = ""
    try:
        with open(CONFIG_FILE, "r") as f:
            config = yaml.safe_load(f)
            auth_token = config.get("twitter_auth_token", "")
            ct0 = config.get("twitter_ct0", "")
    except Exception as e:
        print(f"Error loading config: {e}")
        return
        
    print(f"Loaded cookies: auth_token={auth_token[:5]}..., ct0={ct0[:5]}...")
    cookies = f"auth_token={auth_token}; ct0={ct0}"
    
    # Add dummy account
    await api.pool.add_account("dummy_user", "dummy_pass", "dummy@email.com", "dummy_pass", cookies=cookies)
    await api.pool.login_all()
    
    print("Searching...")
    tweets = await gather(api.search("EPR India", limit=2))
    print(f"Found {len(tweets)} tweets")
    for t in tweets:
        print(t.id, t.rawContent[:50])

if __name__ == "__main__":
    asyncio.run(main())
