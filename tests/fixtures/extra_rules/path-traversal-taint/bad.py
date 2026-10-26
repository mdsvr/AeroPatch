import os

from flask import Flask, request, send_file

app = Flask(__name__)
UPLOADS = "/srv/uploads"


@app.route("/download")
def download():
    name = request.args.get("name", "")
    return send_file(os.path.join(UPLOADS, name))


@app.route("/note")
def note():
    path = os.path.join(UPLOADS, request.args["file"])
    with open(path, encoding="utf-8") as f:
        return f.read()
