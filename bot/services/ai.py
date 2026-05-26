from typing import Optional

from .. import config

_client = None


def is_configured() -> bool:
    return bool(config.ANTHROPIC_API_KEY)


def _get_client():
    global _client
    if _client is None:
        from anthropic import AsyncAnthropic

        _client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


async def generate_reply(user_text: str, system_prompt: Optional[str] = None) -> str:
    """Generate a short AI reply. The system prompt is marked for prompt caching
    so repeated calls with the same persona reuse the cached prefix."""
    client = _get_client()
    system = system_prompt or config.DEFAULT_SYSTEM_PROMPT

    resp = await client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=config.ANTHROPIC_MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_text}],
    )

    parts = [block.text for block in resp.content if getattr(block, "type", None) == "text"]
    return "".join(parts).strip() or "..."
