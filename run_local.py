"""Start from any folder; open the event URL without printing its token."""
import json
import threading
import webbrowser
from urllib.parse import urlencode
from urllib.request import urlopen
import uvicorn
import main

if __name__ == "__main__":
    url = "http://localhost:8000/?" + urlencode({"t": main.setting("EVENT_TOKEN")})
    running = False
    try:
        with urlopen('http://localhost:8000/api/config', timeout=1) as response:
            running = 'questions' in json.load(response)
    except Exception:
        pass
    if running:
        print('The local feedback server is already running. Opening the participant page.')
        webbrowser.open(url)
    else:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
        print("Opening local feedback app. Organizer dashboard: http://localhost:8000/admin")
        uvicorn.run(main.app, host="127.0.0.1", port=8000, access_log=False)
