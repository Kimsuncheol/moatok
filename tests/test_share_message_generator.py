"""Automated tests for the rule-based share message generator and admin editing API."""

from __future__ import annotations

import pytest

from app.models import ValidationError
from app.repositories import (
    ArticleRepository,
    ShareMessageRepository,
    SourceRepository,
)
from app.services.rss_collector import collect_rss_articles
from app.services.share_message_generator import (
    RuleBasedShareMessageGenerator,
    build_rule_based_share_message,
)
from app.services.url_validator import SyntheticProbeResponse


def test_rule_based_share_message_generator_with_and_without_description(fake_db):
    """Verify prefix, title, optional short description, original URL, and initial pending status."""
    share_repo = ShareMessageRepository(db=fake_db)
    generator = RuleBasedShareMessageGenerator(
        share_repo=share_repo,
        prefix="[오늘의 IT 픽]",
    )

    # 1. Article with description
    msg_with_desc, created1 = generator.generate_for_article_with_status(
        {
            "id": "art_101",
            "title": "Python 3.12 주요 업데이트",
            "summary": "성능 개선과 새로운 타입 파라미터 문법을 소개합니다.",
            "canonical_url": "https://example.com/articles/python-312",
        }
    )
    assert created1 is True
    assert msg_with_desc["status"] == "pending"
    assert msg_with_desc["article_id"] == "art_101"
    assert msg_with_desc["title"] == "Python 3.12 주요 업데이트"
    assert msg_with_desc["target_url"] == "https://example.com/articles/python-312"
    assert msg_with_desc["body"] == (
        "[오늘의 IT 픽] Python 3.12 주요 업데이트\n"
        "성능 개선과 새로운 타입 파라미터 문법을 소개합니다.\n"
        "https://example.com/articles/python-312"
    )

    # 2. Article without description (missing / empty summary)
    msg_no_desc, created2 = generator.generate_for_article_with_status(
        {
            "id": "art_102",
            "title": "클라우드 보안 체크리스트",
            "summary": "",
            "canonical_url": "https://example.com/articles/cloud-security",
        }
    )
    assert created2 is True
    assert msg_no_desc["status"] == "pending"
    assert msg_no_desc["body"] == (
        "[오늘의 IT 픽] 클라우드 보안 체크리스트\n"
        "https://example.com/articles/cloud-security"
    )


@pytest.mark.parametrize(
    "incomplete_article,expected_field",
    [
        (
            {
                "title": "Missing ID",
                "canonical_url": "https://example.com/post/1",
            },
            "id",
        ),
        (
            {
                "id": "art_1",
                "title": "   ",
                "canonical_url": "https://example.com/post/1",
            },
            "title",
        ),
        (
            {
                "id": "art_1",
                "title": "Missing URL",
            },
            "canonical_url",
        ),
    ],
)
def test_share_message_generator_rejects_missing_required_fields(
    incomplete_article, expected_field
):
    """Missing article_id, title, or canonical_url must raise ValidationError."""
    with pytest.raises(ValidationError, match=expected_field):
        build_rule_based_share_message(incomplete_article)


def test_share_message_generator_enforces_configurable_length_limits_and_never_copies_full_article(
    fake_db,
):
    """Long titles and full-article descriptions must be truncated to configured limits while preserving the URL."""
    share_repo = ShareMessageRepository(db=fake_db)
    long_title = "A" * 120
    full_article_text = "Full article paragraph content. " * 100  # > 3,000 chars
    target_url = "https://example.com/articles/long-read"

    generator = RuleBasedShareMessageGenerator(
        share_repo=share_repo,
        prefix="[브리핑]",
        max_title_length=40,
        max_description_length=80,
        max_body_length=160,
    )

    msg = generator.generate_for_article(
        {
            "id": "art_long_1",
            "title": long_title,
            "summary": full_article_text,
            "canonical_url": target_url,
        }
    )

    assert msg["status"] == "pending"
    assert len(msg["title"]) <= 40
    assert msg["title"].endswith("...")
    assert len(msg["body"]) <= 160
    assert msg["body"].startswith("[브리핑] ")
    assert msg["body"].endswith(target_url)
    # Ensure full article was NOT copied into the message body
    assert len(msg["body"]) < len(full_article_text)


def test_duplicate_collection_job_execution_does_not_create_duplicate_share_messages(
    fake_db,
):
    """Running the RSS collection job repeatedly must not create duplicate share messages."""
    source_repo = SourceRepository(db=fake_db)
    article_repo = ArticleRepository(db=fake_db)
    share_repo = ShareMessageRepository(db=fake_db)

    source_repo.create(
        name="Tech RSS",
        url="https://feeds.example.com/rss.xml",
        source_type="rss",
        enabled=True,
    )

    rss_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Tech RSS</title>
        <item>
          <title>First Article</title>
          <link>https://example.com/articles/first</link>
          <guid isPermaLink="false">guid-first</guid>
          <description>Short summary of the first article.</description>
        </item>
        <item>
          <title>Second Article</title>
          <link>https://example.com/articles/second</link>
          <guid isPermaLink="false">guid-second</guid>
        </item>
      </channel>
    </rss>"""

    def _mock_http_open(req, timeout):
        return SyntheticProbeResponse(status=200, body=rss_xml)

    # First collection job run
    summary1 = collect_rss_articles(
        source_repo=source_repo,
        article_repo=article_repo,
        share_repo=share_repo,
        http_open=_mock_http_open,
        allowed_domains=("example.com", "*.example.com"),
    )
    assert summary1["new"] == 2
    assert summary1["share_messages_created"] == 2

    messages_after_run1 = share_repo.list_messages()
    assert len(messages_after_run1) == 2
    assert all(m["status"] == "pending" for m in messages_after_run1)

    # Second collection job run with identical feed
    summary2 = collect_rss_articles(
        source_repo=source_repo,
        article_repo=article_repo,
        share_repo=share_repo,
        http_open=_mock_http_open,
        allowed_domains=("example.com", "*.example.com"),
    )
    assert summary2["new"] == 0
    assert summary2["duplicate"] == 2
    assert summary2["share_messages_created"] == 0
    assert len(share_repo.list_messages()) == 2


def test_admin_can_edit_pending_share_message_via_protected_api(
    client, fake_db, mock_firebase_auth
):
    """Administrators can edit pending share messages; non-admins and non-pending messages are rejected."""
    share_repo = ShareMessageRepository(db=fake_db)
    generator = RuleBasedShareMessageGenerator(share_repo=share_repo)

    msg = generator.generate_for_article(
        {
            "id": "art_edit_1",
            "title": "Original Title",
            "summary": "Original summary.",
            "canonical_url": "https://example.com/articles/edit-test",
        }
    )
    msg_id = msg["id"]
    assert msg["status"] == "pending"

    user_headers = {"Authorization": "Bearer valid-token-user-1"}
    admin_headers = {"Authorization": "Bearer valid-token-admin"}

    # 1. Non-admin user is forbidden from editing share messages (403)
    forbidden_res = client.patch(
        f"/api/v1/admin/share-messages/{msg_id}",
        headers=user_headers,
        json={"title": "Unauthorized Edit"},
    )
    assert forbidden_res.status_code == 403
    assert forbidden_res.get_json()["error"] == "forbidden"

    # 2. Administrator edits the pending share message (200)
    edit_res = client.patch(
        f"/api/v1/admin/share-messages/{msg_id}",
        headers=admin_headers,
        json={
            "title": "관리자가 다듬은 제목",
            "body": "[모아톡 브리핑] 관리자가 다듬은 제목\n핵심 요약 문장입니다.\nhttps://example.com/articles/edit-test",
        },
    )
    assert edit_res.status_code == 200
    updated_msg = edit_res.get_json()["share_message"]
    assert updated_msg["id"] == msg_id
    assert updated_msg["title"] == "관리자가 다듬은 제목"
    assert "관리자가 다듬은 제목" in updated_msg["body"]
    assert updated_msg["status"] == "pending"

    # 3. Administrator transitions status to 'ready_to_share'; subsequent edits to non-pending message are rejected (400)
    share_repo.update_status(msg_id, status="ready_to_share")

    non_pending_res = client.patch(
        f"/api/v1/admin/share-messages/{msg_id}",
        headers=admin_headers,
        json={"title": "Should Fail Because Not Pending"},
    )
    assert non_pending_res.status_code == 400
    assert "only 'pending' messages can be edited" in non_pending_res.get_json()["message"]
