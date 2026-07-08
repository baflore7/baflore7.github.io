from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from src.config import AccountConfig, weighted_pillars
from src.content.prompts import BATCH_SCHEMA, SYSTEM_PROMPT, build_user_prompt


@dataclass
class GeneratedPost:
    pillar: str
    topic: str
    body: str
    hashtags: list[str]
    platform: str
    image_prompt: str | None = None
    hook: str | None = None
    cta: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        tags = " ".join(f"#{t.lstrip('#')}" for t in self.hashtags)
        return f"{self.body}\n\n{tags}".strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "pillar": self.pillar,
            "topic": self.topic,
            "body": self.body,
            "hashtags": self.hashtags,
            "platform": self.platform,
            "image_prompt": self.image_prompt,
            "hook": self.hook,
            "cta": self.cta,
            "full_text": self.full_text,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GeneratedPost:
        return cls(
            pillar=data["pillar"],
            topic=data["topic"],
            body=data["body"],
            hashtags=data.get("hashtags", []),
            platform=data["platform"],
            image_prompt=data.get("image_prompt"),
            hook=data.get("hook"),
            cta=data.get("cta"),
            metadata=data.get("metadata", {}),
        )


class ContentGenerator:
    def __init__(self, config: AccountConfig, client: OpenAI | None = None) -> None:
        self.config = config
        self._client = client
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
                )
            self._client = OpenAI(api_key=api_key)
        return self._client

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0]
        return json.loads(cleaned)

    def _pick_pillar(self) -> dict[str, Any]:
        return random.choice(weighted_pillars(self.config.content_pillars))

    def generate_post(
        self,
        platform: str,
        *,
        max_chars: int,
        hashtag_count: int,
        include_image_prompt: bool = False,
        topic_hint: str | None = None,
        pillar: dict[str, Any] | None = None,
    ) -> GeneratedPost:
        pillar = pillar or self._pick_pillar()
        account = self.config.account
        voice = self.config.voice

        prompt = build_user_prompt(
            account_name=account["name"],
            tagline=account["tagline"],
            voice=voice,
            pillar=pillar,
            platform=platform,
            max_chars=max_chars,
            hashtag_count=hashtag_count,
            include_image_prompt=include_image_prompt,
            topic_hint=topic_hint,
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.9,
            response_format={"type": "json_object"},
        )

        payload = self._parse_json(response.choices[0].message.content or "{}")
        body = payload.get("body", "").strip()
        if len(body) > max_chars:
            body = body[: max_chars - 1].rstrip() + "…"

        return GeneratedPost(
            pillar=payload.get("pillar", pillar["name"]),
            topic=payload.get("topic", ""),
            body=body,
            hashtags=[str(t).lstrip("#") for t in payload.get("hashtags", [])][:hashtag_count],
            platform=platform,
            image_prompt=payload.get("image_prompt"),
            hook=payload.get("hook"),
            cta=payload.get("cta"),
            metadata={"model": self.model},
        )

    def generate_batch(self, count: int = 3) -> list[GeneratedPost]:
        posts: list[GeneratedPost] = []
        for platform_cfg in self.config.platform_configs():
            for _ in range(count):
                posts.append(
                    self.generate_post(
                        platform_cfg.name,
                        max_chars=platform_cfg.max_chars,
                        hashtag_count=platform_cfg.hashtag_count,
                        include_image_prompt=platform_cfg.include_image_prompt,
                    )
                )
        return posts

    def generate_week_plan(self) -> list[GeneratedPost]:
        posts_per_day = int(self.config.schedule.get("posts_per_day", 2))
        days = 7
        plan: list[GeneratedPost] = []
        platforms = self.config.platform_configs()
        if not platforms:
            return plan

        for day in range(days):
            for slot in range(posts_per_day):
                platform_cfg = platforms[(day + slot) % len(platforms)]
                plan.append(
                    self.generate_post(
                        platform_cfg.name,
                        max_chars=platform_cfg.max_chars,
                        hashtag_count=platform_cfg.hashtag_count,
                        include_image_prompt=platform_cfg.include_image_prompt,
                    )
                )
        return plan

    def repurpose(self, post: GeneratedPost, target_platform: str, max_chars: int, hashtag_count: int) -> GeneratedPost:
        prompt = f"""Repurpose this faceless social post for {target_platform}.
Keep the same pillar and topic. Max {max_chars} chars. {hashtag_count} hashtags.

Original ({post.platform}):
{post.full_text}

Return JSON:
{BATCH_SCHEMA.replace('"posts": [', '').replace(']', '')}
"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        payload = self._parse_json(response.choices[0].message.content or "{}")
        body = payload.get("body", post.body).strip()
        if len(body) > max_chars:
            body = body[: max_chars - 1].rstrip() + "…"

        return GeneratedPost(
            pillar=payload.get("pillar", post.pillar),
            topic=payload.get("topic", post.topic),
            body=body,
            hashtags=[str(t).lstrip("#") for t in payload.get("hashtags", post.hashtags)][:hashtag_count],
            platform=target_platform,
            image_prompt=payload.get("image_prompt", post.image_prompt),
            hook=payload.get("hook", post.hook),
            cta=payload.get("cta", post.cta),
            metadata={"repurposed_from": post.platform, "model": self.model},
        )
