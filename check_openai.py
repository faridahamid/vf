import main
try:
    main.transcriber().models.retrieve(main.config.MODEL)
    print('OpenAI accessible')
except Exception as error:
    print('OpenAI error code:', getattr(error, 'code', None))
    print('OpenAI error type:', getattr(error, 'type', None))
    print('HTTP status:', getattr(error, 'status_code', None))
    print('Client uses .env key:', main.transcriber().api_key == main.os.environ.get('OPENAI_API_KEY'))
    print('Client uses official API:', str(main.transcriber().base_url) == 'https://api.openai.com/v1/')
