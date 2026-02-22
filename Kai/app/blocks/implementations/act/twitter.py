"""Twitter/X integration blocks — post tweets and read timelines."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

import tweepy

from app.blocks.executor import register_implementation
from app.config import settings

logger = logging.getLogger("agentflow.blocks.twitter")

TWEET_MAX_LENGTH = 280
TRUNCATION_SUFFIX = "..."

# Cache the authenticated username to avoid an API call on every tweet
_cached_username: str | None = None


def _get_client() -> tweepy.Client:
    """Create an authenticated Twitter API v2 client."""
    required = {
        "TWITTER_API_KEY": settings.twitter_api_key,
        "TWITTER_API_SECRET": settings.twitter_api_secret,
        "TWITTER_ACCESS_TOKEN": settings.twitter_access_token,
        "TWITTER_ACCESS_TOKEN_SECRET": settings.twitter_access_token_secret,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(
            f"Twitter credentials not configured — missing: {', '.join(missing)}. "
            "Add them to .env"
        )
    return tweepy.Client(
        consumer_key=settings.twitter_api_key,
        consumer_secret=settings.twitter_api_secret,
        access_token=settings.twitter_access_token,
        access_token_secret=settings.twitter_access_token_secret,
    )


def _get_username(client: tweepy.Client) -> str:
    """Get the authenticated user's username, cached after first call."""
    global _cached_username
    if _cached_username is None:
        me = client.get_me()
        _cached_username = me.data.username if me.data else "user"
    return _cached_username


@register_implementation("twitter_post")
async def twitter_post(inputs: dict[str, Any]) -> dict[str, Any]:
    """Post a tweet to X/Twitter."""
    text = inputs["text"]
    truncated = False
    if len(text) > TWEET_MAX_LENGTH:
        text = text[: TWEET_MAX_LENGTH - len(TRUNCATION_SUFFIX)] + TRUNCATION_SUFFIX
        truncated = True

    reply_to = inputs.get("reply_to_tweet_id")

    try:
        client = _get_client()
        kwargs: dict[str, Any] = {"text": text}
        if reply_to:
            if not re.fullmatch(r"\d{1,20}", str(reply_to)):
                raise ValueError("Invalid reply_to_tweet_id: must be a numeric tweet ID")
            kwargs["in_reply_to_tweet_id"] = str(reply_to)

        response = client.create_tweet(**kwargs)
        tweet_data = response.data
        tweet_id = str(tweet_data["id"])
        username = _get_username(client)
    except ValueError:
        raise
    except Exception as e:
        logger.error("Twitter post error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Twitter post failed: {type(e).__name__}") from None

    return {
        "tweet_id": tweet_id,
        "tweet_url": f"https://x.com/{username}/status/{tweet_id}",
        "text": text,
        "truncated": truncated,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@register_implementation("twitter_read_timeline")
async def twitter_read_timeline(inputs: dict[str, Any]) -> dict[str, Any]:
    """Read recent tweets from a user's timeline."""
    raw_username = inputs["username"].lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{1,15}", raw_username):
        raise ValueError("Invalid Twitter username")
    count = min(int(inputs.get("count", 10)), 100)

    try:
        client = _get_client()

        user_response = client.get_user(username=raw_username)
        if not user_response.data:
            raise ValueError("Twitter user not found")

        user_id = user_response.data.id

        tweets_response = client.get_users_tweets(
            id=user_id,
            max_results=max(count, 5),  # API minimum is 5
            tweet_fields=["created_at", "public_metrics"],
        )
    except ValueError:
        raise
    except Exception as e:
        logger.error("Twitter read error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Twitter read failed: {type(e).__name__}") from None

    tweets = []
    if tweets_response.data:
        # Trim to requested count (API enforces a minimum of 5)
        for tweet in tweets_response.data[:count]:
            metrics = tweet.public_metrics or {}
            tweets.append({
                "id": str(tweet.id),
                "text": tweet.text,
                "created_at": str(tweet.created_at) if tweet.created_at else "",
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
            })

    return {
        "tweets": tweets,
        "username": raw_username,
        "tweet_count": len(tweets),
    }
