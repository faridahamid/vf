# NASA Space Apps Cairo — project guide

## Participant flow

Enter a name and rating (1–5). Optionally record up to 90 seconds in English, Arabic, or both, or type feedback directly. After recording, the app creates a transcript automatically when the text field is empty. Review and edit the wording, listen to the local recording if needed, then press Send. Existing typed text is preserved; Create transcript asks before replacing it.

Only name and rating are required. If transcription fails, retry, type your feedback, or discard the recording and send your rating. Discarding audio preserves text; clear the text as well if you want rating-only feedback. The text limit is 10,000 characters.

## Where everything goes

- Vercel serves the website and FastAPI backend; GitHub stores source code.
- `/api/transcribe` sends temporary audio to the configured provider and returns text. It never writes to Supabase.
- `/api/answer` receives only name, rating, final text and request metadata. It stores the final text in `public.responses.transcript`.
- New rows have null `audio_path` and `model`, and empty `transcript_raw`. IDs, timestamps and existing question metadata remain for administration.
- No new audio is saved in Supabase. Old audio remains in the private `Audio` bucket until explicitly deleted.

Audio remains in browser memory for review and is cleared along with text after confirmed submission. Refreshing or closing the page can lose these drafts. A failed Send preserves the draft and submission ID for retry. Server multipart handling may temporarily spool uploaded files; the transcription endpoint closes them after processing. Audio still passes through the backend and provider, so this is not a promise of zero provider retention. Transcription consumes provider quota even when the participant never submits.

## Admin, export and deletion

Production: https://vf-ten-virid.vercel.app/ (use the full event-token link).

Admin: https://vf-ten-virid.vercel.app/admin

Admin displays final text in the Transcript column. New responses show No audio stored. Older recordings still play through temporary signed links valid for one hour. Reload to refresh expired playback links; keep the bucket private.

CSV export includes all responses, not just loaded pages. Open it in Excel; import as UTF-8 if Arabic appears incorrectly. Final text is in `transcript`; audio is not embedded. Only older responses have audio paths. Names, ratings, timestamps and metadata remain available.

Delete removes the database row. For older audio responses, it deletes the audio first, then the row. Failed audio removal keeps the row for retry. There is no restore button; downloaded exports, backups and provider-retained data are outside this deletion. This update deletes no existing feedback.

## Deployment and testing

No database migration is needed. Commit and push to the GitHub branch connected to Vercel Production, then wait for Ready. A local commit alone does not publish. Keep existing Vercel environment settings; local `.env` changes do not update them.

Old already-open pages that send audio to `/api/answer` receive a refresh error instead of storing audio. Ask participants to reload after deployment.

Test name/rating only, typed feedback, recording then correcting the transcript, failed transcription followed by typing, and retrying a failed submission. In admin and CSV, verify that the final edited wording appears and no new audio path exists. Local tests use the Supabase project configured in `.env`; production credentials mean real production data.

The new regression suite checks validation, temporary transcription without database/storage writes, legacy-upload rejection, retries, 40 concurrent simulated final submissions, old audio deletion, and frontend editing/error behavior. These mocked tests do not prove live event capacity or real microphone compatibility.

## Limits

The browser limits recordings to 90 seconds; the backend caps uploads at 4 MB. Text uses much less storage than audio, but existing audio still occupies space. Transcription remains synchronous and subject to hosting timeouts and provider quotas; there is no background retry queue.

Transcription requests are limited to 120 per IP per hour per server process. Participants sharing Wi-Fi may share that limit; it is not distributed abuse prevention. Test expected peak traffic before a large event. A saved transcription preview is not created: until Send succeeds, no feedback row exists.

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


