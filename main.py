import os
import requests
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from supabase import create_client, Client
from openai import OpenAI
from gradio_client import Client as GradioClient

# =======================
# ENV
# =======================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL")  # http://127.0.0.1:8000

HF_TOKEN = os.getenv("HF_TOKEN")  # Qwen Image için önerilir

# =======================
# CLIENTS
# =======================
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

qwen_image = GradioClient(
    "Qwen/Qwen-Image-2512",
    hf_token=HF_TOKEN
)

# =======================
# APP
# =======================
app = FastAPI(title="BurakGPT")

# =======================
# LOCAL LLM (llama.cpp SERVER)
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
        return f"Local model cevap veremedi: {e}"

# =======================
# AI ROUTER
# =======================
def ai_response(prompt: str) -> str:
    if not USE_LOCAL_LLM and openai_client:
        try:
            res = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Sen BurakGPT isimli yardımcı bir yapay zekasın."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return res.choices[0].message.content
        except Exception:
            return local_llm(prompt)

    return local_llm(prompt)

# =======================
# IMAGE GENERATION (QWEN)
# =======================
def generate_image(prompt: str) -> str:
    result = qwen_image.predict(
        prompt,
        api_name="/predict"
    )

    if isinstance(result, list):
        return result[0]

    return result

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
# HOME
# =======================
@app.get("/", response_class=HTMLResponse)
async def home():
    if os.path.exists("index.html"):
        return open("index.html", encoding="utf-8").read()
    return "<h2>🤖 BurakGPT Online</h2>"

# =======================
# CHECK USER
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
        return JSONResponse(
            status_code=403,
            content={"reply": "🚫 Banlısın"}
        )

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
        return JSONResponse(
            status_code=403,
            content={"error": "🚫 Banlısın"}
        )

    try:
        image_url = generate_image(prompt)
    except Exception as e:
        return {"error": str(e)}

    supabase.table("images").insert({
        "username": username,
        "prompt": prompt,
        "image_url": image_url
    }).execute()

    return {"image": image_url}
