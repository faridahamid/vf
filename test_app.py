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
    data = {'token': 'test-token', 'submission_id': str(uuid4()), 'question_id': 'experience', 'rating': '4', 'participant_name': 'Test Participant', 'consent': 'true'}
    data.update(overrides)
    return client.post('/api/answer', data=data, files={'audio': ('a.webm', b'test recording bytes', 'audio/webm;codecs=opus')})

def test_static_and_config(setup):
    client, _, _ = setup
    assert client.get('/').status_code == 200
    assert '<html lang="en"' in client.get('/').text
    assert client.get('/styles.css').status_code == 200
    assert client.get('/event-artwork.png').status_code == 200
    assert client.get('/admin').status_code == 200
    assert client.get('/api/config').json()['questions'][0]['rating'] is True
    assert 'test-badge' not in client.get('/').text
    assert 'mic-help' not in client.get('/').text
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
    result = client.get('/api/admin/export?include_tests=false', headers=headers)
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
    result = client.post('/api/answer', data={'token':'test-token','question_id':'experience','rating':'4','submission_id':str(uuid4()),'participant_name':'Test Participant','consent':'true'}, files={'audio':('recording', b'test audio',ctype)})
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
    missing = client.post('/api/answer', data={'token':'test-token','question_id':'experience','rating':'4','submission_id':str(uuid4()),'consent':'true'},files={'audio':('a.webm',b'test','audio/webm')})
    assert missing.status_code == 422


@pytest.mark.parametrize('rating', ['0', '6', '-1', 'abc', '1.5'])
def test_invalid_ratings(setup, rating):
    client, db, _ = setup
    assert send(client, rating=rating).status_code in (400, 422)
    assert not db.rows and not db.uploads


def test_rating_only_does_not_call_transcription_or_storage(setup):
    client, db, calls = setup
    payload = {'token':'test-token','question_id':'experience','submission_id':str(uuid4()),'participant_name':'Rating only','consent':'true','rating':'5'}
    result = client.post('/api/answer', data=payload)
    assert result.status_code == 200 and not result.json()['audio_saved']
    assert db.rows[0]['rating'] == 5 and db.rows[0]['audio_path'] is None
    assert not calls and not db.uploads
    del payload['rating']; payload['submission_id'] = str(uuid4())
    assert client.post('/api/answer',data=payload).status_code == 400


def test_old_open_page_can_still_submit(setup):
    client, db, _ = setup
    assert send(client, question_id='q1', rating=None).status_code == 200
    assert db.rows[0]['question_id'] == 'q1'


def test_delete_removes_audio_and_database_requires_admin(setup):
    client, db, _ = setup
    rid = send(client).json()['id']; path = db.rows[0]['audio_path']
    assert client.delete('/api/admin/responses/' + rid).status_code == 401
    assert path in db.files
    headers = {'X-Admin-Password':'test-admin'}
    result = client.delete('/api/admin/responses/' + rid,headers=headers)
    assert result.status_code == 200 and result.json()['deleted']
    assert not db.rows and path not in db.files
    assert client.delete('/api/admin/responses/' + rid,headers=headers).status_code == 200


@pytest.mark.parametrize('failure', ['fail_remove','fail_delete'])
def test_failed_delete_keeps_row_for_retry(setup, failure):
    client, db, _ = setup
    rid=send(client).json()['id']; setattr(db, failure, True)
    headers={'X-Admin-Password':'test-admin'}
    assert client.delete('/api/admin/responses/'+rid,headers=headers).status_code == 502
    assert len(db.rows) == 1
    setattr(db,failure,False)
    assert client.delete('/api/admin/responses/'+rid,headers=headers).status_code == 200
    assert not db.rows and not db.files


def test_concurrent_participants_keep_their_own_data(setup, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading, time
    _, db, _ = setup
    active=0; maximum=0; guard=threading.Lock()
    def transcribe(data, ctype, lang):
        nonlocal active, maximum
        with guard: active+=1; maximum=max(maximum,active)
        time.sleep(.03)
        with guard: active-=1
        return data.decode(), 'test-model'
    monkeypatch.setattr(main,'transcribe_audio',transcribe)
    def submit(n):
        with TestClient(main.app) as client:
            payload={'token':'test-token','question_id':'experience','rating':str(n%5+1),'submission_id':str(uuid4()),'participant_name':f'Participant {n}','consent':'true'}
            result=client.post('/api/answer',data=payload,files={'audio':('test.webm',f'Voice {n}'.encode(),'audio/webm')} if n%2 else None)
            return n,result
    with ThreadPoolExecutor(max_workers=20) as pool: results=list(pool.map(submit,range(40)))
    assert len(db.rows)==40 and maximum>1
    for n,result in results:
        assert result.status_code==200
        row=next(r for r in db.rows if r['id']==result.json()['id'])
        assert row['participant_name']==f'Participant {n}' and row['rating']==n%5+1
        assert row['transcript']==(f'Voice {n}' if n%2 else '')
    assert len(db.files)==20


def test_concurrent_retries_only_create_one_response(setup):
    from concurrent.futures import ThreadPoolExecutor
    _, db, calls = setup; rid=str(uuid4())
    def submit(_):
        with TestClient(main.app) as client: return send(client,submission_id=rid)
    with ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(submit,range(8)))
    assert all(r.status_code==200 for r in results)
    assert len(db.rows)==len(db.uploads)==len(calls)==1


def test_delete_during_transcription_does_not_resurrect_feedback(setup, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    client,db,_=setup; started=threading.Event(); proceed=threading.Event(); rid=str(uuid4())
    def transcribe(*args):
        started.set(); assert proceed.wait(5); return 'late transcript','test-model'
    monkeypatch.setattr(main,'transcribe_audio',transcribe)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(send,client,submission_id=rid)
        assert started.wait(5)
        assert client.delete('/api/admin/responses/'+rid,headers={'X-Admin-Password':'test-admin'}).status_code==200
        proceed.set(); assert future.result().status_code==410
    assert not db.rows and not db.files
