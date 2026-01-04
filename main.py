from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import os
import requests

app = FastAPI()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

# ------------------ HOME ------------------
@app.get("/")
async def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# ------------------ LOGIN (FAKE / DEMO) ------------------
@app.post("/login")
async def login(req: Request):
    data = await req.json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return JSONResponse(status_code=400, content={"error": "Eksik bilgi"})

    return {"success": True, "user": email}

# ------------------ SIGNUP (FAKE / DEMO) ------------------
@app.post("/signup")
async def signup(req: Request):
    data = await req.json()
    email = data.get("email")
    password = data.get("password")
    password2 = data.get("password2")

    if password != password2:
        return JSONResponse(status_code=400, content={"error": "Şifreler uyuşmuyor"})

    return {"success": True, "user": email}

# ------------------ CHAT (LOCAL / MOCK) ------------------
@app.post("/chat")
async def chat(req: Request):
    data = await req.json()
    msg = data.get("message", "")

    return {
        "reply": f"🧠 BurakGPT (local): {msg}"
    }

# ------------------ IMAGE (REPLICATE) ------------------
@app.post("/image")
async def image(req: Request):
    data = await req.json()
    prompt = data.get("prompt")

    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "version": "db21e45c7f7020c92cfc1f3f90b3c4c62c1f4f7a8a7a6e2a0d2f0f9c3c7c3a4",
        "input": {"prompt": prompt}
    }

    r = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=headers)
    return r.json()
