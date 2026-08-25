# -*- coding: utf-8 -*-
"""
๐‘‘ Mr.krit AI learning Ultra XXXX - Central Cloud License & Telemetry Server
=============================================================================
เธฃเธฐเธเธเธจเธนเธเธขเนเธเธฅเธฒเธเธเธฑเธ”เธเธฒเธฃเธเธตเธขเนเธชเธดเธ—เธเธดเนเธเธฒเธฃเนเธเนเธเธฒเธ, เธ•เธฃเธงเธเธเธฑเธเธเธญเธ—เธญเธญเธเนเธฅเธเนเธชเธ”, เนเธฅเธฐเนเธ”เธเธเธญเธฃเนเธ”เธซเธฅเธฑเธเธเนเธฒเธ (Vercel Native)
"""

import os
import sys
import json
import time
import secrets
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, HTTPException, Depends, status, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# -----------------------------------------------------------------------------
# CONFIGURATION & DATABASE (Vercel Serverless Writable Path)
# -----------------------------------------------------------------------------
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "mrkrit8888")
SECRET_TOKEN_KEY = os.getenv("SECRET_TOKEN_KEY", "MR_KRIT_ULTRA_SECURITY_SECRET_2026")

# In Vercel serverless environment, /tmp is the only writable directory
DB_FILE = "/tmp/central_hub.db" if os.environ.get("VERCEL") else os.path.join(os.path.dirname(os.path.abspath(__file__)), "central_hub.db")

app = FastAPI(
    title="Mr.krit AI Central Cloud Gateway",
    version="2.0.0",
    description="Central License Authentication & Telemetry Hub"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Table: License Keys
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS license_keys (
                key_code TEXT PRIMARY KEY,
                customer_name TEXT,
                customer_contact TEXT,
                hwid_bound TEXT DEFAULT '',
                created_at TEXT,
                expires_at TEXT,
                status TEXT DEFAULT 'ACTIVE',
                duration_days INTEGER,
                max_terminals INTEGER DEFAULT 1,
                notes TEXT DEFAULT ''
            )
        """)
        
        # Table: Bot Telemetry / Active Sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_telemetry (
                hwid TEXT PRIMARY KEY,
                key_code TEXT,
                account_login TEXT,
                broker_server TEXT,
                balance REAL DEFAULT 0.0,
                equity REAL DEFAULT 0.0,
                profit_today REAL DEFAULT 0.0,
                open_orders INTEGER DEFAULT 0,
                bot_version TEXT DEFAULT 'v20.5',
                last_seen REAL,
                ip_address TEXT DEFAULT '',
                status TEXT DEFAULT 'ONLINE',
                remote_command TEXT DEFAULT 'NONE'
            )
        """)
        
        # Table: Admin Sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_sessions (
                token TEXT PRIMARY KEY,
                created_at REAL,
                expires_at REAL
            )
        """)
        
        # Default Master VIP Key
        cursor.execute("SELECT COUNT(*) as count FROM license_keys")
        if cursor.fetchone()["count"] == 0:
            now = datetime.now()
            exp = now + timedelta(days=365)
            cursor.execute("""
                INSERT INTO license_keys (key_code, customer_name, customer_contact, hwid_bound, created_at, expires_at, status, duration_days, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "KRIT-VIP-DEMO-8888-9999",
                "Mr. Krit (Master Admin)",
                "admin@mrkrit.ai",
                "",
                now.strftime("%Y-%m-%d %H:%M:%S"),
                exp.strftime("%Y-%m-%d %H:%M:%S"),
                "ACTIVE",
                365,
                "Master Initial Key"
            ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database init notice: {e}")

init_db()

# -----------------------------------------------------------------------------
# PYDANTIC MODELS
# -----------------------------------------------------------------------------
class VerifyRequest(BaseModel):
    key: str
    hwid: str
    bot_version: Optional[str] = "v20.5"

class HeartbeatRequest(BaseModel):
    key: str
    hwid: str
    account_login: Optional[str] = ""
    broker_server: Optional[str] = ""
    balance: Optional[float] = 0.0
    equity: Optional[float] = 0.0
    profit_today: Optional[float] = 0.0
    open_orders: Optional[int] = 0
    bot_version: Optional[str] = "v20.5"

class CreateKeyRequest(BaseModel):
    customer_name: str
    customer_contact: Optional[str] = ""
    duration_days: int = 30
    notes: Optional[str] = ""

# -----------------------------------------------------------------------------
# CLIENT BOT API ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/")
@app.get("/api/index")
@app.get("/api/index/")
def health_check():
    init_db()
    return {
        "status": "online",
        "service": "Mr.krit AI Central Cloud Gateway (Vercel Global Edge)",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "admin_portal": "/admin"
    }

@app.get("/admin", response_class=HTMLResponse)
@app.get("/api/index/admin", response_class=HTMLResponse)
def get_admin_portal():
    return HTMLResponse(content=ADMIN_HTML)

@app.post("/api/v1/license/verify")
def verify_license(req: VerifyRequest, request: Request):
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM license_keys WHERE key_code = ?", (req.key.strip(),))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return {
            "valid": False,
            "status": "INVALID_KEY",
            "message": "โ เนเธกเนเธเธเธเธตเธขเนเธเธตเนเนเธเธฃเธฐเธเธ เธเธฃเธธเธ“เธฒเธ•เธฃเธงเธเธชเธญเธเธเธงเธฒเธกเธ–เธนเธเธ•เนเธญเธ"
        }
    
    key_data = dict(row)
    now = datetime.now()
    expires_at = datetime.strptime(key_data["expires_at"], "%Y-%m-%d %H:%M:%S")
    
    if key_data["status"] in ["BANNED", "REVOKED"]:
        conn.close()
        return {
            "valid": False,
            "status": key_data["status"],
            "message": f"๐ซ เธชเธดเธ—เธเธดเนเธเธฒเธฃเนเธเนเธเธฒเธเธ–เธนเธเธฃเธฐเธเธฑเธ (เธชเธ–เธฒเธเธฐ: {key_data['status']})"
        }
    
    if now > expires_at:
        cursor.execute("UPDATE license_keys SET status = 'EXPIRED' WHERE key_code = ?", (req.key.strip(),))
        conn.commit()
        conn.close()
        return {
            "valid": False,
            "status": "EXPIRED",
            "message": f"โณ เธชเธดเธ—เธเธดเนเธเธฒเธฃเนเธเนเธเธฒเธเธซเธกเธ”เธญเธฒเธขเธธเนเธฅเนเธงเน€เธกเธทเนเธญ {key_data['expires_at']}"
        }
    
    bound_hwid = (key_data.get("hwid_bound") or "").strip()
    if bound_hwid == "":
        cursor.execute("UPDATE license_keys SET hwid_bound = ? WHERE key_code = ?", (req.hwid.strip(), req.key.strip()))
        conn.commit()
        bound_hwid = req.hwid.strip()
    elif bound_hwid != req.hwid.strip():
        conn.close()
        return {
            "valid": False,
            "status": "HWID_MISMATCH",
            "message": f"โ ๏ธ เธเธตเธขเนเธเธตเนเธ–เธนเธเธเธนเธเนเธงเนเธเธฑเธเน€เธเธฃเธทเนเธญเธเธญเธทเนเธเนเธฅเนเธง ({bound_hwid[:4]}****) เธเธฃเธธเธ“เธฒเธ•เธดเธ”เธ•เนเธญเนเธญเธ”เธกเธดเธเน€เธเธทเนเธญเธขเนเธฒเธขเน€เธเธฃเธทเนเธญเธ"
        }
    
    days_left = max(0, (expires_at - now).days)
    hours_left = max(0, int((expires_at - now).total_seconds() // 3600))
    
    conn.close()
    return {
        "valid": True,
        "status": "ACTIVE",
        "customer_name": key_data["customer_name"],
        "expires_at": key_data["expires_at"],
        "days_left": days_left,
        "hours_left": hours_left,
        "hwid": bound_hwid,
        "message": f"โ… เธชเธดเธ—เธเธดเนเธเธฒเธฃเนเธเนเธเธฒเธเธ–เธนเธเธ•เนเธญเธ (เน€เธซเธฅเธทเธญเน€เธงเธฅเธฒ {days_left} เธงเธฑเธ)"
    }

@app.post("/api/v1/telemetry/heartbeat")
def record_heartbeat(req: HeartbeatRequest, request: Request):
    init_db()
    client_ip = request.client.host if request.client else ""
    now_ts = time.time()
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT status FROM license_keys WHERE key_code = ?", (req.key.strip(),))
    k = cursor.fetchone()
    if not k or k["status"] in ["BANNED", "REVOKED"]:
        conn.close()
        return {"status": "error", "command": "STOP", "message": "License invalid or revoked"}
    
    cursor.execute("""
        INSERT INTO bot_telemetry (
            hwid, key_code, account_login, broker_server, balance, equity, 
            profit_today, open_orders, bot_version, last_seen, ip_address, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ONLINE')
        ON CONFLICT(hwid) DO UPDATE SET
            key_code = excluded.key_code,
            account_login = excluded.account_login,
            broker_server = excluded.broker_server,
            balance = excluded.balance,
            equity = excluded.equity,
            profit_today = excluded.profit_today,
            open_orders = excluded.open_orders,
            bot_version = excluded.bot_version,
            last_seen = excluded.last_seen,
            ip_address = excluded.ip_address,
            status = 'ONLINE'
    """, (
        req.hwid.strip(), req.key.strip(), req.account_login, req.broker_server,
        req.balance, req.equity, req.profit_today, req.open_orders,
        req.bot_version, now_ts, client_ip
    ))
    
    cursor.execute("SELECT remote_command FROM bot_telemetry WHERE hwid = ?", (req.hwid.strip(),))
    res = cursor.fetchone()
    cmd = res["remote_command"] if res else "NONE"
    
    conn.commit()
    conn.close()
    return {"status": "ok", "command": cmd, "server_time": datetime.now().strftime("%H:%M:%S")}

# -----------------------------------------------------------------------------
# ADMIN API & WEB DASHBOARD
# -----------------------------------------------------------------------------
def check_admin_token(token: Optional[str] = None):
    init_db()
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin_sessions WHERE token = ? AND expires_at > ?", (token, time.time()))
    session = cursor.fetchone()
    conn.close()
    if not session:
        raise HTTPException(status_code=401, detail="Session expired")
    return True

@app.post("/api/admin/login")
def admin_login(username: str = Form(...), password: str = Form(...)):
    init_db()
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = secrets.token_hex(32)
        exp = time.time() + 86400 * 7
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO admin_sessions (token, created_at, expires_at) VALUES (?, ?, ?)", (token, time.time(), exp))
        conn.commit()
        conn.close()
        return {"success": True, "token": token}
    return {"success": False, "message": "เธเธทเนเธญเธเธนเนเนเธเนเธซเธฃเธทเธญเธฃเธซเธฑเธชเธเนเธฒเธเนเธกเนเธ–เธนเธเธ•เนเธญเธ"}

@app.get("/api/admin/overview")
def admin_overview(token: str):
    check_admin_token(token)
    conn = get_db()
    cursor = conn.cursor()
    
    now_ts = time.time()
    online_threshold = now_ts - 90
    
    cursor.execute("UPDATE bot_telemetry SET status = 'OFFLINE' WHERE last_seen < ?", (online_threshold,))
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) as total FROM license_keys")
    total_keys = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as active FROM license_keys WHERE status = 'ACTIVE'")
    active_keys = cursor.fetchone()["active"]
    
    cursor.execute("SELECT COUNT(*) as online FROM bot_telemetry WHERE status = 'ONLINE'")
    online_bots = cursor.fetchone()["online"]
    
    cursor.execute("SELECT SUM(balance) as total_bal, SUM(profit_today) as total_prof FROM bot_telemetry WHERE status = 'ONLINE'")
    fin = cursor.fetchone()
    total_balance = fin["total_bal"] or 0.0
    total_profit = fin["total_prof"] or 0.0
    
    cursor.execute("SELECT * FROM bot_telemetry ORDER BY last_seen DESC LIMIT 50")
    bots = [dict(r) for r in cursor.fetchall()]
    for b in bots:
        b["is_online"] = (now_ts - b["last_seen"]) <= 90
        b["last_seen_sec"] = int(now_ts - b["last_seen"])
    
    cursor.execute("SELECT * FROM license_keys ORDER BY created_at DESC")
    keys = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "stats": {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "online_bots": online_bots,
            "total_balance": round(total_balance, 2),
            "total_profit": round(total_profit, 2)
        },
        "bots": bots,
        "keys": keys
    }

@app.post("/api/admin/keys/create")
def admin_create_key(req: CreateKeyRequest, token: str):
    check_admin_token(token)
    conn = get_db()
    cursor = conn.cursor()
    
    random_part = secrets.token_hex(3).upper()
    key_code = f"KRIT-{req.duration_days}D-{secrets.token_hex(2).upper()}-{random_part}"
    
    now = datetime.now()
    if req.duration_days >= 20000:
        exp = now + timedelta(days=29000)
    else:
        exp = now + timedelta(days=req.duration_days)
        
    cursor.execute("""
        INSERT INTO license_keys (
            key_code, customer_name, customer_contact, hwid_bound, created_at, 
            expires_at, status, duration_days, notes
        ) VALUES (?, ?, ?, '', ?, ?, 'ACTIVE', ?, ?)
    """, (
        key_code, req.customer_name, req.customer_contact,
        now.strftime("%Y-%m-%d %H:%M:%S"), exp.strftime("%Y-%m-%d %H:%M:%S"),
        req.duration_days, req.notes
    ))
    conn.commit()
    conn.close()
    return {"success": True, "key_code": key_code, "expires_at": exp.strftime("%Y-%m-%d %H:%M:%S")}

@app.post("/api/admin/keys/action")
def admin_key_action(key_code: str = Form(...), action: str = Form(...), token: str = Form(...)):
    check_admin_token(token)
    conn = get_db()
    cursor = conn.cursor()
    
    if action == "RESET_HWID":
        cursor.execute("UPDATE license_keys SET hwid_bound = '' WHERE key_code = ?", (key_code,))
    elif action == "BAN":
        cursor.execute("UPDATE license_keys SET status = 'BANNED' WHERE key_code = ?", (key_code,))
    elif action == "ACTIVATE":
        cursor.execute("UPDATE license_keys SET status = 'ACTIVE' WHERE key_code = ?", (key_code,))
    elif action == "DELETE":
        cursor.execute("DELETE FROM license_keys WHERE key_code = ?", (key_code,))
    elif action == "EXTEND_30D":
        cursor.execute("SELECT expires_at FROM license_keys WHERE key_code = ?", (key_code,))
        r = cursor.fetchone()
        if r:
            cur_exp = datetime.strptime(r["expires_at"], "%Y-%m-%d %H:%M:%S")
            new_exp = max(datetime.now(), cur_exp) + timedelta(days=30)
            cursor.execute("UPDATE license_keys SET expires_at = ?, status = 'ACTIVE' WHERE key_code = ?", (new_exp.strftime("%Y-%m-%d %H:%M:%S"), key_code))
            
    conn.commit()
    conn.close()
    return {"success": True}

# -----------------------------------------------------------------------------
# ULTRA PREMIUM GOLD & BLACK ADMIN DASHBOARD
# -----------------------------------------------------------------------------
ADMIN_HTML = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>๐‘‘ MR.KRIT AI ULTRA โ€” Cloud Command Center</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=Prompt:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --g1:#FFD700;--g2:#FFA500;--g3:#B8860B;--g4:#F5C518;
  --gg:rgba(255,215,0,.35);--gs:rgba(255,215,0,.1);
  --b1:#000;--b2:#0a0a0a;--b3:#111;--b4:#161616;--b5:#1c1c1c;
  --tp:#F5F5F0;--ts:#9E9E8A;--tm:#4a4a3a;
  --green:#00e676;--red:#ff3d5a;
  --bor:rgba(255,215,0,.14);--borh:rgba(255,215,0,.45);
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:var(--b1);color:var(--tp);font-family:'Outfit','Prompt',sans-serif;min-height:100vh;overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 50% at 10% 0%,rgba(255,215,0,.05) 0%,transparent 60%),radial-gradient(ellipse 60% 40% at 90% 100%,rgba(255,165,0,.04) 0%,transparent 60%);pointer-events:none;z-index:0}

/* NAVBAR */
.navbar{position:sticky;top:0;z-index:200;display:flex;align-items:center;justify-content:space-between;padding:0 40px;height:68px;background:rgba(0,0,0,.94);backdrop-filter:blur(20px);border-bottom:1px solid var(--bor)}
.navbar::after{content:'';position:absolute;bottom:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--g1),transparent)}
.nav-brand{display:flex;align-items:center;gap:14px}
.nav-crown{width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,var(--g1),var(--g2));display:flex;align-items:center;justify-content:center;font-size:18px;box-shadow:0 0 16px var(--gg)}
.nav-title{font-size:16px;font-weight:800;letter-spacing:1.5px;background:linear-gradient(135deg,var(--g1),var(--g4),var(--g2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.nav-subtitle{font-size:10px;letter-spacing:3px;color:var(--tm);font-weight:500;text-transform:uppercase;margin-top:1px}
.nav-right{display:flex;align-items:center;gap:12px}
.live-ind{display:flex;align-items:center;gap:7px;font-size:12px;color:var(--g1);font-weight:600}
.live-dot{width:8px;height:8px;border-radius:50%;background:var(--g1);box-shadow:0 0 8px var(--g1),0 0 16px var(--gg);animation:pulse 1.8s infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(.7)}}

/* LAYOUT */
.layout{display:flex;min-height:calc(100vh - 68px)}

/* SIDEBAR */
.sidebar{width:240px;flex-shrink:0;background:var(--b2);border-right:1px solid var(--bor);padding:28px 16px;display:flex;flex-direction:column;gap:6px;position:sticky;top:68px;height:calc(100vh - 68px);overflow-y:auto}
.sidebar-label{font-size:10px;font-weight:700;letter-spacing:2.5px;color:var(--tm);text-transform:uppercase;padding:0 12px;margin:14px 0 6px}
.nav-item{display:flex;align-items:center;gap:11px;padding:11px 14px;border-radius:10px;font-size:13.5px;font-weight:500;cursor:pointer;transition:all .2s;color:var(--ts);border:1px solid transparent}
.nav-item:hover{background:var(--gs);color:var(--g1);border-color:var(--bor)}
.nav-item.active{background:linear-gradient(135deg,rgba(255,215,0,.16),rgba(255,165,0,.07));color:var(--g1);font-weight:700;border-color:rgba(255,215,0,.28);box-shadow:0 0 12px rgba(255,215,0,.07)}
.nav-icon{font-size:16px;width:22px;text-align:center}
.sidebar-bottom{margin-top:auto}
.btn-logout{width:100%;display:flex;align-items:center;justify-content:center;gap:8px;padding:12px;border-radius:10px;border:1px solid rgba(255,61,90,.3);background:rgba(255,61,90,.07);color:#ff3d5a;font-size:13px;font-weight:600;cursor:pointer;transition:all .2s;font-family:'Outfit',sans-serif}
.btn-logout:hover{background:rgba(255,61,90,.2);border-color:#ff3d5a}

/* MAIN */
.main{flex:1;padding:32px 36px;overflow-x:hidden}
.page-header{margin-bottom:30px}
.page-header h1{font-size:26px;font-weight:800}
.page-header h1 span{color:var(--g1)}
.breadcrumb{font-size:11px;color:var(--tm);margin-top:5px;letter-spacing:1.5px}

/* STATS */
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin-bottom:28px}
.stat-card{background:var(--b3);border:1px solid var(--bor);border-radius:16px;padding:22px 24px;position:relative;overflow:hidden;transition:all .3s}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--g1),transparent);opacity:0;transition:opacity .3s}
.stat-card:hover{border-color:var(--borh);transform:translateY(-2px);box-shadow:0 8px 32px rgba(255,215,0,.09)}
.stat-card:hover::before{opacity:1}
.stat-bg{position:absolute;right:-10px;bottom:-10px;font-size:80px;opacity:.04;line-height:1}
.stat-label{font-size:10.5px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--tm)}
.stat-value{font-size:36px;font-weight:900;margin:10px 0 4px;letter-spacing:-1px}
.stat-value.gold{color:var(--g1);text-shadow:0 0 20px var(--gg)}
.stat-value.green{color:var(--green)}
.stat-sub{font-size:12px;color:var(--tm)}
.stat-badge{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;background:var(--gs);color:var(--g1);border:1px solid rgba(255,215,0,.22)}

/* PANEL */
.panel{background:var(--b3);border:1px solid var(--bor);border-radius:18px;overflow:hidden;margin-bottom:24px}
.panel-header{display:flex;align-items:center;justify-content:space-between;padding:20px 26px;border-bottom:1px solid var(--bor);background:rgba(255,215,0,.02)}
.ph-left{display:flex;align-items:center;gap:12px}
.panel-icon{width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,rgba(255,215,0,.18),rgba(255,165,0,.08));border:1px solid rgba(255,215,0,.22);display:flex;align-items:center;justify-content:center;font-size:16px}
.panel-title{font-size:15px;font-weight:700}
.panel-sub{font-size:11px;color:var(--tm);margin-top:2px}

/* BUTTONS */
.btn{display:inline-flex;align-items:center;gap:7px;padding:9px 18px;border-radius:10px;font-size:13px;font-weight:700;cursor:pointer;border:none;transition:all .2s;white-space:nowrap;font-family:'Outfit',sans-serif}
.btn-gold{background:linear-gradient(135deg,var(--g1),var(--g2));color:#000;box-shadow:0 4px 16px rgba(255,215,0,.32)}
.btn-gold:hover{transform:translateY(-1px);box-shadow:0 6px 24px rgba(255,215,0,.5);filter:brightness(1.05)}
.btn-out{background:transparent;color:var(--g1);border:1px solid rgba(255,215,0,.32)}
.btn-out:hover{background:var(--gs);border-color:var(--g1)}
.btn-dan{background:rgba(255,61,90,.09);color:var(--red);border:1px solid rgba(255,61,90,.28)}
.btn-dan:hover{background:rgba(255,61,90,.22);border-color:var(--red)}
.btn-act{background:rgba(0,230,118,.09);color:var(--green);border:1px solid rgba(0,230,118,.28)}
.btn-sm{padding:6px 13px;font-size:11.5px;border-radius:7px}
.btn-xs{padding:4px 10px;font-size:11px;border-radius:6px}

/* TABLE */
.tw{overflow-x:auto}
table{width:100%;border-collapse:collapse}
thead th{padding:13px 16px;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--tm);border-bottom:1px solid var(--bor);white-space:nowrap;background:rgba(0,0,0,.3)}
tbody td{padding:15px 16px;font-size:13.5px;border-bottom:1px solid rgba(255,215,0,.04)}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:rgba(255,215,0,.025)}

/* BADGES */
.badge{display:inline-flex;align-items:center;gap:5px;padding:4px 11px;border-radius:20px;font-size:11px;font-weight:700}
.bdot{width:6px;height:6px;border-radius:50%;background:currentColor}
.b-on{background:rgba(0,230,118,.11);color:var(--green);border:1px solid rgba(0,230,118,.28)}
.b-off{background:rgba(74,74,58,.18);color:var(--tm);border:1px solid rgba(74,74,58,.28)}
.b-act{background:rgba(255,215,0,.11);color:var(--g1);border:1px solid rgba(255,215,0,.28)}
.b-exp{background:rgba(255,165,0,.11);color:#FFA500;border:1px solid rgba(255,165,0,.28)}
.b-ban{background:rgba(255,61,90,.11);color:var(--red);border:1px solid rgba(255,61,90,.28)}

/* EMPTY */
.empty{text-align:center;padding:50px 20px;color:var(--tm)}
.empty-icon{font-size:44px;margin-bottom:12px;opacity:.45}
.empty p{font-size:14px}

/* LOGIN */
#login-view{position:fixed;inset:0;z-index:500;display:flex;align-items:center;justify-content:center;background:#000}
#login-view::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 70% 60% at 50% 50%,rgba(255,215,0,.055) 0%,transparent 70%)}
.lc{position:relative;width:430px;max-width:95vw}
.l-logo{text-align:center;margin-bottom:36px}
.l-crown{width:68px;height:68px;border-radius:20px;margin:0 auto 16px;background:linear-gradient(135deg,var(--g1),var(--g2));display:flex;align-items:center;justify-content:center;font-size:32px;box-shadow:0 0 40px rgba(255,215,0,.38),0 0 80px rgba(255,215,0,.13);animation:float 3s ease-in-out infinite}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
.l-title{font-size:23px;font-weight:900;letter-spacing:1px}
.l-title span{background:linear-gradient(135deg,var(--g1),var(--g2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.l-desc{font-size:13px;color:var(--tm);margin-top:6px}
.l-card{background:var(--b3);border:1px solid rgba(255,215,0,.18);border-radius:22px;padding:36px;box-shadow:0 24px 80px rgba(0,0,0,.8)}
.fg{margin-bottom:20px}
.fl{display:block;font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--tm);margin-bottom:8px}
.fi{width:100%;padding:13px 16px;background:var(--b5);border:1px solid rgba(255,215,0,.13);border-radius:11px;color:var(--tp);font-size:14px;outline:none;transition:all .2s;font-family:'Outfit',sans-serif}
.fi:focus{border-color:rgba(255,215,0,.48);box-shadow:0 0 0 3px rgba(255,215,0,.07)}
.fi::placeholder{color:var(--tm)}
.l-btn{width:100%;padding:14px;border:none;border-radius:11px;background:linear-gradient(135deg,var(--g1),var(--g2));color:#000;font-size:15px;font-weight:800;cursor:pointer;letter-spacing:1px;transition:all .25s;box-shadow:0 4px 20px rgba(255,215,0,.38);margin-top:8px;font-family:'Outfit',sans-serif}
.l-btn:hover{transform:translateY(-2px);box-shadow:0 8px 32px rgba(255,215,0,.52);filter:brightness(1.05)}
.l-foot{text-align:center;margin-top:20px;font-size:12px;color:var(--tm)}

/* MODAL */
.mover{display:none;position:fixed;inset:0;z-index:900;background:rgba(0,0,0,.86);backdrop-filter:blur(10px);align-items:center;justify-content:center}
.mbox{background:var(--b3);border:1px solid rgba(255,215,0,.22);border-radius:22px;padding:36px;width:95%;max-width:500px;box-shadow:0 30px 80px rgba(0,0,0,.9);position:relative}
.mtitle{font-size:19px;font-weight:800;color:var(--g1);margin-bottom:24px}
.mclose{position:absolute;top:18px;right:20px;background:none;border:none;color:var(--tm);font-size:22px;cursor:pointer;transition:color .2s}
.mclose:hover{color:var(--red)}

/* SCROLLBAR */
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--b2)}
::-webkit-scrollbar-thumb{background:var(--g3);border-radius:10px}

/* ANIMATIONS */
@keyframes fadeUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
.fu{animation:fadeUp .4s ease forwards}

@media(max-width:1100px){.stats-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:768px){.sidebar{display:none}.main{padding:20px 16px}.stats-grid{grid-template-columns:1fr 1fr;gap:12px}.navbar{padding:0 16px}}
</style>
</head>
<body>

<!-- LOGIN -->
<div id="login-view">
  <div class="lc">
    <div class="l-logo">
      <div class="l-crown">๐‘‘</div>
      <div class="l-title"><span>MR.KRIT AI ULTRA</span></div>
      <div class="l-desc">Central Cloud Command Center ยท Restricted Access</div>
    </div>
    <div class="l-card">
      <div class="fg"><label class="fl">Username</label><input type="text" id="login-user" class="fi" placeholder="Enter username" value="admin"></div>
      <div class="fg"><label class="fl">Password</label><input type="password" id="login-pass" class="fi" placeholder="โ€ขโ€ขโ€ขโ€ขโ€ขโ€ขโ€ขโ€ขโ€ขโ€ข" onkeydown="if(event.key==='Enter')doLogin()"></div>
      <button class="l-btn" onclick="doLogin()" id="login-btn">๐” ACCESS SYSTEM</button>
      <div id="login-err" style="color:#ff3d5a;font-size:13px;text-align:center;margin-top:14px;display:none;"></div>
    </div>
    <div class="l-foot">๐”’ Encrypted Session ยท Gold Tier Security</div>
  </div>
</div>

<!-- NAVBAR -->
<nav class="navbar" id="main-nav" style="display:none">
  <div class="nav-brand">
    <div class="nav-crown">๐‘‘</div>
    <div><div class="nav-title">MR.KRIT AI ULTRA ยท CLOUD HUB</div><div class="nav-subtitle">Command Center v2.0</div></div>
  </div>
  <div class="nav-right">
    <div class="live-ind"><div class="live-dot"></div> LIVE MONITORING</div>
    <button class="btn btn-out btn-sm" onclick="fetchDash()" style="margin-left:16px">๐” Refresh</button>
  </div>
</nav>

<!-- LAYOUT -->
<div class="layout" id="main-layout" style="display:none">
  <aside class="sidebar">
    <div class="sidebar-label">Main Menu</div>
    <div class="nav-item active"><span class="nav-icon">๐ </span> Overview</div>
    <div class="nav-item"><span class="nav-icon">๐ฐ๏ธ</span> Bot Radar</div>
    <div class="nav-item"><span class="nav-icon">๐”‘</span> License Keys</div>
    <div class="sidebar-label">System</div>
    <div class="nav-item" onclick="fetchDash()"><span class="nav-icon">๐”</span> Sync Data</div>
    <div class="sidebar-bottom">
      <button class="btn-logout" onclick="doLogout()">๐ช Sign Out</button>
    </div>
  </aside>

  <main class="main">
    <div class="page-header fu">
      <h1>Command <span>Overview</span></h1>
      <div class="breadcrumb">DASHBOARD ยท OVERVIEW ยท REAL-TIME</div>
    </div>

    <div class="stats-grid fu">
      <div class="stat-card"><div class="stat-bg">๐ฐ๏ธ</div><div class="stat-label">Active Live Bots</div><div class="stat-value green" id="s-online">0</div><div class="stat-sub">Bots reporting in real-time</div></div>
      <div class="stat-card"><div class="stat-bg">๐”‘</div><div class="stat-label">Active License Keys</div><div class="stat-value gold" id="s-keys">0/0</div><div class="stat-sub">Active / Total issued</div></div>
      <div class="stat-card"><div class="stat-bg">๐’ฐ</div><div class="stat-label">Total Portfolio Balance</div><div class="stat-value gold" id="s-bal">$0.00</div><div class="stat-sub">Combined live balance</div></div>
      <div class="stat-card"><div class="stat-bg">๐“</div><div class="stat-label">Today's Total Profit</div><div class="stat-value" id="s-prof" style="color:var(--green)">$0.00</div><div class="stat-sub">Profit across all accounts</div></div>
    </div>

    <!-- BOT RADAR PANEL -->
    <div class="panel fu">
      <div class="panel-header">
        <div class="ph-left">
          <div class="panel-icon">๐ฐ๏ธ</div>
          <div><div class="panel-title">Real-Time Bot Telemetry Radar</div><div class="panel-sub">เธเธญเธ—เธ—เธตเนเธญเธญเธเนเธฅเธเนเธชเธ”เนเธฅเธฐเธชเนเธเธชเธฑเธเธเธฒเธ“เน€เธเนเธฒเธกเธฒเธฅเนเธฒเธชเธธเธ”</div></div>
        </div>
        <div style="display:flex;gap:10px;align-items:center">
          <div class="stat-badge" id="bot-badge">0 Online</div>
          <button class="btn btn-out btn-sm" onclick="fetchDash()">๐” Refresh</button>
        </div>
      </div>
      <div class="tw"><table>
        <thead><tr><th>Status</th><th>MT5 Account</th><th>Broker / Server</th><th>Balance / Equity</th><th>Today Profit</th><th>Open Orders</th><th>HWID Machine</th><th>Last Signal</th></tr></thead>
        <tbody id="bot-tb"><tr><td colspan="8"><div class="empty"><div class="empty-icon">๐“ก</div><p>No bots connected at this time</p></div></td></tr></tbody>
      </table></div>
    </div>

    <!-- LICENSE KEYS PANEL -->
    <div class="panel fu">
      <div class="panel-header">
        <div class="ph-left">
          <div class="panel-icon">๐”‘</div>
          <div><div class="panel-title">License Keys Master Management</div><div class="panel-sub">เธฃเธฐเธเธเธญเธญเธเธเธตเธขเน เธเธฑเธ”เธเธฒเธฃเธชเธดเธ—เธเธดเน เนเธฅเธฐเธเธงเธเธเธธเธกเธฅเธนเธเธเนเธฒ</div></div>
        </div>
        <button class="btn btn-gold" onclick="openKM()">โฆ Generate New Key</button>
      </div>
      <div class="tw"><table>
        <thead><tr><th>License Key</th><th>Customer / User</th><th>Status</th><th>HWID Bound</th><th>Expiry Date</th><th>Actions</th></tr></thead>
        <tbody id="key-tb"></tbody>
      </table></div>
    </div>
  </main>
</div>

<!-- MODAL: GENERATE KEY -->
<div id="km" class="mover">
  <div class="mbox">
    <button class="mclose" onclick="closeKM()">โ•</button>
    <div class="mtitle">โฆ Generate New License Key</div>
    <div class="fg"><label class="fl">Customer Name</label><input type="text" id="kn" class="fi" placeholder="เน€เธเนเธ เธเธธเธ“เธชเธกเธเธฒเธข โ€” VIP Client"></div>
    <div class="fg"><label class="fl">License Duration</label>
      <select id="kd" class="fi">
        <option value="7">7 Days โ€” Trial</option>
        <option value="30" selected>30 Days โ€” 1 Month</option>
        <option value="90">90 Days โ€” 3 Months</option>
        <option value="180">180 Days โ€” 6 Months</option>
        <option value="365">365 Days โ€” 1 Year</option>
        <option value="29000">Lifetime โ€” VIP Unlimited</option>
      </select>
    </div>
    <div class="fg"><label class="fl">Notes (Optional)</label><input type="text" id="knt" class="fi" placeholder="เน€เธเนเธ เธเธณเธฃเธฐเนเธฅเนเธงเธ—เธฒเธเนเธฅเธเน"></div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:26px">
      <button class="btn btn-out" onclick="closeKM()">Cancel</button>
      <button class="btn btn-gold" onclick="createKey()">โฆ Confirm & Generate</button>
    </div>
  </div>
</div>

<!-- MODAL: RESULT -->
<div id="rm" class="mover">
  <div class="mbox" style="max-width:460px;text-align:center">
    <button class="mclose" onclick="closeRM()">โ•</button>
    <div style="font-size:48px;margin-bottom:14px">โฆ</div>
    <div style="font-size:18px;font-weight:800;color:var(--g1);margin-bottom:8px">Key Generated Successfully!</div>
    <div style="font-size:12px;color:var(--tm);margin-bottom:20px">Copy and send this key to your customer</div>
    <div style="background:var(--b5);border:1px solid rgba(255,215,0,.28);border-radius:12px;padding:18px 20px;margin-bottom:20px">
      <div id="rk" style="font-size:14px;font-weight:800;color:var(--g1);letter-spacing:1.5px;word-break:break-all"></div>
      <div id="re" style="font-size:12px;color:var(--tm);margin-top:8px"></div>
    </div>
    <button class="btn btn-gold" style="width:100%;justify-content:center" onclick="copyK()">๐“ Copy Key to Clipboard</button>
  </div>
</div>

<script>
let tok = localStorage.getItem('mka_tok') || '';
let lastKey = '';

function checkAuth() {
  if (tok) {
    document.getElementById('login-view').style.display = 'none';
    document.getElementById('main-nav').style.display = 'flex';
    document.getElementById('main-layout').style.display = 'flex';
    fetchDash();
    setInterval(fetchDash, 15000);
  } else {
    document.getElementById('login-view').style.display = 'flex';
    document.getElementById('main-nav').style.display = 'none';
    document.getElementById('main-layout').style.display = 'none';
  }
}

async function doLogin() {
  const btn = document.getElementById('login-btn');
  const err = document.getElementById('login-err');
  const u = document.getElementById('login-user').value;
  const p = document.getElementById('login-pass').value;
  btn.disabled = true; btn.textContent = 'Authenticating...'; err.style.display = 'none';
  const fd = new FormData(); fd.append('username', u); fd.append('password', p);
  try {
    const r = await fetch('/api/admin/login', {method:'POST', body:fd});
    const d = await r.json();
    if (d.success) { tok = d.token; localStorage.setItem('mka_tok', tok); checkAuth(); }
    else { err.textContent = 'โ  ' + (d.message || 'Invalid credentials.'); err.style.display = 'block'; btn.disabled = false; btn.textContent = '๐” ACCESS SYSTEM'; }
  } catch(e) { err.textContent = 'โ  Cannot connect to server.'; err.style.display = 'block'; btn.disabled = false; btn.textContent = '๐” ACCESS SYSTEM'; }
}

function doLogout() { localStorage.removeItem('mka_tok'); tok = ''; checkAuth(); }

async function fetchDash() {
  if (!tok) return;
  try {
    const r = await fetch('/api/admin/overview?token=' + tok);
    if (r.status === 401) { doLogout(); return; }
    const d = await r.json();
    const ob = d.stats.online_bots;
    document.getElementById('s-online').textContent = ob;
    document.getElementById('s-keys').textContent = d.stats.active_keys + '/' + d.stats.total_keys;
    document.getElementById('s-bal').textContent = '$' + d.stats.total_balance.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
    const pe = document.getElementById('s-prof');
    pe.textContent = (d.stats.total_profit >= 0 ? '+' : '') + '$' + Math.abs(d.stats.total_profit).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
    pe.style.color = d.stats.total_profit >= 0 ? 'var(--green)' : 'var(--red)';
    document.getElementById('bot-badge').textContent = ob + ' Online';

    const bt = document.getElementById('bot-tb');
    if (!d.bots.length) {
      bt.innerHTML = '<tr><td colspan="8"><div class="empty"><div class="empty-icon">๐“ก</div><p>No bots connected at this time</p></div></td></tr>';
    } else {
      bt.innerHTML = d.bots.map(b => `<tr>
        <td><span class="badge ${b.is_online?'b-on':'b-off'}"><span class="bdot"></span>${b.is_online?'ONLINE':'OFFLINE'}</span></td>
        <td><strong style="color:var(--g1)">#${b.account_login||'N/A'}</strong></td>
        <td style="color:var(--ts);font-size:13px">${b.broker_server||'N/A'}</td>
        <td><strong>$${b.balance.toLocaleString()}</strong> <span style="color:var(--tm);font-size:12px">/ $${b.equity.toLocaleString()}</span></td>
        <td style="color:${b.profit_today>=0?'var(--green)':'var(--red)'};font-weight:700">${b.profit_today>=0?'+':''}$${b.profit_today.toFixed(2)}</td>
        <td><span class="badge b-act">${b.open_orders} orders</span></td>
        <td><code style="background:rgba(255,215,0,.07);border:1px solid rgba(255,215,0,.14);padding:3px 8px;border-radius:6px;font-size:12px;color:var(--g1)">${b.hwid.substring(0,12)}...</code></td>
        <td style="color:var(--tm);font-size:12px">${b.last_seen_sec}s ago</td>
      </tr>`).join('');
    }

    const kt = document.getElementById('key-tb');
    kt.innerHTML = d.keys.map(k => `<tr>
      <td><strong style="color:var(--g1);font-size:13px;letter-spacing:.8px">${k.key_code}</strong></td>
      <td><div style="font-weight:600">${k.customer_name}</div>${k.notes?'<div style="color:var(--tm);font-size:12px">'+k.notes+'</div>':''}</td>
      <td><span class="badge ${k.status==='ACTIVE'?'b-act':k.status==='BANNED'?'b-ban':k.status==='EXPIRED'?'b-exp':'b-off'}"><span class="bdot"></span>${k.status}</span></td>
      <td style="font-size:12px">${k.hwid_bound?'<code style="color:var(--green);background:rgba(0,230,118,.07);padding:2px 7px;border-radius:5px">'+k.hwid_bound.substring(0,16)+'...</code>':'<span style="color:var(--tm)">Not bound yet</span>'}</td>
      <td style="font-size:12.5px;color:var(--ts)">${k.expires_at}</td>
      <td><div style="display:flex;gap:6px;flex-wrap:wrap">
        ${k.hwid_bound?'<button class="btn btn-out btn-xs" onclick="ka(\''+k.key_code+'\',\'RESET_HWID\')">๐” Reset HWID</button>':''}
        <button class="btn btn-out btn-xs" onclick="ka('${k.key_code}','EXTEND_30D')">+30d</button>
        ${k.status==='ACTIVE'?'<button class="btn btn-dan btn-xs" onclick="ka(\''+k.key_code+'\',\'BAN\')">๐ซ Ban</button>':'<button class="btn btn-act btn-xs" onclick="ka(\''+k.key_code+'\',\'ACTIVATE\')">โ… Activate</button>'}
      </div></td>
    </tr>`).join('');
  } catch(e) { console.error(e); }
}

async function ka(kc, action) {
  if (action === 'BAN' && !confirm('Confirm BAN this license? Bot will stop immediately.')) return;
  const fd = new FormData(); fd.append('key_code',kc); fd.append('action',action); fd.append('token',tok);
  await fetch('/api/admin/keys/action',{method:'POST',body:fd});
  fetchDash();
}

function openKM() { document.getElementById('km').style.display = 'flex'; }
function closeKM() { document.getElementById('km').style.display = 'none'; }
function closeRM() { document.getElementById('rm').style.display = 'none'; }

async function createKey() {
  const n = document.getElementById('kn').value.trim();
  const dur = parseInt(document.getElementById('kd').value);
  const nt = document.getElementById('knt').value.trim();
  if (!n) { alert('Please enter customer name.'); return; }
  const r = await fetch('/api/admin/keys/create?token='+tok, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({customer_name:n,duration_days:dur,notes:nt})});
  const data = await r.json();
  if (data.success) {
    lastKey = data.key_code;
    closeKM();
    document.getElementById('rk').textContent = data.key_code;
    document.getElementById('re').textContent = 'Expires: ' + data.expires_at;
    document.getElementById('rm').style.display = 'flex';
    fetchDash();
  }
}

function copyK() {
  navigator.clipboard.writeText(lastKey).then(() => {
    const b = document.querySelector('#rm .btn-gold');
    b.textContent = 'โ… Copied!';
    setTimeout(() => { b.textContent = '๐“ Copy Key to Clipboard'; }, 2000);
  });
}

checkAuth();
</script>
</body>
</html>"""

@app.get("/admin", response_class=HTMLResponse)
@app.get("/api/index/admin", response_class=HTMLResponse)
def get_admin_portal():
    return HTMLResponse(content=ADMIN_HTML)

