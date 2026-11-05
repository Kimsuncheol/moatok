"""Automated tests for administrator-only content source endpoints and SSRF-safe URL validation."""

from __future__ import annotations

import socket
import pytest

from app.services.source_connectors import (
    OfficialApiSourceConnector,
    get_supported_source_types,
    register_source_connector,
)
from app.services.url_validator import SyntheticProbeResponse


def test_source_endpoints_require_administrator(client, mock_firebase_auth):
    """Unauthenticated callers get 401 and regular authenticated users get 403 on all source endpoints."""
    # Unauthenticated -> 401
    res_unauth = client.get("/api/v1/admin/sources")
    assert res_unauth.status_code == 401
    assert res_unauth.get_json()["error"] == "unauthorized"

    # Regular authenticated user -> 403
    user_headers = {"Authorization": "Bearer valid-token-user-1"}
    for method, path in [
        ("POST", "/api/v1/admin/sources"),
        ("GET", "/api/v1/admin/sources"),
        ("GET", "/api/v1/admin/sources/src_123"),
        ("PATCH", "/api/v1/admin/sources/src_123"),
        ("POST", "/api/v1/admin/sources/src_123/enable"),
        ("POST", "/api/v1/admin/sources/src_123/disable"),
        ("POST", "/api/v1/sources"),
        ("GET", "/api/v1/sources"),
    ]:
        res = client.open(
            path,
            method=method,
            headers=user_headers,
            json={
                "name": "Attempt",
                "url": "https://example.com/rss",
                "source_type": "rss",
            },
        )
        assert res.status_code == 403
        assert res.get_json()["error"] == "forbidden"
        assert res.get_json()["code"] == "admin_required"


def test_admin_create_list_update_enable_disable_sources(client, mock_firebase_auth):
    """Administrators can create, list, update, disable, and enable RSS and official API sources."""
    admin_headers = {"Authorization": "Bearer valid-token-admin"}

    # 1. Create RSS source
    rss_res = client.post(
        "/api/v1/admin/sources",
        headers=admin_headers,
        json={
            "name": "Example Tech RSS",
            "url": "https://feeds.example.com/tech/rss.xml",
            "source_type": "rss",
            "enabled": True,
        },
    )
    assert rss_res.status_code == 201
    rss_body = rss_res.get_json()
    assert rss_body["created"] is True
    rss_source = rss_body["source"]
    assert rss_source["id"].startswith("src_")
    assert rss_source["name"] == "Example Tech RSS"
    assert rss_source["url"] == "https://feeds.example.com/tech/rss.xml"
    assert rss_source["source_type"] == "rss"
    assert rss_source["enabled"] is True

    # 2. Create Official API source
    api_res = client.post(
        "/api/v1/admin/sources",
        headers=admin_headers,
        json={
            "name": "Example News Official API",
            "url": "https://news.example.com/api/v1/articles",
            "source_type": "official_api",
            "enabled": True,
        },
    )
    assert api_res.status_code == 201
    api_source = api_res.get_json()["source"]
    assert api_source["source_type"] == "official_api"

    # 3. List sources
    list_res = client.get("/api/v1/admin/sources", headers=admin_headers)
    assert list_res.status_code == 200
    list_body = list_res.get_json()
    assert list_body["count"] == 2
    assert "rss" in list_body["supported_source_types"]
    assert "official_api" in list_body["supported_source_types"]

    # 4. Update source name and URL
    patch_res = client.patch(
        f"/api/v1/admin/sources/{rss_source['id']}",
        headers=admin_headers,
        json={
            "name": "Updated Tech Feed",
            "url": "https://feeds.example.com/tech/v2/rss.xml",
        },
    )
    assert patch_res.status_code == 200
    updated_source = patch_res.get_json()["source"]
    assert updated_source["name"] == "Updated Tech Feed"
    assert updated_source["url"] == "https://feeds.example.com/tech/v2/rss.xml"

    # 5. Disable source
    disable_res = client.post(
        f"/api/v1/admin/sources/{rss_source['id']}/disable",
        headers=admin_headers,
    )
    assert disable_res.status_code == 200
    assert disable_res.get_json()["source"]["enabled"] is False

    # Verify enabled_only filter excludes disabled source
    enabled_list = client.get(
        "/api/v1/admin/sources?enabled_only=true", headers=admin_headers
    )
    assert enabled_list.status_code == 200
    assert enabled_list.get_json()["count"] == 1
    assert enabled_list.get_json()["sources"][0]["id"] == api_source["id"]

    # 6. Re-enable source
    enable_res = client.post(
        f"/api/v1/admin/sources/{rss_source['id']}/enable",
        headers=admin_headers,
    )
    assert enable_res.status_code == 200
    assert enable_res.get_json()["source"]["enabled"] is True


def test_extensible_official_api_connector_registration(client, mock_firebase_auth):
    """Verify the extensible connector interface allows registering new official API connectors."""

    class PartnerHeadlinesApiConnector(OfficialApiSourceConnector):
        source_type = "partner_headlines_api"

    register_source_connector(PartnerHeadlinesApiConnector())
    assert "partner_headlines_api" in get_supported_source_types()

    res = client.post(
        "/api/v1/admin/sources",
        headers={"Authorization": "Bearer valid-token-admin"},
        json={
            "name": "Partner Official API",
            "url": "https://example.org/api/headlines",
            "source_type": "partner_headlines_api",
        },
    )
    assert res.status_code == 201
    assert res.get_json()["source"]["source_type"] == "partner_headlines_api"


@pytest.mark.parametrize(
    "forbidden_url,expected_code",
    [
        # Unconfigured public domains
        ("https://untrusted-domain.io/feed.xml", "domain_not_allowed"),
        ("https://attacker-example.com/feed.xml", "domain_not_allowed"),
        # Localhost & internal hostnames
        ("http://localhost/rss.xml", "forbidden_address"),
        ("http://sub.localhost/rss.xml", "forbidden_address"),
        ("http://internal.local/rss.xml", "forbidden_address"),
        # Loopback IPv4 & IPv6 literals
        ("http://127.0.0.1/rss.xml", "forbidden_address"),
        ("http://127.0.0.53:8080/rss.xml", "forbidden_address"),
        ("http://[::1]/rss.xml", "forbidden_address"),
        # Private RFC1918 & IPv6 unique local addresses
        ("http://10.0.0.1/rss.xml", "forbidden_address"),
        ("http://172.16.10.5/rss.xml", "forbidden_address"),
        ("http://192.168.1.100/rss.xml", "forbidden_address"),
        ("http://[fc00::1]/rss.xml", "forbidden_address"),
        ("http://[::ffff:10.0.0.1]/rss.xml", "forbidden_address"),
        # Link-local & Cloud Metadata service addresses
        ("http://169.254.169.254/latest/meta-data/", "forbidden_address"),
        ("http://169.254.10.20/rss.xml", "forbidden_address"),
        ("http://[fe80::1]/rss.xml", "forbidden_address"),
        ("http://metadata.google.internal/computeMetadata/v1/", "forbidden_address"),
        ("http://100.100.100.200/latest/meta-data/", "forbidden_address"),
        # Invalid schemes & embedded credentials
        ("file:///etc/passwd", "invalid_source_url"),
        ("ftp://example.com/feed.xml", "invalid_source_url"),
        ("https://user:pass@example.com/feed.xml", "invalid_source_url"),
    ],
)
def test_source_url_rejects_unallowed_domains_localhost_private_and_metadata_addresses(
    client, mock_firebase_auth, forbidden_url, expected_code
):
    """Ensure only explicitly configured public domains are allowed and all internal/metadata addresses are rejected."""
    res = client.post(
        "/api/v1/admin/sources",
        headers={"Authorization": "Bearer valid-token-admin"},
        json={
            "name": "Rejected Source",
            "url": forbidden_url,
            "source_type": "rss",
        },
    )
    assert res.status_code == 400
    body = res.get_json()
    assert body["error"] == "validation_error"
    assert body["code"] == expected_code


def test_source_url_rejects_dns_rebinding_to_private_or_metadata_ip(
    client, mock_firebase_auth, monkeypatch
):
    """Even if a hostname is in ALLOWED_SOURCE_DOMAINS, reject it if DNS resolves to a private/metadata IP."""

    def _fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 80))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)

    res = client.post(
        "/api/v1/admin/sources",
        headers={"Authorization": "Bearer valid-token-admin"},
        json={
            "name": "DNS Rebound Source",
            "url": "https://example.com/feed.xml",
            "source_type": "rss",
        },
    )
    assert res.status_code == 400
    assert res.get_json()["code"] == "forbidden_address"


def test_redirect_destination_validation_blocks_ssrf_and_allows_safe_redirects(
    app, client, mock_firebase_auth
):
    """Redirect targets must be validated with the same rules as the original URL."""
    admin_headers = {"Authorization": "Bearer valid-token-admin"}

    # 1. Redirect from allowed domain to metadata service -> rejected!
    def _redirect_to_metadata(req, timeout):
        return SyntheticProbeResponse(
            status=302,
            body=b"",
            headers={"Location": "http://169.254.169.254/latest/meta-data/"},
        )

    app.config["SOURCE_HTTP_OPENER"] = _redirect_to_metadata
    res_meta = client.post(
        "/api/v1/admin/sources",
        headers=admin_headers,
        json={
            "name": "Redirect to Metadata",
            "url": "https://example.com/rss",
            "source_type": "rss",
        },
    )
    assert res_meta.status_code == 400
    assert res_meta.get_json()["code"] == "forbidden_address"
    assert "Redirect destination URL" in res_meta.get_json()["message"]

    # 2. Redirect from allowed domain to unallowed external domain -> rejected!
    def _redirect_to_unallowed(req, timeout):
        return SyntheticProbeResponse(
            status=301,
            body=b"",
            headers={"Location": "https://malicious.invalid/feed.xml"},
        )

    app.config["SOURCE_HTTP_OPENER"] = _redirect_to_unallowed
    res_unallowed = client.post(
        "/api/v1/admin/sources",
        headers=admin_headers,
        json={
            "name": "Redirect to Unallowed",
            "url": "https://example.com/rss",
            "source_type": "rss",
        },
    )
    assert res_unallowed.status_code == 400
    assert res_unallowed.get_json()["code"] == "domain_not_allowed"

    # 3. Redirect from allowed domain to another configured allowed domain -> succeeds!
    def _redirect_to_allowed_subdomain(req, timeout):
        if req.full_url == "https://example.com/old-rss":
            return SyntheticProbeResponse(
                status=301,
                body=b"",
                headers={"Location": "https://feeds.example.com/new-rss.xml"},
            )
        return SyntheticProbeResponse(status=200)

    app.config["SOURCE_HTTP_OPENER"] = _redirect_to_allowed_subdomain
    res_ok = client.post(
        "/api/v1/admin/sources",
        headers=admin_headers,
        json={
            "name": "Valid Redirected Feed",
            "url": "https://example.com/old-rss",
            "source_type": "rss",
        },
    )
    assert res_ok.status_code == 201
    assert (
        res_ok.get_json()["source"]["url"] == "https://feeds.example.com/new-rss.xml"
    )


def test_source_url_enforces_timeouts_and_response_size_limits(
    app, client, mock_firebase_auth
):
    """Timeouts and oversized source responses must be rejected with consistent 400 JSON errors."""
    admin_headers = {"Authorization": "Bearer valid-token-admin"}
    captured_timeouts: list[float] = []

    # 1. Timeout enforcement
    def _slow_opener(req, timeout):
        captured_timeouts.append(timeout)
        raise socket.timeout("Connection timed out")

    app.config["SOURCE_FETCH_TIMEOUT_SECONDS"] = 2.5
    app.config["SOURCE_HTTP_OPENER"] = _slow_opener

    timeout_res = client.post(
        "/api/v1/admin/sources",
        headers=admin_headers,
        json={
            "name": "Slow Source",
            "url": "https://example.com/slow-feed.xml",
            "source_type": "rss",
        },
    )
    assert timeout_res.status_code == 400
    assert timeout_res.get_json()["code"] == "source_timeout"
    assert captured_timeouts == [2.5]

    # 2. Response size limit enforcement (streaming body larger than SOURCE_FETCH_MAX_BYTES)
    app.config["SOURCE_FETCH_MAX_BYTES"] = 1024

    def _oversized_opener(req, timeout):
        oversized_body = b"x" * 2048
        return SyntheticProbeResponse(
            status=200,
            body=oversized_body,
            headers={"Content-Type": "application/rss+xml"},
        )

    app.config["SOURCE_HTTP_OPENER"] = _oversized_opener

    size_res = client.post(
        "/api/v1/admin/sources",
        headers=admin_headers,
        json={
            "name": "Oversized Source",
            "url": "https://example.com/huge-feed.xml",
            "source_type": "rss",
        },
    )
    assert size_res.status_code == 400
    assert size_res.get_json()["code"] == "response_too_large"
