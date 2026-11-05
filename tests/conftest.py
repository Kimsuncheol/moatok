"""Pytest fixtures and in-memory Firestore/Firebase mocks for automated testing."""

from __future__ import annotations

from typing import Any
import uuid
import pytest

from app import create_app
from app.extensions import set_firestore_client


class FakeDocumentSnapshot:
    def __init__(self, doc_id: str, data: dict[str, Any] | None):
        self.id = doc_id
        self._data = data.copy() if data is not None else None

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict[str, Any] | None:
        return self._data.copy() if self._data is not None else None


class FakeDocumentReference:
    def __init__(self, store: dict[str, dict[str, Any]], doc_id: str | None = None):
        self._store = store
        self.id = doc_id or f"doc-{uuid.uuid4().hex[:10]}"

    def set(self, data: dict[str, Any], merge: bool = False) -> None:
        if merge and self.id in self._store:
            merged = self._store[self.id].copy()
            merged.update(data)
            self._store[self.id] = merged
        else:
            self._store[self.id] = data.copy()

    def update(self, updates: dict[str, Any]) -> None:
        if self.id not in self._store:
            raise KeyError(f"Document {self.id} does not exist")
        self._store[self.id].update(updates)

    def get(self) -> FakeDocumentSnapshot:
        return FakeDocumentSnapshot(self.id, self._store.get(self.id))


class FakeQuery:
    def __init__(
        self,
        store: dict[str, dict[str, Any]],
        filters: list[tuple[str, str, Any]] | None = None,
        limit_val: int | None = None,
    ):
        self._store = store
        self._filters = filters or []
        self._limit = limit_val

    def where(self, field: str, op: str, value: Any) -> FakeQuery:
        return FakeQuery(
            self._store,
            filters=[*self._filters, (field, op, value)],
            limit_val=self._limit,
        )

    def limit(self, count: int) -> FakeQuery:
        return FakeQuery(self._store, filters=self._filters, limit_val=count)

    def stream(self) -> list[FakeDocumentSnapshot]:
        snapshots: list[FakeDocumentSnapshot] = []
        for doc_id, data in self._store.items():
            matched = True
            for field, op, val in self._filters:
                if op == "==" and data.get(field) != val:
                    matched = False
                    break
            if matched:
                snapshots.append(FakeDocumentSnapshot(doc_id, data))
        if self._limit is not None:
            snapshots = snapshots[: self._limit]
        return snapshots


class FakeCollection:
    def __init__(self, store: dict[str, dict[str, Any]]):
        self._store = store

    def document(self, doc_id: str | None = None) -> FakeDocumentReference:
        return FakeDocumentReference(self._store, doc_id=doc_id)

    def where(self, field: str, op: str, value: Any) -> FakeQuery:
        return FakeQuery(self._store).where(field, op, value)


class FakeFirestoreClient:
    def __init__(self):
        self.collections: dict[str, dict[str, dict[str, Any]]] = {}

    def collection(self, name: str) -> FakeCollection:
        if name not in self.collections:
            self.collections[name] = {}
        return FakeCollection(self.collections[name])


@pytest.fixture()
def fake_db() -> FakeFirestoreClient:
    db = FakeFirestoreClient()
    set_firestore_client(db)
    yield db
    set_firestore_client(None)


@pytest.fixture()
def app(fake_db: FakeFirestoreClient):
    application = create_app("testing")
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def mock_firebase_auth(monkeypatch):
    """Mock Firebase ID token verification for tests."""

    def _verify(token: str):
        if token == "valid-token-user-1":
            return {"uid": "user-1", "email": "user1@example.com"}
        if token == "valid-token-user-2":
            return {"uid": "user-2", "email": "user2@example.com"}
        raise ValueError("Invalid token")

    monkeypatch.setattr("app.auth.verify_firebase_token", _verify)


@pytest.fixture()
def mock_fcm_send(monkeypatch):
    """Mock Firebase Cloud Messaging send call."""
    sent_messages: list[Any] = []

    def _send(message):
        sent_messages.append(message)
        return f"projects/test-moatok-project/messages/msg-{len(sent_messages)}"

    monkeypatch.setattr("firebase_admin.messaging.send", _send)
    return sent_messages
