# NASA Space Apps Cairo — project guide

This document explains the current application, how feedback moves through it, and how to test and publish updates. It contains no passwords, API keys, or event access codes.

## 1. What participants do

1. Open the event link or scan its QR code.
2. Enter their name.
3. Answer **“How was your experience at NASA Space Apps Cairo?”** with a rating from 1 to 5.
4. Optionally record up to 90 seconds. The recorder is always visible. English, Arabic, and mixed speech are supported without a language selector.
5. Press **Send my feedback**. The notice above Send explains what is shared; there is no consent checkbox.

Only the name and rating are required. Recording is optional. Participants can listen to or discard their recording before sending. Recording stays in browser memory until Send is pressed; it is not a saved draft and can be lost when the page closes or reloads.

The interface is English. The transcription instructions preserve the original spoken language instead of translating it. Transcripts can contain mistakes, so organizers should listen to the audio when wording matters.

## 2. Where the website runs

| Component | Purpose | Location |
| --- | --- | --- |
| HTML, CSS, JavaScript and artwork | Participant and admin interfaces | GitHub source, served through Vercel |
| FastAPI backend | Validate submissions, save feedback, call transcription, protect admin actions | Vercel |
| Supabase database | Names, ratings, timestamps, transcripts and audio references | `public.responses` table |
| Supabase Storage | Original audio files | Private bucket named `Audio` in this setup |
| OpenAI | Convert optional audio into text | Selected transcription provider; default model `gpt-4o-transcribe` |

Production website: https://vf-ten-virid.vercel.app/

Organizer dashboard: https://vf-ten-virid.vercel.app/admin

Participants should receive the full event link with `?t=YOUR_EVENT_TOKEN`. The actual code is deliberately omitted here.

## 3. What happens when someone presses Send

For rating-only feedback, the browser sends the name, rating, question ID and unique submission ID to `/api/answer`. The server validates the event code and fields, then saves a database row. It does not call OpenAI.

For feedback with a recording:

1. The browser sends the same fields plus the audio to the backend.
2. The backend uploads the audio to the private Supabase bucket.
3. It saves the database row, including the audio path, before requesting transcription.
4. It sends the audio to the configured transcription provider.
5. When transcription succeeds, it updates the saved row with the transcript and model name.

Audio paths look like `experience/<submission-UUID>.webm`. The extension can differ by browser, such as `.mp4` on some devices. The path is an object identifier inside the bucket, not a public download link.

If transcription fails after storage succeeds, the feedback and audio remain available. Admin can still listen to the recording. Failed or interrupted transcription is not automatically retried in the current app. A storage failure is reported as a failed submission; the participant can retry while the page remains open. Upload and database insert are separate operations, so an interrupted storage operation can leave an audio object without a completed database row.

## 4. Where to find feedback and audio

### In the app

Open `/admin` and enter the configured admin password. Load responses to see participant names, ratings, transcripts and recordings. Older voice-only feedback may have no rating. Rating-only submissions have no audio or transcript.

### In Supabase

- **Table Editor → responses:** saved feedback records.
- **Storage → Audio:** original audio objects, organized by question ID.
- Use the row's `audio_path` to identify its recording.

The bucket should remain private. The backend uses its server-side Supabase service key to access it. Admin playback uses temporary signed links valid for one hour; reload the dashboard to obtain a fresh link after expiry. Anyone holding an unexpired signed link can use it, so treat it as private.

Participant recordings are not stored in GitHub. Vercel runs the application but Supabase is the persistent feedback store.

## 5. Exporting to Excel

Use the CSV export button in `/admin`, then open the downloaded `space-apps-feedback.csv` in Excel. It includes all responses returned by the export query, including pages not loaded in the dashboard. The current admin export includes older test entries too.

The export includes IDs, timestamps, participant names, question details, ratings, transcripts, audio paths, model names and legacy metadata. Audio files are not embedded in the spreadsheet. Use admin playback or Supabase Storage to access them.

If Excel displays Arabic incorrectly, import the file through **Data → From Text/CSV** and select UTF-8 encoding. Timestamps are stored with timezone information; convert them to Cairo time if needed for reporting.

## 6. Deleting feedback

The admin Delete button asks for confirmation. The server removes the audio object first and then deletes the response row, including the transcript. Rating-only deletion removes the row.

If audio removal fails, the row is kept so the operation can be retried. If the database deletion fails after audio removal, the row can temporarily remain without playable audio; retry deletion.

Deletion removes active app data. It cannot erase downloaded spreadsheets, downloaded recordings, external backups, or copies retained by a transcription provider. There is no restore button in this app. Test deletion only on a disposable test response.


## 8. The event token

The `t` parameter is an event access code checked by the server. It helps limit submissions to people with the event link. It is not an individual participant login and cannot prevent forwarding or all abuse.

The frontend remembers a validly supplied code in session storage for that browser tab and preserves it on the logo/home link. Returning to the home page without the parameter in the same tab can therefore continue to work. A new browser, private session, or new tab without stored state should use the full event link. If browser storage is blocked, the full URL still works.

Keep the event link in the QR code. Changing `EVENT_TOKEN` invalidates old links and remembered codes, so regenerate and redistribute the link if you change it.


## 9. Environment settings

Local settings live in `vf/.env`. Production settings live in the Vercel project's Environment Variables. Local edits do not change production settings. Never commit `.env`, service keys, API keys or passwords.

| Variable | Purpose |
| --- | --- |
| `SUPABASE_URL` | URL of your Supabase project. |
| `SUPABASE_SERVICE_KEY` | Server-only credential for database and storage access. Never expose it in frontend code. |
| `AUDIO_BUCKET` | Exact case-sensitive bucket name; use `Audio` for this project. |
| `ADMIN_PASSWORD` | Password required by the admin API. |
| `EVENT_TOKEN` | Shared code used in participant event links. |
| `TRANSCRIPTION_PROVIDER` | `openai` by default; optional `gemini` support exists. |
| `OPENAI_API_KEY` | Required when using OpenAI transcription. |
| `TRANSCRIBE_MODEL` | OpenAI model; defaults to `gpt-4o-transcribe`. |
| `GEMINI_API_KEY` | Required only when selecting Gemini. |
| `GEMINI_MODEL` | Gemini model; code default is `gemini-2.5-flash`. |
| `IS_TEST` | Use `false` in production. Labels records; it does not isolate the database or stop provider charges. |
| `SUBMISSIONS_PER_IP_HOUR` | Optional process-local request limit; default 1000. |

Restart the local server after changing settings. For Vercel setting changes, create a new deployment for them to take effect. Provider calls can consume quota or incur charges; rating-only submissions do not invoke transcription.




## 10. Project files and maintenance

| File or folder | Purpose |
| --- | --- |
| `main.py` | Backend routes, validation, storage, transcription, export and deletion. |
| `config.py` | Questions, transcription instructions and provider/model defaults. |
| `static/index.html`, `styles.css`, `app.js` | Participant page: separate markup, styling and behavior. |
| `static/admin.html`, `admin.css`, `admin.js` | Organizer dashboard. |
| `static/cairo-logo.png`, `event-artwork.png`, `favicon.svg` | Active visual assets. |
| `requirements.txt` | Runtime Python dependencies. |
| `requirements-dev.txt`, `test_app.py`, `test_frontend.cjs` | Development dependencies and automated tests. |
| `check_setup.py` | Optional setup diagnostic; contacts configured external services. |
| `run_local.py` | Local launcher that opens the event link. |
| `schema.sql`, `migrations/` | Initial database setup and schema history. |
| `.gitignore` | Keeps local credentials, environments and caches out of new commits. |
| `.env.example` | Placeholder configuration template; use the full settings table above. |


