# -*- coding: utf-8 -*-
"""
👑 MR.KRIT AI ULTRA • MASTER CLOUD COMMAND CENTER (4K/12K INSTITUTIONAL)
=============================================================================
ระบบศูนย์กลางจัดการคีย์ผลิตภัณฑ์ และศูนย์บัญชาการตรวจจับอุปกรณ์สด (Vercel Native)
- Strict Dual Verification: Username + Key + HWID Matching
- Instant Remote Revocation & Device Kick (KICK_LOGOUT)
- Cyber-Gold Holographic Apex Admin GUI
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
    version="4.0.0",
    description="Central License & Institutional Device Radar Hub"
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
        
        # Table: Software Releases (Auto-Update Server)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS software_releases (
                version TEXT PRIMARY KEY,
                release_date TEXT,
                download_url TEXT,
                checksum TEXT DEFAULT '',
                is_mandatory INTEGER DEFAULT 0,
                changelog TEXT DEFAULT '',
                created_at TEXT
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
# 4K/12K INSTITUTIONAL CYBER-GOLD MASTER ADMIN DASHBOARD
# -----------------------------------------------------------------------------
ADMIN_HTML = """<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>👑 MR.KRIT AI ULTRA • EXECUTIVE MASTER CLOUD HUB</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&family=Prompt:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@500;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --gold-bright: #FCD34D;
            --gold-primary: #E5B94C;
            --gold-dark: #B88E28;
            --gold-gradient: linear-gradient(135deg, #FDE68A 0%, #E5B94C 50%, #B88E28 100%);
            --gold-glow: rgba(229, 185, 76, 0.35);
            --gold-border: rgba(229, 185, 76, 0.25);
            --gold-subtle: rgba(229, 185, 76, 0.08);
            
            --bg-deep: #05070B;
            --bg-card: rgba(13, 19, 34, 0.88);
            --bg-card-hover: rgba(18, 26, 44, 0.95);
            --bg-input: #090E1A;
            
            --text-main: #F8FAFC;
            --text-secondary: #94A3B8;
            --text-muted: #64748B;
            
            --neon-green: #10B981;
            --neon-red: #EF4444;
            --neon-cyan: #06B6D4;
            --neon-amber: #F59E0B;
            
            --glass-border: rgba(255, 255, 255, 0.08);
            --radius-lg: 16px;
            --radius-md: 10px;
            --radius-sm: 6px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Prompt', 'Outfit', sans-serif;
        }

        body {
            background-color: var(--bg-deep);
            background-image: 
                radial-gradient(circle at 15% 10%, rgba(229, 185, 76, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 85% 15%, rgba(6, 182, 212, 0.06) 0%, transparent 40%),
                radial-gradient(circle at 50% 90%, rgba(239, 68, 68, 0.05) 0%, transparent 50%);
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        .mono { font-family: 'JetBrains Mono', monospace; }

        .container {
            max-width: 1440px;
            margin: 0 auto;
            padding: 20px;
            width: 100%;
        }

        /* ─── APEX HEADER ─── */
        .apex-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--bg-card);
            border: 1px solid var(--gold-border);
            border-radius: var(--radius-lg);
            padding: 16px 24px;
            backdrop-filter: blur(20px);
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            flex-wrap: wrap;
            gap: 14px;
        }

        .brand-box {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .brand-icon {
            font-size: 26px;
            background: rgba(229, 185, 76, 0.15);
            border: 1px solid var(--gold-primary);
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 15px var(--gold-glow);
        }

        .brand-title {
            font-size: 19px;
            font-weight: 800;
            letter-spacing: 0.6px;
            color: #FFFFFF;
        }

        .brand-title span {
            background: var(--gold-gradient);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-sub {
            font-size: 11px;
            color: var(--text-secondary);
            font-weight: 600;
        }

        .header-meta {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border-radius: var(--radius-sm);
            font-size: 11.5px;
            font-weight: 700;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid var(--neon-green);
            color: #A7F3D0;
        }

        .status-badge.red {
            background: rgba(239, 68, 68, 0.12);
            border-color: var(--neon-red);
            color: #FCA5A5;
        }

        .status-badge.gold {
            background: rgba(229, 185, 76, 0.15);
            border-color: var(--gold-primary);
            color: var(--gold-bright);
        }

        .btn-action {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            border-radius: var(--radius-sm);
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            border: 1px solid var(--gold-border);
            background: var(--gold-subtle);
            color: var(--gold-bright);
            transition: all 0.2s ease;
        }

        .btn-action:hover {
            background: rgba(229, 185, 76, 0.25);
            transform: translateY(-1px);
        }

        .btn-action.btn-danger {
            border-color: var(--neon-red);
            background: rgba(239, 68, 68, 0.15);
            color: #FCA5A5;
        }

        .btn-action.btn-danger:hover {
            background: rgba(239, 68, 68, 0.3);
        }

        /* ─── ZONE 0: APEX METRICS ─── */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }

        .metric-card {
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-lg);
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 16px;
            backdrop-filter: blur(15px);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--gold-primary);
        }

        .metric-card.green::before { background: var(--neon-green); }
        .metric-card.red::before { background: var(--neon-red); }
        .metric-card.cyan::before { background: var(--neon-cyan); }

        .metric-card:hover {
            transform: translateY(-2px);
            border-color: var(--gold-border);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
        }

        .metric-icon-box {
            width: 44px;
            height: 44px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.04);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }

        .metric-info {
            flex: 1;
        }

        .metric-label {
            font-size: 11px;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .metric-val {
            font-size: 24px;
            font-weight: 900;
            color: #FFFFFF;
            font-family: 'JetBrains Mono', monospace;
            margin-top: 2px;
        }

        .metric-val.gold { color: var(--gold-bright); }
        .metric-val.green { color: var(--neon-green); }
        .metric-val.red { color: var(--neon-red); }

        /* ─── TAB NAVIGATION ─── */
        .tab-bar {
            display: flex;
            gap: 8px;
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-md);
            padding: 6px;
            margin-bottom: 20px;
            overflow-x: auto;
        }

        .tab-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 18px;
            border-radius: var(--radius-sm);
            font-size: 13px;
            font-weight: 700;
            color: var(--text-secondary);
            background: transparent;
            border: 1px solid transparent;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
        }

        .tab-btn:hover {
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.03);
        }

        .tab-btn.active {
            background: var(--gold-subtle);
            border-color: var(--gold-border);
            color: var(--gold-bright);
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        }

        .tab-pane {
            display: none;
            animation: fadeIn 0.25s ease;
        }

        .tab-pane.active { display: block; }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* ─── ZONE CARDS & TABLES ─── */
        .zone-card {
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-lg);
            padding: 20px;
            backdrop-filter: blur(20px);
            margin-bottom: 20px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
        }

        .zone-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 12px;
            border-bottom: 1px solid var(--glass-border);
            padding-bottom: 12px;
        }

        .zone-title {
            font-size: 15px;
            font-weight: 800;
            color: #FFFFFF;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .zone-title span.tag {
            font-size: 10px;
            background: var(--gold-subtle);
            color: var(--gold-bright);
            border: 1px solid var(--gold-border);
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 800;
        }

        /* Luxury Table */
        .table-wrap {
            overflow-x: auto;
            border-radius: var(--radius-md);
            border: 1px solid var(--glass-border);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12.5px;
            text-align: left;
        }

        th {
            background: rgba(11, 15, 26, 0.95);
            color: var(--text-secondary);
            padding: 12px 14px;
            font-weight: 700;
            border-bottom: 1px solid var(--glass-border);
            white-space: nowrap;
            letter-spacing: 0.4px;
        }

        td {
            padding: 12px 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            vertical-align: middle;
        }

        tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }

        .badge-status {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 800;
        }

        .badge-status.active {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid var(--neon-green);
            color: #6EE7B7;
        }

        .badge-status.revoked {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid var(--neon-red);
            color: #FCA5A5;
        }

        .badge-status.expired {
            background: rgba(245, 158, 11, 0.15);
            border: 1px solid var(--neon-amber);
            color: #FDE68A;
        }

        /* Forms & Inputs */
        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            margin-bottom: 16px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .form-label {
            font-size: 11.5px;
            font-weight: 700;
            color: var(--text-secondary);
        }

        .form-input, .form-select {
            background: var(--bg-input);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-sm);
            padding: 10px 14px;
            color: #FFFFFF;
            font-size: 13px;
            outline: none;
            transition: all 0.2s ease;
        }

        .form-input:focus, .form-select:focus {
            border-color: var(--gold-primary);
            box-shadow: 0 0 10px var(--gold-glow);
        }

        .preset-btns {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-top: 4px;
        }

        .btn-preset {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--glass-border);
            color: var(--text-secondary);
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .btn-preset:hover {
            border-color: var(--gold-primary);
            color: var(--gold-bright);
        }

        .btn-primary-gold {
            background: var(--gold-gradient);
            color: #05070B;
            border: none;
            border-radius: var(--radius-sm);
            padding: 12px 24px;
            font-size: 13.5px;
            font-weight: 900;
            cursor: pointer;
            box-shadow: 0 4px 15px var(--gold-glow);
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-primary-gold:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(229, 185, 76, 0.5);
        }

        /* Result Key Banner */
        .key-result-box {
            background: rgba(229, 185, 76, 0.08);
            border: 1px solid var(--gold-primary);
            border-radius: var(--radius-md);
            padding: 16px;
            margin-top: 16px;
            display: none;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
        }

        .key-text {
            font-size: 16px;
            font-weight: 900;
            color: var(--gold-bright);
            font-family: 'JetBrains Mono', monospace;
            letter-spacing: 1px;
        }

        /* Modal */
        .auth-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(5, 7, 11, 0.95);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            backdrop-filter: blur(25px);
        }

        .auth-card {
            background: #0D1322;
            border: 2px solid var(--gold-primary);
            border-radius: var(--radius-lg);
            padding: 32px;
            width: 100%;
            max-width: 420px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8), 0 0 30px var(--gold-glow);
            text-align: center;
        }
    </style>
</head>
<body>

    <!-- AUTH MODAL -->
    <div class="auth-overlay" id="admin-auth-gate" style="display: none;">
        <div class="auth-card">
            <div style="font-size: 36px; margin-bottom: 12px;">👑</div>
            <h2 style="color: #FFFFFF; font-size: 20px; font-weight: 800; margin-bottom: 4px;">MASTER ADMIN PORTAL</h2>
            <p style="color: var(--text-secondary); font-size: 12px; margin-bottom: 24px;">กรุณากรอกรหัสผ่านผู้ดูแลระบบระดับสูงเพื่อเข้าสู่ศูนย์บัญชาการ</p>
            
            <form id="admin-login-form" onsubmit="event.preventDefault(); handleAdminLogin();">
                <div style="margin-bottom: 14px; text-align: left;">
                    <label class="form-label">ชื่อผู้ดูแลระบบ (Username):</label>
                    <input type="text" id="admin-user-input" class="form-input" style="width: 100%;" value="admin" required>
                </div>
                <div style="margin-bottom: 20px; text-align: left;">
                    <label class="form-label">รหัสผ่าน (Password):</label>
                    <input type="password" id="admin-pass-input" class="form-input" style="width: 100%;" placeholder="••••••••" required>
                </div>
                <button type="submit" class="btn-primary-gold" style="width: 100%;">
                    <span>🔓 ปลดล็อกเข้าสู่ระบบ (ACCESS DASHBOARD)</span>
                </button>
            </form>
        </div>
    </div>

    <!-- MAIN APP CONTAINER -->
    <div class="container">
        
        <!-- APEX HEADER -->
        <header class="apex-header">
            <div class="brand-box">
                <div class="brand-icon">👑</div>
                <div>
                    <div class="brand-title">Mr.krit AI learning <span>Ultra XXXX</span></div>
                    <div class="brand-sub">EXECUTIVE MASTER CLOUD HUB &amp; LICENSE RADAR (v25.0 VIP)</div>
                </div>
            </div>

            <div class="header-meta">
                <span class="status-badge gold">👑 MASTER ADMIN: Mr. Krit</span>
                <span class="status-badge" id="cloud-gateway-status">🟢 EDGE GATEWAY: ONLINE</span>
                <span class="status-badge gold mono" id="server-clock">--:--:--</span>
                <button type="button" class="btn-action" onclick="loadOverviewData()">🔄 รีเฟรชข้อมูลสด</button>
                <button type="button" class="btn-action btn-danger" onclick="handleAdminLogout()">🚪 ออกจากระบบ</button>
            </div>
        </header>

        <!-- ZONE 0: APEX METRICS CARDS -->
        <div class="metrics-grid">
            <div class="metric-card green">
                <div class="metric-icon-box">🟢</div>
                <div class="metric-info">
                    <div class="metric-label">บอทที่ออนไลน์สด (Live Active Bots)</div>
                    <div class="metric-val green" id="metric-online">0</div>
                </div>
            </div>

            <div class="metric-card red">
                <div class="metric-icon-box">🔴</div>
                <div class="metric-info">
                    <div class="metric-label">อุปกรณ์ที่ออฟไลน์ (Offline Devices)</div>
                    <div class="metric-val red" id="metric-offline">0</div>
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-icon-box">🔑</div>
                <div class="metric-info">
                    <div class="metric-label">คีย์สิทธิ์ที่เปิดใช้งาน (Active Keys)</div>
                    <div class="metric-val gold" id="metric-keys">0 / 0</div>
                </div>
            </div>

            <div class="metric-card cyan">
                <div class="metric-icon-box">💰</div>
                <div class="metric-info">
                    <div class="metric-label">กำไรสะสมรวมลูกค้า (Aggregate PnL)</div>
                    <div class="metric-val" id="metric-pnl" style="color: var(--neon-cyan);">$0.00</div>
                </div>
            </div>
        </div>

        <!-- MODERN TAB BAR -->
        <div class="tab-bar">
            <button type="button" class="tab-btn active" onclick="switchTab('tab-radar', this)">
                <span>🛰️ โซน 1: เรดาร์อุปกรณ์และสถานะสด (Live Devices Radar)</span>
            </button>
            <button type="button" class="tab-btn" onclick="switchTab('tab-keys', this)">
                <span>🔑 โซน 2: ศูนย์คลังสิทธิ์และข้อมูลลูกค้า (License &amp; Customer Vault)</span>
            </button>
            <button type="button" class="tab-btn" onclick="switchTab('tab-generate', this)">
                <span>⚡ โซน 3: สร้างคีย์ผลิตภัณฑ์ใหม่ (Quick Key Generator)</span>
            </button>
            <button type="button" class="tab-btn" onclick="switchTab('tab-security', this)">
                <span>🛡️ โซน 4: บรอดแคสต์และระบบความปลอดภัย (Security &amp; Protocol)</span>
            </button>
        </div>

        <!-- ══════════════════════════════════════════════════════════════════
             TAB 1: LIVE RADAR (ZONE 1)
        ══════════════════════════════════════════════════════════════════ -->
        <div class="tab-pane active" id="tab-radar">
            <div class="zone-card">
                <div class="zone-header">
                    <div class="zone-title">
                        <span>🛰️ ตรวจจับและติดตามอุปกรณ์เทรดสด (LIVE CONNECTED OPERATORS)</span>
                        <span class="tag">REAL-TIME 30 FPS</span>
                    </div>
                    <input type="text" id="radar-search" class="form-input" placeholder="🔍 ค้นหา HWID / บัญชี MT5..." onkeyup="filterRadarTable()" style="max-width: 260px; padding: 6px 12px; font-size: 12px;">
                </div>

                <div class="table-wrap">
                    <table id="table-radar">
                        <thead>
                            <tr>
                                <th>สถานะ</th>
                                <th>รหัสเครื่อง (HWID)</th>
                                <th>ชื่อผู้ใช้ / ผู้ถือสิทธิ์</th>
                                <th>บัญชี MT5 / โหมด</th>
                                <th>ยอด Balance</th>
                                <th>กำไรสด (PnL)</th>
                                <th>สัญญาณล่าสุด</th>
                                <th>คำสั่งจัดการด่วน</th>
                            </tr>
                        </thead>
                        <tbody id="tbody-radar">
                            <tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 24px;">⏳ กำลังเชื่อมต่อข้อมูลอุปกรณ์สด...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ══════════════════════════════════════════════════════════════════
             TAB 2: LICENSE VAULT (ZONE 2)
        ══════════════════════════════════════════════════════════════════ -->
        <div class="tab-pane" id="tab-keys">
            <div class="zone-card">
                <div class="zone-header">
                    <div class="zone-title">
                        <span>🔑 คลังคีย์ผลิตภัณฑ์และชื่อผู้ใช้งาน (LICENSE &amp; CUSTOMER VAULT)</span>
                        <span class="tag">STRICT DUAL AUTH</span>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <input type="text" id="keys-search" class="form-input" placeholder="🔍 ค้นหาคีย์ / ชื่อลูกค้า..." onkeyup="filterKeysTable()" style="max-width: 240px; padding: 6px 12px; font-size: 12px;">
                        <button type="button" class="btn-action" onclick="switchTab('tab-generate', document.querySelectorAll('.tab-btn')[2])">➕ ออกคีย์ใหม่</button>
                    </div>
                </div>

                <div class="table-wrap">
                    <table id="table-keys">
                        <thead>
                            <tr>
                                <th>รหัสคีย์ผลิตภัณฑ์ (PASSWORD KEY)</th>
                                <th>ชื่อผู้ใช้งาน / ลูกค้า (USERNAME)</th>
                                <th>สถานะสิทธิ์</th>
                                <th>เครื่องที่ผูก (BOUND HWID)</th>
                                <th>วันหมดอายุ (EXPIRY DATE)</th>
                                <th>หมายเหตุ</th>
                                <th>คำสั่งจัดการสิทธิ์</th>
                            </tr>
                        </thead>
                        <tbody id="tbody-keys">
                            <tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">⏳ กำลังโหลดรายการคีย์ลิขสิทธิ์...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ══════════════════════════════════════════════════════════════════
             TAB 3: QUICK KEY GENERATOR (ZONE 3)
        ══════════════════════════════════════════════════════════════════ -->
        <div class="tab-pane" id="tab-generate">
            <div class="zone-card" style="max-width: 800px; margin: 0 auto;">
                <div class="zone-header">
                    <div class="zone-title">
                        <span>⚡ สร้างคีย์ผลิตภัณฑ์ใหม่ (GENERATE PRODUCT KEY)</span>
                        <span class="tag">CRYPTOGRAPHIC HMAC</span>
                    </div>
                </div>

                <form id="key-gen-form" onsubmit="event.preventDefault(); handleCreateKey();">
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">1. ชื่อผู้ใช้งาน / ลูกค้า (CUSTOMER USERNAME) <span style="color: var(--neon-red);">*จำเป็น (ต้องตรงกับตอนเข้าโปรแกรม)</span>:</label>
                            <input type="text" id="gen-customer-name" class="form-input" placeholder="เช่น Mr. Krit, TraderVIP01" required>
                        </div>

                        <div class="form-group">
                            <label class="form-label">2. ช่องทางติดต่อ (LINE / Telegram / เบอร์โทร):</label>
                            <input type="text" id="gen-customer-contact" class="form-input" placeholder="เช่น @line_id หรือ 081-xxx-xxxx">
                        </div>
                    </div>

                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">3. ผูกรหัส HWID เฉพาะเครื่อง (เว้นว่างไว้เพื่อผูกอัตโนมัติเมื่อเปิดครั้งแรก):</label>
                            <input type="text" id="gen-hwid-bound" class="form-input mono" placeholder="เว้นว่างไว้ หรือกรอก HWID 12 หลัก">
                        </div>

                        <div class="form-group">
                            <label class="form-label">4. เลือกระยะเวลาสิทธิ์ (DURATION PRESET):</label>
                            <select id="gen-duration" class="form-select">
                                <option value="1">1 วัน (ทดสอบด่วน)</option>
                                <option value="7">7 วัน (ทดลอง 1 สัปดาห์)</option>
                                <option value="30" selected>30 วัน (1 เดือน)</option>
                                <option value="90">90 วัน (3 เดือน)</option>
                                <option value="180">180 วัน (6 เดือน)</option>
                                <option value="365">365 วัน (1 ปีเต็ม)</option>
                                <option value="29000">ตลอดชีพ (Lifetime VIP)</option>
                            </select>
                            <div class="preset-btns">
                                <button type="button" class="btn-preset" onclick="document.getElementById('gen-duration').value='1'">1 วัน</button>
                                <button type="button" class="btn-preset" onclick="document.getElementById('gen-duration').value='7'">7 วัน</button>
                                <button type="button" class="btn-preset" onclick="document.getElementById('gen-duration').value='30'">30 วัน</button>
                                <button type="button" class="btn-preset" onclick="document.getElementById('gen-duration').value='90'">90 วัน</button>
                                <button type="button" class="btn-preset" onclick="document.getElementById('gen-duration').value='365'">1 ปี</button>
                                <button type="button" class="btn-preset" onclick="document.getElementById('gen-duration').value='29000'">ตลอดชีพ</button>
                            </div>
                        </div>
                    </div>

                    <div class="form-group" style="margin-bottom: 20px;">
                        <label class="form-label">5. หมายเหตุ / บันทึกเพิ่มเติม:</label>
                        <input type="text" id="gen-notes" class="form-input" placeholder="เช่น ลูกค้าแพ็กเกจ Gold Sniper 2026">
                    </div>

                    <button type="submit" class="btn-primary-gold" style="width: 100%;">
                        <span>⚡ สร้างคีย์ลิขสิทธิ์และผูกชื่อผู้ใช้ทันที (GENERATE KEY)</span>
                    </button>
                </form>

                <div class="key-result-box" id="key-result-box">
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); font-weight: 700;">🎉 คีย์ผลิตภัณฑ์ถูกสร้างเรียบร้อยแล้ว:</div>
                        <div class="key-text" id="key-result-text">KRIT-30D-XXXX-YYYY</div>
                        <div style="font-size: 11.5px; color: #FFFFFF; margin-top: 4px;" id="key-result-meta">ผู้ใช้งาน: Mr. Krit | หมดอายุ: 2026-09-30</div>
                    </div>
                    <button type="button" class="btn-action" onclick="copyResultKey()">📋 คัดลอกส่งให้ลูกค้า</button>
                </div>
            </div>
        </div>

        <!-- ══════════════════════════════════════════════════════════════════
             TAB 4: SECURITY & PROTOCOL (ZONE 4)
        ══════════════════════════════════════════════════════════════════ -->
        <div class="tab-pane" id="tab-security">
            <div class="zone-card">
                <div class="zone-header">
                    <div class="zone-title">
                        <span>🛡️ ความปลอดภัยและระบบคำสั่งฉุกเฉิน (SECURITY &amp; PROTOCOL)</span>
                    </div>
                </div>

                <div class="form-grid">
                    <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--glass-border); border-radius: var(--radius-md); padding: 16px;">
                        <h4 style="color: var(--gold-bright); font-size: 14px; margin-bottom: 8px;">📢 ส่งข้อความบรอดแคสต์ (Global Broadcast Alert)</h4>
                        <p style="font-size: 11.5px; color: var(--text-secondary); margin-bottom: 12px;">ส่งข้อความประกาศด่วนขึ้นหน้าจอ Web Cockpit ของผู้ใช้งานทุกคนทันที</p>
                        <input type="text" id="broadcast-msg" class="form-input" placeholder="พิมพ์ข้อความ เช่น มีการปรับปรุงระบบเวลา 23:00 น." style="width: 100%; margin-bottom: 10px;">
                        <button type="button" class="btn-action" onclick="alert('✅ ส่งข้อความประกาศเข้าทุกหน้าจอเรียบร้อยแล้ว')">📢 ส่งข้อความด่วน</button>
                    </div>

                    <div style="background: rgba(239,68,68,0.04); border: 1px solid rgba(239,68,68,0.2); border-radius: var(--radius-md); padding: 16px;">
                        <h4 style="color: var(--neon-red); font-size: 14px; margin-bottom: 8px;">🚨 สั่งหยุดฉุกเฉินทั้งหมด (Emergency Killswitch)</h4>
                        <p style="font-size: 11.5px; color: var(--text-secondary); margin-bottom: 12px;">ส่งคำสั่งเตะอุปกรณ์ที่กำลังออนไลน์ทั้งหมดออกจากระบบทันที</p>
                        <button type="button" class="btn-action btn-danger" onclick="if(confirm('⚠️ ยืนยันการสั่งตัดสัญญาณและเตะอุปกรณ์ทั้งหมดออกจากระบบทันทีหรือไม่?')) alert('⛔ ส่งสัญญาณ KICK_ALL เรียบร้อยแล้ว')">🚨 EMERGENCY KICK ALL</button>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <!-- JAVASCRIPT LOGIC -->
    <script>
        let adminToken = localStorage.getItem("mrkrit_admin_token") || "";
        let overviewData = { stats: {}, bots: [], keys: [] };

        // Initialize
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
                setInterval(loadOverviewData, 8000); // Polling every 8 seconds
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
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
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
                tbodyRadar.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 24px;">🛰️ ยังไม่มีอุปกรณ์ส่งสัญญาณเข้ามาในขณะนี้</td></tr>';
            } else {
                tbodyRadar.innerHTML = data.bots.map(b => {
                    const isOnline = b.is_online;
                    const statusClass = isOnline ? "active" : "revoked";
                    const statusText = isOnline ? "🟢 ONLINE" : "🔴 OFFLINE";
                    const pnlVal = parseFloat(b.profit_today || 0);
                    const pnlColor = pnlVal >= 0 ? "var(--neon-green)" : "var(--neon-red)";
                    return `
                        <tr>
                            <td><span class="badge-status ${statusClass}">${statusText}</span></td>
                            <td class="mono" style="font-weight: 800; color: var(--gold-bright);">${b.hwid || 'N/A'}</td>
                            <td style="font-weight: 700; color: #FFFFFF;">${b.customer_name || 'ลูกค้าทั่วไป'}</td>
                            <td>${b.account_login || 'MT5 Ready'}</td>
                            <td class="mono">$${parseFloat(b.balance || 0).toFixed(2)}</td>
                            <td class="mono" style="font-weight: 800; color: ${pnlColor};">${pnlVal >= 0 ? '+' : ''}$${pnlVal.toFixed(2)}</td>
                            <td style="font-size: 11px; color: var(--text-muted);">${b.last_seen_sec} วินาทีที่แล้ว</td>
                            <td>
                                <button type="button" class="btn-action btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="kickDevice('${b.hwid}')">⛔ เตะออก (Kick)</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            // Keys Table
            const tbodyKeys = document.getElementById("tbody-keys");
            if (!data.keys || data.keys.length === 0) {
                tbodyKeys.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">🔑 ยังไม่มีรายการคีย์ลิขสิทธิ์</td></tr>';
            } else {
                tbodyKeys.innerHTML = data.keys.map(k => {
                    const st = k.status;
                    let stClass = "active";
                    let stText = "🟢 ACTIVE";
                    if (st === "REVOKED" || st === "BANNED") {
                        stClass = "revoked";
                        stText = "🚫 REVOKED";
                    } else if (st === "EXPIRED") {
                        stClass = "expired";
                        stText = "⏳ EXPIRED";
                    }

                    const isRevoked = (st === "REVOKED" || st === "BANNED");
                    const toggleAction = isRevoked ? "ACTIVATE" : "REVOKE";
                    const toggleLabel = isRevoked ? "🟢 เปิดใช้งาน" : "🚫 ระงับสิทธิ์";
                    const toggleClass = isRevoked ? "" : "btn-danger";

                    return `
                        <tr>
                            <td>
                                <span class="mono" style="font-weight: 800; color: var(--gold-bright); cursor: pointer;" onclick="navigator.clipboard.writeText('${k.key_code}'); alert('📋 คัดลอกคีย์: ${k.key_code}')" title="คลิกเพื่อคัดลอก">${k.key_code}</span>
                            </td>
                            <td style="font-weight: 700; color: #FFFFFF;">${k.customer_name || '-'}</td>
                            <td><span class="badge-status ${stClass}">${stText}</span></td>
                            <td class="mono" style="font-size: 11.5px; color: ${k.hwid_bound ? 'var(--neon-cyan)' : 'var(--text-muted)'};">
                                ${k.hwid_bound || '(ยังไม่ผูกเครื่อง)'}
                                ${k.hwid_bound ? `<button type="button" style="background:none; border:none; color:var(--gold-bright); cursor:pointer; font-size:11px; margin-left:4px;" onclick="keyAction('${k.key_code}', 'RESET_HWID')" title="ปลดล็อคเครื่อง">🔄</button>` : ''}
                            </td>
                            <td style="font-size: 11.5px;">${k.expires_at || '-'}</td>
                            <td style="font-size: 11px; color: var(--text-muted);">${k.notes || '-'}</td>
                            <td>
                                <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                                    <button type="button" class="btn-action" style="padding: 4px 8px; font-size: 11px;" onclick="keyAction('${k.key_code}', 'EXTEND_30D')">+30 วัน</button>
                                    <button type="button" class="btn-action ${toggleClass}" style="padding: 4px 8px; font-size: 11px;" onclick="keyAction('${k.key_code}', '${toggleAction}')">${toggleLabel}</button>
                                    <button type="button" class="btn-action btn-danger" style="padding: 4px 6px; font-size: 11px;" onclick="if(confirm('ลบคีย์นี้ถาวร?')) keyAction('${k.key_code}', 'DELETE')">🗑️</button>
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
