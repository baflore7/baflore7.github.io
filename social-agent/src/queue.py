from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from src.content.generator import GeneratedPost


class PostStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class QueuedPost:
    id: str
    post: GeneratedPost
    status: PostStatus
    created_at: str
    scheduled_for: str | None = None
    published_at: str | None = None
    publish_result: dict[str, Any] | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "post": self.post.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at,
            "scheduled_for": self.scheduled_for,
            "published_at": self.published_at,
            "publish_result": self.publish_result,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueuedPost:
        return cls(
            id=data["id"],
            post=GeneratedPost.from_dict(data["post"]),
            status=PostStatus(data["status"]),
            created_at=data["created_at"],
            scheduled_for=data.get("scheduled_for"),
            published_at=data.get("published_at"),
            publish_result=data.get("publish_result"),
            notes=data.get("notes", ""),
        )


class ContentQueue:
    def __init__(self, path: str | Path | None = None) -> None:
        root = Path(__file__).resolve().parent.parent
        self.path = Path(path or root / "data" / "queue.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    def _read(self) -> list[QueuedPost]:
        with self.path.open(encoding="utf-8") as f:
            raw = json.load(f)
        return [QueuedPost.from_dict(item) for item in raw]

    def _write(self, items: list[QueuedPost]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump([item.to_dict() for item in items], f, indent=2)

    def add(self, post: GeneratedPost, *, scheduled_for: str | None = None) -> QueuedPost:
        items = self._read()
        queued = QueuedPost(
            id=str(uuid.uuid4())[:8],
            post=post,
            status=PostStatus.SCHEDULED if scheduled_for else PostStatus.DRAFT,
            created_at=datetime.now(timezone.utc).isoformat(),
            scheduled_for=scheduled_for,
        )
        items.append(queued)
        self._write(items)
        return queued

    def list(self, status: PostStatus | None = None) -> list[QueuedPost]:
        items = self._read()
        if status is None:
            return items
        return [item for item in items if item.status == status]

    def get(self, post_id: str) -> QueuedPost | None:
        for item in self._read():
            if item.id == post_id:
                return item
        return None

    def update_status(
        self,
        post_id: str,
        status: PostStatus,
        *,
        publish_result: dict[str, Any] | None = None,
        notes: str | None = None,
    ) -> QueuedPost | None:
        items = self._read()
        for item in items:
            if item.id != post_id:
                continue
            item.status = status
            if publish_result is not None:
                item.publish_result = publish_result
            if notes is not None:
                item.notes = notes
            if status == PostStatus.PUBLISHED:
                item.published_at = datetime.now(timezone.utc).isoformat()
            self._write(items)
            return item
        return None

    def approve(self, post_id: str) -> QueuedPost | None:
        return self.update_status(post_id, PostStatus.APPROVED)

    def reject(self, post_id: str, notes: str = "") -> QueuedPost | None:
        return self.update_status(post_id, PostStatus.REJECTED, notes=notes)

    def pending_approval(self) -> list[QueuedPost]:
        return self.list(PostStatus.DRAFT)

    def ready_to_publish(self) -> list[QueuedPost]:
        return [p for p in self.list(PostStatus.APPROVED) if p.scheduled_for is None] + [
            p
            for p in self.list(PostStatus.SCHEDULED)
            if p.scheduled_for and p.scheduled_for <= datetime.now(timezone.utc).isoformat()
        ]
