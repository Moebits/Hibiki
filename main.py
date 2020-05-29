import os
import re
import tweepy
import requests
import asyncio
import urllib.request
from dotenv import load_dotenv
from dotmap import DotMap
from concurrent.futures import ProcessPoolExecutor
load_dotenv()

consumer_key = os.getenv("TWITTER_CONSUMER_KEY")
consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET")
access_token = os.getenv("TWITTER_ACCESS_TOKEN")
access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
danbooru_key = os.getenv("DANBOORU_API_KEY")

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
twitter = tweepy.API(auth)

def proper_case(str):
    """Utility to convert to Proper Case."""
    str = re.sub(r"_", "", str)
    return str.title()

async def sync_followers():
    """Follow people who follow the bot and unfollow those who unfollow it."""
    while True:
        followers = tweepy.Cursor(twitter.followers).items()
        friends = tweepy.Cursor(twitter.friends).items()
        for friend in friends:
            if friend not in followers:
                friend.unfollow()
        for follower in followers:
            if not follower.following:
                follower.follow()
        await asyncio.sleep(60)

async def fetch_anime_picture():
    """Fetch an anime picture from danbooru and tweet it."""
    while True:
        url = f"https://danbooru.donmai.us/posts.json?login=hibikidestroyer&api_key={danbooru_key}&limit=1&&random=true&tags=pantyhose"
        post = requests.get(url).json()[0]
        post = DotMap(post)
        source = f"https://www.pixiv.net/en/artworks/{post.pixiv_id}" if post.pixiv_id else post.source
        artist = proper_case(post.tag_string_artist)[:30] if post.tag_string_artist else "Unknown"
        character = proper_case(post.tag_string_character)[:30] if post.tag_string_character else "Original"
        dest = f"assets/{post.id}.{post.file_ext}"
        urllib.request.urlretrieve(post.file_url, dest)
        media = twitter.media_upload(dest)
        print(media)
        content = f"Character: {character} Artist: {artist}\n{source}"
        r18 = False if post.rating == "s" else True
        twitter.update_status(content, media_ids=[media.media_id], possibly_sensitive=r18)
        await asyncio.sleep(60 * 60)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(sync_followers())
    loop.create_task(fetch_anime_picture())
    loop.run_forever()