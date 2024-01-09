from waitress import serve
import app

import os
HOST = os.environ.get('SERVER_HOST', '10.0.100.176')
try:
    PORT = int(os.environ.get('SERVER_PORT', '5555'))
except ValueError:
    PORT = 5555

print("Server running at ", HOST, " @ ", PORT)
serve(app.app, host=HOST, port=PORT)