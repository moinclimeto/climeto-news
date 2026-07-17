import asyncio
import os
import yaml
from twscrape import API, gather
from twscrape.logger import set_log_level

async def main():
    api = API()
    # Add dummy account with real cookies
    CONFIG_FILE = /root/.agent-reach/config.yaml
    with open(CONFIG_FILE, r) as f:
        config = yaml.safe_load(f)
        auth_token = config.get(twitter_auth_token, ")
