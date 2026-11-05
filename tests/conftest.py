"""Pytest fixtures and in-memory Firestore/Firebase mocks for automated testing."""

from __future__ import annotations

import threading
from typing import Any, Callable
import uuid
from firebase_admin import auth as firebase_auth
from google.api_core.exceptions import AlreadyExists
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
    def __init__(
        self,
        client: FakeFirestoreClient,
        collection_path: str,
        store: dict[str, dict[str, Any]],
        doc_id: str | None = None,
    ):
        self._client = client
        self._collection_path = collection_path
        self._store = store
        self.id = doc_id or f"doc-{uuid.uuid4().hex[:10]}"

    @property
    def path(self) -> str:
        return f"{self._collection_path}/{self.id}"

    def collection(self, name: str) -> FakeCollection:
        sub_path = f"{self.path}/{name}"
        return self._client.collection(sub_path)

    def create(self, data: dict[str, Any]) -> None:
        with self._client._lock:
            if self.id in self._store:
                raise AlreadyExists(f"Document {self.path} already exists")
            self._store[self.id] = data.copy()

    def set(self, data: dict[str, Any], merge: bool = False) -> None:
        with self._client._lock:
            if merge and self.id in self._store:
                merged = self._store[self.id].copy()
                merged.update(data)
                self._store[self.id] = merged
            else:
                self._store[self.id] = data.copy()

    def update(self, updates: dict[str, Any]) -> None:
        with self._client._lock:
            if self.id not in self._store:
                raise KeyError(f"Document {self.path} does not exist")
            self._store[self.id].update(updates)

    def delete(self) -> None:
        with self._client._lock:
            self._store.pop(self.id, None)

    def get(self, transaction: Any = None) -> FakeDocumentSnapshot:
        with self._client._lock:
            return FakeDocumentSnapshot(self.id, self._store.get(self.id))


class FakeQuery:
    def __init__(
        self,
        client: FakeFirestoreClient,
        store: dict[str, dict[str, Any]],
        filters: list[tuple[str, str, Any]] | None = None,
        limit_val: int | None = None,
    ):
        self._client = client
        self._store = store
        self._filters = filters or []
        self._limit = limit_val

    def where(self, field: str, op: str, value: Any) -> FakeQuery:
        return FakeQuery(
            self._client,
            self._store,
            filters=[*self._filters, (field, op, value)],
            limit_val=self._limit,
        )

    def limit(self, count: int) -> FakeQuery:
        return FakeQuery(
            self._client,
            self._store,
            filters=self._filters,
            limit_val=count,
        )

    def stream(self) -> list[FakeDocumentSnapshot]:
        with self._client._lock:
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
    def __init__(
        self,
        client: FakeFirestoreClient,
        path: str,
        store: dict[str, dict[str, Any]],
    ):
        self._client = client
        self._path = path
        self._store = store

    def document(self, doc_id: str | None = None) -> FakeDocumentReference:
        return FakeDocumentReference(
            self._client, self._path, self._store, doc_id=doc_id
        )

    def where(self, field: str, op: str, value: Any) -> FakeQuery:
        return FakeQuery(self._client, self._store).where(field, op, value)

    def limit(self, count: int) -> FakeQuery:
        return FakeQuery(self._client, self._store, limit_val=count)

    def stream(self) -> list[FakeDocumentSnapshot]:
        return FakeQuery(self._client, self._store).stream()


class FakeTransaction:
    """In-memory transaction compatible with `@google.cloud.firestore.transactional`."""

    def __init__(self, client: FakeFirestoreClient, max_attempts: int = 5):
        self._client = client
        self._max_attempts = max_attempts
        self._read_only = False
        self._id = b"fake-txn-id"
        self._staged_ops: list[Callable[[], None]] = []
        self._lock_held = False

    def _clean_up(self) -> None:
        self._staged_ops.clear()
        if self._lock_held:
            self._client._lock.release()
            self._lock_held = False

    def _begin(self, retry_id: bytes | None = None) -> None:
        self._client._lock.acquire()
        self._lock_held = True
        self._staged_ops.clear()

    def _commit(self) -> list[Any]:
        try:
            for op in self._staged_ops:
                op()
            self._staged_ops.clear()
            return []
        finally:
            if self._lock_held:
                self._client._lock.release()
                self._lock_held = False

    def _rollback(self) -> None:
        self._staged_ops.clear()
        if self._lock_held:
            self._client._lock.release()
            self._lock_held = False

    def get(self, ref: FakeDocumentReference) -> FakeDocumentSnapshot:
        return ref.get(transaction=self)

    def create(self, reference: FakeDocumentReference, document_data: dict[str, Any]) -> None:
        data_copy = document_data.copy()
        self._staged_ops.append(lambda: reference.create(data_copy))

    def set(
        self,
        reference: FakeDocumentReference,
        document_data: dict[str, Any],
        merge: bool = False,
    ) -> None:
        data_copy = document_data.copy()
        self._staged_ops.append(lambda: reference.set(data_copy, merge=merge))

    def update(self, reference: FakeDocumentReference, field_updates: dict[str, Any]) -> None:
        updates_copy = field_updates.copy()
        self._staged_ops.append(lambda: reference.update(updates_copy))

    def delete(self, reference: FakeDocumentReference) -> None:
        self._staged_ops.append(reference.delete)


class FakeFirestoreClient:
    def __init__(self):
        self.collections: dict[str, dict[str, dict[str, Any]]] = {}
        self._lock = threading.RLock()

    def collection(self, name: str) -> FakeCollection:
        with self._lock:
            if name not in self.collections:
                self.collections[name] = {}
            return FakeCollection(self, name, self.collections[name])

    def transaction(self, **kwargs: Any) -> FakeTransaction:
        max_attempts = int(kwargs.get("max_attempts", 5))
        return FakeTransaction(self, max_attempts=max_attempts)


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
        if token == "valid-token-admin":
            return {
                "uid": "admin-1",
                "email": "admin@example.com",
                "admin": True,
            }
        if token == "expired-token":
            raise firebase_auth.ExpiredIdTokenError("Token expired", cause=None)
        if token == "revoked-token":
            raise firebase_auth.RevokedIdTokenError("Token revoked")
        if token == "disabled-user-token":
            raise firebase_auth.UserDisabledError("User disabled")
        raise firebase_auth.InvalidIdTokenError("Invalid token")

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
