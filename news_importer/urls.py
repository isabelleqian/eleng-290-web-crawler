"""Validate and normalize URLs without contacting the network."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from news_importer.errors import ImporterError


@dataclass(frozen=True)
class UrlCheck:
    ok: bool
    normalized: str | None = None
    hostname: str | None = None
    code: str | None = None
    message: str | None = None


def check_url(original: str | None) -> UrlCheck:
    """Accept an absolute http(s) URL and build a comparison form.

    The original string is not returned or rewritten here. Callers store it
    unchanged. Normalization trims surrounding whitespace, lowercases the
    scheme and hostname, and drops the fragment. Path, query, and percent
    encoding stay as written. HTTP and HTTPS stay distinct.
    """
    if original is None or original.strip() == "":
        return UrlCheck(False, code="missing_url", message="missing url")

    stripped = original.strip()
    if any(character.isspace() for character in stripped):
        return UrlCheck(
            False,
            code="unescaped_whitespace",
            message="URL contains unescaped whitespace",
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in stripped):
        return UrlCheck(
            False,
            code="malformed_url",
            message="URL contains an invalid control character",
        )
    if "://" not in stripped:
        return UrlCheck(
            False,
            code="unsupported_scheme",
            message="URL must be an absolute http or https URL",
        )

    parts = urlsplit(stripped)
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        label = parts.scheme or "(none)"
        return UrlCheck(
            False,
            code="unsupported_scheme",
            message=(
                f"unsupported URL scheme '{label}'; only http and https are accepted"
            ),
        )
    if parts.netloc == "":
        return UrlCheck(
            False,
            code="missing_hostname",
            message="URL must include a hostname",
        )

    userinfo, hostport = _split_userinfo(parts.netloc)
    hostname, port_token, error = _parse_hostport(hostport)
    if error is not None:
        return UrlCheck(False, code=error[0], message=error[1])
    if hostname == "" or hostname.strip(".") == "":
        return UrlCheck(
            False,
            code="missing_hostname",
            message="URL must include a hostname",
        )

    host_lower = hostname.lower()
    if hostport.startswith("["):
        host_text = f"[{host_lower}]"
    else:
        host_text = host_lower
    netloc = f"{userinfo}@{host_text}" if userinfo is not None else host_text
    if port_token is not None:
        netloc = f"{netloc}:{port_token}"
    normalized = urlunsplit((scheme, netloc, parts.path, parts.query, ""))
    return UrlCheck(True, normalized=normalized, hostname=host_lower)


def searched_at_error(value: str) -> str | None:
    """Return a message when a supplied search time is not an accepted form.

    A calendar date (YYYY-MM-DD) is accepted. A timestamp must include an
    explicit timezone. Naive timestamps are rejected so the importer cannot
    quietly treat them as UTC or as the import time.
    """
    import re
    from datetime import datetime

    text = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            return "searched_at is not a valid calendar date"
        return None

    match = re.fullmatch(
        r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})",
        text,
    )
    if match is None:
        return (
            "searched_at must be an ISO 8601 date (YYYY-MM-DD) or a timestamp "
            "with an explicit timezone (for example 2026-03-01T15:04:00Z)"
        )
    date_part, time_part, fraction, zone = match.groups()
    if zone == "Z":
        zone = "+00:00"
    try:
        datetime.fromisoformat(f"{date_part}T{time_part}{fraction or ''}{zone}")
    except ValueError:
        return "searched_at is not a valid timestamp"
    return None


def require_valid_searched_at(value: str, source: str) -> None:
    """Raise ImporterError when a command-line search time is unusable."""
    message = searched_at_error(value)
    if message is not None:
        raise ImporterError(f"{source}: {message}")


def _split_userinfo(netloc: str) -> tuple[str | None, str]:
    separator = netloc.rfind("@")
    if separator == -1:
        return None, netloc
    return netloc[:separator], netloc[separator + 1 :]


def _parse_hostport(
    hostport: str,
) -> tuple[str, str | None, tuple[str, str] | None]:
    bracketed = hostport.startswith("[")
    if bracketed:
        closing = hostport.find("]")
        if closing == -1:
            return "", None, ("malformed_url", "URL has a malformed host")
        hostname = hostport[1:closing]
        rest = hostport[closing + 1 :]
        if rest == "":
            return hostname, None, None
        if not rest.startswith(":"):
            return "", None, ("malformed_url", "URL has a malformed host")
        port_token = rest[1:]
    elif ":" in hostport:
        hostname, port_token = hostport.rsplit(":", 1)
    else:
        return hostport, None, None

    if (not bracketed) and (":" in hostname):
        return "", None, ("malformed_url", "URL has a malformed host")

    port_error = _port_error(port_token)
    if port_error is not None:
        return hostname, port_token, port_error
    return hostname, port_token, None


def _port_error(port: str) -> tuple[str, str] | None:
    if port == "" or not port.isdecimal():
        return "malformed_port", "URL has a malformed port"
    number = int(port)
    if number < 1 or number > 65535:
        return "malformed_port", "URL port must be an integer from 1 to 65535"
    return None
