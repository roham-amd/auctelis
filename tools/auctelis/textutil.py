"""Neutral text helpers shared by the rule engine and export renderers."""

from __future__ import annotations

import re
from urllib.parse import urlsplit


def validated_http_url(value: str, *, what: str = "URL") -> str:
    """Return an http(s) URL or raise — never pass file:/custom schemes to urlopen."""
    text = str(value or "").strip()
    try:
        parts = urlsplit(text)
    except ValueError as exc:
        raise ValueError(f"invalid {what}: {text!r}") from exc
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        raise ValueError(f"{what} must be an http(s) URL with a host: {text!r}")
    return text


# Escape markdown specials that enable injection. Dots are left alone so paths
# like `.cursor/mcp.json` stay readable (ordered-list dots only matter at BOL).
_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+!|>])")
_URL_RE = re.compile(r"https?://([^/\s]+)(\S*)", re.IGNORECASE)
_MENTION_RE = re.compile(r"(^|[^/\w])@[\w-]+")
# ANSI CSI / OSC sequences (CSI: ESC [ params intermediates final; OSC: ESC ] … BEL/ST).
_CONTROL_SEQ_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
# Remaining C0/C1 controls plus Unicode bidi / zero-width formatting characters.
# Repo-controlled names and paths must not be able to move the cursor, spoof a
# rendered line, or hide text when a scan target is untrusted.
_UNSAFE_CHARS_RE = re.compile(
    "[\x00-\x08\x0b-\x1f\x7f-\x9f\u061c\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff\u2028\u2029]"
)


def strip_control(value: object) -> str:
    """Flatten to one line and remove terminal / bidi formatting characters.

    Used for fields interpolated into terminal or markdown output. Surrounding
    whitespace is trimmed; callers rendering whole lines use
    :func:`sanitize_terminal_line` to keep indentation.
    """
    return sanitize_terminal_line(value).strip()


def sanitize_terminal_line(value: object) -> str:
    """Strip terminal / bidi formatting characters while preserving indentation."""
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    text = _CONTROL_SEQ_RE.sub("", text)
    text = _UNSAFE_CHARS_RE.sub("", text)
    return text.rstrip()


def sanitize_terminal_text(value: str, *, max_len: int = 160) -> str:
    """Flatten one line and strip control sequences for plain terminal output.

    Same hygiene as :func:`escape_markdown` minus markdown escaping, so CLI
    stdout shows literal text (``(no authority change)``) instead of the
    backslash escapes required in a GitHub PR body.
    """
    text = strip_control(value)
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    return text


def escape_markdown_inline(value: object, *, max_len: int = 160) -> str:
    """Escape Markdown/HTML syntax without eliding URLs or defusing @mentions.

    For local report artifacts where package names (``@scope/pkg``) must stay
    readable but target-controlled text must not create links, images, or HTML.
    """
    text = strip_control(value)
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    text = _MD_SPECIAL.sub(r"\\\1", text)
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    return text


# Pasteable pin snippets. Longer than this is omitted — never truncated —
# because a cut JSON fragment is not a pin.
PASTEABLE_SNIPPET_MAX = 100


def pasteable_code_text(value: object, *, max_len: int = PASTEABLE_SNIPPET_MAX) -> str | None:
    """Literal snippet text, or None when it must not be shown.

    Newlines and over-budget values are omitted. Nothing is backslash-escaped,
    entity-escaped, or truncated. Control and bidi characters are stripped so
    a package name cannot spoof the line.
    """
    raw = str(value if value is not None else "")
    if "\n" in raw or "\r" in raw:
        return None
    text = strip_control(raw)
    if not text or len(text) > max_len:
        return None
    return text


def markdown_code_span(value: object, *, max_len: int = PASTEABLE_SNIPPET_MAX) -> str | None:
    """CommonMark code span around a pasteable snippet, or None to omit it.

    The fence is longer than any backtick run inside the snippet. A single
    space is padded on both sides so a leading or trailing backtick cannot
    merge with the fence; CommonMark strips that pair when it renders.
    """
    text = pasteable_code_text(value, max_len=max_len)
    if text is None:
        return None
    longest = 0
    run = 0
    for char in text:
        if char == "`":
            run += 1
            if run > longest:
                longest = run
        else:
            run = 0
    fence = "`" * (longest + 1)
    return f"{fence} {text} {fence}"


def escape_markdown(value: str, *, max_len: int = 160) -> str:
    """Neutralize markdown/HTML injection from target-controlled strings."""
    # Strip terminal/OSC control sequences as well as markdown.
    text = strip_control(value)
    # Keep destination hosts visible in code spans; drop URL paths (injection defense).
    # Placeholders survive markdown escaping, then expand to unescaped `` `host` ``.
    hosts: list[str] = []

    def _stash_host(match: re.Match[str]) -> str:
        host = match.group(1) or "redacted-host"
        # Hostnames are shown inside code spans; strip only injection-prone chars.
        safe = re.sub(r"[\\`*_{}\[\]()#!|>]", "", host)
        hosts.append(safe or "redacted-host")
        return f"\x00HOST{len(hosts) - 1}\x00"

    text = _URL_RE.sub(_stash_host, text)
    text = _MENTION_RE.sub(r"\1[@]", text)
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    text = _MD_SPECIAL.sub(r"\\\1", text)
    for idx, host in enumerate(hosts):
        text = text.replace(f"\x00HOST{idx}\x00", f"`{host}`")
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    return text
