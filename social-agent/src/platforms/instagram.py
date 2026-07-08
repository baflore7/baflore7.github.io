from __future__ import annotations

import os

import requests

from src.content.generator import GeneratedPost
from src.platforms.base import PlatformAdapter, PublishResult


class InstagramAdapter(PlatformAdapter):
    """Publishes caption text via Instagram Graph API (image URL required for real posts)."""

    name = "instagram"
    GRAPH_URL = "https://graph.facebook.com/v19.0"

    def is_configured(self) -> bool:
        return bool(os.environ.get("INSTAGRAM_ACCESS_TOKEN") and os.environ.get("INSTAGRAM_ACCOUNT_ID"))

    def publish(self, post: GeneratedPost) -> PublishResult:
        if not self.is_configured():
            return PublishResult(
                success=False,
                platform=self.name,
                message="Instagram credentials missing. Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID.",
            )

        image_url = post.metadata.get("image_url")
        if not image_url:
            return PublishResult(
                success=False,
                platform=self.name,
                message=(
                    "Instagram requires an image. Set post.metadata['image_url'] after generating "
                    "or uploading a faceless visual."
                ),
            )

        token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
        account_id = os.environ["INSTAGRAM_ACCOUNT_ID"]

        try:
            container = requests.post(
                f"{self.GRAPH_URL}/{account_id}/media",
                data={
                    "image_url": image_url,
                    "caption": post.full_text,
                    "access_token": token,
                },
                timeout=30,
            )
            container.raise_for_status()
            creation_id = container.json()["id"]

            publish = requests.post(
                f"{self.GRAPH_URL}/{account_id}/media_publish",
                data={"creation_id": creation_id, "access_token": token},
                timeout=30,
            )
            publish.raise_for_status()
            media_id = publish.json()["id"]
            return PublishResult(
                success=True,
                platform=self.name,
                post_id=media_id,
                message="Instagram post published.",
            )
        except Exception as exc:  # noqa: BLE001
            return PublishResult(
                success=False,
                platform=self.name,
                message=str(exc),
            )
