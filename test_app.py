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

@pytest.mark.parametrize('role', ['participant','speaker','volunteer','mentor','judge'])
def test_audience_links_submission_and_question_binding(setup, role):
    client, db, calls = setup
    token = main.audience_tokens()[role]
    info = client.get('/api/config', params={'t': token}).json()
    assert info['audience'] == role and info['intro']
    question_id = info['questions'][0]['id']
    assert send(client, token=token, question_id=question_id, ptype='forged').status_code == 200
    assert db.rows[0]['ptype'] == role and db.rows[0]['audio_path'] is None
    assert transcribe(client, token=token).status_code == 200
    assert not db.uploads
    if role != 'participant':
        assert send(client, token=token, question_id='experience').status_code == 400


def test_admin_links_and_filtered_export(setup):
    client, db, _ = setup
    assert client.get('/api/admin/links').status_code == 401
    headers={'X-Admin-Password':'test-admin'}
    links=client.get('/api/admin/links',headers=headers).json()
    assert len(links)==6 and len({x['path'] for x in links})==6
    assert links[0]['path']=='/?t=test-token'
    send(client, participant_name='Participant Example')
    for i in range(102):
        assert send(client,token=main.audience_tokens()['mentor'],question_id='mentor_experience',participant_name='Mentor Example').status_code==200
    page=client.get('/api/admin/responses?audience=mentor&offset=100',headers=headers).json()
    assert len(page)==2 and all(r['ptype']=='mentor' for r in page)
    csv=client.get('/api/admin/export?audience=mentor',headers=headers).text
    assert csv.count('Mentor Example')==102 and 'Participant Example' not in csv
    assert client.get('/api/admin/responses?audience=invalid',headers=headers).status_code==400
    assert client.get('/api/admin/export?audience=invalid',headers=headers).status_code==400
    assert client.get('/api/config?t=invalid').status_code==403


def form_scores(role):
    return {q['id']: ('Written answer' if q.get('type') == 'paragraph' else q['options'][0] if 'options' in q else 4)
            for q in main.config.audience_questions(role)}


@pytest.mark.parametrize('role', ['speaker', 'volunteer', 'attendee'])
def test_section_forms_atomic_required_paragraphs_validation_export(setup, role):
    import json, csv, io
    client, db, calls = setup
    token = main.audience_tokens()[role]
    info = client.get('/api/config', params={'t': token}).json()
    assert len({q['section'] for q in info['questions']}) == (4 if role == 'speaker' else 5)
    assert len(info['workshops']) == 14
    scores = form_scores(role)
    paragraphs = [q for q in info['questions'] if q.get('type') == 'paragraph']
    assert paragraphs and all(q['required'] is True for q in paragraphs)
    scores[paragraphs[0]['id']] = 'My edited transcript بالعربي'
    data = dict(token=token, question_id=role+'_form', workshop='NASA Data', speaker_name='Example speaker',
                ratings=json.dumps(scores), submission_id=str(uuid4()))
    assert send(client, **{**data, 'workshop': 'unknown'}).status_code == 400
    assert send(client, **{**data, 'ratings': '{}'}).status_code == 400
    if role != 'speaker':
        assert send(client, **{**data, 'speaker_name': ''}).status_code == 400
    numeric = next(q['id'] for q in info['questions'] if q.get('rating'))
    for bad in [None, True, 6, '4']:
        assert send(client, **{**data, 'ratings': json.dumps({**scores, numeric: bad})}).status_code == 400
    for bad in [None, '', '   ', '\n\t', 'x'*10001]:
        assert send(client, **{**data, 'ratings': json.dumps({**scores, paragraphs[0]['id']: bad})}).status_code == 400
    assert send(client, **data).status_code == 200
    assert send(client, **data).status_code == 200
    assert len(db.rows) == 1 and not calls
    assert json.loads(db.rows[0]['transcript_raw'])['ratings'] == scores
    headers = {'X-Admin-Password':'test-admin'}
    row = client.get('/api/admin/responses', headers=headers).json()[0]
    assert row['average_rating'] == 4 and row['scores'] == scores
    exported = client.get('/api/admin/export', params={'audience':role}, headers=headers).text
    table = list(csv.DictReader(io.StringIO(exported.lstrip('\ufeff'))))
    assert table[0][paragraphs[0]['en']] == 'My edited transcript بالعربي'
    assert table[0]['Speaker name'] == 'Example speaker'
    assert any(link['audience'] == 'attendee' for link in client.get('/api/admin/links',headers=headers).json())


def test_historical_forms_remain_readable():
    import json
    for role, questions in main.config.LEGACY_FORM_QUESTIONS.items():
        scores = {q['id']: (q['options'][0] if 'options' in q else 4) for q in questions}
        summary = main.feedback_summary({'question_id':role+'_form','transcript_raw':json.dumps({'ratings':scores,'workshop':'NASA Data'})})
        assert summary['average_rating'] == 4 and summary['scores'] == scores


@pytest.mark.parametrize('password', ['test-admin', 'كلمة سر آمنة', 'pass%20+word'])
def test_admin_password_header_encoding(setup, monkeypatch, password):
    from urllib.parse import quote
    client, _, _ = setup
    monkeypatch.setenv('ADMIN_PASSWORD', password)
    headers = {'X-Admin-Password': quote(password, safe=''), 'X-Admin-Password-Encoding': 'percent-utf8'}
    for path in ['/api/admin/responses', '/api/admin/links', '/api/admin/status', '/api/admin/export']:
        assert client.get(path, headers=headers).status_code == 200
    assert client.delete('/api/admin/responses/'+str(uuid4()), headers=headers).status_code == 200
    headers['X-Admin-Password'] = quote('كلمة غير صحيحة', safe='')
    assert client.get('/api/admin/responses', headers=headers).status_code == 401
    headers['X-Admin-Password'] = '%FF'
    assert client.get('/api/admin/responses', headers=headers).status_code == 401


def test_export_columns_match_selected_audience(setup):
    import csv, io
    client, _, _ = setup
    headers = {'X-Admin-Password': 'test-admin'}
    def columns(audience):
        text = client.get('/api/admin/export', params={'audience':audience}, headers=headers).text
        return next(csv.reader(io.StringIO(text.lstrip('\ufeff'))))
    speaker, volunteer, combined = columns('speaker'), columns('volunteer'), columns('')
    speaker_label = main.config.SPEAKER_QUESTIONS[0]['en']
    volunteer_label = main.config.VOLUNTEER_QUESTIONS[0]['en']
    assert speaker_label in speaker and speaker_label not in volunteer
    assert volunteer_label in volunteer and volunteer_label not in speaker
    assert speaker_label in combined and volunteer_label in combined

def test_general_participant_form_is_complete_without_workshop(setup):
    import json, csv, io
    client, db, _ = setup
    questions = main.config.audience_questions('participant')
    assert len(questions) == 14
    assert len({q['section'] for q in questions}) == 4
    scores = {q['id']: ('Written feedback' if q.get('type') == 'paragraph' else q['options'][-1] if 'options' in q else 4) for q in questions}
    for q in questions:
        if q.get('condition') and scores.get(q['condition']['id']) != q['condition']['value']:
            scores[q['id']] = None
    data = dict(question_id='participant_form', ratings=json.dumps(scores), feedback_text='')
    bad = {**scores, 'participant_highlight': '   '}
    assert send(client, **{**data, 'ratings': json.dumps(bad)}).status_code == 400
    assert send(client, **data).status_code == 200
    assert len(db.rows) == 1 and db.rows[0]['rating'] == 4
    summary = main.feedback_summary(db.rows[0])
    assert summary['scores'] == scores and summary['average_rating'] == 4
    exported = client.get('/api/admin/export?audience=participant', headers={'X-Admin-Password':'test-admin'}).text
    table = list(csv.DictReader(io.StringIO(exported.lstrip('\ufeff'))))
    assert table[0]['What did you enjoy most about the event?'] == 'Written feedback'
    assert table[0]['How helpful were the organizers when you needed assistance?'] == ''


@pytest.mark.parametrize('attended', ['Yes', 'No'])
def test_participant_attendance_controls_required_ratings(setup, attended):
    import json
    client, db, _ = setup
    questions = main.config.audience_questions('participant')
    scores = {q['id']: ('Useful event' if q.get('type') == 'paragraph' else attended if q.get('options') == ['Yes', 'No'] else q['options'][0] if 'options' in q else 4) for q in questions}
    for q in questions:
        if q.get('condition') and scores[q['condition']['id']] != q['condition']['value']:
            scores[q['id']] = None
    data = dict(question_id='participant_form',ratings=json.dumps(scores))
    assert send(client, **data).status_code == 200
    assert main.feedback_summary(db.rows[0])['average_rating'] == 4
    bad = {**scores, 'participant_vip': None if attended == 'Yes' else 4}
    assert send(client, **{**data,'ratings':json.dumps(bad)}).status_code == 400
