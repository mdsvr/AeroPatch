import zlib

from flask import Flask, request

app = Flask(__name__)
MAX_OUTPUT = 10 * 1024 * 1024


@app.route("/upload", methods=["POST"])
def upload():
    d = zlib.decompressobj()
    body = d.decompress(request.get_data(), MAX_OUTPUT)
    if d.unconsumed_tail:
        return "too large", 413
    return str(len(body))
