#!/usr/bin/env python3
"""CLI for the faceless social media agent."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

# Allow running from social-agent/ without installing as a package
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.agent import FacelessSocialAgent  # noqa: E402
from src.config import load_config  # noqa: E402


def _agent() -> FacelessSocialAgent:
    return FacelessSocialAgent(load_config())


def _print_post(post, post_id: str | None = None) -> None:
    click.echo("─" * 60)
    if post_id:
        click.echo(click.style(f"ID: {post_id}", fg="cyan"))
    click.echo(click.style(f"[{post.platform}] {post.pillar} → {post.topic}", fg="green"))
    click.echo(post.body)
    if post.hashtags:
        click.echo(click.style(" ".join(f"#{t}" for t in post.hashtags), fg="blue"))
    if post.image_prompt:
        click.echo(click.style(f"Image prompt: {post.image_prompt}", fg="yellow"))
    if post.cta:
        click.echo(click.style(f"CTA: {post.cta}", dim=True))


@click.group()
@click.version_option(version="0.1.0", prog_name="faceless-social-agent")
def cli() -> None:
    """AI agent for faceless social media accounts."""


@cli.command("config")
def show_config() -> None:
    """Show loaded account configuration."""
    config = load_config()
    click.echo(json.dumps(config.raw, indent=2))


@cli.command("generate")
@click.option("--platform", "-p", default=None, help="twitter, threads, or instagram")
@click.option("--topic", "-t", default=None, help="Optional topic hint")
@click.option("--count", "-c", default=1, show_default=True, help="Number of posts")
@click.option("--no-queue", is_flag=True, help="Don't add to approval queue")
def generate(platform: str | None, topic: str | None, count: int, no_queue: bool) -> None:
    """Generate new post(s) with AI."""
    agent = _agent()
    for _ in range(count):
        post = agent.create_post(platform, topic_hint=topic, enqueue=not no_queue)
        queued = agent.queue.list()[-1] if not no_queue else None
        _print_post(post, queued.id if queued else None)


@cli.command("batch")
@click.option("--count", "-c", default=3, show_default=True, help="Posts per platform")
def batch(count: int) -> None:
    """Generate a batch across all enabled platforms."""
    agent = _agent()
    posts = agent.create_batch(count)
    queued = agent.queue.list()[-len(posts) :]
    for post, item in zip(posts, queued, strict=True):
        _print_post(post, item.id)


@cli.command("plan")
def week_plan() -> None:
    """Generate a 7-day content plan."""
    agent = _agent()
    posts = agent.create_week_plan()
    queued = agent.queue.list()[-len(posts) :]
    click.echo(click.style(f"Generated {len(posts)} posts for the week.", bold=True))
    for post, item in zip(posts, queued, strict=True):
        _print_post(post, item.id)


@cli.command("queue")
@click.option("--status", "-s", default=None, help="Filter by status: draft, approved, published")
def show_queue(status: str | None) -> None:
    """List posts in the content queue."""
    from src.queue import PostStatus

    agent = _agent()
    filter_status = PostStatus(status) if status else None
    items = agent.queue.list(filter_status)
    if not items:
        click.echo("Queue is empty.")
        return
    for item in items:
        _print_post(item.post, item.id)
        click.echo(click.style(f"Status: {item.status.value}", dim=True))


@cli.command("approve")
@click.argument("post_id")
def approve(post_id: str) -> None:
    """Approve a draft post for publishing."""
    result = _agent().approve(post_id)
    click.echo(result["message"] if not result["ok"] else f"Approved {post_id}")


@cli.command("reject")
@click.argument("post_id")
@click.option("--notes", "-n", default="", help="Reason for rejection")
def reject(post_id: str, notes: str) -> None:
    """Reject a draft post."""
    result = _agent().reject(post_id, notes)
    click.echo(result["message"] if not result["ok"] else f"Rejected {post_id}")


@cli.command("publish")
@click.argument("post_id")
@click.option("--live", is_flag=True, help="Actually post to APIs (not dry-run)")
@click.option("--force", is_flag=True, help="Skip approval check")
def publish(post_id: str, live: bool, force: bool) -> None:
    """Publish an approved post."""
    result = _agent().publish(post_id, dry_run=not live, force=force)
    if result["ok"]:
        click.echo(click.style("Success!", fg="green"))
    else:
        click.echo(click.style("Failed.", fg="red"))
    click.echo(result.get("message", ""))
    if result.get("url"):
        click.echo(result["url"])


@cli.command("run")
@click.option("--live", is_flag=True, help="Publish for real")
def run_scheduled(live: bool) -> None:
    """Process scheduled posts that are due."""
    results = _agent().run_scheduled(dry_run=not live)
    if not results:
        click.echo("No posts ready.")
        return
    for result in results:
        click.echo(json.dumps(result, indent=2))


@cli.command("status")
def status() -> None:
    """Show queue summary."""
    summary = _agent().status_summary()
    click.echo("Queue summary:")
    for key, value in sorted(summary.items()):
        click.echo(f"  {key}: {value}")


if __name__ == "__main__":
    cli()
