from flask import Flask, request, jsonify, render_template_string
from supabase import create_client
import uuid, datetime

# ================= CONFIG =================
SUPABASE_URL = "https://XXXX.supabase.co"
SUPABASE_KEY = "SERVICE_ROLE_KEY"   # 👑 KRAL ANAHTAR
OWNER_USERNAME = "burak"           # 👑 FULL YETKİ

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

# ================= HELPERS =================
def now():
    return datetime.datetime.utcnow().isoformat()

def is_banned(username):
    r = supabase.table("users").select("banned").eq("username", username).execute()
    return bool(r.data and r.data[0]["banned"])

# ================= UI =================
HTML = """
<!doctype html>
<html>
<head>
<title>BurakGPT</title>
<style>
body{background:#0f0f0f;color:#eee;font-family:Arial}
.box{max-width:900px;margin:auto;padding:20px}
input,button{padding:10px;margin:5px;background:#1e1e1e;color:#fff;border:1px solid #444}
button{cursor:pointer}
.chat{height:300px;overflow:auto;border:1px solid #333;padding:10px}
.msg{margin:4px 0}
.admin{margin-top:20px;padding:10px;border:1px solid #333}
</style>
</head>

<body>
<div class="box">
<h2>🔥 BurakGPT</h2>

<input id="username" placeholder="Kullanıcı adı">
<button onclick="join()">Giriş</button>

<div class="chat" id="chat"></div>

<input id="msg" placeholder="Mesaj">
<button onclick="send()">Gönder</button>

<div class="admin">
<h3>👑 Admin Panel</h3>
<input id="target" placeholder="Username">
<button onclick="ban()">Ban</button>
<button onclick="unban()">Unban</button>
<button onclick="del()">Hesabı Sil</button>
</div>
</div>

<script>
let me = ""

function join(){
  me = username.value
  fetch("/join",{method:"POST",headers:{'Content-Type':'application/json'},
  body:JSON.stringify({username:me})})
}

function send(){
  fetch("/chat",{method:"POST",headers:{'Content-Type':'application/json'},
  body:JSON.stringify({username:me,text:msg.value})})
  msg.value=""
}

function load(){
 fetch("/chat").then(r=>r.json()).then(d=>{
  chat.innerHTML=""
  d.forEach(m=>{
   chat.innerHTML += `<div class="msg"><b>${m.username}</b>: ${m.text}</div>`
  })
 })
}

function ban(){
 fetch("/ban",{method:"POST",headers:{'Content-Type':'application/json'},
 body:JSON.stringify({admin:me,target:target.value})})
}

function unban(){
 fetch("/unban",{method:"POST",headers:{'Content-Type':'application/json'},
 body:JSON.stringify({admin:me,target:target.value})})
}

function del(){
 fetch("/delete",{method:"POST",headers:{'Content-Type':'application/json'},
 body:JSON.stringify({admin:me,target:target.value})})
}

setInterval(load,2000)
</script>
</body>
</html>
"""

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/join", methods=["POST"])
def join():
    u = request.json["username"]
    supabase.table("users").upsert({
        "username": u,
        "banned": False
    }).execute()
    return jsonify(ok=True)

@app.route("/chat", methods=["GET","POST"])
def chat():
    if request.method == "POST":
        d = request.json
        if is_banned(d["username"]):
            return jsonify(error="banned"),403

        supabase.table("messages").insert({
            "id": str(uuid.uuid4()),
            "username": d["username"],
            "text": d["text"],
            "created_at": now()
        }).execute()
        return jsonify(ok=True)

    r = supabase.table("messages").select("*").order("created_at").limit(100).execute()
    return jsonify(r.data)

# ================= ADMIN =================
def owner_only(admin):
    return admin == OWNER_USERNAME

@app.route("/ban", methods=["POST"])
def ban():
    d = request.json
    if not owner_only(d["admin"]):
        return jsonify(error="yetki yok"),403

    supabase.table("users").update({"banned": True}).eq("username", d["target"]).execute()
    return jsonify(ok=True)

@app.route("/unban", methods=["POST"])
def unban():
    d = request.json
    if not owner_only(d["admin"]):
        return jsonify(error="yetki yok"),403

    supabase.table("users").update({"banned": False}).eq("username", d["target"]).execute()
    return jsonify(ok=True)

@app.route("/delete", methods=["POST"])
def delete():
    d = request.json
    if not owner_only(d["admin"]):
        return jsonify(error="yetki yok"),403

    supabase.table("users").delete().eq("username", d["target"]).execute()
    supabase.table("messages").delete().eq("username", d["target"]).execute()
    return jsonify(ok=True)

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
