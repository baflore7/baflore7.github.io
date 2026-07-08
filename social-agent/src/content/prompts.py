from __future__ import annotations

SYSTEM_PROMPT = """You are a social media strategist for a FACELESS account.
The account never shows a human face, never references the operator by name,
and builds community through niche expertise, aesthetics, and relatable writing.

Rules:
- Write original, scroll-stopping copy — no cliché filler.
- Match the configured voice exactly.
- Stay within character limits.
- Hashtags must be relevant and not spammy.
- For Instagram, when asked, also provide a DALL·E-style image prompt:
  no people, no faces, no text in image — objects, scenes, textures, pets from behind, etc.
- Return valid JSON only, with no markdown fences.
"""

POST_SCHEMA = """{
  "pillar": "content pillar used",
  "topic": "specific angle",
  "body": "main post text",
  "hashtags": ["tag1", "tag2"],
  "image_prompt": "optional visual prompt or null",
  "hook": "first line if threading",
  "cta": "soft call to action"
}"""

BATCH_SCHEMA = """{
  "posts": [""" + POST_SCHEMA.strip() + """]
}"""


def build_user_prompt(
    *,
    account_name: str,
    tagline: str,
    voice: dict,
    pillar: dict,
    platform: str,
    max_chars: int,
    hashtag_count: int,
    include_image_prompt: bool,
    topic_hint: str | None = None,
) -> str:
    topics = ", ".join(pillar.get("topics", []))
    hint = f"\nOptional angle: {topic_hint}" if topic_hint else ""

    image_line = (
        "Include image_prompt for a faceless, aesthetic visual."
        if include_image_prompt
        else "Set image_prompt to null."
    )

    return f"""Account: {account_name}
Tagline: {tagline}
Voice tone: {voice.get('tone')}
Perspective: {voice.get('perspective')}
Avoid: {', '.join(voice.get('avoid', []))}
Always: {', '.join(voice.get('always', []))}

Platform: {platform}
Max characters for body: {max_chars}
Hashtag count: {hashtag_count}
Pillar: {pillar.get('name')}
Topic ideas: {topics}{hint}

{image_line}

Return JSON matching this schema:
{POST_SCHEMA}
"""
