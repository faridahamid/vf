"""Explicit one-time live report verification. Never imported by automated tests."""
import json
import sys
from pathlib import Path
from urllib.parse import quote
from fastapi.testclient import TestClient
import main

if __name__ == '__main__':
    if sys.argv[1:] != ['--run-live-once']:
        raise SystemExit('Pass --run-live-once explicitly. This can consume API credits once.')
    out = Path(__file__).resolve().parent.parent / 'output' / 'pdf'
    out.mkdir(parents=True, exist_ok=True)
    receipt = out / 'live-report-verification.json'
    headers = {'X-Admin-Password':quote(main.setting('ADMIN_PASSWORD'),safe=''), 'X-Admin-Password-Encoding':'percent-utf8'}
    client = TestClient(main.app)
    status = client.get('/api/admin/report', headers=headers)
    if status.status_code != 200:
        raise SystemExit('Report status failed: ' + status.text)
    state = status.json()
    if receipt.exists():
        raise SystemExit('A live verification receipt already exists. No new AI call was made.')
    if not state['can_generate']:
        raise SystemExit('No live call made: report dataset is empty or exceeds the input limit.')
    # Durable local guard is written before the only generation request.
    receipt.write_text(json.dumps({'status':'attempt-started','snapshot':state['snapshot']}),encoding='utf-8')
    print('Starting one live report generation for',state['responses'],'submissions. Estimated ceiling USD',state['estimated_max_usd'],flush=True)
    result = client.post('/api/admin/report', headers=headers, data={'snapshot':state['snapshot'],'confirm_ai':'true','test_run':'true'})
    if result.status_code != 200:
        receipt.write_text(json.dumps({'status':'failed-no-auto-retry','snapshot':state['snapshot'],'detail':result.json()}),encoding='utf-8')
        raise SystemExit('Single live attempt failed: ' + result.text)
    receipt.write_text(json.dumps(result.json(),indent=2),encoding='utf-8')
    for i in range(2):
        pdf = client.get('/api/admin/report/download',headers=headers)
        if pdf.status_code != 200 or not pdf.content.startswith(b'%PDF'):
            raise SystemExit('Saved report download failed.')
        (out / 'nasa-cairo-audience-analysis.pdf').write_bytes(pdf.content)
    print(json.dumps(result.json()),flush=True)
    print('Saved PDF downloaded twice without generating again.',flush=True)
