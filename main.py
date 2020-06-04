import os
import re
import tweepy
import requests
import asyncio
import time
import urllib.request
from dotenv import load_dotenv
from dotmap import DotMap
load_dotenv()

consumer_key = os.getenv("TWITTER_CONSUMER_KEY")
consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET")
access_token = os.getenv("TWITTER_ACCESS_TOKEN")
access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
danbooru_key = os.getenv("DANBOORU_API_KEY")

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
twitter = tweepy.API(auth)

if not os.path.exists("assets"):
    os.makedirs("assets")

def proper_case(str):
    """Utility to convert to Proper Case."""
    str = re.sub(r"_", "", str)
    return str.title()

def rate_limit(cursor):
    """Handle tweepy cursor rate limits."""
    while True:
        try:
            yield cursor.next()
        except tweepy.RateLimitError:
            time.sleep(15 * 60)
        except StopIteration:
            break

async def sync_followers():
    """Follow people who follow the bot and unfollow those who unfollow it."""
    while True:
        followers = rate_limit(tweepy.Cursor(twitter.followers).items())
        friends = rate_limit(tweepy.Cursor(twitter.friends).items())
        for friend in friends:
            if friend not in followers:
                friend.unfollow()
        for follower in followers:
            if not follower.following:
                follower.follow()
        await asyncio.sleep(60)

def danbooru(tags, tweet=None):
    url = f"https://danbooru.donmai.us/posts.json?login=hibikidestroyer&api_key={danbooru_key}&limit=1&&random=true&tags={tags}"
    try:
        post = requests.get(url).json()[0]
    except:
        if tweet:
            twitter.update_status(f"@{tweet.user.screen_name} Sorry, no search results were found.", in_reply_to_status_id=tweet.id)
        return
    post = DotMap(post)
    source = f"https://www.pixiv.net/en/artworks/{post.pixiv_id}" if post.pixiv_id else post.source
    artist = proper_case(post.tag_string_artist)[:30] if post.tag_string_artist else "Unknown"
    character = proper_case(post.tag_string_character)[:30] if post.tag_string_character else "Original"
    dest = os.path.abspath(f"assets/{post.id}.{post.file_ext}")
    urllib.request.urlretrieve(post.file_url, dest)
    media = twitter.media_upload(dest)
    content = f"Character: {character} Artist: {artist}\n{source}"
    r18 = False if post.rating == "s" else True
    if tweet:
        twitter.update_status(f"@{tweet.user.screen_name} {content}", media_ids=[media.media_id], possibly_sensitive=r18, in_reply_to_status_id=tweet.id)
    else:
        twitter.update_status(content, media_ids=[media.media_id], possibly_sensitive=r18)

async def fetch_anime_picture():
    """Fetch an anime picture from danbooru and tweet it."""
    while True:
        danbooru("pantyhose")
        await asyncio.sleep(60 * 60)

def check_mentions(since_id):
    new_id = since_id
    for tweet in rate_limit(tweepy.Cursor(twitter.mentions_timeline, since_id=since_id).items()):
        new_id = max(tweet.id, new_id)
        if tweet.favorited:
            continue
        if tweet.in_reply_to_status_id is not None:
            continue
        args = re.split(r" +", re.sub(r"@.*? ", "", tweet.text.lower()))
        command = args[0]
        if command == "help":
            content = f"@{tweet.user.screen_name} Hibiki Help: \ndanbooru tag1, tag2?"
            try:
                twitter.create_favorite(tweet.id)
                twitter.update_status(status=content, in_reply_to_status_id=tweet.id)
            except:
                pass

        if command == "danbooru":
            tags = ",".join(map(lambda tag: re.sub(r" +", "_", tag), re.split(r", ", " ".join(args[1:]))))
            print(tags)
            try:
                twitter.create_favorite(tweet.id)
                danbooru(tags, tweet)
            except:
                pass
    return new_id

async def command_loop():
    since_id = 1
    while True:
        since_id = check_mentions(since_id)
        await asyncio.sleep(60)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(
        sync_followers(),
        fetch_anime_picture(),
        command_loop()
    ))
    loop.close()