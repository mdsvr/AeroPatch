"""Results page for the 6-person review test. Serves recorded cards only; no AI runs here."""

import json
from pathlib import Path

from flask import Flask, render_template

HERE = Path(__file__).resolve().parent


def create_app():
    app = Flask(__name__, template_folder=str(HERE / "templates"))
    cards = json.loads((HERE / "cards.json").read_text(encoding="utf-8"))["cards"]

    @app.route("/")
    def results():
        return render_template("results.html", cards=cards)

    return app


if __name__ == "__main__":
    # Local only: the test runs on the facilitator's screen or laptop.
    create_app().run(host="127.0.0.1", port=5050)
