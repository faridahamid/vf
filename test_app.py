import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fastapi.testclient import TestClient
import main

class FakeQuery:
    def __init__(self, db):
        self.db = db; self.filters = []; self.window = (0, 999); self.pending = None; self.changes = None; self.removing = False
    def select(self, fields): return self
    def eq(self, key, value): self.filters.append((key, value)); return self
    def order(self, *args, **kwargs): return self
    def range(self, start, end): self.window = (start, end); return self
    def upsert(self, row, **kwargs): self.pending = row; return self
    def update(self, changes): self.changes = changes; return self
    def delete(self): self.removing = True; return self
    def execute(self):
        with self.db.lock:
            if self.pending is not None:
                if self.db.fail_insert: raise RuntimeError('insert unavailable')
                if not any(r['id'] == self.pending['id'] for r in self.db.rows):
                    self.db.rows.append({**self.pending, 'created_at': '2026-10-01T12:00:00Z'})
            matches = [r for r in self.db.rows if all(r.get(k) == v for k,v in self.filters)]
            if self.changes is not None:
                for row in matches: row.update(self.changes)
            if self.removing:
                if self.db.fail_delete: raise RuntimeError('delete unavailable')
                self.db.rows = [r for r in self.db.rows if r not in matches]
            return SimpleNamespace(data=[r.copy() for r in matches][self.window[0]:self.window[1]+1])


class FakeDB:
    def __init__(self):
        import threading
        self.lock = threading.Lock(); self.rows = []; self.uploads = []; self.removed = []; self.files = {}
        self.storage = self; self.fail_insert = False; self.fail_remove = False; self.fail_delete = False
    def table(self, name): return FakeQuery(self)
    def from_(self, name): return self
    def upload(self, *args):
        with self.lock:
            self.uploads.append(args); self.files[args[0]] = args[1]
    def remove(self, paths):
        with self.lock:
            if self.fail_remove: raise RuntimeError('storage unavailable')
            for path in paths: self.files.pop(path, None); self.removed.append(path)
        return []
    def create_signed_url(self, path, seconds): return {'signedURL': 'https://example.test/audio'}

@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setattr(main.config, 'PROVIDER', 'openai')
    monkeypatch.setattr(main, 'last_transcription_error', None)
    monkeypatch.setenv('EVENT_TOKEN', 'test-token')
    monkeypatch.setenv('ADMIN_PASSWORD', 'test-admin')
    db = FakeDB(); calls = []
    monkeypatch.setattr(main, 'database', lambda: db)
    def transcribe(**kwargs): calls.append(kwargs); return SimpleNamespace(text='Great workshop و المينتور ساعدنا')
    monkeypatch.setattr(main, 'transcriber', lambda: SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=transcribe))))
    main.hits.clear()
    return TestClient(main.app), db, calls


def send(client, **overrides):
    data = dict(token='test-token', submission_id=str(uuid4()), question_id='experience', rating='4', participant_name='Test Participant', consent='true', feedback_text='Great event شكراً')
    data.update(overrides)
    return client.post('/api/answer', data=data)


def test_final_text_only_and_retry(setup):
    client, db, calls = setup
    rid = str(uuid4())
    assert send(client, submission_id=rid).status_code == 200
    assert send(client, submission_id=rid).status_code == 200
    assert len(db.rows) == 1 and not db.uploads and not calls
    assert db.rows[0]['transcript'] == 'Great event شكراً'
    assert db.rows[0]['audio_path'] is None
    assert db.rows[0]['transcript_raw'] == ''

@pytest.mark.parametrize('changes,code', [({'token':'wrong'},403),({'rating':'0'},400),({'participant_name':'   '},400),({'consent':'false'},400),({'feedback_text':'x'*10001},400)])
def test_validation(setup, changes, code):
    client, db, _ = setup
    assert send(client, **changes).status_code == code
    assert not db.rows and not db.uploads


def test_rating_only_and_storage_retry(setup):
    client, db, calls = setup
    rid = str(uuid4()); db.fail_insert = True
    assert send(client, submission_id=rid, feedback_text='').status_code == 502
    db.fail_insert = False
    assert send(client, submission_id=rid, feedback_text='').status_code == 200
    assert not db.uploads and not calls


def transcribe(client, token='test-token', body=b'audio', mime='audio/webm'):
    return client.post('/api/transcribe', data={'token':token}, files={'audio':('a.webm',body,mime)})


def test_transcription_never_saves(setup):
    client, db, calls = setup
    response = transcribe(client)
    assert response.status_code == 200 and response.json()['transcript']
    assert 'language' not in calls[0]
    assert not db.rows and not db.uploads

@pytest.mark.parametrize('kwargs,code', [({'token':'bad'},403),({'body':b''},400),({'mime':'text/plain'},415),({'body':b'x'*4000001},413)])
def test_transcription_validation(setup, kwargs, code):
    client, db, calls = setup
    assert transcribe(client, **kwargs).status_code == code
    assert not db.rows and not db.uploads and not calls


def test_provider_failure_then_typed_feedback(setup, monkeypatch):
    client, db, _ = setup
    def fail(*args): raise RuntimeError('unavailable')
    monkeypatch.setattr(main, 'transcribe_audio', fail)
    assert transcribe(client).status_code == 502
    assert not db.rows and not db.uploads
    assert send(client).status_code == 200


def test_old_audio_submission_rejected(setup):
    client, db, calls = setup
    response = client.post('/api/answer', data=dict(token='test-token',submission_id=str(uuid4()),question_id='experience',participant_name='Test',rating=4,consent='true'),files={'audio':('a.webm',b'audio','audio/webm')})
    assert response.status_code == 409
    assert not db.rows and not db.uploads and not calls


def test_admin_export_delete_legacy_audio(setup):
    client, db, _ = setup
    send(client)
    row = db.rows[0]; row['audio_path'] = 'q1/old.webm'; db.files[row['audio_path']] = b'old'
    headers = {'X-Admin-Password':'test-admin'}
    assert client.get('/api/admin/responses').status_code == 401
    assert client.get('/api/admin/responses',headers=headers).json()[0]['audio_url']
    assert 'Great event' in client.get('/api/admin/export',headers=headers).text
    db.fail_remove = True
    assert client.delete('/api/admin/responses/'+row['id'],headers=headers).status_code == 502
    assert db.rows
    db.fail_remove = False
    assert client.delete('/api/admin/responses/'+row['id'],headers=headers).status_code == 200
    assert not db.rows and not db.files


def test_concurrent_text_submissions(setup):
    from concurrent.futures import ThreadPoolExecutor
    client, db, calls = setup
    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(lambda n: send(client, participant_name=str(n), feedback_text='Text '+str(n)), range(40)))
    assert all(r.status_code == 200 for r in results)
    assert len(db.rows) == 40
    assert all(r['transcript'] == 'Text '+r['participant_name'] for r in db.rows)
    assert not db.uploads and not calls
