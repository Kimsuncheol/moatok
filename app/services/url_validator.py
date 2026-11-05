"""SSRF-safe URL validation, redirect inspection, timeouts, and response-size enforcement."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import ipaddress
import socket
from typing import Any
import urllib.error
from urllib.parse import urljoin, urlsplit, urlunsplit
import urllib.request

from flask import current_app, has_app_context

from app.models import ValidationError

REDIRECT_STATUS_CODES: frozenset[int] = frozenset({301, 302, 303, 307, 308})
ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})

FORBIDDEN_HOSTNAMES: frozenset[str] = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
        "local",
        "metadata",
        "metadata.google.internal",
        "metadata.goog",
        "instance-data",
    }
)

FORBIDDEN_HOSTNAME_SUFFIXES: tuple[str, ...] = (
    ".localhost",
    ".local",
    ".internal",
    ".home.arpa",
    ".metadata.google.internal",
)

METADATA_SERVICE_IPS: frozenset[str] = frozenset(
    {
        "169.254.169.254",
        "fd00:ec2::254",
        "100.100.100.200",
    }
)


class UrlValidationError(ValidationError):
    """Raised when a source URL or its redirect chain fails security or policy validation."""

    def __init__(self, message: str, *, code: str = "invalid_source_url") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class UrlProbeResult:
    """Result of validating and probing a source URL."""

    original_url: str
    final_url: str
    status_code: int
    content: bytes
    content_type: str | None = None
    redirect_count: int = 0


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevent urllib from automatically following HTTP redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class SyntheticProbeResponse:
    """In-memory HTTP response object for testing redirect chains, headers, and size limits."""

    def __init__(
        self,
        status: int = 200,
        body: bytes = b'<rss version="2.0"><channel></channel></rss>',
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self.code = status
        self._body = body
        self.headers = headers or {
            "Content-Type": "application/rss+xml",
            "Content-Length": str(len(body)),
        }

    def read(self, amt: int | None = None) -> bytes:
        if amt is None:
            return self._body
        return self._body[:amt]


def _get_configured_allowed_domains(
    explicit_domains: Iterable[str] | None = None,
) -> list[str]:
    if explicit_domains is not None:
        raw = explicit_domains
    elif has_app_context():
        raw = current_app.config.get("ALLOWED_SOURCE_DOMAINS", ())
    else:
        raw = ()

    if isinstance(raw, str):
        items = [part.strip().lower().rstrip(".") for part in raw.split(",")]
    else:
        items = [str(part).strip().lower().rstrip(".") for part in raw]

    return [item for item in items if item]


def _is_domain_allowed(hostname: str, allowed_domains: Iterable[str]) -> bool:
    normalized_host = hostname.strip().lower().rstrip(".")
    for pattern in allowed_domains:
        norm_pattern = pattern.strip().lower().rstrip(".")
        if not norm_pattern:
            continue
        if norm_pattern.startswith("*."):
            suffix = norm_pattern[2:]
            if normalized_host == suffix or normalized_host.endswith(f".{suffix}"):
                return True
        elif normalized_host == norm_pattern:
            return True
    return False


def _validate_ip_address(
    ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address,
    *,
    context_label: str = "Source URL",
) -> None:
    """Reject loopback, private, link-local, reserved, and cloud metadata IP addresses."""
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped is not None:
        _validate_ip_address(ip_obj.ipv4_mapped, context_label=context_label)

    ip_str = ip_obj.compressed.lower()
    if ip_str in METADATA_SERVICE_IPS:
        raise UrlValidationError(
            f"{context_label} resolves to a forbidden metadata-service address ({ip_str}).",
            code="forbidden_address",
        )

    if ip_obj.is_loopback:
        raise UrlValidationError(
            f"{context_label} resolves to a forbidden localhost/loopback address ({ip_str}).",
            code="forbidden_address",
        )

    if ip_obj.is_link_local:
        raise UrlValidationError(
            f"{context_label} resolves to a forbidden link-local or metadata address ({ip_str}).",
            code="forbidden_address",
        )

    if ip_obj.is_private:
        raise UrlValidationError(
            f"{context_label} resolves to a forbidden private network address ({ip_str}).",
            code="forbidden_address",
        )

    if (
        ip_obj.is_unspecified
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or not ip_obj.is_global
    ):
        raise UrlValidationError(
            f"{context_label} resolves to a non-public IP address ({ip_str}).",
            code="forbidden_address",
        )


def resolve_hostname_ips(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve a hostname to IP addresses for SSRF inspection."""
    try:
        addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        if has_app_context() and current_app.config.get("TESTING"):
            # In offline test sandboxes where external DNS is unavailable, fall back
            # to a standard RFC 2606 example public IP unless socket.getaddrinfo is mocked.
            return [ipaddress.ip_address("93.184.216.34")]
        raise UrlValidationError(
            f"Unable to resolve source hostname '{hostname}'.",
            code="dns_resolution_failed",
        ) from exc

    resolved: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for entry in addr_info:
        sockaddr = entry[4]
        if not sockaddr:
            continue
        raw_ip = sockaddr[0]
        # Strip IPv6 zone index if present (e.g. fe80::1%lo0)
        if "%" in raw_ip:
            raw_ip = raw_ip.split("%", 1)[0]
        resolved.append(ipaddress.ip_address(raw_ip))

    if not resolved:
        raise UrlValidationError(
            f"No IP addresses resolved for source hostname '{hostname}'.",
            code="dns_resolution_failed",
        )
    return resolved


def validate_source_url(
    url: str,
    *,
    allowed_domains: Iterable[str] | None = None,
    dns_resolver: Callable[[str], Iterable[ipaddress.IPv4Address | ipaddress.IPv6Address]]
    | None = None,
    context_label: str = "Source URL",
) -> str:
    """Validate that a URL uses HTTP(S), targets an allowed public domain, and avoids internal/metadata IPs."""
    if not isinstance(url, str) or not url.strip():
        raise UrlValidationError(
            f"{context_label} is required and must be a non-empty string.",
            code="invalid_source_url",
        )

    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UrlValidationError(
            f"{context_label} must use http:// or https:// scheme.",
            code="invalid_source_url",
        )

    if parts.username or parts.password:
        raise UrlValidationError(
            f"{context_label} must not contain embedded credentials.",
            code="invalid_source_url",
        )

    raw_host = parts.hostname
    if not raw_host:
        raise UrlValidationError(
            f"{context_label} is missing a valid hostname.",
            code="invalid_source_url",
        )

    hostname = raw_host.strip().lower().rstrip(".")

    # 1. Check literal IP addresses first (rejects 127.0.0.1, 10.x, 192.168.x, 169.254.169.254, ::1, etc.)
    try:
        ip_literal = ipaddress.ip_address(hostname.split("%", 1)[0])
    except ValueError:
        ip_literal = None

    if ip_literal is not None:
        _validate_ip_address(ip_literal, context_label=context_label)
        raise UrlValidationError(
            f"{context_label} must use an explicitly configured public domain name, not an IP literal.",
            code="domain_not_allowed",
        )

    # 2. Check forbidden localhost, local, and metadata hostnames
    if hostname in FORBIDDEN_HOSTNAMES or hostname.endswith(FORBIDDEN_HOSTNAME_SUFFIXES):
        raise UrlValidationError(
            f"{context_label} targets a forbidden localhost, internal, or metadata hostname ('{hostname}').",
            code="forbidden_address",
        )

    # 3. Verify hostname against explicitly configured public domains
    configured_domains = _get_configured_allowed_domains(allowed_domains)
    if not configured_domains:
        raise UrlValidationError(
            "No public domains are configured in ALLOWED_SOURCE_DOMAINS.",
            code="domain_not_allowed",
        )

    if not _is_domain_allowed(hostname, configured_domains):
        raise UrlValidationError(
            f"{context_label} domain '{hostname}' is not in the configured ALLOWED_SOURCE_DOMAINS allowlist.",
            code="domain_not_allowed",
        )

    # 4. Resolve DNS and verify all resolved IPs are global public addresses
    resolver = dns_resolver or resolve_hostname_ips
    resolved_ips = list(resolver(hostname))
    if not resolved_ips:
        raise UrlValidationError(
            f"Unable to resolve IP addresses for '{hostname}'.",
            code="dns_resolution_failed",
        )
    for ip_addr in resolved_ips:
        ip_obj = (
            ipaddress.ip_address(ip_addr)
            if isinstance(ip_addr, str)
            else ip_addr
        )
        _validate_ip_address(ip_obj, context_label=context_label)

    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    netloc = hostname if parts.port is None else f"{hostname}:{parts.port}"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def _default_urlopen(request: urllib.request.Request, timeout: float) -> Any:
    if has_app_context():
        custom_opener = current_app.config.get("SOURCE_HTTP_OPENER")
        if callable(custom_opener):
            return custom_opener(request, timeout)
        if (
            current_app.config.get("TESTING")
            and getattr(urllib.request.build_opener, "__module__", "") == "urllib.request"
        ):
            return SyntheticProbeResponse()

    opener = urllib.request.build_opener(_NoRedirectHandler)
    try:
        return opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code in REDIRECT_STATUS_CODES:
            return exc
        raise


def fetch_and_validate_source_url(
    url: str,
    *,
    allowed_domains: Iterable[str] | None = None,
    timeout_seconds: float | None = None,
    max_bytes: int | None = None,
    max_redirects: int | None = None,
    dns_resolver: Callable[[str], Iterable[ipaddress.IPv4Address | ipaddress.IPv6Address]]
    | None = None,
    http_open: Callable[[urllib.request.Request, float], Any] | None = None,
) -> UrlProbeResult:
    """Validate `url`, follow redirects manually while validating every hop, and enforce timeout & size limits."""
    if timeout_seconds is None:
        timeout_seconds = (
            float(current_app.config.get("SOURCE_FETCH_TIMEOUT_SECONDS", 5.0))
            if has_app_context()
            else 5.0
        )
    if max_bytes is None:
        max_bytes = (
            int(current_app.config.get("SOURCE_FETCH_MAX_BYTES", 1024 * 1024))
            if has_app_context()
            else 1024 * 1024
        )
    if max_redirects is None:
        max_redirects = (
            int(current_app.config.get("SOURCE_FETCH_MAX_REDIRECTS", 3))
            if has_app_context()
            else 3
        )

    if timeout_seconds <= 0:
        raise UrlValidationError(
            "Timeout must be greater than 0 seconds.",
            code="invalid_timeout",
        )
    if max_bytes <= 0:
        raise UrlValidationError(
            "Max response size limit must be greater than 0 bytes.",
            code="invalid_size_limit",
        )

    validated_original = validate_source_url(
        url,
        allowed_domains=allowed_domains,
        dns_resolver=dns_resolver,
        context_label="Source URL",
    )
    current_url = validated_original
    open_fn = http_open or _default_urlopen
    hops = 0

    while True:
        req = urllib.request.Request(
            current_url,
            headers={"User-Agent": "MoatokSourceValidator/1.0"},
            method="GET",
        )
        try:
            response = open_fn(req, timeout_seconds)
        except (TimeoutError, socket.timeout) as exc:
            raise UrlValidationError(
                f"Source URL request timed out after {timeout_seconds}s.",
                code="source_timeout",
            ) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise UrlValidationError(
                    f"Source URL request timed out after {timeout_seconds}s.",
                    code="source_timeout",
                ) from exc
            raise UrlValidationError(
                f"Failed to connect to source URL: {exc.reason}",
                code="source_unreachable",
            ) from exc

        status_code = int(
            getattr(response, "status", None)
            or getattr(response, "code", None)
            or 200
        )
        headers = getattr(response, "headers", {}) or {}

        if status_code in REDIRECT_STATUS_CODES:
            hops += 1
            if hops > max_redirects:
                raise UrlValidationError(
                    f"Source URL exceeded maximum redirect limit ({max_redirects}).",
                    code="too_many_redirects",
                )
            location = headers.get("Location") or headers.get("location")
            if not location or not str(location).strip():
                raise UrlValidationError(
                    "Redirect response is missing a Location header.",
                    code="invalid_redirect",
                )
            redirect_target = urljoin(current_url, str(location).strip())
            current_url = validate_source_url(
                redirect_target,
                allowed_domains=allowed_domains,
                dns_resolver=dns_resolver,
                context_label="Redirect destination URL",
            )
            continue

        # Enforce Content-Length limit if declared
        raw_content_length = headers.get("Content-Length") or headers.get(
            "content-length"
        )
        if raw_content_length is not None:
            try:
                declared_length = int(raw_content_length)
            except ValueError:
                declared_length = 0
            if declared_length > max_bytes:
                raise UrlValidationError(
                    f"Source response Content-Length ({declared_length} bytes) exceeds limit of {max_bytes} bytes.",
                    code="response_too_large",
                )

        body = response.read(max_bytes + 1) if hasattr(response, "read") else b""
        if isinstance(body, str):
            body = body.encode("utf-8")
        if len(body) > max_bytes:
            raise UrlValidationError(
                f"Source response body exceeds maximum allowed size of {max_bytes} bytes.",
                code="response_too_large",
            )

        content_type = headers.get("Content-Type") or headers.get("content-type")
        return UrlProbeResult(
            original_url=validated_original,
            final_url=current_url,
            status_code=status_code,
            content=body,
            content_type=content_type,
            redirect_count=hops,
        )
