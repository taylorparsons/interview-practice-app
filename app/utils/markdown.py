from typing import Optional

import bleach
from markdown import markdown

ALLOWED_TAGS = [
    "p",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "code",
    "pre",
    "blockquote",
    "h1",
    "h2",
    "h3",
    "h4",
    "br",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "code": ["class"],
    "pre": ["class"],
}


def render_markdown_safe(text: Optional[str]) -> str:
    """Render Markdown to sanitized HTML suitable for display."""
    if not text:
        return ""
    # Convert to HTML first, then sanitize to avoid unsafe tags.
    html = markdown(text, extensions=["extra"])
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
