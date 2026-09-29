"""Read-only configuration check. Never prints credentials or participant data."""
import main

print('Selected transcription provider:', main.config.PROVIDER)
key_name = 'GEMINI_API_KEY' if main.config.PROVIDER == 'gemini' else 'OPENAI_API_KEY'
for name in [key_name, 'SUPABASE_URL', 'SUPABASE_SERVICE_KEY', 'ADMIN_PASSWORD', 'EVENT_TOKEN']:
    try:
        main.setting(name)
        print(f'{name}: configured')
    except Exception:
        print(f'{name}: missing')
try:
    client = main.database()
    client.table('responses').select('id,participant_name', count='exact').limit(0).execute()
    print('Supabase responses table: reachable')
    bucket = client.storage.get_bucket(main.AUDIO_BUCKET)
    public = getattr(bucket, 'public', None)
    if public is None and isinstance(bucket, dict): public = bucket.get('public')
    print('Supabase audio bucket:', 'PRIVATE (correct)' if public is False else 'PUBLIC - change to private' if public is True else 'reachable; verify privacy in dashboard')
except Exception as error:
    print('Supabase check failed:', type(error).__name__)
try:
    if main.config.PROVIDER == 'gemini':
        main.gemini_transcriber().models.get(model=main.config.GEMINI_MODEL)
    elif main.config.PROVIDER == 'openai':
        main.transcriber().models.retrieve(main.config.MODEL)
    else:
        raise ValueError('Choose openai or gemini')
    print('Transcription model: accessible (audio transcription still needs a sample test)')
except Exception as error:
    print('Transcription provider check failed:', type(error).__name__)
    print('Reason:', main.transcription_error(error))
