"""Extensible content source connector interface supporting RSS feeds and official APIs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from typing import Any
import xml.etree.ElementTree as ET

from app.models import ValidationError
from app.services.url_validator import (
    UrlProbeResult,
    UrlValidationError,
    fetch_and_validate_source_url,
    validate_source_url,
)


class SourceConnector(ABC):
    """Abstract base interface for content source connectors (RSS, official APIs, etc.)."""

    source_type: str

    @abstractmethod
    def validate_source(
        self,
        url: str,
        *,
        allowed_domains: Iterable[str] | None = None,
        probe_result: UrlProbeResult | None = None,
    ) -> str:
        """Validate the source URL and optional probed payload, returning the canonical URL."""

    def fetch(
        self,
        url: str,
        *,
        allowed_domains: Iterable[str] | None = None,
        timeout_seconds: float | None = None,
        max_bytes: int | None = None,
        max_redirects: int | None = None,
        http_open: Callable[..., Any] | None = None,
    ) -> UrlProbeResult:
        """Fetch source content safely with redirect validation, timeouts, and size limits."""
        probe = fetch_and_validate_source_url(
            url,
            allowed_domains=allowed_domains,
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
            max_redirects=max_redirects,
            http_open=http_open,
        )
        self.validate_source(
            probe.final_url,
            allowed_domains=allowed_domains,
            probe_result=probe,
        )
        return probe


class RssSourceConnector(SourceConnector):
    """Connector for RSS / Atom syndication feeds."""

    source_type = "rss"

    def validate_source(
        self,
        url: str,
        *,
        allowed_domains: Iterable[str] | None = None,
        probe_result: UrlProbeResult | None = None,
    ) -> str:
        canonical_url = validate_source_url(url, allowed_domains=allowed_domains)
        if probe_result and probe_result.content:
            text = probe_result.content.decode("utf-8", errors="replace").strip()
            if text.startswith("<"):
                try:
                    root = ET.fromstring(text)
                except ET.ParseError as exc:
                    raise UrlValidationError(
                        "Invalid RSS/Atom XML payload returned by source URL.",
                        code="invalid_rss_payload",
                    ) from exc
                tag_lower = root.tag.lower()
                if not (
                    tag_lower.endswith("rss")
                    or tag_lower.endswith("feed")
                    or tag_lower.endswith("rdf")
                ):
                    raise UrlValidationError(
                        "XML root element is not a valid RSS or Atom feed.",
                        code="invalid_rss_payload",
                    )
        return canonical_url


class OfficialApiSourceConnector(SourceConnector):
    """Extensible connector for official JSON REST APIs."""

    source_type = "official_api"

    def validate_source(
        self,
        url: str,
        *,
        allowed_domains: Iterable[str] | None = None,
        probe_result: UrlProbeResult | None = None,
    ) -> str:
        return validate_source_url(url, allowed_domains=allowed_domains)


_CONNECTOR_REGISTRY: dict[str, SourceConnector] = {}


def register_source_connector(
    connector: SourceConnector, *, aliases: Iterable[str] = ()
) -> None:
    """Register a source connector implementation for `connector.source_type` (and optional aliases)."""
    primary = connector.source_type.strip().lower()
    if not primary:
        raise ValueError("Connector 'source_type' must be non-empty.")
    _CONNECTOR_REGISTRY[primary] = connector
    for alias in aliases:
        cleaned_alias = alias.strip().lower()
        if cleaned_alias:
            _CONNECTOR_REGISTRY[cleaned_alias] = connector


def get_source_connector(source_type: str) -> SourceConnector:
    """Retrieve a registered `SourceConnector` for the given `source_type`."""
    cleaned = str(source_type or "").strip().lower()
    connector = _CONNECTOR_REGISTRY.get(cleaned)
    if connector is None:
        supported = sorted({c.source_type for c in _CONNECTOR_REGISTRY.values()})
        raise ValidationError(
            f"Unsupported source_type '{cleaned}'. Supported types: {supported}"
        )
    return connector


def get_supported_source_types() -> list[str]:
    """Return sorted canonical names of registered source connectors."""
    return sorted({c.source_type for c in _CONNECTOR_REGISTRY.values()})


# Register default built-in connectors: RSS and Official API
register_source_connector(RssSourceConnector())
register_source_connector(OfficialApiSourceConnector(), aliases=("api",))
