# Faceless Social Media Agent

An AI-powered agent that runs a **faceless** social media account — no selfies, no on-camera presence. It generates niche content, queues it for your approval, and publishes to Twitter/X, Threads, and Instagram when you're ready.

Built as a starter you can customize for any niche (coffee, pets, coding, local life, etc.).

## What it does

1. **Content generation** — Uses OpenAI to write posts aligned with your voice, content pillars, and platform limits.
2. **Faceless by design** — Prompts forbid faces/personal photos; Instagram mode includes aesthetic image prompts (objects, scenes, pets from behind).
3. **Approval queue** — Drafts land in a local queue; nothing posts until you approve (unless you turn that off).
4. **Multi-platform** — Twitter/X, Threads (caption reuse), and Instagram adapters.
5. **Dry-run default** — Publishing simulates posts until you pass `--live` and configure API keys.

## Quick start

```bash
cd social-agent
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # Add your OPENAI_API_KEY
```

Generate your first post:

```bash
python main.py generate --topic "summer coffee without caffeine"
python main.py queue
python main.py approve <post-id>
python main.py publish <post-id>          # dry-run
python main.py publish <post-id> --live   # real post (needs API keys)
```

## Customize your account

Edit `config/account.yaml`:

| Section | Purpose |
|---------|---------|
| `account` | Name, handle, tagline |
| `voice` | Tone, perspective, do's and don'ts |
| `content_pillars` | Themes + weights (higher = more often) |
| `platforms` | Char limits, hashtag counts per network |
| `schedule` | Timezone and posting windows |
| `safety` | `require_human_approval`, `auto_post` |

The sample config is themed around coffee, chihuahuas, Arizona life, and introvert-friendly coding — inspired by your personal site. Change it to any faceless niche you want.

## CLI commands

| Command | Description |
|---------|-------------|
| `python main.py config` | Show current YAML config |
| `python main.py generate` | Create 1+ posts |
| `python main.py batch` | Batch across all platforms |
| `python main.py plan` | 7-day content plan |
| `python main.py queue` | List queued posts |
| `python main.py approve <id>` | Approve a draft |
| `python main.py reject <id>` | Reject a draft |
| `python main.py publish <id>` | Publish (dry-run by default) |
| `python main.py run` | Process due scheduled posts |
| `python main.py status` | Queue counts by status |

## Platform setup

### Twitter / X

1. Create a developer account at [developer.twitter.com](https://developer.twitter.com).
2. Create an app with **Read and Write** permissions.
3. Add keys to `.env`.

### Instagram

Instagram posting uses the [Instagram Graph API](https://developers.facebook.com/docs/instagram-api). You need:

- A Facebook Page linked to an Instagram Business/Creator account
- `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_ACCOUNT_ID`
- An `image_url` on the post (host a faceless image, or generate one with DALL·E/Midjourney using the `image_prompt` from generated posts)

### Threads

Meta's Threads API is still limited. The agent reuses Twitter infrastructure where possible, or runs in dry-run mode for Threads captions until you wire up a dedicated integration.

## Recommended faceless workflows

### 1. Text-first (Twitter / Threads)

Best for tips, hot takes, and community questions. Lowest friction — no images required.

```bash
python main.py plan
python main.py queue --status draft
# Review, approve the ones you like, schedule or publish
```

### 2. Aesthetic carousel (Instagram)

1. Generate posts with `include_image_prompt: true` (default in config).
2. Create images from prompts (no faces).
3. Upload to cloud storage; set `image_url` in queue JSON or extend the agent.
4. Approve and `publish --live`.

### 3. Repurpose one idea everywhere

Use the Python API:

```python
from src.agent import FacelessSocialAgent

agent = FacelessSocialAgent()
post = agent.create_post("twitter", topic_hint="monsoon season survival")
threads = agent.generator.repurpose(post.post, "threads", max_chars=500, hashtag_count=3)
```

## Automation (optional)

Run on a schedule with cron:

```cron
# Generate morning batch at 7am Phoenix
0 7 * * * cd /path/to/social-agent && .venv/bin/python main.py batch -c 2

# Publish approved scheduled posts every 30 minutes
*/30 * * * * cd /path/to/social-agent && .venv/bin/python main.py run --live
```

Or use GitHub Actions / a small VPS with the same commands.

## Project layout

```
social-agent/
├── config/account.yaml    # Your niche + voice
├── data/queue.json        # Local post queue (gitignored)
├── src/
│   ├── agent.py           # Main orchestrator
│   ├── config.py          # YAML loader
│   ├── content/           # LLM prompts + generator
│   ├── platforms/         # Twitter, Instagram adapters
│   └── queue.py           # Approval workflow
├── main.py                # CLI
└── requirements.txt
```

## Safety notes

- Keep `require_human_approval: true` until you trust the output.
- Review posts for accidental PII or off-brand tone.
- Respect each platform's automation and spam policies.
- Faceless ≠ anonymous for legal purposes; follow disclosure rules for sponsored content.

## Next steps you might add

- DALL·E / Replicate integration for automatic faceless images
- Notion or Google Sheets export for content calendars
- Analytics ingestion (engagement → feed back into prompts)
- TikTok script generator (voiceover + B-roll suggestions)
- Bluesky or LinkedIn adapters

---

Questions or want help tailoring this to a specific niche? Open an issue or iterate on `config/account.yaml` first — that's where 80% of the "personality" lives.
