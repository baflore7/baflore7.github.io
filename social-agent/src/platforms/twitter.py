from __future__ import annotations

import os

import tweepy

from src.content.generator import GeneratedPost
from src.platforms.base import PlatformAdapter, PublishResult


class TwitterAdapter(PlatformAdapter):
    name = "twitter"

    def __init__(self) -> None:
        self._client: tweepy.Client | None = None

    def is_configured(self) -> bool:
        keys = [
            os.environ.get("TWITTER_API_KEY"),
            os.environ.get("TWITTER_API_SECRET"),
            os.environ.get("TWITTER_ACCESS_TOKEN"),
            os.environ.get("TWITTER_ACCESS_SECRET"),
        ]
        return all(keys)

    def _get_client(self) -> tweepy.Client:
        if self._client is None:
            self._client = tweepy.Client(
                consumer_key=os.environ["TWITTER_API_KEY"],
                consumer_secret=os.environ["TWITTER_API_SECRET"],
                access_token=os.environ["TWITTER_ACCESS_TOKEN"],
                access_token_secret=os.environ["TWITTER_ACCESS_SECRET"],
            )
        return self._client

    def publish(self, post: GeneratedPost) -> PublishResult:
        if not self.is_configured():
            return PublishResult(
                success=False,
                platform=self.name,
                message="Twitter credentials missing. Copy .env.example to .env and fill in API keys.",
            )

        try:
            response = self._get_client().create_tweet(text=post.full_text)
            tweet_id = str(response.data["id"])
            return PublishResult(
                success=True,
                platform=self.name,
                post_id=tweet_id,
                url=f"https://twitter.com/i/web/status/{tweet_id}",
                message="Tweet published.",
            )
        except Exception as exc:  # noqa: BLE001 — surface API errors to user
            return PublishResult(
                success=False,
                platform=self.name,
                message=str(exc),
            )
