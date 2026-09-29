create table responses (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),
  participant_name text,
  question_id text, ptype text, lang text, rating int,
  transcript text, transcript_raw text, audio_path text,
  model text, edit_key text, is_test boolean default true
);
alter table responses enable row level security;
