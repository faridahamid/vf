import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fastapi.testclient import TestClient
import main

class FakeDB:
    def __init__(self):
        self.rows = []; self.uploads = []; self.filters = []; self.window = (0, 999)
        self.storage = self; self.fail_insert = False
    def table(self, name):
        self.filters = []; self.window = (0, 999); self.pending = None; return self
    def select(self, fields): return self
    def eq(self, key, value): self.filters.append((key, value)); return self
    def order(self, *args, **kwargs): return self
    def range(self, start, end): self.window = (start, end); return self
    def upsert(self, row, **kwargs): self.pending = row; return self
    def execute(self):
        if self.pending is not None:
            if self.fail_insert: raise RuntimeError('insert unavailable')
            if not any(r['id'] == self.pending['id'] for r in self.rows):
                self.rows.append({**self.pending, 'created_at': '2026-09-29T12:00:00Z'})
        result = [r.copy() for r in self.rows if all(r.get(k) == v for k, v in self.filters)]
        return SimpleNamespace(data=result[self.window[0]:self.window[1]+1])
    def from_(self, name): return self
    def upload(self, *args): self.uploads.append(args)
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
    data = {'token': 'test-token', 'submission_id': str(uuid4()), 'question_id': 'q1', 'participant_name': 'Test Participant', 'consent': 'true'}
    data.update(overrides)
    return client.post('/api/answer', data=data, files={'audio': ('a.webm', b'test recording bytes', 'audio/webm;codecs=opus')})

def test_static_and_config(setup):
    client, _, _ = setup
    assert client.get('/').status_code == 200
    assert '<html lang="en"' in client.get('/').text
    assert client.get('/styles.css').status_code == 200
    assert client.get('/event-artwork.png').status_code == 200
    assert client.get('/admin').status_code == 200
    assert 'rating' not in client.get('/api/config').json()['questions'][0]
    assert client.get('/.env').status_code == 404

@pytest.mark.parametrize('overrides,code', [({'token':'wrong'},403), ({'consent':'false'},400), ({'participant_name':'   '},400), ({'participant_name':'x' * 121},400), ({'question_id':'unknown'},400)])
def test_invalid_requests(setup, overrides, code):
    client, db, _ = setup
    assert send(client, **overrides).status_code == code
    assert not db.uploads

def test_mixed_language_and_retry_are_one_response(setup):
    client, db, calls = setup; rid = str(uuid4())
    result = send(client, submission_id=rid)
    assert result.status_code == 200 and result.json()['saved']
    assert 'language' not in calls[0]
    assert db.rows[0]['lang'] == 'auto'
    assert db.rows[0]['participant_name'] == 'Test Participant'
    assert send(client, submission_id=rid).status_code == 200
    assert len(db.rows) == 1 and len(db.uploads) == 1

@pytest.mark.parametrize('language', ['en','ar'])
def test_legacy_language_field_does_not_force_language(setup, language):
    client, _, calls = setup
    assert send(client, lang=language).status_code == 200
    assert 'language' not in calls[0]

def test_transcription_failure_preserves_audio(setup, monkeypatch):
    client, db, _ = setup
    def fail(): raise RuntimeError('API unavailable')
    monkeypatch.setattr(main, 'transcriber', fail)
    result = send(client)
    assert result.status_code == 200
    assert not result.json()['transcript_available']
    assert db.rows[0]['audio_path'] and db.rows[0]['model'] is None

def test_db_failure_can_retry_same_id(setup):
    client, db, _ = setup; rid = str(uuid4()); db.fail_insert = True
    assert send(client, submission_id=rid).status_code == 502
    db.fail_insert = False
    assert send(client, submission_id=rid).status_code == 200
    assert len(db.rows) == 1
    assert db.uploads[0][0] == db.uploads[1][0]

def test_admin_export_all_pages_and_excel_safety(setup):
    client, db, _ = setup
    assert client.get('/api/admin/responses').status_code == 401
    assert client.get('/api/admin/export').status_code == 401
    db.rows = [{'id': str(uuid4()), 'created_at':'2026-09-29', 'participant_name':'سارة', 'question_id':'q1', 'ptype':'participant', 'lang':'mixed', 'transcript':'=1+1', 'transcript_raw':'شكراً', 'audio_path':'q1/example.webm', 'model':'test', 'is_test':False} for _ in range(1001)]
    db.rows.append({**db.rows[0], 'id':str(uuid4()), 'is_test':True})
    headers = {'X-Admin-Password':'test-admin'}
    result = client.get('/api/admin/export', headers=headers)
    assert result.content.startswith(b'\xef\xbb\xbf')
    assert len(result.text.splitlines()) == 1002
    assert "'=1+1" in result.text and 'شكراً' in result.text
    assert len(client.get('/api/admin/export?include_tests=true', headers=headers).text.splitlines()) == 1003
    assert len(client.get('/api/admin/responses', headers=headers).json()) == 100


@pytest.mark.parametrize('ctype,expected_mime', [('audio/webm','audio/webm'), ('audio/mp4','audio/m4a'), ('audio/wav','audio/wav')])
def test_gemini_transcribes_browser_audio(setup, monkeypatch, ctype, expected_mime):
    client, db, openai_calls = setup
    monkeypatch.setattr(main.config, 'PROVIDER', 'gemini')
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text='The mentors were helpful والمكان كان جميل')
    monkeypatch.setattr(main, 'gemini_transcriber', lambda: SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    result = client.post('/api/answer', data={'token':'test-token','question_id':'q1','submission_id':str(uuid4()),'participant_name':'Test Participant','consent':'true'}, files={'audio':('recording', b'test audio',ctype)})
    assert result.status_code == 200 and result.json()['transcript_available']
    assert calls[0]['contents'][0].inline_data.mime_type == expected_mime
    assert calls[0]['contents'][0].inline_data.data == b'test audio'
    assert 'mixed' in calls[0]['contents'][1]
    assert db.rows[0]['model'] == 'gemini:' + main.config.GEMINI_MODEL
    assert db.uploads[0][2]['content-type'] == ctype
    assert not openai_calls
    assert client.get('/api/config').json()['transcription_provider'] == 'Google Gemini'


def test_gemini_quota_failure_preserves_audio_without_paid_fallback(setup, monkeypatch):
    client, db, openai_calls = setup
    monkeypatch.setattr(main.config, 'PROVIDER', 'gemini')
    class QuotaError(Exception): code = 429
    def fail(): raise QuotaError()
    monkeypatch.setattr(main, 'gemini_transcriber', fail)
    result = send(client)
    assert result.status_code == 200 and not result.json()['transcript_available']
    assert db.rows[0]['audio_path'] and not openai_calls
    assert client.get('/api/admin/status').status_code == 401
    state = client.get('/api/admin/status', headers={'X-Admin-Password':'test-admin'}).json()
    assert state['provider'] == 'gemini' and 'quota' in state['last_error']
    assert 'API_KEY' not in str(state)


def test_name_is_required_and_trimmed(setup):
    client, db, _ = setup
    response = send(client, participant_name='  سارة Ahmed  ')
    assert response.status_code == 200
    assert db.rows[0]['participant_name'] == 'سارة Ahmed'
    headers = {'X-Admin-Password':'test-admin'}
    assert client.get('/api/admin/responses', headers=headers).json()[0]['participant_name'] == 'سارة Ahmed'
    export = client.get('/api/admin/export?include_tests=true', headers=headers).text
    assert 'participant_name' in export and 'سارة Ahmed' in export
    missing = client.post('/api/answer', data={'token':'test-token','question_id':'q1','submission_id':str(uuid4()),'consent':'true'},files={'audio':('a.webm',b'test','audio/webm')})
    assert missing.status_code == 422
