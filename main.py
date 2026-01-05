import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from supabase import create_client, Client

# =======================
# ENV
# =======================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# =======================
# SUPABASE
# =======================
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =======================
# APP
# =======================
app = FastAPI(title="BurakGPT")

# =======================
# LOCAL MODEL (DUMMY)
# buraya sonra gerçek local model bağlanır
# =======================
def local_model_response(prompt: str) -> str:
    return f"🤖 BurakGPT: '{prompt}' üzerine düşünüyorum..."

# =======================
# BAN CHECK
# =======================
def is_user_banned(username: str):
    res = supabase.table("users") \
        .select("banned_until") \
        .eq("username", username) \
        .single() \
        .execute()

    if not res.data:
        return False

    banned_until = res.data.get("banned_until")
    if banned_until:
        return datetime.utcnow() < datetime.fromisoformat(banned_until.replace("Z", ""))
    return False

# =======================
# HOME
# =======================
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
<!DOCTYPE html>
<html>
<head>
<title>BurakGPT</title>
<style>
body {
    margin: 0;
    font-family: Inter, sans-serif;
    background: linear-gradient(120deg,#0f172a,#020617);
    color: white;
}
#login, #chat {
    max-width: 700px;
    margin: 100px auto;
    padding: 30px;
    border-radius: 12px;
    background: rgba(255,255,255,0.05);
}
input, button {
    width: 100%;
    padding: 14px;
    margin-top: 10px;
    border-radius: 8px;
    border: none;
}
button {
    background: #2563eb;
    color: white;
    font-weight: bold;
    cursor: pointer;
}
#chat { display: none; }
#messages {
    height: 300px;
    overflow-y: auto;
    margin-bottom: 10px;
}
.msg { margin: 8px 0; }
.user { color: #38bdf8; }
.bot { color: #a7f3d0; }
</style>
</head>

<body>

<div id="login">
    <h2>BurakGPT</h2>
    <p>Adını gir ve devam et</p>
    <input id="username" placeholder="Kullanıcı adı">
    <button onclick="start()">Devam Et</button>
</div>

<div id="chat">
    <h3 id="welcome"></h3>
    <div id="messages"></div>
    <input id="prompt" placeholder="Mesaj yaz..." onkeydown="if(event.key==='Enter')send()">
</div>

<script>
let username = "";

async function start(){
    username = document.getElementById("username").value;
    if(!username) return alert("İsim gir");

    const r = await fetch("/check",{
        method:"POST",
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({username})
    });

    const j = await r.json();
    if(j.banned){
        alert("🚫 Banlısın");
        return;
    }

    document.getElementById("login").style.display="none";
    document.getElementById("chat").style.display="block";
    document.getElementById("welcome").innerText="Hoş geldin "+username;
}

async function send(){
    const input = document.getElementById("prompt");
    const msg = input.value;
    if(!msg) return;
    input.value="";

    add("user", msg);

    const r = await fetch("/chat",{
        method:"POST",
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({username, prompt: msg})
    });

    const j = await r.json();
    add("bot", j.reply);
}

function add(type,text){
    const div = document.createElement("div");
    div.className="msg "+type;
    div.innerText = (type==="user"?"Sen: ":"BurakGPT: ") + text;
    document.getElementById("messages").appendChild(div);
}
</script>

</body>
</html>
"""

# =======================
# CHECK BAN
# =======================
@app.post("/check")
async def check_user(data: dict):
    username = data.get("username")

    # kullanıcı yoksa oluştur
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
        return JSONResponse(status_code=403, content={"reply": "Banlısın"})

    reply = local_model_response(prompt)

    # log
    supabase.table("messages").insert({
        "username": username,
        "message": prompt,
        "reply": reply
    }).execute()

    return {"reply": reply}
