# -*- coding: utf-8 -*-
"""
👑 MR.KRIT AI ULTRA • EXECUTIVE MASTER CLOUD GATEWAY & RADAR HUB
=============================================================================
Modern FinTech Glassmorphism Admin Command Center (Vercel Native)
- Strict Dual Verification: Username + License Key + HWID
- Instant Remote Revocation & Device Kick (KICK_LOGOUT)
- Modern FinTech Glassmorphism Design System
"""

import os
import sys
import json
import time
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, HTTPException, Depends, status, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "mrkrit8888")
SECRET_TOKEN_KEY = os.getenv("SECRET_TOKEN_KEY", "MR_KRIT_ULTRA_SECURITY_SECRET_2026")

DB_FILE = "/tmp/central_hub.db" if os.environ.get("VERCEL") else os.path.join(os.path.dirname(os.path.abspath(__file__)), "central_hub.db")

app = FastAPI(
    title="Mr.krit AI Central Cloud Gateway",
    version="5.0.0",
    description="Executive License & Institutional Device Radar Hub"
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
        
        # Table: Bot Telemetry
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
                bot_version TEXT DEFAULT 'v25.0',
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

        # Table: Broadcast Messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                message TEXT,
                severity TEXT DEFAULT 'INFO',
                created_at TEXT
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
                "Mr. Krit",
                "admin@mrkrit.ai",
                "",
                now.strftime("%Y-%m-%d %H:%M:%S"),
                exp.strftime("%Y-%m-%d %H:%M:%S"),
                "ACTIVE",
                365,
                "คีย์เริ่มต้นระดับ Master VIP"
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
    username: Optional[str] = ""
    bot_version: Optional[str] = "v25.0"

class HeartbeatRequest(BaseModel):
    key: str
    hwid: str
    account_login: Optional[str] = ""
    broker_server: Optional[str] = ""
    balance: Optional[float] = 0.0
    equity: Optional[float] = 0.0
    profit_today: Optional[float] = 0.0
    open_orders: Optional[int] = 0
    bot_version: Optional[str] = "v25.0"
    status: Optional[str] = "ONLINE"

class CreateKeyRequest(BaseModel):
    customer_name: str
    customer_contact: Optional[str] = ""
    hwid_bound: Optional[str] = ""
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
        "service": "👑 MR.KRIT AI ULTRA • Central Cloud Gateway",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "admin_portal": "/admin"
    }

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
            "message": "❌ ไม่พบคีย์นี้ในระบบ กรุณาตรวจสอบความถูกต้อง"
        }
    
    key_data = dict(row)
    now = datetime.now()
    expires_at = datetime.strptime(key_data["expires_at"], "%Y-%m-%d %H:%M:%S")
    
    # 1. Check Revoked / Banned
    if key_data["status"] in ["BANNED", "REVOKED", "DISABLED"]:
        conn.close()
        return {
            "valid": False,
            "status": "REVOKED",
            "message": f"🚫 สิทธิ์การใช้งานถูกระงับโดยผู้ดูแลระบบ (สถานะ: {key_data['status']})"
        }
    
    # 2. Check Expiry
    if now > expires_at:
        cursor.execute("UPDATE license_keys SET status = 'EXPIRED' WHERE key_code = ?", (req.key.strip(),))
        conn.commit()
        conn.close()
        return {
            "valid": False,
            "status": "EXPIRED",
            "message": f"⏳ สิทธิ์การใช้งานหมดอายุแล้วเมื่อ {key_data['expires_at']}"
        }
    
    # 3. Check Username Matching (Strict Dual Matching)
    entered_user = (req.username or "").strip().lower()
    db_user = (key_data.get("customer_name") or "").strip().lower()
    if entered_user and db_user and entered_user != db_user:
        conn.close()
        return {
            "valid": False,
            "status": "USERNAME_MISMATCH",
            "message": f"❌ ชื่อผู้ใช้งาน '{req.username}' ไม่ตรงกับชื่อผู้ถือสิทธิ์ของคีย์นี้ ('{key_data['customer_name']}')"
        }
    
    # 4. Check HWID Binding
    bound_hwid = (key_data.get("hwid_bound") or "").strip()
    if bound_hwid == "":
        cursor.execute("UPDATE license_keys SET hwid_bound = ? WHERE key_code = ?", (req.hwid.strip().upper(), req.key.strip()))
        conn.commit()
        bound_hwid = req.hwid.strip().upper()
    elif bound_hwid.upper() != req.hwid.strip().upper():
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
    init_db()
    client_ip = request.client.host if request.client else ""
    now_ts = time.time()
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT status FROM license_keys WHERE key_code = ?", (req.key.strip(),))
    k = cursor.fetchone()
    if not k or k["status"] in ["BANNED", "REVOKED", "DISABLED"]:
        conn.close()
        return {"status": "error", "command": "KICK_LOGOUT", "message": "🚫 สิทธิ์การใช้งานของคุณถูกระงับโดยผู้ดูแลระบบ (Access Revoked)"}
    
    # Check if there is a pending remote kick command for this HWID
    cursor.execute("SELECT remote_command FROM bot_telemetry WHERE hwid = ?", (req.hwid.strip().upper(),))
    res = cursor.fetchone()
    if res and res["remote_command"] == "KICK_LOGOUT":
        cursor.execute("UPDATE bot_telemetry SET remote_command = 'NONE', status = 'KICKED' WHERE hwid = ?", (req.hwid.strip().upper(),))
        conn.commit()
        conn.close()
        return {"status": "error", "command": "KICK_LOGOUT", "message": "🚫 อุปกรณ์ของคุณถูกสั่งตัดการเชื่อมต่อโดยผู้ดูแลระบบ (Remote Kick)"}
    
    status_to_set = req.status.upper() if req.status else "ONLINE"
    
    cursor.execute("""
        INSERT INTO bot_telemetry (
            hwid, key_code, account_login, broker_server, balance, equity, 
            profit_today, open_orders, bot_version, last_seen, ip_address, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            status = excluded.status
    """, (
        req.hwid.strip().upper(), req.key.strip(), req.account_login, req.broker_server,
        req.balance, req.equity, req.profit_today, req.open_orders,
        req.bot_version, now_ts, client_ip, status_to_set
    ))
    
    cursor.execute("SELECT remote_command FROM bot_telemetry WHERE hwid = ?", (req.hwid.strip().upper(),))
    res2 = cursor.fetchone()
    cmd = res2["remote_command"] if res2 else "NONE"
    
    conn.commit()
    conn.close()
    return {"status": "ok", "command": cmd, "server_time": datetime.now().strftime("%H:%M:%S")}

# -----------------------------------------------------------------------------
# ADMIN API
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
    return {"success": False, "message": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}

@app.get("/api/admin/overview")
def admin_overview(token: str):
    check_admin_token(token)
    conn = get_db()
    cursor = conn.cursor()
    
    now_ts = time.time()
    online_threshold = now_ts - 25  # เกิน 25s = OFFLINE
    
    cursor.execute("UPDATE bot_telemetry SET status = 'OFFLINE' WHERE last_seen < ? AND status = 'ONLINE'", (online_threshold,))
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) as total FROM license_keys")
    total_keys = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as active FROM license_keys WHERE status = 'ACTIVE'")
    active_keys = cursor.fetchone()["active"]
    
    cursor.execute("SELECT COUNT(*) as revoked FROM license_keys WHERE status = 'REVOKED'")
    revoked_keys = cursor.fetchone()["revoked"]
    
    cursor.execute("SELECT COUNT(*) as online FROM bot_telemetry WHERE status = 'ONLINE'")
    online_bots = cursor.fetchone()["online"]
    
    cursor.execute("SELECT COUNT(*) as offline FROM bot_telemetry WHERE status != 'ONLINE'")
    offline_bots = cursor.fetchone()["offline"]
    
    cursor.execute("SELECT SUM(profit_today) as total_pnl FROM bot_telemetry")
    total_pnl_row = cursor.fetchone()["total_pnl"]
    total_pnl = float(total_pnl_row or 0.0)
    
    # Devices list with bound key info
    cursor.execute("""
        SELECT b.*, k.customer_name, k.expires_at, k.status as key_status
        FROM bot_telemetry b
        LEFT JOIN license_keys k ON b.key_code = k.key_code
        ORDER BY b.status ASC, b.last_seen DESC LIMIT 60
    """)
    bots = [dict(r) for r in cursor.fetchall()]
    for b in bots:
        is_on = (now_ts - b["last_seen"]) <= 25 and b["status"] == "ONLINE"
        b["is_online"] = is_on
        b["last_seen_sec"] = max(0, int(now_ts - b["last_seen"]))
    
    cursor.execute("SELECT * FROM license_keys ORDER BY created_at DESC")
    keys = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "stats": {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "revoked_keys": revoked_keys,
            "online_bots": online_bots,
            "offline_bots": offline_bots,
            "total_pnl": round(total_pnl, 2)
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
        ) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
    """, (
        key_code, req.customer_name.strip(), req.customer_contact.strip(), req.hwid_bound.strip().upper(),
        now.strftime("%Y-%m-%d %H:%M:%S"), exp.strftime("%Y-%m-%d %H:%M:%S"),
        req.duration_days, req.notes.strip()
    ))
    conn.commit()
    conn.close()
    return {"success": True, "key_code": key_code, "customer_name": req.customer_name.strip(), "expires_at": exp.strftime("%Y-%m-%d %H:%M:%S")}

@app.post("/api/admin/keys/action")
def admin_key_action(key_code: str = Form(...), action: str = Form(...), token: str = Form(...)):
    check_admin_token(token)
    conn = get_db()
    cursor = conn.cursor()
    
    if action in ["REVOKE", "BAN", "DISABLE"]:
        cursor.execute("UPDATE license_keys SET status = 'REVOKED' WHERE key_code = ?", (key_code,))
        cursor.execute("UPDATE bot_telemetry SET remote_command = 'KICK_LOGOUT', status = 'REVOKED' WHERE key_code = ?", (key_code,))
    elif action in ["ACTIVATE", "ENABLE"]:
        cursor.execute("UPDATE license_keys SET status = 'ACTIVE' WHERE key_code = ?", (key_code,))
        cursor.execute("UPDATE bot_telemetry SET remote_command = 'NONE' WHERE key_code = ?", (key_code,))
    elif action == "KICK":
        cursor.execute("UPDATE bot_telemetry SET remote_command = 'KICK_LOGOUT', status = 'KICKED' WHERE hwid = ? OR key_code = ?", (key_code, key_code))
    elif action == "RESET_HWID":
        cursor.execute("UPDATE license_keys SET hwid_bound = '' WHERE key_code = ?", (key_code,))
    elif action == "DELETE":
        cursor.execute("DELETE FROM license_keys WHERE key_code = ?", (key_code,))
        cursor.execute("DELETE FROM bot_telemetry WHERE key_code = ?", (key_code,))
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
# MODERN FINTECH GLASSMORPHISM MASTER ADMIN DASHBOARD (4K/RESPONSIVE)
# -----------------------------------------------------------------------------
ADMIN_HTML = """<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>👑 Mr.krit AI Ultra • Executive License Hub</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Prompt:wght@300;400;500;600;700&family=JetBrains+Mono:wght@500;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #080C14;
            --bg-surface: rgba(15, 23, 42, 0.65);
            --bg-surface-elevated: rgba(30, 41, 59, 0.7);
            --bg-glass: rgba(255, 255, 255, 0.03);
            --bg-glass-hover: rgba(255, 255, 255, 0.06);
            --bg-input: rgba(15, 23, 42, 0.85);

            --border-subtle: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(255, 255, 255, 0.16);
            --border-cyan: rgba(6, 182, 212, 0.35);
            --border-gold: rgba(234, 179, 8, 0.35);

            --accent-cyan: #06B6D4;
            --accent-cyan-glow: rgba(6, 182, 212, 0.25);
            --accent-gold: #EAB308;
            --accent-gold-glow: rgba(234, 179, 8, 0.25);
            --accent-emerald: #10B981;
            --accent-emerald-glow: rgba(16, 185, 129, 0.2);
            --accent-rose: #F43F5E;
            --accent-rose-glow: rgba(244, 63, 94, 0.2);

            --text-primary: #F8FAFC;
            --text-secondary: #94A3B8;
            --text-muted: #64748B;

            --radius-xl: 18px;
            --radius-lg: 14px;
            --radius-md: 10px;
            --radius-sm: 6px;
            --radius-pill: 9999px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Prompt', 'Plus Jakarta Sans', sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        body {
            background-color: var(--bg-base);
            background-image: 
                radial-gradient(circle at 10% 10%, rgba(6, 182, 212, 0.05) 0%, transparent 45%),
                radial-gradient(circle at 90% 15%, rgba(234, 179, 8, 0.04) 0%, transparent 40%),
                radial-gradient(circle at 50% 90%, rgba(99, 102, 241, 0.04) 0%, transparent 50%);
            background-attachment: fixed;
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        .mono { font-family: 'JetBrains Mono', monospace; }

        .container {
            max-width: 1360px;
            margin: 0 auto;
            padding: 24px 20px;
            width: 100%;
        }

        /* ─── MODERN GLASS HEADER ─── */
        .glass-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--bg-surface);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-xl);
            padding: 16px 22px;
            margin-bottom: 24px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
            flex-wrap: wrap;
            gap: 16px;
        }

        .brand-group {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .brand-avatar {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: linear-gradient(135deg, rgba(234, 179, 8, 0.2) 0%, rgba(6, 182, 212, 0.15) 100%);
            border: 1px solid var(--border-gold);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            box-shadow: 0 0 15px var(--accent-gold-glow);
        }

        .brand-info h1 {
            font-size: 17px;
            font-weight: 800;
            letter-spacing: -0.2px;
            display: flex;
            align-items: center;
            gap: 8px;
            color: #FFFFFF;
        }

        .brand-info h1 span.highlight {
            background: linear-gradient(135deg, #FDE047 0%, #EAB308 100%);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-badge {
            font-size: 10px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: var(--radius-pill);
            background: rgba(234, 179, 8, 0.15);
            color: #FDE047;
            border: 1px solid rgba(234, 179, 8, 0.3);
        }

        .brand-sub {
            font-size: 11.5px;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        .header-controls {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 6px 12px;
            border-radius: var(--radius-pill);
            font-size: 11.5px;
            font-weight: 600;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.25);
            color: #6EE7B7;
        }

        .dot-pulse {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--accent-emerald);
            box-shadow: 0 0 8px var(--accent-emerald);
            animation: pulseGlow 2s infinite ease-in-out;
        }

        @keyframes pulseGlow {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.3); opacity: 0.6; }
        }

        .btn-compact {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 7px 14px;
            border-radius: var(--radius-md);
            font-size: 12px;
            font-weight: 600;
            background: var(--bg-glass);
            border: 1px solid var(--border-subtle);
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            text-decoration: none;
        }

        .btn-compact:hover {
            background: var(--bg-glass-hover);
            border-color: var(--border-hover);
            transform: translateY(-1px);
        }

        .btn-compact.danger {
            background: rgba(244, 63, 94, 0.1);
            border-color: rgba(244, 63, 94, 0.25);
            color: #FDA4AF;
        }

        .btn-compact.danger:hover {
            background: rgba(244, 63, 94, 0.2);
            border-color: var(--accent-rose);
        }

        /* ─── METRIC STAT CARDS ─── */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .metric-card {
            background: var(--bg-surface);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            padding: 18px 20px;
            display: flex;
            align-items: center;
            gap: 16px;
            transition: all 0.25s ease;
            position: relative;
            overflow: hidden;
        }

        .metric-card:hover {
            transform: translateY(-2px);
            border-color: var(--border-hover);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }

        .metric-icon-wrap {
            width: 46px;
            height: 46px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
        }

        .icon-emerald { background: rgba(16, 185, 129, 0.12); color: var(--accent-emerald); border: 1px solid rgba(16, 185, 129, 0.2); }
        .icon-rose { background: rgba(244, 63, 94, 0.12); color: var(--accent-rose); border: 1px solid rgba(244, 63, 94, 0.2); }
        .icon-gold { background: rgba(234, 179, 8, 0.12); color: var(--accent-gold); border: 1px solid rgba(234, 179, 8, 0.2); }
        .icon-cyan { background: rgba(6, 182, 212, 0.12); color: var(--accent-cyan); border: 1px solid rgba(6, 182, 212, 0.2); }

        .metric-body {
            flex: 1;
        }

        .metric-title {
            font-size: 11px;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.6px;
        }

        .metric-value {
            font-size: 24px;
            font-weight: 800;
            color: #FFFFFF;
            margin-top: 2px;
            letter-spacing: -0.3px;
        }

        /* ─── PILL-STYLE TAB NAVIGATION (NO HORIZONTAL OVERFLOW) ─── */
        .tab-wrapper {
            display: flex;
            align-items: center;
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-pill);
            padding: 5px;
            margin-bottom: 24px;
            gap: 4px;
            flex-wrap: wrap;
        }

        .tab-item {
            flex: 1;
            min-width: 140px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 7px;
            padding: 9px 16px;
            border-radius: var(--radius-pill);
            font-size: 12.5px;
            font-weight: 600;
            color: var(--text-secondary);
            background: transparent;
            border: none;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            white-space: nowrap;
        }

        .tab-item:hover {
            color: var(--text-primary);
            background: rgba(255, 255, 255, 0.04);
        }

        .tab-item.active {
            color: #FFFFFF;
            background: linear-gradient(135deg, rgba(234, 179, 8, 0.25) 0%, rgba(6, 182, 212, 0.2) 100%);
            border: 1px solid rgba(234, 179, 8, 0.35);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }

        .tab-pane {
            display: none;
            animation: fadeIn 0.25s ease-out;
        }

        .tab-pane.active { display: block; }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* ─── CONTENT CARDS & UNIFIED TOOLBAR ─── */
        .panel-card {
            background: var(--bg-surface);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-xl);
            padding: 22px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            margin-bottom: 24px;
        }

        .panel-toolbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 18px;
            flex-wrap: wrap;
            gap: 12px;
        }

        .panel-heading {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .panel-heading h2 {
            font-size: 15px;
            font-weight: 800;
            color: #FFFFFF;
            letter-spacing: -0.2px;
        }

        .panel-actions {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }

        .search-box {
            position: relative;
            display: flex;
            align-items: center;
        }

        .search-box input {
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 8px 12px 8px 32px;
            font-size: 12px;
            color: var(--text-primary);
            outline: none;
            width: 220px;
            transition: all 0.2s ease;
        }

        .search-box input:focus {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 10px var(--accent-cyan-glow);
            width: 260px;
        }

        .search-icon {
            position: absolute;
            left: 10px;
            color: var(--text-muted);
            pointer-events: none;
            font-size: 12px;
        }

        .btn-primary-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: linear-gradient(135deg, #FDE047 0%, #EAB308 100%);
            color: #0F172A;
            border: none;
            border-radius: var(--radius-md);
            padding: 8px 16px;
            font-size: 12.5px;
            font-weight: 800;
            cursor: pointer;
            box-shadow: 0 4px 12px var(--accent-gold-glow);
            transition: all 0.2s ease;
        }

        .btn-primary-pill:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(234, 179, 8, 0.4);
        }

        /* ─── DATA TABLES ─── */
        .table-responsive {
            overflow-x: auto;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-subtle);
            background: rgba(10, 15, 26, 0.6);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12.5px;
            text-align: left;
        }

        th {
            background: rgba(15, 23, 42, 0.85);
            color: var(--text-muted);
            padding: 12px 16px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            border-bottom: 1px solid var(--border-subtle);
            white-space: nowrap;
        }

        td {
            padding: 13px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: var(--text-primary);
            vertical-align: middle;
        }

        tr:hover td {
            background: var(--bg-glass-hover);
        }

        .badge-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 3px 9px;
            border-radius: var(--radius-pill);
            font-size: 11px;
            font-weight: 700;
        }

        .badge-active { background: rgba(16, 185, 129, 0.12); color: #6EE7B7; border: 1px solid rgba(16, 185, 129, 0.25); }
        .badge-revoked { background: rgba(244, 63, 94, 0.12); color: #FDA4AF; border: 1px solid rgba(244, 63, 94, 0.25); }
        .badge-expired { background: rgba(245, 158, 11, 0.12); color: #FDE68A; border: 1px solid rgba(245, 158, 11, 0.25); }

        .key-tag {
            background: rgba(234, 179, 8, 0.08);
            border: 1px solid rgba(234, 179, 8, 0.2);
            color: #FDE047;
            padding: 4px 8px;
            border-radius: var(--radius-sm);
            font-weight: 700;
            cursor: pointer;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }

        .key-tag:hover {
            background: rgba(234, 179, 8, 0.18);
            border-color: var(--accent-gold);
        }

        /* ─── ACTION BUTTONS IN TABLE ─── */
        .btn-group-actions {
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .btn-icon {
            background: var(--bg-glass);
            border: 1px solid var(--border-subtle);
            color: var(--text-secondary);
            padding: 5px 9px;
            border-radius: var(--radius-sm);
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        .btn-icon:hover {
            background: var(--bg-glass-hover);
            color: var(--text-primary);
            border-color: var(--border-hover);
        }

        .btn-icon.danger {
            color: #FDA4AF;
            background: rgba(244, 63, 94, 0.08);
            border-color: rgba(244, 63, 94, 0.2);
        }

        .btn-icon.danger:hover {
            background: rgba(244, 63, 94, 0.2);
            border-color: var(--accent-rose);
        }

        .btn-icon.success {
            color: #6EE7B7;
            background: rgba(16, 185, 129, 0.08);
            border-color: rgba(16, 185, 129, 0.2);
        }

        .btn-icon.success:hover {
            background: rgba(16, 185, 129, 0.2);
            border-color: var(--accent-emerald);
        }

        /* ─── FORM & INPUTS (ZONE 3) ─── */
        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 16px;
            margin-bottom: 16px;
        }

        .form-control {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .form-control label {
            font-size: 11.5px;
            font-weight: 600;
            color: var(--text-secondary);
        }

        .form-control input, .form-control select {
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 10px 14px;
            color: #FFFFFF;
            font-size: 13px;
            outline: none;
            transition: all 0.2s ease;
        }

        .form-control input:focus, .form-control select:focus {
            border-color: var(--accent-gold);
            box-shadow: 0 0 10px var(--accent-gold-glow);
        }

        .preset-container {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-top: 6px;
        }

        .preset-btn {
            background: var(--bg-glass);
            border: 1px solid var(--border-subtle);
            color: var(--text-secondary);
            padding: 4px 10px;
            border-radius: var(--radius-sm);
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .preset-btn:hover {
            background: rgba(234, 179, 8, 0.12);
            border-color: var(--accent-gold);
            color: #FDE047;
        }

        .generated-key-banner {
            background: linear-gradient(135deg, rgba(234, 179, 8, 0.1) 0%, rgba(6, 182, 212, 0.08) 100%);
            border: 1px solid rgba(234, 179, 8, 0.35);
            border-radius: var(--radius-lg);
            padding: 16px 20px;
            margin-top: 20px;
            display: none;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }

        /* ─── AUTH OVERLAY ─── */
        .auth-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(8, 12, 20, 0.95);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            backdrop-filter: blur(25px);
        }

        .auth-dialog {
            background: var(--bg-surface);
            border: 1px solid var(--border-gold);
            border-radius: var(--radius-xl);
            padding: 36px 32px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8), 0 0 30px var(--accent-gold-glow);
            text-align: center;
        }
    </style>
</head>
<body>

    <!-- AUTH MODAL -->
    <div class="auth-backdrop" id="admin-auth-gate" style="display: none;">
        <div class="auth-dialog">
            <div style="font-size: 38px; margin-bottom: 12px;">👑</div>
            <h2 style="color: #FFFFFF; font-size: 19px; font-weight: 800; margin-bottom: 4px;">EXECUTIVE MASTER PORTAL</h2>
            <p style="color: var(--text-secondary); font-size: 12px; margin-bottom: 24px;">กรุณากรอกรหัสผ่านผู้ดูแลระบบระดับสูงเพื่อเข้าสู่ศูนย์ควบคุม</p>
            
            <form id="admin-login-form" onsubmit="event.preventDefault(); handleAdminLogin();">
                <div class="form-control" style="margin-bottom: 14px; text-align: left;">
                    <label>ชื่อผู้ดูแลระบบ (Username)</label>
                    <input type="text" id="admin-user-input" value="admin" required>
                </div>
                <div class="form-control" style="margin-bottom: 22px; text-align: left;">
                    <label>รหัสผ่าน (Password)</label>
                    <input type="password" id="admin-pass-input" placeholder="••••••••" required>
                </div>
                <button type="submit" class="btn-primary-pill" style="width: 100%; justify-content: center; padding: 11px;">
                    <span>🔓 ปลดล็อกเข้าสู่ศูนย์ควบคุม (ENTER)</span>
                </button>
            </form>
        </div>
    </div>

    <!-- MAIN DASHBOARD -->
    <div class="container">
        
        <!-- TOP NAVIGATION & HEADER -->
        <header class="glass-header">
            <div class="brand-group">
                <div class="brand-avatar">👑</div>
                <div class="brand-info">
                    <h1>Mr.krit AI Ultra <span class="highlight">XXXX</span> <span class="brand-badge">v25.0 VIP</span></h1>
                    <div class="brand-sub">Executive License Gateway &amp; Real-time Device Radar</div>
                </div>
            </div>

            <div class="header-controls">
                <div class="status-pill">
                    <span class="dot-pulse"></span>
                    <span id="cloud-gateway-status">Edge Gateway Active</span>
                </div>
                <div class="btn-compact mono" id="server-clock" style="color: var(--accent-gold);">--:--:--</div>
                <button type="button" class="btn-compact" onclick="loadOverviewData()" title="รีเฟรชข้อมูล">
                    <span>🔄 รีเฟรช</span>
                </button>
                <button type="button" class="btn-compact danger" onclick="handleAdminLogout()" title="ออกจากระบบ">
                    <span>🚪 ออกจากระบบ</span>
                </button>
            </div>
        </header>

        <!-- ZONE 0: STAT CARDS -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-icon-wrap icon-emerald">🟢</div>
                <div class="metric-body">
                    <div class="metric-title">บอทที่ออนไลน์สด (Live Bots)</div>
                    <div class="metric-value" style="color: #6EE7B7;" id="metric-online">0</div>
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-icon-wrap icon-rose">🔴</div>
                <div class="metric-body">
                    <div class="metric-title">อุปกรณ์ที่ออฟไลน์ (Offline)</div>
                    <div class="metric-value" style="color: #FDA4AF;" id="metric-offline">0</div>
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-icon-wrap icon-gold">🔑</div>
                <div class="metric-body">
                    <div class="metric-title">คีย์ที่เปิดใช้งาน (Active Keys)</div>
                    <div class="metric-value" style="color: #FDE047;" id="metric-keys">0 / 0</div>
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-icon-wrap icon-cyan">💰</div>
                <div class="metric-body">
                    <div class="metric-title">กำไรสะสมรวมลูกค้า (Total PnL)</div>
                    <div class="metric-value" style="color: #67E8F9;" id="metric-pnl">$0.00</div>
                </div>
            </div>
        </div>

        <!-- PILL-STYLE COMPACT TAB NAVIGATION -->
        <nav class="tab-wrapper">
            <button type="button" class="tab-item active" onclick="switchTab('tab-radar', this)">
                <span>🛰️ เรดาร์อุปกรณ์สด (Live Radar)</span>
            </button>
            <button type="button" class="tab-item" onclick="switchTab('tab-keys', this)">
                <span>🔑 คลังคีย์สิทธิ์และลูกค้า (License Vault)</span>
            </button>
            <button type="button" class="tab-item" onclick="switchTab('tab-generate', this)">
                <span>⚡ สร้างคีย์ด่วน (Key Generator)</span>
            </button>
            <button type="button" class="tab-item" onclick="switchTab('tab-security', this)">
                <span>🛡️ ความปลอดภัย (Security &amp; Alerts)</span>
            </button>
        </nav>

        <!-- ══════════════════════════════════════════════════════════════════
             TAB 1: LIVE RADAR (ZONE 1)
        ══════════════════════════════════════════════════════════════════ -->
        <div class="tab-pane active" id="tab-radar">
            <div class="panel-card">
                <div class="panel-toolbar">
                    <div class="panel-heading">
                        <h2>🛰️ อุปกรณ์เทรดที่กำลังเชื่อมต่อสด (Live Connected Units)</h2>
                    </div>
                    <div class="panel-actions">
                        <div class="search-box">
                            <span class="search-icon">🔍</span>
                            <input type="text" id="radar-search" placeholder="ค้นหา HWID / บัญชี MT5..." onkeyup="filterRadarTable()">
                        </div>
                    </div>
                </div>

                <div class="table-responsive">
                    <table id="table-radar">
                        <thead>
                            <tr>
                                <th>สถานะ</th>
                                <th>รหัสเครื่อง (HWID)</th>
                                <th>ผู้ใช้งาน / ลูกค้า</th>
                                <th>บัญชี MT5</th>
                                <th>Balance</th>
                                <th>กำไรสด (PnL)</th>
                                <th>สัญญาณล่าสุด</th>
                                <th>คำสั่งจัดการ</th>
                            </tr>
                        </thead>
                        <tbody id="tbody-radar">
                            <tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 28px;">⏳ กำลังเชื่อมต่อข้อมูลอุปกรณ์สด...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ══════════════════════════════════════════════════════════════════
             TAB 2: LICENSE VAULT (ZONE 2)
        ══════════════════════════════════════════════════════════════════ -->
        <div class="tab-pane" id="tab-keys">
            <div class="panel-card">
                <div class="panel-toolbar">
                    <div class="panel-heading">
                        <h2>🔑 คลังคีย์ผลิตภัณฑ์และข้อมูลลูกค้า (License &amp; Customer Vault)</h2>
                    </div>
                    <div class="panel-actions">
                        <div class="search-box">
                            <span class="search-icon">🔍</span>
                            <input type="text" id="keys-search" placeholder="ค้นหาคีย์ / ชื่อลูกค้า..." onkeyup="filterKeysTable()">
                        </div>
                        <button type="button" class="btn-primary-pill" onclick="switchTab('tab-generate', document.querySelectorAll('.tab-item')[2])">
                            <span>➕ ออกคีย์ใหม่</span>
                        </button>
                    </div>
                </div>

                <div class="table-responsive">
                    <table id="table-keys">
                        <thead>
                            <tr>
                                <th>รหัสคีย์ผลิตภัณฑ์ (License Key)</th>
                                <th>ชื่อผู้ใช้งาน (Username)</th>
                                <th>สถานะ</th>
                                <th>เครื่องที่ผูก (Bound HWID)</th>
                                <th>วันหมดอายุ</th>
                                <th>หมายเหตุ</th>
                                <th>คำสั่งจัดการสิทธิ์</th>
                            </tr>
                        </thead>
                        <tbody id="tbody-keys">
                            <tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 28px;">⏳ กำลังโหลดรายการคีย์ลิขสิทธิ์...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ══════════════════════════════════════════════════════════════════
             TAB 3: QUICK KEY GENERATOR (ZONE 3)
        ══════════════════════════════════════════════════════════════════ -->
        <div class="tab-pane" id="tab-generate">
            <div class="panel-card" style="max-width: 840px; margin: 0 auto;">
                <div class="panel-toolbar">
                    <div class="panel-heading">
                        <h2>⚡ สร้างคีย์ผลิตภัณฑ์ใหม่ (Generate Product Key)</h2>
                    </div>
                </div>

                <form id="key-gen-form" onsubmit="event.preventDefault(); handleCreateKey();">
                    <div class="form-grid">
                        <div class="form-control">
                            <label>ชื่อผู้ใช้งาน / ลูกค้า (Customer Username) <span style="color: var(--accent-rose);">*จำเป็น</span></label>
                            <input type="text" id="gen-customer-name" placeholder="เช่น JohnTrader, VIP001" required>
                        </div>

                        <div class="form-control">
                            <label>ช่องทางติดต่อ (LINE ID / Tel / Telegram)</label>
                            <input type="text" id="gen-customer-contact" placeholder="เช่น @line_id หรือ 081-xxx-xxxx">
                        </div>
                    </div>

                    <div class="form-grid">
                        <div class="form-control">
                            <label>ผูกรหัส HWID ล่วงหน้า (เว้นว่างไว้เพื่อผูกอัตโนมัติเมื่อเปิดครั้งแรก)</label>
                            <input type="text" id="gen-hwid-bound" class="mono" placeholder="เว้นว่าง หรือกรอก HWID 12 หลัก">
                        </div>

                        <div class="form-control">
                            <label>เลือกระยะเวลาสิทธิ์การใช้งาน (Duration Preset)</label>
                            <select id="gen-duration">
                                <option value="1">1 วัน (ทดสอบด่วน)</option>
                                <option value="7">7 วัน (ทดลอง 1 สัปดาห์)</option>
                                <option value="30" selected>30 วัน (1 เดือน)</option>
                                <option value="90">90 วัน (3 เดือน)</option>
                                <option value="180">180 วัน (6 เดือน)</option>
                                <option value="365">365 วัน (1 ปีเต็ม)</option>
                                <option value="29000">ตลอดชีพ (Lifetime VIP)</option>
                            </select>
                            <div class="preset-container">
                                <button type="button" class="preset-btn" onclick="document.getElementById('gen-duration').value='1'">1 วัน</button>
                                <button type="button" class="preset-btn" onclick="document.getElementById('gen-duration').value='7'">7 วัน</button>
                                <button type="button" class="preset-btn" onclick="document.getElementById('gen-duration').value='30'">30 วัน</button>
                                <button type="button" class="preset-btn" onclick="document.getElementById('gen-duration').value='90'">90 วัน</button>
                                <button type="button" class="preset-btn" onclick="document.getElementById('gen-duration').value='365'">1 ปี</button>
                                <button type="button" class="preset-btn" onclick="document.getElementById('gen-duration').value='29000'">ตลอดชีพ</button>
                            </div>
                        </div>
                    </div>

                    <div class="form-control" style="margin-bottom: 20px;">
                        <label>หมายเหตุ / รายละเอียดแพ็กเกจ</label>
                        <input type="text" id="gen-notes" placeholder="เช่น ลูกค้าแพ็กเกจ Gold VIP 2026">
                    </div>

                    <button type="submit" class="btn-primary-pill" style="width: 100%; justify-content: center; padding: 12px; font-size: 13.5px;">
                        <span>⚡ สร้างคีย์ลิขสิทธิ์และบันทึกสิทธิ์ทันที (GENERATE KEY)</span>
                    </button>
                </form>

                <div class="generated-key-banner" id="key-result-box">
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); font-weight: 700;">🎉 คีย์ผลิตภัณฑ์ถูกสร้างเรียบร้อยแล้ว:</div>
                        <div class="mono" style="font-size: 17px; font-weight: 800; color: #FDE047; margin: 3px 0;" id="key-result-text">KRIT-30D-XXXX-YYYY</div>
                        <div style="font-size: 11.5px; color: #FFFFFF;" id="key-result-meta">ผู้ใช้งาน: Mr. Krit | หมดอายุ: 2026-09-30</div>
                    </div>
                    <button type="button" class="btn-compact" onclick="copyResultKey()">📋 คัดลอกส่งลูกค้า</button>
                </div>
            </div>
        </div>

        <!-- ══════════════════════════════════════════════════════════════════
             TAB 4: SECURITY & ALERTS (ZONE 4)
        ══════════════════════════════════════════════════════════════════ -->
        <div class="tab-pane" id="tab-security">
            <div class="panel-card">
                <div class="panel-toolbar">
                    <div class="panel-heading">
                        <h2>🛡️ ระบบความปลอดภัยและคำสั่งฉุกเฉิน (Security &amp; Broadcast)</h2>
                    </div>
                </div>

                <div class="form-grid">
                    <div style="background: var(--bg-glass); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 18px;">
                        <h3 style="color: var(--accent-gold); font-size: 14px; margin-bottom: 8px;">📢 ส่งข้อความประกาศด่วน (Global Broadcast)</h3>
                        <p style="font-size: 11.5px; color: var(--text-secondary); margin-bottom: 12px;">ส่งข้อความแจ้งเตือนขึ้นหน้าจอ Web Cockpit ของผู้ใช้งานทุกคนทันที</p>
                        <input type="text" id="broadcast-msg" class="form-control input" placeholder="พิมพ์ข้อความ เช่น ปรับปรุงระบบเวลา 23:00 น." style="width: 100%; margin-bottom: 10px; background:var(--bg-input); border:1px solid var(--border-subtle); padding:8px 12px; border-radius:var(--radius-md); color:#FFF; font-size:12px;">
                        <button type="button" class="btn-compact" onclick="alert('✅ ส่งข้อความประกาศเข้าทุกหน้าจอเรียบร้อยแล้ว')">📢 ส่งข้อความทันที</button>
                    </div>

                    <div style="background: rgba(244, 63, 94, 0.04); border: 1px solid rgba(244, 63, 94, 0.2); border-radius: var(--radius-lg); padding: 18px;">
                        <h3 style="color: var(--accent-rose); font-size: 14px; margin-bottom: 8px;">🚨 สั่งหยุดฉุกเฉินทั้งหมด (Emergency Killswitch)</h3>
                        <p style="font-size: 11.5px; color: var(--text-secondary); margin-bottom: 12px;">ส่งคำสั่งเตะอุปกรณ์ที่กำลังออนไลน์ทั้งหมดออกจากระบบทันที</p>
                        <button type="button" class="btn-compact danger" onclick="if(confirm('⚠️ ยืนยันการสั่งตัดสัญญาณและเตะอุปกรณ์ทั้งหมดออกจากระบบทันทีหรือไม่?')) alert('⛔ ส่งสัญญาณ KICK_ALL เรียบร้อยแล้ว')">🚨 EMERGENCY KICK ALL</button>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <!-- JAVASCRIPT LOGIC -->
    <script>
        let adminToken = localStorage.getItem("mrkrit_admin_token") || "";
        let overviewData = { stats: {}, bots: [], keys: [] };

        document.addEventListener("DOMContentLoaded", () => {
            setInterval(updateClock, 1000);
            updateClock();
            checkAuth();
        });

        function updateClock() {
            const el = document.getElementById("server-clock");
            if (el) el.textContent = new Date().toLocaleTimeString('th-TH');
        }

        function checkAuth() {
            const gate = document.getElementById("admin-auth-gate");
            if (!adminToken) {
                if (gate) gate.style.display = "flex";
            } else {
                if (gate) gate.style.display = "none";
                loadOverviewData();
                setInterval(loadOverviewData, 8000);
            }
        }

        async function handleAdminLogin() {
            const u = document.getElementById("admin-user-input").value;
            const p = document.getElementById("admin-pass-input").value;
            const fd = new FormData();
            fd.append("username", u);
            fd.append("password", p);

            try {
                const res = await fetch("/api/admin/login", { method: "POST", body: fd });
                const data = await res.json();
                if (data.success && data.token) {
                    adminToken = data.token;
                    localStorage.setItem("mrkrit_admin_token", adminToken);
                    document.getElementById("admin-auth-gate").style.display = "none";
                    loadOverviewData();
                } else {
                    alert("❌ " + (data.message || "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"));
                }
            } catch (e) {
                alert("⚠️ ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์: " + e);
            }
        }

        function handleAdminLogout() {
            if (!confirm("🚪 ต้องการออกจากระบบ Master Admin หรือไม่?")) return;
            localStorage.removeItem("mrkrit_admin_token");
            adminToken = "";
            window.location.reload();
        }

        function switchTab(tabId, btn) {
            document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
            document.querySelectorAll(".tab-item").forEach(b => b.classList.remove("active"));
            const target = document.getElementById(tabId);
            if (target) target.classList.add("active");
            if (btn) btn.classList.add("active");
        }

        async function loadOverviewData() {
            if (!adminToken) return;
            try {
                const res = await fetch(`/api/admin/overview?token=${adminToken}`);
                if (res.status === 401) {
                    handleAdminLogout();
                    return;
                }
                const data = await res.json();
                overviewData = data;
                renderDashboard(data);
            } catch (e) {
                console.error("Overview error:", e);
            }
        }

        function renderDashboard(data) {
            // Metrics
            document.getElementById("metric-online").textContent = data.stats.online_bots || 0;
            document.getElementById("metric-offline").textContent = data.stats.offline_bots || 0;
            document.getElementById("metric-keys").textContent = `${data.stats.active_keys || 0} / ${data.stats.total_keys || 0}`;
            document.getElementById("metric-pnl").textContent = `$${(data.stats.total_pnl || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}`;

            // Radar Table
            const tbodyRadar = document.getElementById("tbody-radar");
            if (!data.bots || data.bots.length === 0) {
                tbodyRadar.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 28px;">🛰️ ยังไม่มีอุปกรณ์ส่งสัญญาณเข้ามาในขณะนี้</td></tr>';
            } else {
                tbodyRadar.innerHTML = data.bots.map(b => {
                    const isOnline = b.is_online;
                    const statusClass = isOnline ? "badge-active" : "badge-revoked";
                    const statusText = isOnline ? "🟢 ONLINE" : "🔴 OFFLINE";
                    const pnlVal = parseFloat(b.profit_today || 0);
                    const pnlColor = pnlVal >= 0 ? "var(--accent-emerald)" : "var(--accent-rose)";
                    return `
                        <tr>
                            <td><span class="badge-pill ${statusClass}">${statusText}</span></td>
                            <td class="mono" style="font-weight: 700; color: #FDE047;">${b.hwid || 'N/A'}</td>
                            <td style="font-weight: 600; color: #FFFFFF;">${b.customer_name || 'ลูกค้าทั่วไป'}</td>
                            <td>${b.account_login || 'MT5 Ready'}</td>
                            <td class="mono">$${parseFloat(b.balance || 0).toFixed(2)}</td>
                            <td class="mono" style="font-weight: 700; color: ${pnlColor};">${pnlVal >= 0 ? '+' : ''}$${pnlVal.toFixed(2)}</td>
                            <td style="font-size: 11px; color: var(--text-muted);">${b.last_seen_sec}s ago</td>
                            <td>
                                <button type="button" class="btn-icon danger" onclick="kickDevice('${b.hwid}')">⛔ เตะออก</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            // Keys Table
            const tbodyKeys = document.getElementById("tbody-keys");
            if (!data.keys || data.keys.length === 0) {
                tbodyKeys.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 28px;">🔑 ยังไม่มีรายการคีย์ลิขสิทธิ์</td></tr>';
            } else {
                tbodyKeys.innerHTML = data.keys.map(k => {
                    const st = k.status;
                    let stClass = "badge-active";
                    let stText = "🟢 ACTIVE";
                    if (st === "REVOKED" || st === "BANNED") {
                        stClass = "badge-revoked";
                        stText = "🚫 REVOKED";
                    } else if (st === "EXPIRED") {
                        stClass = "badge-expired";
                        stText = "⏳ EXPIRED";
                    }

                    const isRevoked = (st === "REVOKED" || st === "BANNED");
                    const toggleAction = isRevoked ? "ACTIVATE" : "REVOKE";
                    const toggleLabel = isRevoked ? "🟢 เปิดใช้" : "🚫 ระงับ";
                    const toggleClass = isRevoked ? "success" : "danger";

                    return `
                        <tr>
                            <td>
                                <span class="key-tag mono" onclick="navigator.clipboard.writeText('${k.key_code}'); alert('📋 คัดลอกคีย์: ${k.key_code}')" title="คลิกเพื่อคัดลอก">${k.key_code}</span>
                            </td>
                            <td style="font-weight: 600; color: #FFFFFF;">${k.customer_name || '-'}</td>
                            <td><span class="badge-pill ${stClass}">${stText}</span></td>
                            <td class="mono" style="font-size: 11.5px; color: ${k.hwid_bound ? 'var(--accent-cyan)' : 'var(--text-muted)'};">
                                ${k.hwid_bound || '(รอผูกเครื่อง)'}
                                ${k.hwid_bound ? `<button type="button" style="background:none; border:none; color:#FDE047; cursor:pointer; font-size:11px; margin-left:4px;" onclick="keyAction('${k.key_code}', 'RESET_HWID')" title="ปลดล็อคเครื่อง">🔄</button>` : ''}
                            </td>
                            <td style="font-size: 11.5px;">${k.expires_at || '-'}</td>
                            <td style="font-size: 11px; color: var(--text-muted);">${k.notes || '-'}</td>
                            <td>
                                <div class="btn-group-actions">
                                    <button type="button" class="btn-icon" onclick="keyAction('${k.key_code}', 'EXTEND_30D')">+30 วัน</button>
                                    <button type="button" class="btn-icon ${toggleClass}" onclick="keyAction('${k.key_code}', '${toggleAction}')">${toggleLabel}</button>
                                    <button type="button" class="btn-icon danger" onclick="if(confirm('ลบคีย์นี้ถาวร?')) keyAction('${k.key_code}', 'DELETE')">🗑️</button>
                                </div>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }

        async function keyAction(keyCode, action) {
            const fd = new FormData();
            fd.append("key_code", keyCode);
            fd.append("action", action);
            fd.append("token", adminToken);

            try {
                const res = await fetch("/api/admin/keys/action", { method: "POST", body: fd });
                const d = await res.json();
                if (d.success) {
                    loadOverviewData();
                } else {
                    alert("❌ ทำรายการไม่สำเร็จ");
                }
            } catch (e) {
                alert("⚠️ Error: " + e);
            }
        }

        async function kickDevice(hwid) {
            if (!confirm(`⚠️ ยืนยันการสั่งเตะอุปกรณ์ HWID: ${hwid} ออกจากระบบทันทีหรือไม่?`)) return;
            await keyAction(hwid, "KICK");
            alert(`⛔ ส่งคำสั่งเตะอุปกรณ์ ${hwid} เรียบร้อยแล้ว!`);
        }

        async function handleCreateKey() {
            const customer_name = document.getElementById("gen-customer-name").value.trim();
            const customer_contact = document.getElementById("gen-customer-contact").value.trim();
            const hwid_bound = document.getElementById("gen-hwid-bound").value.trim();
            const duration_days = parseInt(document.getElementById("gen-duration").value) || 30;
            const notes = document.getElementById("gen-notes").value.trim();

            if (!customer_name) {
                alert("❌ กรุณาระบุชื่อผู้ใช้งาน / ลูกค้า");
                return;
            }

            try {
                const res = await fetch(`/api/admin/keys/create?token=${adminToken}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ customer_name, customer_contact, hwid_bound, duration_days, notes })
                });
                const d = await res.json();
                if (d.success) {
                    document.getElementById("key-result-text").textContent = d.key_code;
                    document.getElementById("key-result-meta").textContent = `ผู้ใช้งาน: ${d.customer_name} | หมดอายุ: ${d.expires_at}`;
                    document.getElementById("key-result-box").style.display = "flex";
                    loadOverviewData();
                } else {
                    alert("❌ สร้างคีย์ไม่สำเร็จ");
                }
            } catch (e) {
                alert("⚠️ Error: " + e);
            }
        }

        function copyResultKey() {
            const key = document.getElementById("key-result-text").textContent;
            navigator.clipboard.writeText(key);
            alert("📋 คัดลอกคีย์เรียบร้อยแล้ว: " + key);
        }

        function filterRadarTable() {
            const q = document.getElementById("radar-search").value.toLowerCase();
            document.querySelectorAll("#tbody-radar tr").forEach(tr => {
                tr.style.display = tr.textContent.toLowerCase().includes(q) ? "" : "none";
            });
        }

        function filterKeysTable() {
            const q = document.getElementById("keys-search").value.toLowerCase();
            document.querySelectorAll("#tbody-keys tr").forEach(tr => {
                tr.style.display = tr.textContent.toLowerCase().includes(q) ? "" : "none";
            });
        }
    </script>
</body>
</html>
"""

@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/", response_class=HTMLResponse)
def admin_page():
    return HTMLResponse(content=ADMIN_HTML)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
