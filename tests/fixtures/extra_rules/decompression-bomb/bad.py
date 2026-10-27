import zlib

from flask import Flask, request

app = Flask(__name__)


@app.route("/upload", methods=["POST"])
def upload():
    body = zlib.decompress(request.get_data())
    return str(len(body))
