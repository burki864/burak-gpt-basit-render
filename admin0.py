import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from supabase import create_client

# ======================
# ENV
# ======================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
MOD_PASSWORD = os.getenv("MOD_PASSWORD")
MOD2_PASSWORD = os.getenv("MOD2_PASSWORD")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="BurakGPT Admin Panel")

# ======================
# AUTH
# ======================
def get_role(password: str):
    if password == ADMIN_PASSWORD:
        return "admin"
    if password == MOD_PASSWORD:
        return "mod"
    if password == MOD2_PASSWORD:
        return "mod2"
    return None

def auth(password: str):
    role = get_role(password)
    if not role:
        raise HTTPException(status_code=401, detail="Yetkisiz")
    return role

# ======================
# MODELS
# ======================
class Login(BaseModel):
    password: str

class BanRequest(BaseModel):
    user_id: str
    reason: str = "İhlal"

# ======================
# PANEL (ROOT)
# ======================
@app.get("/", response_class=HTMLResponse)
def admin_panel():
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>BurakGPT Admin Panel</title>
<style>
body{font-family:Arial;background:#0f0f0f;color:#fff;padding:20px}
input,button{padding:8px;margin:5px}
button{cursor:pointer}
.card{border:1px solid #333;padding:10px;margin:10px 0}
</style>
</head>
<body>

<h1>🛡 BurakGPT Admin Panel</h1>

<input id="password" type="password" placeholder="Admin / Mod Şifre">
<button onclick="login()">Giriş</button>

<hr>

<button onclick="loadUsers()">👥 Kullanıcıları Getir</button>

<div id="users"></div>

<script>
let PASSWORD = ""

function login(){
  PASSWORD = document.getElementById("password").value
  alert("Şifre alındı")
}

async function loadUsers(){
  const res = await fetch(`/admin/users?password=${PASSWORD}`)
  const data = await res.json()
  const div = document.getElementById("users")
  div.innerHTML = ""
  data.forEach(u=>{
    div.innerHTML += `
      <div class="card">
        <b>${u.id}</b><br>
        Banned: ${u.is_banned}<br>
        <button onclick="viewMessages('${u.id}')">💬 Mesajlar</button>
        <button onclick="banUser('${u.id}')">🔨 Ban</button>
      </div>
    `
  })
}

async function viewMessages(uid){
  const res = await fetch(`/admin/user/${uid}/messages?password=${PASSWORD}`)
  const data = await res.json()
  alert(data.map(m=>m.content).join("\\n"))
}

async function banUser(uid){
  const reason = prompt("Ban sebebi?")
  await fetch(`/admin/ban?password=${PASSWORD}`,{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({user_id:uid, reason})
  })
  alert("Banlandı")
}
</script>

</body>
</html>
"""

# ======================
# API
# ======================
@app.get("/admin/users")
def users(password: str = Query(...)):
    auth(password)
    return supabase.table("users").select("*").execute().data

@app.get("/admin/user/{user_id}/messages")
def messages(user_id: str, password: str = Query(...)):
    auth(password)
    return supabase.table("messages").select("*").eq("user_id", user_id).execute().data

@app.post("/admin/ban")
def ban(data: BanRequest, password: str = Query(...)):
    role = auth(password)

    if role == "mod":
        until = datetime.utcnow() + timedelta(hours=1)
    elif role == "mod2":
        until = datetime.utcnow() + timedelta(hours=24)
    else:
        until = None

    supabase.table("users").update({
        "is_banned": True,
        "banned_until": until
    }).eq("id", data.user_id).execute()

    return {"status": "banned", "until": until}
