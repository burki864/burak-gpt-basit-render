import os
import requests
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from supabase import create_client, Client
from openai import OpenAI
from gradio_client import Client as GradioClient
import gradio as gr

# ======================
# APP
# ======================

app = FastAPI(title="BurakGPT")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# ENV
# ======================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
MOD_PASSWORD = os.getenv("MOD_PASSWORD")
MOD2_PASSWORD = os.getenv("MOD2_PASSWORD")

# ======================
# CLIENTS
# ======================

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
qwen_image = GradioClient("Qwen/Qwen-Image-2512")

# ======================
# ROLE SYSTEM (BİREBİR)
# ======================

def get_role(password: str):
    if password == ADMIN_PASSWORD:
        return "admin"
    if password == MOD2_PASSWORD:
        return "ban_admin"
    if password == MOD_PASSWORD:
        return "mod"
    return None

# ======================
# BAN CHECK (DOĞRU)
# ======================

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

# ======================
# USER REGISTER
# ======================

def register_user(username: str):
    if not username or len(username.strip()) < 2:
        return False, "❌ Geçerli bir ad gir"

    supabase.table("users").upsert({
        "username": username.strip()
    }).execute()

    return True, "✅ Giriş başarılı"

# ======================
# LOCAL LLM
# ======================

def local_llm(prompt: str) -> str:
    try:
        r = requests.post(
            f"{LOCAL_LLM_URL}/v1/chat/completions",
            json={
                "model": "local-model",
                "messages": [
                    {"role": "system", "content": "Sen BurakGPT'sin. Türkçe, samimi ve net cevap ver."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 256
            },
            timeout=60
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Local LLM hata verdi: {e}"

# ======================
# AI ROUTER
# ======================

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

# ======================
# IMAGE
# ======================

def generate_image(prompt: str) -> str:
    result = qwen_image.predict(prompt, api_name="/predict")
    return result[0] if isinstance(result, list) else result

# ======================
# CHAT LOGIC
# ======================

def chat_handler(username, message, history):
    if is_user_banned(username):
        return history + [(message, "🚫 Banlısın")]

    reply = ai_response(message)

    supabase.table("messages").insert({
        "username": username,
        "message": message,
        "reply": reply
    }).execute()

    return history + [(message, reply)]

def image_handler(username, prompt):
    if is_user_banned(username):
        return None, "🚫 Banlısın"

    url = generate_image(prompt)

    supabase.table("images").insert({
        "username": username,
        "prompt": prompt,
        "image_url": url
    }).execute()

    return url, "✅ Görsel oluşturuldu"

# ======================
# UI (LOGIN + CHAT)
# ======================

with gr.Blocks(title="🤖 BurakGPT", theme=gr.themes.Soft()) as demo:
    gr.Markdown("## 🤖 **BurakGPT**\nGiriş yap ve sohbet etmeye başla")

    username_state = gr.State()

    with gr.Group(visible=True) as login_box:
        username_input = gr.Textbox(label="Kullanıcı Adı")
        login_btn = gr.Button("Giriş Yap")
        login_status = gr.Textbox(label="Durum")

    with gr.Group(visible=False) as chat_box:
        chatbot = gr.Chatbot(height=400)
        msg = gr.Textbox(label="Mesaj")
        send = gr.Button("Gönder")

        img_prompt = gr.Textbox(label="Görsel Prompt")
        img_btn = gr.Button("Görsel Oluştur")
        img_out = gr.Image()
        img_status = gr.Textbox(label="Durum")

    def login(username):
        ok, status = register_user(username)
        if not ok:
            return None, status, gr.update(), gr.update()

        return (
            username,
            status,
            gr.update(visible=False),
            gr.update(visible=True)
        )

    login_btn.click(
        login,
        inputs=username_input,
        outputs=[username	username_state, login_status, login_box, chat_box]
    )

    send.click(
        chat_handler,
        inputs=[username_state, msg, chatbot],
        outputs=chatbot
    )

    img_btn.click(
        image_handler,
        inputs=[username_state, img_prompt],
        outputs=[img_out, img_status]
    )

# ======================
# MOUNT
# ======================

app = gr.mount_gradio_app(app, demo, path="/")

@app.get("/", response_class=HTMLResponse)
def home():
    return "<h2>🤖 BurakGPT Online</h2>"
