# -*- coding: utf-8 -*-
"""
👑 Mr.krit AI learning Ultra XXXX - Central Cloud License & Telemetry Server
=============================================================================
ระบบศูนย์กลางจัดการคีย์สิทธิ์การใช้งาน, ตรวจจับบอทออนไลน์สด, และแดชบอร์ดหลังบ้าน
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
# CONFIGURATION & DATABASE
# -----------------------------------------------------------------------------
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "mrkrit8888")
SECRET_TOKEN_KEY = os.getenv("SECRET_TOKEN_KEY", "MR_KRIT_ULTRA_SECURITY_SECRET_2026")
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "central_hub.db")

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
            status TEXT DEFAULT 'ACTIVE', -- ACTIVE, EXPIRED, BANNED, REVOKED
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
            remote_command TEXT DEFAULT 'NONE' -- NONE, STOP, RESUME
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
    
    # Insert default master demo key if table is empty
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

class RemoteCommandRequest(BaseModel):
    hwid: str
    command: str  # NONE, STOP, RESUME

# -----------------------------------------------------------------------------
# CLIENT BOT API ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "Mr.krit AI Central Cloud Gateway",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "admin_portal": "/admin"
    }

@app.post("/api/v1/license/verify")
def verify_license(req: VerifyRequest, request: Request):
    """Client Bot calls this to verify if license key is valid & active"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM license_keys WHERE key_code = ?", (req.key.strip(),))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return {
            "valid": False,
            "status": "INVALID_KEY",
            "message": "❌ ไม่พบคีย์นี้ในระบบ กรุณาตรวจสอบความถูกต้อง"
        }
    
    key_data = dict(row)
    now = datetime.now()
    expires_at = datetime.strptime(key_data["expires_at"], "%Y-%m-%d %H:%M:%S")
    
    # Check Banned or Revoked
    if key_data["status"] in ["BANNED", "REVOKED"]:
        conn.close()
        return {
            "valid": False,
            "status": key_data["status"],
            "message": f"🚫 สิทธิ์การใช้งานถูกระงับ (สถานะ: {key_data['status']})"
        }
    
    # Check Expired
    if now > expires_at:
        cursor.execute("UPDATE license_keys SET status = 'EXPIRED' WHERE key_code = ?", (req.key.strip(),))
        conn.commit()
        conn.close()
        return {
            "valid": False,
            "status": "EXPIRED",
            "message": f"⏳ สิทธิ์การใช้งานหมดอายุแล้วเมื่อ {key_data['expires_at']}"
        }
    
    # Check HWID Binding
    bound_hwid = (key_data.get("hwid_bound") or "").strip()
    if bound_hwid == "":
        # First time activation on this HWID -> Bind it automatically!
        cursor.execute("UPDATE license_keys SET hwid_bound = ? WHERE key_code = ?", (req.hwid.strip(), req.key.strip()))
        conn.commit()
        bound_hwid = req.hwid.strip()
    elif bound_hwid != req.hwid.strip():
        conn.close()
        return {
            "valid": False,
            "status": "HWID_MISMATCH",
            "message": f"⚠️ คีย์นี้ถูกผูกไว้กับเครื่องอื่นแล้ว ({bound_hwid[:4]}****) กรุณาติดต่อแอดมินเพื่อย้ายเครื่อง"
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
        "message": f"✅ สิทธิ์การใช้งานถูกต้อง (เหลือเวลา {days_left} วัน)"
    }

@app.post("/api/v1/telemetry/heartbeat")
def record_heartbeat(req: HeartbeatRequest, request: Request):
    """Client Bot reports status every 30-60s to show live online radar"""
    client_ip = request.client.host if request.client else ""
    now_ts = time.time()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if key is valid first
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
    
    # Check if there is any pending remote command
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
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = secrets.token_hex(32)
        exp = time.time() + 86400 * 7 # 7 days
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO admin_sessions (token, created_at, expires_at) VALUES (?, ?, ?)", (token, time.time(), exp))
        conn.commit()
        conn.close()
        return {"success": True, "token": token}
    return {"success": False, "message": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}

@app.get("/api/admin/overview")
def admin_overview(token: str):
    check_admin_token(token)
    conn = get_db()
    cursor = conn.cursor()
    
    now_ts = time.time()
    online_threshold = now_ts - 90  # Seen within last 90 seconds = ONLINE
    
    # Update offline statuses
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
    
    # Generate unique VIP Key code
    random_part = secrets.token_hex(3).upper()
    key_code = f"KRIT-{req.duration_days}D-{secrets.token_hex(2).upper()}-{random_part}"
    
    now = datetime.now()
    if req.duration_days >= 20000: # Lifetime
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
# EMBEDDED LUXURY ADMIN WEB DASHBOARD
# -----------------------------------------------------------------------------
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>👑 Mr.krit AI Ultra XXXX - Central Cloud Cockpit</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;900&family=Prompt:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #07090e;
            --bg-card: rgba(16, 23, 38, 0.75);
            --border-glow: rgba(0, 242, 254, 0.2);
            --accent-cyan: #00f2fe;
            --accent-green: #00e676;
            --accent-gold: #ffd700;
            --accent-red: #ff3366;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', 'Prompt', sans-serif; }
        body { background: radial-gradient(circle at top right, #101c38 0%, #07090e 100%); color: var(--text-primary); min-height: 100vh; }
        
        .navbar { display: flex; justify-content: space-between; align-items: center; padding: 18px 36px; background: rgba(7, 9, 14, 0.85); backdrop-filter: blur(15px); border-bottom: 1px solid var(--border-glow); position: sticky; top: 0; z-index: 100; }
        .logo-text { font-size: 20px; font-weight: 900; background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 1px; }
        
        .container { max-width: 1400px; margin: 30px auto; padding: 0 24px; }
        
        /* Stats Grid */
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: var(--bg-card); border: 1px solid var(--border-glow); border-radius: 16px; padding: 22px; backdrop-filter: blur(12px); transition: 0.3s; position: relative; overflow: hidden; }
        .stat-card:hover { transform: translateY(-4px); border-color: var(--accent-cyan); box-shadow: 0 10px 30px rgba(0, 242, 254, 0.15); }
        .stat-card::before { content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: var(--accent-cyan); }
        .stat-card.green::before { background: var(--accent-green); }
        .stat-card.gold::before { background: var(--accent-gold); }
        .stat-label { font-size: 13px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600; }
        .stat-val { font-size: 32px; font-weight: 900; margin-top: 8px; color: #fff; }
        
        /* Section Containers */
        .panel { background: var(--bg-card); border: 1px solid var(--border-glow); border-radius: 18px; padding: 26px; backdrop-filter: blur(12px); margin-bottom: 30px; }
        .panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .panel-title { font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
        
        /* Buttons */
        .btn { padding: 10px 20px; border-radius: 10px; font-weight: 600; cursor: pointer; border: none; transition: 0.2s; display: inline-flex; align-items: center; gap: 8px; font-size: 14px; }
        .btn-cyan { background: linear-gradient(135deg, #00f2fe, #4facfe); color: #000; font-weight: 700; box-shadow: 0 4px 15px rgba(0, 242, 254, 0.3); }
        .btn-cyan:hover { opacity: 0.9; transform: scale(1.02); }
        .btn-sm { padding: 6px 12px; font-size: 12px; border-radius: 6px; }
        .btn-red { background: rgba(255, 51, 102, 0.2); color: #ff3366; border: 1px solid #ff3366; }
        .btn-red:hover { background: #ff3366; color: #fff; }
        .btn-gray { background: rgba(255, 255, 255, 0.1); color: #fff; }
        .btn-gray:hover { background: rgba(255, 255, 255, 0.2); }
        
        /* Tables */
        .table-responsive { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th { padding: 14px; font-size: 12px; text-transform: uppercase; color: var(--text-secondary); border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
        td { padding: 16px 14px; font-size: 14px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
        tr:hover td { background: rgba(0, 242, 254, 0.03); }
        
        /* Badges */
        .badge { padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; gap: 5px; }
        .badge-online { background: rgba(0, 230, 118, 0.15); color: var(--accent-green); border: 1px solid var(--accent-green); }
        .badge-offline { background: rgba(148, 163, 184, 0.15); color: var(--text-secondary); border: 1px solid rgba(148, 163, 184, 0.3); }
        .badge-active { background: rgba(0, 242, 254, 0.15); color: var(--accent-cyan); border: 1px solid var(--accent-cyan); }
        .badge-banned { background: rgba(255, 51, 102, 0.15); color: var(--accent-red); border: 1px solid var(--accent-red); }
        
        /* Modal */
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(8px); z-index: 1000; justify-content: center; align-items: center; }
        .modal-box { background: #0c1220; border: 1px solid var(--accent-cyan); border-radius: 20px; padding: 32px; width: 90%; max-width: 500px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8); }
        .form-group { margin-bottom: 18px; }
        .form-group label { display: block; font-size: 13px; color: var(--text-secondary); margin-bottom: 6px; font-weight: 600; }
        .form-control { width: 100%; padding: 12px 16px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px; color: #fff; font-size: 14px; outline: none; }
        .form-control:focus { border-color: var(--accent-cyan); }
        
        /* Login Card */
        #login-view { min-height: 80vh; display: flex; justify-content: center; align-items: center; }
        .login-card { background: var(--bg-card); border: 1px solid var(--border-glow); padding: 40px; border-radius: 24px; width: 100%; max-width: 420px; box-shadow: 0 20px 50px rgba(0,0,0,0.5); backdrop-filter: blur(15px); }
    </style>
</head>
<body>

    <div class="navbar">
        <div class="logo-text">👑 MR.KRIT AI ULTRA • CLOUD HUB</div>
        <div id="nav-user" style="display: none;">
            <button class="btn btn-gray btn-sm" onclick="logout()">🚪 ออกจากระบบ</button>
        </div>
    </div>

    <!-- LOGIN SCREEN -->
    <div id="login-view">
        <div class="login-card">
            <h2 style="font-size: 22px; font-weight: 900; margin-bottom: 8px; color: #fff;">👑 Admin Master Login</h2>
            <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 24px;">เข้าสู่ระบบศูนย์กลางเพื่อตรวจสอบบอทและจัดการสิทธิ์</p>
            <div class="form-group">
                <label>ชื่อผู้ใช้ (Username)</label>
                <input type="text" id="login-user" class="form-control" placeholder="admin" value="admin">
            </div>
            <div class="form-group">
                <label>รหัสผ่าน (Password)</label>
                <input type="password" id="login-pass" class="form-control" placeholder="••••••••" value="mrkrit8888">
            </div>
            <button class="btn btn-cyan" style="width: 100%; justify-content: center; margin-top: 10px;" onclick="handleLogin()">🚀 เข้าสู่ระบบเซิร์ฟเวอร์</button>
        </div>
    </div>

    <!-- MAIN DASHBOARD -->
    <div id="dash-view" class="container" style="display: none;">
        
        <!-- Stats -->
        <div class="stats-grid">
            <div class="stat-card green">
                <div class="stat-label">🟢 บอทออนไลน์สด (Active Live Bots)</div>
                <div class="stat-val" id="stat-online">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">🔑 คีย์ทั้งหมดที่เปิดใช้งาน (Active Keys)</div>
                <div class="stat-val" id="stat-keys">0</div>
            </div>
            <div class="stat-card gold">
                <div class="stat-label">💰 พอร์ตรวมทั้งหมด (Total Live Balance)</div>
                <div class="stat-val" id="stat-balance">$0.00</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">📈 กำไรรวมวันนี้ (Today's Profit)</div>
                <div class="stat-val" id="stat-profit">$0.00</div>
            </div>
        </div>

        <!-- Live Bot Radar Panel -->
        <div class="panel">
            <div class="panel-header">
                <div class="panel-title">🛰️ เรดาร์ตรวจจับบอทสด (Real-Time Bot Telemetry Radar)</div>
                <button class="btn btn-gray btn-sm" onclick="fetchDashboard()">🔄 รีเฟรชข้อมูล</button>
            </div>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>สถานะ</th>
                            <th>บัญชี MT5</th>
                            <th>โบรกเกอร์ / Server</th>
                            <th>ยอด Balance / Equity</th>
                            <th>กำไรวันนี้</th>
                            <th>ออเดอร์ค้าง</th>
                            <th>HWID เครื่อง</th>
                            <th>สัญญาณล่าสุด</th>
                        </tr>
                    </thead>
                    <tbody id="bot-table-body">
                        <tr><td colspan="8" style="text-align: center; color: var(--text-secondary);">กำลังค้นหาการเชื่อมต่อ...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- License Keys Panel -->
        <div class="panel">
            <div class="panel-header">
                <div class="panel-title">🔑 ระบบจัดการสิทธิ์การใช้งาน (License Keys Master Management)</div>
                <button class="btn btn-cyan" onclick="openKeyModal()">➕ สร้างคีย์ใหม่ (Generate Key)</button>
            </div>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>รหัสคีย์ (License Key)</th>
                            <th>ชื่อลูกค้า / ผู้ใช้</th>
                            <th>สถานะสิทธิ์</th>
                            <th>เครื่องที่ผูก (HWID)</th>
                            <th>วันหมดอายุ</th>
                            <th>จัดการคำสั่ง</th>
                        </tr>
                    </thead>
                    <tbody id="key-table-body">
                        <!-- Populated by JS -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- MODAL: CREATE KEY -->
    <div id="key-modal" class="modal-overlay">
        <div class="modal-box">
            <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 18px;">➕ สร้างรหัสสิทธิ์การใช้งานใหม่ (New License)</h3>
            <div class="form-group">
                <label>ชื่อลูกค้า (Customer Name)</label>
                <input type="text" id="new-cust-name" class="form-control" placeholder="เช่น คุณสมชาย (VIP)">
            </div>
            <div class="form-group">
                <label>ระยะเวลาสิทธิ์ (Duration)</label>
                <select id="new-duration" class="form-control">
                    <option value="7">7 วัน (ทดลองใช้งาน Trial)</option>
                    <option value="30" selected>30 วัน (1 เดือน)</option>
                    <option value="90">90 วัน (3 เดือน)</option>
                    <option value="365">365 วัน (1 ปี)</option>
                    <option value="29000">ตลอดชีพ (Lifetime VIP)</option>
                </select>
            </div>
            <div class="form-group">
                <label>บันทึกช่วยจำ (Notes)</label>
                <input type="text" id="new-notes" class="form-control" placeholder="เช่น ชำระเงินแล้วทางไลน์">
            </div>
            <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 24px;">
                <button class="btn btn-gray" onclick="closeKeyModal()">ยกเลิก</button>
                <button class="btn btn-cyan" onclick="submitCreateKey()">✨ ยืนยันสร้างคีย์</button>
            </div>
        </div>
    </div>

    <script>
        let adminToken = localStorage.getItem('mrkrit_admin_token') || '';

        function checkAuth() {
            if (adminToken) {
                document.getElementById('login-view').style.display = 'none';
                document.getElementById('dash-view').style.display = 'block';
                document.getElementById('nav-user').style.display = 'block';
                fetchDashboard();
                setInterval(fetchDashboard, 15000); // Auto refresh every 15s
            } else {
                document.getElementById('login-view').style.display = 'flex';
                document.getElementById('dash-view').style.display = 'none';
                document.getElementById('nav-user').style.display = 'none';
            }
        }

        async function handleLogin() {
            const u = document.getElementById('login-user').value;
            const p = document.getElementById('login-pass').value;
            const fd = new FormData();
            fd.append('username', u);
            fd.append('password', p);
            
            try {
                const res = await fetch('/api/admin/login', { method: 'POST', body: fd });
                const data = await res.json();
                if (data.success) {
                    adminToken = data.token;
                    localStorage.setItem('mrkrit_admin_token', adminToken);
                    checkAuth();
                } else {
                    alert(data.message || 'รหัสผ่านไม่ถูกต้อง');
                }
            } catch(e) {
                alert('เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์');
            }
        }

        function logout() {
            localStorage.removeItem('mrkrit_admin_token');
            adminToken = '';
            checkAuth();
        }

        async function fetchDashboard() {
            if (!adminToken) return;
            try {
                const res = await fetch(`/api/admin/overview?token=${adminToken}`);
                if (res.status === 401) { logout(); return; }
                const data = await res.json();
                
                // Stats
                document.getElementById('stat-online').innerText = data.stats.online_bots;
                document.getElementById('stat-keys').innerText = `${data.stats.active_keys} / ${data.stats.total_keys}`;
                document.getElementById('stat-balance').innerText = `$${data.stats.total_balance.toLocaleString()}`;
                document.getElementById('stat-profit').innerText = `$${data.stats.total_profit.toLocaleString()}`;

                // Bots Table
                const botTbody = document.getElementById('bot-table-body');
                if (data.bots.length === 0) {
                    botTbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: #94a3b8; padding: 25px;">ยังไม่มีบอทเชื่อมต่อเข้ามาในขณะนี้</td></tr>`;
                } else {
                    botTbody.innerHTML = data.bots.map(b => `
                        <tr>
                            <td><span class="badge ${b.is_online ? 'badge-online' : 'badge-offline'}">${b.is_online ? '🟢 ออนไลน์' : '⚪ ออฟไลน์'}</span></td>
                            <td style="font-weight: 700;">#${b.account_login || 'N/A'}</td>
                            <td>${b.broker_server || 'N/A'}</td>
                            <td><strong>$${b.balance.toLocaleString()}</strong> <span style="color: #94a3b8; font-size: 12px;">(Eq: $${b.equity.toLocaleString()})</span></td>
                            <td style="color: ${b.profit_today >= 0 ? '#00e676' : '#ff3366'}; font-weight: 700;">${b.profit_today >= 0 ? '+' : ''}$${b.profit_today.toFixed(2)}</td>
                            <td><span class="badge badge-active">${b.open_orders} ไม้</span></td>
                            <td><code style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">${b.hwid}</code></td>
                            <td style="color: #94a3b8; font-size: 12px;">${b.last_seen_sec} วินาทีที่แล้ว</td>
                        </tr>
                    `).join('');
                }

                // Keys Table
                const keyTbody = document.getElementById('key-table-body');
                keyTbody.innerHTML = data.keys.map(k => `
                    <tr>
                        <td><strong style="color: #00f2fe; letter-spacing: 0.5px;">${k.key_code}</strong></td>
                        <td>${k.customer_name} ${k.notes ? `<span style="color: #94a3b8; font-size: 12px;">(${k.notes})</span>` : ''}</td>
                        <td><span class="badge ${k.status === 'ACTIVE' ? 'badge-active' : (k.status === 'BANNED' ? 'badge-banned' : 'badge-offline')}">${k.status}</span></td>
                        <td>${k.hwid_bound ? `<code style="color: #00e676;">${k.hwid_bound}</code>` : '<span style="color: #94a3b8;">(ยังไม่ผูกเครื่อง)</span>'}</td>
                        <td style="font-size: 13px;">${k.expires_at}</td>
                        <td>
                            <div style="display: flex; gap: 6px;">
                                ${k.hwid_bound ? `<button class="btn btn-gray btn-sm" onclick="keyAction('${k.key_code}', 'RESET_HWID')">🔄 ปลดล็อค HWID</button>` : ''}
                                <button class="btn btn-gray btn-sm" onclick="keyAction('${k.key_code}', 'EXTEND_30D')">+30 วัน</button>
                                ${k.status === 'ACTIVE' ? `<button class="btn btn-red btn-sm" onclick="keyAction('${k.key_code}', 'BAN')">🚫 ระงับคีย์</button>` : `<button class="btn btn-cyan btn-sm" onclick="keyAction('${k.key_code}', 'ACTIVATE')">✅ เปิดใช้งาน</button>`}
                            </div>
                        </td>
                    </tr>
                `).join('');

            } catch(e) { console.error(e); }
        }

        async function keyAction(keyCode, action) {
            if (action === 'BAN' && !confirm('คุณแน่ใจหรือไม่ว่าต้องการระงับสิทธิ์คีย์นี้ทันที?')) return;
            const fd = new FormData();
            fd.append('key_code', keyCode);
            fd.append('action', action);
            fd.append('token', adminToken);
            await fetch('/api/admin/keys/action', { method: 'POST', body: fd });
            fetchDashboard();
        }

        function openKeyModal() { document.getElementById('key-modal').style.display = 'flex'; }
        function closeKeyModal() { document.getElementById('key-modal').style.display = 'none'; }

        async function submitCreateKey() {
            const name = document.getElementById('new-cust-name').value;
            const duration = parseInt(document.getElementById('new-duration').value);
            const notes = document.getElementById('new-notes').value;
            if (!name) { alert('กรุณากรอกชื่อลูกค้า'); return; }

            const res = await fetch(`/api/admin/keys/create?token=${adminToken}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ customer_name: name, duration_days: duration, notes: notes })
            });
            const data = await res.json();
            if (data.success) {
                alert(`✨ สร้างคีย์สำเร็จ!\\nรหัสคีย์: ${data.key_code}\\nหมดอายุ: ${data.expires_at}`);
                closeKeyModal();
                fetchDashboard();
            }
        }

        checkAuth();
    </script>
</body>
</html>
"""

@app.get("/admin", response_class=HTMLResponse)
def get_admin_portal():
    return HTMLResponse(content=ADMIN_HTML)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
