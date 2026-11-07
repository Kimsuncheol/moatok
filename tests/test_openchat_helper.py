import importlib.util
import uuid
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('helper', Path(__file__).parents[1] / 'frontend/public/openchat-helper.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def payload():
    return {'version': 1, 'jobs': [{'id': str(uuid.uuid4()), 'room': 'Exact room', 'message': 'Hello', 'due': '2030-01-01T00:00:00+00:00'}]}


def test_reimport_restart_and_uncertain_send_never_retry(tmp_path):
    db = helper.connect(tmp_path / 'jobs.sqlite')
    data = payload()
    helper.import_jobs(db, data)
    calls = []
    def fail(*args):
        calls.append(args)
        raise TimeoutError()
    now = 1893456000
    helper.tick(db, fail, now)
    helper.import_jobs(db, data)
    db.close()
    db = helper.connect(tmp_path / 'jobs.sqlite')
    helper.tick(db, fail, now + 1)
    assert len(calls) == 1
    assert db.execute('SELECT status FROM jobs').fetchone()[0] == 'review_required'


def test_late_jobs_not_sent(tmp_path):
    db = helper.connect(tmp_path / 'jobs.sqlite')
    helper.import_jobs(db, payload())
    calls = []
    helper.tick(db, lambda *args: calls.append(args), 1893456301)
    assert calls == []
    assert db.execute('SELECT status FROM jobs').fetchone()[0] == 'missed'


def test_immutable_identity_and_atomic_import(tmp_path):
    db = helper.connect(tmp_path / 'jobs.sqlite')
    data = payload()
    helper.import_jobs(db, data)
    data['jobs'][0]['room'] = 'Other room'
    with pytest.raises(ValueError):
        helper.import_jobs(db, data)
    assert db.execute('SELECT room FROM jobs').fetchone()[0] == 'Exact room'
