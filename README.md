# NASA Space Apps Cairo — voice feedback

An English interface using the supplied “One Spark, Infinite Impact” artwork. Participants answer the question by recording up to 90 seconds in English, Arabic, or a mixture. No numerical ratings and no typed-answer flow.

The participant form now asks only for a name before recording; there are no role or language selectors.

## Start on this Windows laptop

1. Open `vf/.env` in your editor. Keep real keys in this file only.
2. Choose a transcription provider as described below. On September 29, 2026, the previous OpenAI key returned `invalid_api_key` (401); it exactly matched the key in the Downloads Lumen project. The API dashboard row later supplied by the owner showed that key (`lumin2`) as **Revoked**, explaining the authentication failure. Audio storage was verified independently of transcription.
3. Your existing Supabase bucket is named **Audio** (capital A), and it is private. `AUDIO_BUCKET=Audio` has been added to your local `.env`; bucket names are case sensitive. The responses table was reachable.
4. Double-click `Start-feedback.cmd` in the project folder. It starts the server and opens the correct localhost URL with your event token. Keep the terminal open; Ctrl+C stops the server. If port 8000 is already running, use that server or stop it before starting another.
5. Allow the browser's microphone permission. Enter your name, record in English, Arabic, or both, stop, listen, check the consent box, then send.
6. Open http://localhost:8000/admin. Use `ADMIN_PASSWORD` from `.env`. “Include test recordings” starts checked so laptop tests are visible.

## OpenAI or Gemini: change providers without losing feedback

For Gemini testing, create a key at https://aistudio.google.com/apikey in a project on Google's free tier. Save these settings in `vf/.env`:

```dotenv
TRANSCRIPTION_PROVIDER=gemini
GEMINI_API_KEY=your-actual-gemini-key
GEMINI_MODEL=gemini-2.5-flash
```

Restart the server after saving. Gemini 2.5 Flash currently has a free tier subject to quotas. Whether requests are free depends on your Google API project's plan; the model name alone does not guarantee free requests. The app never falls back automatically to a paid OpenAI request. Google states that free-tier submissions may be used to improve its products; use non-personal test recordings. Review data handling before collecting real participant recordings.

To switch back, keep the Gemini settings and change only:

```dotenv
TRANSCRIPTION_PROVIDER=openai
OPENAI_API_KEY=your-valid-openai-key
TRANSCRIBE_MODEL=gpt-4o-transcribe
```

Restart the server. Existing feedback and audio stay in Supabase. The dashboard and CSV work with either provider; Gemini rows store `gemini:<model-name>` in the existing `model` column. The interface names the provider in the consent text. Failed transcripts are not automatically retried after switching providers.

Official Google documentation:
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/api-key
- https://ai.google.dev/gemini-api/docs/generate-content/audio

## Verified live storage test

A one-second generated tone was submitted as **test data**, reference `a82aed34-dad1-48a3-bb19-5054f05ff5c9`. This was not a participant recording or a speech-transcription accuracy test.

- The API confirmed the response was saved.
- The row appeared in the admin API and CSV export.
- Downloading its signed audio URL returned exactly the uploaded bytes.
- Its transcript is blank because the OpenAI key was rejected.
- Find the row under Supabase → Table Editor → `responses`, or open `/admin` and include test recordings.
- Its file is under Storage → `Audio` → `q1/a82aed34-dad1-48a3-bb19-5054f05ff5c9.wav`.

## Install on a different laptop

The `.venv` and dependencies are already installed on this laptop. To recreate them on a different machine with Python 3.11+:

```powershell
cd vf
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env  # only when .env does not already exist
# Fill in .env in your editor.
.\.venv\Scripts\python.exe run_local.py
```

You can also run from the repository root:

```powershell
.\vf\.venv\Scripts\python.exe -m uvicorn main:app --app-dir vf --host 127.0.0.1 --port 8000 --reload --no-access-log
```

Then open `http://localhost:8000/?t=YOUR_EVENT_TOKEN`. Do not open `index.html` directly or use a static-only Live Server; this app needs the Python API.

## Microphone permissions: laptop versus phone

- Laptop: `http://localhost:8000` is accepted as a secure context by browsers. Permission is requested only when Record is pressed.
- The page cannot grant itself microphone permission. If permission was blocked, allow Microphone in the browser's site settings and reload. On Windows also check Settings → Privacy & security → Microphone, including access for desktop apps.
- If no device is found, connect/select a microphone. If it is busy, close another app using it.
- Phone: use the **HTTPS** address after deployment, opening it directly in Safari on iPhone or Chrome on Android. A phone's `localhost` refers to the phone, not your laptop. `http://192.168.x.x:8000` normally cannot use the microphone; being on the same Wi-Fi does not change that.
- Before deployment, a trusted HTTPS development tunnel is an alternative, but it exposes the local app. This project does not create a tunnel automatically.
- The recorder selects a supported WebM, MP4, or Ogg format. Recording stops after 90 seconds or when the page is hidden. Microphone tracks are released when recording stops. Keep the tab open until sending finishes.

Reference: https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia

## Where feedback goes

1. Until Send is pressed, the recording stays in browser memory. Reloading or closing the page loses an unsent recording.
2. Send uploads the original audio to your private Supabase bucket (`AUDIO_BUCKET`) under `q1/<submission-uuid>.<format>`.
3. The server sends audio to the selected provider (OpenAI or Google Gemini) for transcription, preserving the spoken language. Participants do not choose a language. Every new recording is transcribed without forcing a single language, with English and Egyptian Arabic supported in the prompt. New rows store `lang=auto`; this is a mode, not a detected language. Test actual Egyptian Arabic/English samples before the event; transcription is not guaranteed to be perfect.
4. Supabase → Table Editor → `responses` contains the transcript, original transcript, audio path, participant name, automatic language mode, time, and test flag.
5. If transcription is unavailable, the response is still saved with its audio and a blank transcript. The dashboard displays this explicitly. It does not currently retry transcription automatically; organizers can listen to the saved audio.
6. If the database insert fails after upload, the page retains the recording for retry. The upload uses the same path and submission ID. An abandoned failed submission can leave an audio object without a database row.

The legacy `rating` and `edit_key` database columns are retained for compatibility; the new interface does not collect ratings. Existing rows are preserved. For an existing database, run `migrations/001_participant_name.sql` once to add the name column. Existing feedback remains unchanged; older rows display “Not provided” for the name.

Reference: https://developers.openai.com/api/docs/guides/speech-to-text

## View feedback and open it in Excel

1. Visit `/admin` on the same laptop or deployed website.
2. Enter `ADMIN_PASSWORD`, then choose **Load feedback**.
3. Keep **Include test recordings** checked during laptop testing. Uncheck it for event-only feedback.
4. Listen to recordings directly in the table. Signed audio links expire after one hour; load feedback again to refresh them.
5. Choose **Download CSV for Excel**. The export includes all matching rows, even beyond the pages currently displayed, with a UTF-8 BOM to preserve Arabic text.
6. Open the downloaded CSV in Excel. If necessary use Data → From Text/CSV → UTF-8, comma separator. Save As → Excel Workbook (`.xlsx`) to create an Excel workbook.

Exports include participant names, question text, timestamps, legacy role, language mode, transcripts, original transcripts, audio storage paths, model, and test flag. They do not embed audio or expiring playback links. Use the dashboard or Supabase Storage to listen/download audio. Formula-like values are escaped for safe spreadsheet opening.

## Deploy after laptop testing

Deploy the **Python web service**, not only the static files. Example Render settings:

- Repository root directory: `vf` (if the repository contains the outer folder).
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT --no-access-log`
- Add the variables from `.env.example` in the host's environment settings, with real values. Use `AUDIO_BUCKET=Audio` for your existing project.
- Keep `IS_TEST=true` while testing the deployed HTTPS URL on an actual iPhone and Android phone.
- Test English, Egyptian Arabic, and mixed speech; check audio playback, transcription, denied microphone permissions, retries, dashboard visibility, and CSV export.
- Before the event, set `IS_TEST=false`, restart/redeploy, and distribute the full `https://YOUR-HOST/?t=YOUR_EVENT_TOKEN` URL/QR code. Old test rows remain marked as tests.
- The event token is shared with participants; it is not your admin password. Keep admin and service credentials private. Rate limiting is in memory per process/IP; use one worker for a small event and consider shared Wi-Fi traffic when adjusting limits.

No deployment has been performed by this change.

## Files

- `static/index.html`: participant markup.
- `static/styles.css`: theme and responsive styles.
- `static/app.js`: permission handling, recorder, playback, submission.
- `static/admin.html`, `admin.css`, `admin.js`: dashboard and CSV download.
- `static/event-artwork.png`: supplied event artwork, preserved as received.
- `config.py`: English question and multilingual transcription prompt.
- `main.py`: upload, transcription, Supabase access, admin API, and CSV export.
- `run_local.py`: localhost launcher with the event token.
- `check_setup.py`: read-only checks that do not print secrets or participant content.

## Credentials and verification

The original `.env.example` contained credentials. It has been replaced with placeholders. Rotate the exposed OpenAI and Supabase keys, plus the admin password and event token, and update `.env` / deployment settings. If the old file was committed or shared, removing it from the working tree does not remove it from history.

Automated backend tests use fake Supabase/OpenAI/Gemini services, so they do not create real feedback or incur transcription costs:

```powershell
.\vf\.venv\Scripts\python.exe -m pip install pytest httpx
.\vf\.venv\Scripts\python.exe -m pytest vf/test_app.py -q
```

Read-only live checks:

```powershell
.\vf\.venv\Scripts\python.exe vf/check_setup.py
```

Frontend state-machine tests (mock microphone and server, no real audio capture):

```powershell
node --test vf/test_frontend.cjs
```

A real microphone recording on each target phone is still required before distributing the event QR code.
