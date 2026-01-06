from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
from supabase import create_client
import os

app = FastAPI()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# ---------- ROLE CHECK ----------

def get_role(password: str):
    if password == os.getenv("ADMIN_PASSWORD"):
        return "admin"
    if password == os.getenv("MOD2_PASSWORD"):
        return "ban_admin"
    if password == os.getenv("MOD_PASSWORD"):
        return "mod"
    return None

# ---------- CHAT VIEW ----------

@app.get("/panel/chat")
def view_chat(password: str):
    role = get_role(password)
    if role not in ["admin", "ban_admin", "mod"]:
        raise HTTPException(403)

    return supabase.table("messages").select("*").order("created_at").execute().data

# ---------- BAN ----------

@app.post("/panel/ban")
def ban_user(username: str, minutes: int, password: str):
    role = get_role(password)

    if role is None:
        raise HTTPException(403)

    if role == "mod" and minutes > 60:
        raise HTTPException(403, "Mod max 1 saat ban atabilir")

    if role == "ban_admin" and minutes > 1440:
        raise HTTPException(403, "Ban admin max 1 gün")

    if role == "admin":
        pass  # limitsiz

    banned_until = datetime.utcnow() + timedelta(minutes=minutes)

    supabase.table("users").update({
        "banned_until": banned_until.isoformat()
    }).eq("username", username).execute()

    return {"status": "banned", "until": banned_until}

# ---------- UNBAN ----------

@app.post("/panel/unban")
def unban_user(username: str, password: str):
    role = get_role(password)
    if role not in ["admin", "ban_admin"]:
        raise HTTPException(403)

    supabase.table("users").update({
        "banned_until": None
    }).eq("username", username).execute()

    return {"status": "unbanned"}

# ---------- DELETE USER ----------

@app.delete("/panel/user")
def delete_user(username: str, password: str):
    if get_role(password) != "admin":
        raise HTTPException(403)

    supabase.table("users").delete().eq("username", username).execute()
    return {"status": "deleted"}
