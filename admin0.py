import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
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
# LOGIN
# ======================
@app.post("/admin/login")
def admin_login(data: Login):
    role = get_role(data.password)
    if not role:
        raise HTTPException(status_code=401, detail="Hatalı şifre")
    return {"role": role}

# ======================
# USERS
# ======================
@app.get("/admin/users")
def list_users(password: str):
    auth(password)
    response = supabase.table("users").select("*").execute()
    return response.data if hasattr(response, "data") else response

# ======================
# CHATS & MESSAGES
# ======================
@app.get("/admin/user/{user_id}/messages")
def user_messages(user_id: str, password: str):
    auth(password)
    response = supabase.table("messages").select("*").eq("user_id", user_id).execute()
    return response.data if hasattr(response, "data") else response

# ======================
# BAN SYSTEM
# ======================
@app.post("/admin/ban")
def ban_user(data: BanRequest, password: str):
    role = auth(password)

    if role == "mod":
        until = datetime.utcnow() + timedelta(hours=1)
    elif role == "mod2":
        until = datetime.utcnow() + timedelta(hours=24)
    elif role == "admin":
        until = None  # kalıcı
    else:
        raise HTTPException(status_code=403, detail="Yetkiniz yok")

    # Ban işlemi
    supabase.table("users").update({
        "is_banned": True,
        "banned_until": until
    }).eq("id", data.user_id).execute()

    # Ban log
    supabase.table("ban_logs").insert({
        "user_id": data.user_id,
        "banned_by": role,
        "duration": "permanent" if until is None else str(until),
        "reason": data.reason
    }).execute()

    return {"status": "banned", "until": until}

# ======================
# UNBAN (ADMIN ONLY)
# ======================
@app.post("/admin/unban/{user_id}")
def unban_user(user_id: str, password: str):
    role = auth(password)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Sadece admin")

    supabase.table("users").update({
        "is_banned": False,
        "banned_until": None
    }).eq("id", user_id).execute()

    return {"status": "unbanned"}

# ======================
# DELETE USER (ADMIN)
# ======================
@app.delete("/admin/delete_user/{user_id}")
def delete_user(user_id: str, password: str):
    role = auth(password)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok")

    supabase.table("messages").delete().eq("user_id", user_id).execute()
    supabase.table("chats").delete().eq("user_id", user_id).execute()
    supabase.table("users").delete().eq("id", user_id).execute()

    return {"status": "deleted"}
