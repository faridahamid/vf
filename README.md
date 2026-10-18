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




## Audience links and filters

Five groups are supported: participants, speakers, volunteers, mentors and judges. Each link loads a dedicated introduction and question. The server derives the saved `ptype` from the validated link, not from a client-supplied category. Name, rating and reviewed text still go to the same responses table; no new audio is stored.

Sign in to admin and load feedback, then expand **Audience links — share with each group**. Click a link field to select and copy its full URL. Links use the current site's origin: copy production links from production admin, not localhost. No extra environment variables or SQL migrations are needed. The participant link is unchanged. Other audience codes are stable HMAC-derived codes based on EVENT_TOKEN; changing that setting rotates all links.

The Audience selector filters database results before pagination. CSV export follows the selected group and includes all matching pages. Choose All groups to export everything. Existing participant records remain visible. Shared links categorize responses but do not verify someone's role or identity.

Deploy backend and frontend together. Reload the participant/admin pages after deployment. Use one test submission for each audience, confirm its group in admin, and test filtered exports. Opening a new group link replaces the remembered token for that tab.


## Speaker form (October 2026 update)

The speaker link starts with name and one of the organizer's 14 sessions/workshops. Start ratings shows one question at a time. Selecting a score advances automatically; Back and Continue allow review without losing answers. After the fifth rating, optional voice/text feedback and the final Send appear. No ratings are submitted during navigation. Name, workshop and every rating are required. One Send saves one database row atomically, using `speaker_form` as question_id. The overall score remains in rating; the selected workshop and five scores are structured JSON in the existing transcript_raw column. Final typed/reviewed comments remain in transcript. No schema migration is required. Admin shows workshop and ratings; CSV has dedicated workshop and score columns. Retries retain the same submission ID.

Volunteer questions await screenshots. Other audiences retain their existing flow. The source is local until deployment.


Admin calculates speaker averages from all five scores (equal weight, one decimal), including existing complete speaker forms. The stored overall rating remains unchanged. CSV uses readable headers and separate score columns, plus workshop, average, comments and response details. Test status and internal raw data are omitted from CSV; existing records are retained. Older single-question entries show a single rating rather than an invented average.


## Volunteer session evaluation

The volunteer audience link now offers the same 14 workshop titles and a 14-question wizard transcribed from the supplied screenshots: ten 1–5 agreement ratings and four choice questions. Agenda alignment is optional and can be skipped; the other questions are required. Choice answers are Yes/No, except the welcome-back recommendation which also allows Maybe. No answers are preselected from the example screenshots. Evaluation is by session title; the name field identifies the volunteer submitting it.

Optional voice or typed observations follow the questions. One final Send stores one `volunteer_form` row using the existing JSON structure in transcript_raw, with `volunteer_delivery` retained in rating. The average uses only answered numeric ratings, excluding choices and skipped agenda alignment. Admin shows every answer, and CSV gives each question a separate readable column. No database migration or extra audience link is required.

Audience-filtered CSV exports include only that audience's question columns. All groups includes both speaker and volunteer columns, with blanks for questions not applicable to a row. Admin passwords are percent-encoded as UTF-8 for HTTP headers so Arabic input reaches authentication rather than failing in the browser.


## Saved audience analysis PDF

Admin now has Check report status, Generate analysis PDF, and Download saved PDF. This always analyzes all audiences regardless of the table's Audience filter, and renders one page each for participants, speakers, volunteers, mentors and judges. Empty categories get an honest empty page. Reports are in English; Arabic and English comments can be analyzed. Names are not sent as a separate field; known submitter names, emails and phone-like strings are removed from comments, but free-form text can still contain other personal details.

Generation is explicit and confirms estimated API spending. It uses the existing server-only OPENAI_API_KEY with gpt-5.4-mini, one bounded Responses API call, no reasoning, max 6,000 output tokens and no automatic SDK retries. Input is limited to 250,000 UTF-8 bytes; oversized datasets fail before calling AI, rather than silently discarding comments. Current rate assumptions for the displayed estimate are $0.75/M input and $4.50/M output; update them if pricing changes. Report usage is an estimate, not a billing receipt.

Charts and statistics are calculated in Python, not by AI. The headline score averages each submission's answered numeric ratings at full precision. Yes/No/Maybe and skipped ratings are excluded. Question charts include denominators; distribution counts individual numeric answers. Counts are submissions, not verified unique people or attendance/response rates. Legacy single-question rows remain included and are identified in the methodology. AI findings reference existing question/comment IDs in the stored analysis; actions are labelled suggestions. Small samples are flagged. Do not treat automated findings as a substitute for reviewing the original feedback.

No database migration is required. Reports use the existing PRIVATE AUDIO_BUCKET under analysis-reports/<event-namespace>/<snapshot-hash>/. Feedback rows are never updated by report generation. The report contains aggregate statistics and AI interpretations; its private saved analysis also includes redacted source comments. Downloads go through authenticated admin routes, not public signed links. Report snapshots are deliberately retained after feedback deletion, so a previous PDF remains a historical snapshot; use Check report status to see when feedback has changed.

Each snapshot has a create-only durable claim, saved AI output, analysis JSON, a PDF, and metadata. Repeat requests for the same completed snapshot reuse the saved PDF. A PDF-render/storage failure can be retried from saved analysis without calling AI. A provider failure/timeout, interrupted invocation, or failure before analysis is safely stored leaves a claim and blocks automatic paid retries. An organizer must inspect the private claim/raw-analysis/analysis files to recover; do not simply remove the claim without checking whether the original call completed. A local or browser refresh never starts generation automatically. Generating a changed feedback snapshot requires explicit confirmation again.

The one authorized live verification was run on October 18, 2026: 14 submissions, five PDF pages, one AI call. Usage: 2,372 input tokens and 584 output tokens, approximately $0.004407. The saved PDF was downloaded twice without another generation call. It is labelled TEST SNAPSHOT and is not the final event analysis. Do not rerun verify_report_once.py for another live test; its local receipt blocks repeats. Future event generation is via the admin button after collection ends.

Deploy the new reportlab runtime dependency together with frontend and backend. Set the host's request timeout to allow the 75-second model request plus database/storage and rendering time; the endpoint is synchronous and does not provide a background queue. The durable claim prevents accidental duplicate charges even if the hosting request is interrupted, but recovery may require organizer inspection. Keep the Supabase bucket private and service key server-only.

Offline checks: python -m pytest test_app.py test_reporting.py; node --test test_frontend.cjs test_admin.cjs. PDF tests use generated fixtures and mock AI calls. pypdf is a development dependency; reportlab is required in production.
