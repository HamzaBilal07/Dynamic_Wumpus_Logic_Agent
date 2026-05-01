from __future__ import annotations

from flask import Flask, Response, request

from vercel_app import render_get, render_post


app = Flask(__name__)


@app.get("/")
def home() -> Response:
    return Response(render_get(), mimetype="text/html")


@app.post("/action")
def action() -> Response:
    return Response(render_post(request.get_data()), mimetype="text/html")

