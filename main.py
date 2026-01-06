import os
import requests
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from supabase import create_client, Client
from openai import OpenAI
from gradio_client import Client as GradioClient

# =======================
# APP
# =======================

app = FastAPI(title="BurakGPT")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =======================
# ENV
# =======================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL")

HF_TOKEN = os.getenv("HF_TOKEN")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
MOD_PASSWORD = os.getenv("MOD_PASSWORD")
MOD2_PASSWORD = os.getenv("MOD2_PASSWORD")

# =======================
# CLIENTS
# =======================
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

openai_client = OpenAI(
    api_key=OPENAI_API_KEY
) if OPENAI_API_KEY else None

# Gradio Client (hf_token PARAMETRESİ YOK ❌)
qwen_image = GradioClient("Qwen/Qwen-Image-2512")

# =======================
# ROLE SYSTEM (AYNI)
# =======================

def get_role(password: str):
    if password == ADMIN_PASSWORD:
        return "admin"
    if password == MOD2_PASSWORD:
        return "ban_admin"
    if password == MOD_PASSWORD:
        return "mod"
    return None

# =======================
# BAN CHECK
# =======================

def is_user_banned(username: str) -> bool:
    res = (
        supabase
        .table("users")
        .select("banned_until")
        .eq("username", username)
        .single()
        .execute()
    )

    if not res.data:
        return False

    banned_until = res.data.get("banned_until")
    if banned_until:
        return datetime.utcnow() < datetime.fromisoformat(
            banned_until.replace("Z", "")
        )

    return False

# =======================
# LOCAL LLM
# =======================

def local_llm(prompt: str) -> str:
    try:
        r = requests.post(
            f"{LOCAL_LLM_URL}/v1/chat/completions",
            json={
                "model": "local-model",
                "messages": [
                    {
                        "role": "system",
                        "content": "Sen BurakGPT'sin. Türkçe konuşur, samimi, kısa ve net cevaplar verirsin."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 256
            },
            timeout=60
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Local model hata verdi: {e}"

# =======================
# AI ROUTER
# =======================

def ai_response(prompt: str) -> str:
    if not USE_LOCAL_LLM and openai_client:
        try:
            res = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sen BurakGPT'sin."},
                    {"role": "user", "content": prompt}
                ]
            )
            return res.choices[0].message.content
        except Exception:
            return local_llm(prompt)

    return local_llm(prompt)

# =======================
# IMAGE
# =======================

def generate_image(prompt: str) -> str:
    result = qwen_image.predict(prompt, api_name="/predict")
    return result[0] if isinstance(result, list) else result

# =======================
# HOME
# =======================

@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h2>🤖 BurakGPT Online</h2>"

# =======================
# USER CHECK (GİRİŞTE AD)
# =======================

@app.post("/check")
async def check(data: dict):
    username = data.get("username")

    supabase.table("users").upsert({
        "username": username
    }).execute()

    return {"banned": is_user_banned(username)}

# =======================
# CHAT
# =======================

@app.post("/chat")
async def chat(data: dict):
    username = data.get("username")
    prompt = data.get("prompt")

    if is_user_banned(username):
        return JSONResponse(status_code=403, content={"reply": "🚫 Banlısın"})

    reply = ai_response(prompt)

    supabase.table("messages").insert({
        "username": username,
        "message": prompt,
        "reply": reply
    }).execute()

    return {"reply": reply}

# =======================
# IMAGE ENDPOINT
# =======================

@app.post("/image")
async def image(data: dict):
    username = data.get("username")
    prompt = data.get("prompt")

    if is_user_banned(username):
        return JSONResponse(status_code=403, content={"error": "🚫 Banlısın"})

    image_url = generate_image(prompt)

    supabase.table("images").insert({
        "username": username,
        "prompt": prompt,
        "image_url": image_url
    }).execute()

    return {"image": image_url}

# =======================
# ADMIN PANEL (AYNI KOD)
# =======================

@app.get("/panel/chat")
def view_chat(password: str):
    role = get_role(password)
    if role not in ["admin", "ban_admin", "mod"]:
        raise HTTPException(403)

    return supabase.table("messages").select("*").order("created_at").execute().data

@app.post("/panel/ban")
def ban_user(username: str, minutes: int, password: str):
    role = get_role(password)

    if role is None:
        raise HTTPException(403)

    if role == "mod" and minutes > 60:
        raise HTTPException(403, "Mod max 1 saat")

    if role == "ban_admin" and minutes > 1440:
        raise HTTPException(403, "Ban admin max 1 gün")

    banned_until = datetime.utcnow() + timedelta(minutes=minutes)

    supabase.table("users").update({
        "banned_until": banned_until.isoformat()
    }).eq("username", username).execute()

    return {"status": "banned", "until": banned_until}

@app.post("/panel/unban")
def unban_user(username: str, password: str):
    role = get_role(password)
    if role not in ["admin", "ban_admin"]:
        raise HTTPException(403)

    supabase.table("users").update({
        "banned_until": None
    }).eq("username", username).execute()

    return {"status": "unbanned"}

@app.delete("/panel/user")
def delete_user(username: str, password: str):
    if get_role(password) != "admin":
        raise HTTPException(403)

    supabase.table("users").delete().eq("username", username).execute()
    return {"status": "deleted"}
