import ast

from flask import Flask, request

app = Flask(__name__)


@app.route("/calc")
def calc():
    expr = request.args.get("expr", "0")
    return str(ast.literal_eval(expr))


@app.route("/double")
def double():
    n = int(request.args.get("n", "0"))
    return str(eval(f"{n} * 2"))
