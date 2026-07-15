"""
app.py
Entry point. Run with: python app.py
"""

import os
from flask import Flask, send_from_directory, abort
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from api.routes import api

app = Flask(__name__)

# Open CORS since the frontend is served both as a normal website AND
# accessed from inside the Capacitor-wrapped APK's WebView, which may
# present a different effective origin (e.g. capacitor://localhost or
# https://localhost depending on platform). Keeping this open avoids
# CORS failures specifically for API calls made from inside the app shell.
CORS(app, resources={r"/api/*": {"origins": "*"}})

app.register_blueprint(api, url_prefix="/api")

# Where the built .apk file lives - update this path once the actual
# Capacitor build output is placed here (e.g. via CI or manual copy)
APK_DIR = os.path.join(os.path.dirname(__file__), "static", "downloads")
APK_FILENAME = "docket.apk"


@app.route("/download/docket.apk", methods=["GET"])
def download_apk():
    """
    Serves the built APK as a downloadable file. This is the target of
    the website's "Download App" button - browsers hitting this route
    directly get a file download, no JSON involved.
    """
    apk_path = os.path.join(APK_DIR, APK_FILENAME)
    if not os.path.exists(apk_path):
        abort(404, description="APK not yet built or not placed in static/downloads/")
    return send_from_directory(APK_DIR, APK_FILENAME, as_attachment=True)


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
