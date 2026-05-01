from __future__ import annotations

from pathlib import Path

from flask import Flask, Response, request

from vercel_app import render_get, render_post


app = Flask(__name__)
ROOT = Path(__file__).resolve().parent
CSS_PATH = ROOT / "public" / "styles.css"
FALLBACK_CSS_PATH = ROOT / "styles.css"


@app.get("/")
def home() -> Response:
    return Response(render_get(), mimetype="text/html")


@app.get("/styles.css")
def styles() -> Response:
    path = CSS_PATH if CSS_PATH.exists() else FALLBACK_CSS_PATH
    return Response(path.read_bytes(), mimetype="text/css")


@app.post("/action")
def action() -> Response:
    return Response(render_post(request.get_data()), mimetype="text/html")
