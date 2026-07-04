import uuid

import pytest

from app.config import settings
from app.models import FeedbackSubmission


def _submit(client, message="Test feedback", **extra):
    body = {"message": message, **extra}
    return client.post("/api/feedback", json=body)


@pytest.mark.integration
def test_feedback_requires_auth(basic_client):
    res = _submit(basic_client)
    assert res.status_code == 401


@pytest.mark.integration
def test_feedback_submit_success(auth_client, monkeypatch):
    calls = []
    monkeypatch.setattr(settings, "feedback_to_email", "owner@example.com")

    def fake_send(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("app.feedback.send_feedback_email", fake_send)

    res = _submit(auth_client, message="Great app!", category="idea", page_url="/games")
    assert res.status_code == 204
    assert len(calls) == 1
    assert calls[0]["message"] == "Great app!"
    assert calls[0]["category"] == "idea"

    listed = auth_client.get("/api/admin/feedback?reviewed=false")
    assert listed.status_code == 403


@pytest.mark.integration
def test_feedback_submit_success_with_admin_review(auth_client, admin_client, monkeypatch, db):
    calls = []
    monkeypatch.setattr(settings, "feedback_to_email", "owner@example.com")
    monkeypatch.setattr("app.feedback.send_feedback_email", lambda **kw: calls.append(kw))

    res = _submit(auth_client, message="Bug report", category="bug")
    assert res.status_code == 204
    assert len(calls) == 1

    row = db.query(FeedbackSubmission).order_by(FeedbackSubmission.id.desc()).first()
    assert row is not None
    assert row.reviewed is False
    assert row.message == "Bug report"

    unreviewed = admin_client.get("/api/admin/feedback?reviewed=false")
    assert unreviewed.status_code == 200
    ids = [item["id"] for item in unreviewed.json()]
    assert row.id in ids

    patched = admin_client.patch(
        f"/api/admin/feedback/{row.id}",
        json={"reviewed": True},
    )
    assert patched.status_code == 200
    assert patched.json()["reviewed"] is True

    still_unreviewed = admin_client.get("/api/admin/feedback?reviewed=false")
    assert row.id not in [item["id"] for item in still_unreviewed.json()]


@pytest.mark.integration
def test_feedback_rate_limit(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "feedback_to_email", "owner@example.com")
    monkeypatch.setattr(settings, "feedback_rate_limit_per_hour", 5)
    monkeypatch.setattr("app.feedback.send_feedback_email", lambda **kw: None)

    for i in range(5):
        res = _submit(auth_client, message=f"msg {i}")
        assert res.status_code == 204, res.text

    res = _submit(auth_client, message="one too many")
    assert res.status_code == 429


@pytest.mark.integration
def test_feedback_message_too_long(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "feedback_to_email", "owner@example.com")
    monkeypatch.setattr("app.feedback.send_feedback_email", lambda **kw: None)

    res = _submit(auth_client, message="x" * 2001)
    assert res.status_code == 422
