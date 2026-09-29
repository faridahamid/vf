-- Run once in Supabase SQL Editor for existing projects. Safe to run again.
ALTER TABLE public.responses ADD COLUMN IF NOT EXISTS participant_name text;
