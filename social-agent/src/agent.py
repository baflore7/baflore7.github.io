from __future__ import annotations

from typing import Any

from src.config import AccountConfig, load_config
from src.content.generator import ContentGenerator, GeneratedPost
from src.platforms.registry import get_adapter
from src.queue import ContentQueue, PostStatus


class FacelessSocialAgent:
    """Orchestrates content generation, approval workflow, and publishing."""

    def __init__(self, config: AccountConfig | None = None) -> None:
        self.config = config or load_config()
        self.generator = ContentGenerator(self.config)
        self.queue = ContentQueue()
        self.require_approval = bool(self.config.safety.get("require_human_approval", True))
        self.auto_post = bool(self.config.safety.get("auto_post", False))

    def create_post(
        self,
        platform: str | None = None,
        *,
        topic_hint: str | None = None,
        enqueue: bool = True,
    ) -> GeneratedPost:
        platform_cfg = next(
            (p for p in self.config.platform_configs() if p.name == platform),
            self.config.platform_configs()[0] if self.config.platform_configs() else None,
        )
        if platform_cfg is None:
            raise ValueError("No platforms enabled in config/account.yaml")

        post = self.generator.generate_post(
            platform_cfg.name,
            max_chars=platform_cfg.max_chars,
            hashtag_count=platform_cfg.hashtag_count,
            include_image_prompt=platform_cfg.include_image_prompt,
            topic_hint=topic_hint,
        )

        if enqueue:
            self.queue.add(post)
        return post

    def create_batch(self, count: int = 3) -> list[GeneratedPost]:
        posts = self.generator.generate_batch(count)
        for post in posts:
            self.queue.add(post)
        return posts

    def create_week_plan(self) -> list[GeneratedPost]:
        posts = self.generator.generate_week_plan()
        for post in posts:
            self.queue.add(post)
        return posts

    def approve(self, post_id: str) -> dict[str, Any]:
        item = self.queue.approve(post_id)
        if item is None:
            return {"ok": False, "message": f"Post {post_id} not found."}
        return {"ok": True, "post_id": post_id, "status": item.status.value}

    def reject(self, post_id: str, notes: str = "") -> dict[str, Any]:
        item = self.queue.reject(post_id, notes)
        if item is None:
            return {"ok": False, "message": f"Post {post_id} not found."}
        return {"ok": True, "post_id": post_id, "status": item.status.value}

    def publish(self, post_id: str, *, dry_run: bool = False, force: bool = False) -> dict[str, Any]:
        item = self.queue.get(post_id)
        if item is None:
            return {"ok": False, "message": f"Post {post_id} not found."}

        if self.require_approval and not force and item.status not in (
            PostStatus.APPROVED,
            PostStatus.SCHEDULED,
        ):
            return {
                "ok": False,
                "message": "Post needs approval first. Run: python main.py approve <id>",
            }

        adapter = get_adapter(item.post.platform, dry_run=dry_run or not self.auto_post)
        result = adapter.publish(item.post)

        if result.success:
            self.queue.update_status(
                post_id,
                PostStatus.PUBLISHED,
                publish_result={
                    "post_id": result.post_id,
                    "url": result.url,
                    "message": result.message,
                },
            )
        else:
            self.queue.update_status(
                post_id,
                PostStatus.FAILED,
                publish_result={"message": result.message},
            )

        return {
            "ok": result.success,
            "platform": result.platform,
            "post_id": result.post_id,
            "url": result.url,
            "message": result.message,
        }

    def run_scheduled(self, *, dry_run: bool = True) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for item in self.queue.ready_to_publish():
            if self.require_approval and item.status != PostStatus.SCHEDULED:
                continue
            results.append(self.publish(item.id, dry_run=dry_run))
        return results

    def status_summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.queue.list():
            key = item.status.value
            counts[key] = counts.get(key, 0) + 1
        return counts
