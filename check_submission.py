"""Optional integration smoke test: creates ONE clearly marked test recording."""
import io
import json
import math
import struct
import wave
from pathlib import Path
from uuid import uuid4
import httpx
import main

if not main.IS_TEST:
    raise SystemExit('Refusing integration check while IS_TEST=false.')
with httpx.Client(base_url='http://localhost:8000', timeout=120) as client:
    if not client.get('/api/config').json()['is_test']:
        raise SystemExit('Running server is not in test mode.')
    audio = io.BytesIO()
    with wave.open(audio, 'wb') as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(16000)
        out.writeframes(b''.join(struct.pack('<h', int(800 * math.sin(2*math.pi*440*n/16000))) for n in range(16000)))
    rid = str(uuid4())
    response = client.post('/api/answer', data={
        'token': main.setting('EVENT_TOKEN'), 'question_id':'q1', 'submission_id':rid,
        'participant_name':'Setup test', 'consent':'true'
    }, files={'audio':('setup-tone.wav',audio.getvalue(),'audio/wav')})
    print('Submission HTTP status:', response.status_code)
    result = response.json()
    if response.status_code != 200:
        print('Submission failed:', result.get('detail', 'unknown'))
        raise SystemExit(1)
    print('Audio saved:', result.get('saved'))
    print('Transcript available:', result.get('transcript_available'))
    headers = {'X-Admin-Password':main.setting('ADMIN_PASSWORD')}
    rows = client.get('/api/admin/responses', headers=headers)
    row = next((r for r in rows.json() if r['id'] == rid), None)
    assert row and row['is_test'], 'Test response missing from admin API'
    print('Test response visible in dashboard:', True)
    assert row.get('audio_url'), 'Audio playback URL missing'
    download = httpx.get(row['audio_url'], timeout=30)
    assert download.status_code == 200 and download.content == audio.getvalue()
    print('Signed audio playback download matches original:', True)
    csv = client.get('/api/admin/export?include_tests=true', headers=headers)
    assert csv.status_code == 200 and rid in csv.text
    print('Test response included in CSV:', True)
    print('Test reference:', rid)
