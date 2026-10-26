import os

from flask import Flask, request, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOADS = "/srv/uploads"


@app.route("/download")
def download():
    name = secure_filename(request.args.get("name", ""))
    return send_file(os.path.join(UPLOADS, name))


@app.route("/note")
def note():
    path = os.path.realpath(os.path.join(UPLOADS, request.args["file"]))
    if not path.startswith(UPLOADS + os.sep):
        return "not found", 404
    with open(path, encoding="utf-8") as f:
        return f.read()
