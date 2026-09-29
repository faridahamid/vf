import main
try:
    buckets = main.database().storage.list_buckets()
    print('Storage buckets:', [{'name': getattr(b, 'name', None), 'public': getattr(b, 'public', None)} for b in buckets])
except Exception as error:
    print('Storage list failed:', type(error).__name__)
    print('Status:', getattr(error, 'status', None))
    print('Message:', getattr(error, 'message', 'No message'))
