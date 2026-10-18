import io
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pypdf import PdfReader
import config
import main
import reporting
from test_app import setup


def sample_rows():
    rows = []
    for role in config.AUDIENCES:
        for i in range(12):
            scores = {q['id']: ('Maybe' if q.get('options') == ['Yes', 'No', 'Maybe'] else 'Yes' if 'options' in q else 3 + i % 3) for q in config.audience_questions(role)}
            is_form = role in ('speaker', 'volunteer')
            rows.append({'id': str(uuid4()), 'created_at': '2026-10-18T12:00:00Z', 'participant_name': 'Private Person', 'ptype':role,
                         'question_id': role + '_form' if is_form else config.audience_questions(role)[0]['id'],
                         'rating': 3 + i % 3, 'transcript': 'Private Person: Great guidance. More time for questions please.',
                         'transcript_raw': json.dumps({'ratings':scores, 'workshop':'NASA Data'}) if is_form else ''})
    return rows


def fake_notes(stats):
    notes = {}
    for role, stat in stats.items():
        notes[role] = {'summary': 'Feedback reflects positive guidance alongside opportunities to allow more time for audience questions. These findings describe the submitted feedback only.' if stat['responses'] else 'No feedback collected.',
                       'strengths':[{'text':'Respondents appreciated the guidance and practical support.', 'evidence':['C1']}] if stat['comment_count'] else [],
                       'improvements':[{'text':'One submitted comment asks for more time for questions; review whether the session agenda allows enough discussion.', 'evidence':['C1']}] if stat['comment_count'] else [],
                       'actions':['Consider reserving a dedicated question period in each session.', 'Ask the next audience whether the revised timing meets their needs.'] if stat['responses'] else []}
    return notes


def sample_bundle():
    rows = sample_rows()
    stats = reporting.build_statistics(rows, main.feedback_summary)
    return {'snapshot':reporting.fingerprint(rows), 'generated_at':'2026-10-18T12:00:00+00:00', 'model':reporting.MODEL,
            'usage':{'input_tokens':0,'output_tokens':0,'estimated_usd':0},'test_run':True,'statistics':stats,'analysis':fake_notes(stats)}


class Storage:
    def __init__(self): self.files = {}; self.fail_pdf = False
    def download(self, path):
        if path not in self.files:
            from storage3.exceptions import StorageApiError
            raise StorageApiError('Object not found', 'not_found', 404)
        return self.files[path]
    def upload(self, path, data, options):
        if self.fail_pdf and path.endswith('report.pdf'): raise RuntimeError('save failed')
        if path in self.files and options.get('upsert') != 'true': raise RuntimeError('already exists')
        self.files[path] = data


def test_statistics_and_five_page_layout():
    bundle = sample_bundle()
    reporting.validate_notes(bundle['analysis'],bundle['statistics'])
    pdf = reporting.render_pdf(bundle)
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == 5
    for page, audience in zip(reader.pages, config.AUDIENCES.values()):
        assert audience['label'] in page.extract_text()
    assert 'Private Person' not in json.dumps(bundle['statistics'])
    assert bundle['statistics']['volunteer']['rating_count'] == 120
    assert bundle['statistics']['volunteer']['average'] == 4
    empty = reporting.build_statistics([],main.feedback_summary)
    bundle.update(statistics=empty,analysis=fake_notes(empty))
    assert len(PdfReader(io.BytesIO(reporting.render_pdf(bundle))).pages)==5


def test_report_auth_cache_staleness_and_repeated_downloads(setup,monkeypatch):
    client, db, _ = setup
    store = Storage(); calls=[]
    monkeypatch.setenv('OPENAI_API_KEY','fake-test-key')
    monkeypatch.setattr(main,'report_store',lambda:store)
    monkeypatch.setattr(main,'OpenAI',lambda **kwargs:None)
    def fake_analyze(stats, client, checkpoint=None):
        calls.append(1)
        return fake_notes(stats), {'input_tokens':100,'output_tokens':50,'estimated_usd':.001}
    monkeypatch.setattr(reporting,'analyze',fake_analyze)
    db.rows = sample_rows()
    headers={'X-Admin-Password':'test-admin'}
    assert client.get('/api/admin/report').status_code==401
    state=client.get('/api/admin/report',headers=headers).json()
    assert state['saved'] is None and not calls
    body={'snapshot':state['snapshot'],'confirm_ai':'true','test_run':'true'}
    assert client.post('/api/admin/report',headers=headers,data={**body,'confirm_ai':'false'}).status_code==400
    assert client.post('/api/admin/report',headers=headers,data=body).json()['saved']
    assert client.post('/api/admin/report',headers=headers,data=body).json()['cached']
    assert len(calls)==1
    for _ in range(2):
        downloaded=client.get('/api/admin/report/download',headers=headers)
        assert downloaded.status_code==200 and downloaded.content.startswith(b'%PDF')
    assert len(calls)==1
    assert not client.get('/api/admin/report',headers=headers).json()['changed']
    db.rows[0]['transcript']='Changed feedback'
    assert client.get('/api/admin/report',headers=headers).json()['changed']
    assert client.post('/api/admin/report',headers=headers,data=body).status_code==409
    assert len(calls)==1


def test_pdf_retry_uses_saved_analysis_and_failed_ai_is_not_retried(setup,monkeypatch):
    client,db,_=setup;db.rows=sample_rows();store=Storage();calls=[]
    monkeypatch.setenv('OPENAI_API_KEY','fake-test-key')
    monkeypatch.setattr(main,'report_store',lambda:store)
    monkeypatch.setattr(main,'OpenAI',lambda **kwargs:None)
    def analyze(stats,client,checkpoint=None):
        calls.append(1);return fake_notes(stats),{'input_tokens':1,'output_tokens':1,'estimated_usd':.00001}
    monkeypatch.setattr(reporting,'analyze',analyze)
    headers={'X-Admin-Password':'test-admin'}
    body={'snapshot':reporting.fingerprint(db.rows),'confirm_ai':'true'}
    store.fail_pdf=True
    assert client.post('/api/admin/report',headers=headers,data=body).status_code==502
    store.fail_pdf=False
    assert client.post('/api/admin/report',headers=headers,data=body).json()['saved']
    assert len(calls)==1
    db.rows[0]['transcript']='A new snapshot'
    body['snapshot']=reporting.fingerprint(db.rows)
    def fail(*args,**kwargs): calls.append(1);raise RuntimeError('network timed out')
    monkeypatch.setattr(reporting,'analyze',fail)
    assert client.post('/api/admin/report',headers=headers,data=body).status_code==502
    assert client.post('/api/admin/report',headers=headers,data=body).status_code==409
    assert len(calls)==2


def test_model_is_one_call_bounded_and_evidence_checked():
    stats=reporting.build_statistics(sample_rows(),main.feedback_summary)
    calls=[]
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status='completed',output_text=json.dumps(fake_notes(stats)),usage=SimpleNamespace(input_tokens=300,output_tokens=200))
    saved=[]
    notes,usage=reporting.analyze(stats,SimpleNamespace(responses=SimpleNamespace(create=create)),checkpoint=saved.append)
    assert len(calls)==1 and saved and not calls[0]['store']
    assert calls[0]['max_output_tokens']==6000
    notes['speaker']['strengths'][0]['evidence']=['made-up-ref']
    with pytest.raises(ValueError):reporting.validate_notes(notes,stats)
    with pytest.raises(ValueError):reporting.analysis_input({'oversized':'x'*300000})
