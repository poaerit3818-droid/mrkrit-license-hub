# -*- coding: utf-8 -*-
"""
👑 MR.KRIT AI ULTRA • MASTER CLOUD COMMAND CENTER
=============================================================================
ระบบศูนย์กลางจัดการคีย์ผลิตภัณฑ์ และศูนย์บัญชาการตรวจจับอุปกรณ์สด (Vercel Native)
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

# -----------------------------------------------------------------------------
# CONFIGURATION & DATABASE (Vercel Serverless Compatible Path)
# -----------------------------------------------------------------------------
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "mrkrit8888")
SECRET_TOKEN_KEY = os.getenv("SECRET_TOKEN_KEY", "MR_KRIT_ULTRA_SECURITY_SECRET_2026")

# In Vercel serverless environment, /tmp is writable
DB_FILE = "/tmp/central_hub.db" if os.environ.get("VERCEL") else os.path.join(os.path.dirname(os.path.abspath(__file__)), "central_hub.db")

app = FastAPI(
    title="Mr.krit AI Central Cloud Gateway",
    version="3.0.0",
    description="Central License & Live Telemetry Hub"
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
    status: Optional[str] = "ONLINE"

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
    
    if key_data["status"] in ["BANNED", "REVOKED"]:
        conn.close()
        return {
            "valid": False,
            "status": key_data["status"],
            "message": f"🚫 สิทธิ์การใช้งานถูกระงับ (สถานะ: {key_data['status']})"
        }
    
    if now > expires_at:
        cursor.execute("UPDATE license_keys SET status = 'EXPIRED' WHERE key_code = ?", (req.key.strip(),))
        conn.commit()
        conn.close()
        return {
            "valid": False,
            "status": "EXPIRED",
            "message": f"⏳ สิทธิ์การใช้งานหมดอายุแล้วเมื่อ {key_data['expires_at']}"
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
    if not k or k["status"] in ["BANNED", "REVOKED"]:
        conn.close()
        return {"status": "error", "command": "STOP", "message": "License invalid or revoked"}
    
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
        req.hwid.strip(), req.key.strip(), req.account_login, req.broker_server,
        req.balance, req.equity, req.profit_today, req.open_orders,
        req.bot_version, now_ts, client_ip, status_to_set
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
    return {"success": False, "message": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}

@app.get("/api/admin/overview")
def admin_overview(token: str):
    check_admin_token(token)
    conn = get_db()
    cursor = conn.cursor()
    
    now_ts = time.time()
    online_threshold = now_ts - 25  # ขาดการส่งสัญญาณเกิน 25 วินาที -> OFFLINE ทันที
    
    cursor.execute("UPDATE bot_telemetry SET status = 'OFFLINE' WHERE last_seen < ?", (online_threshold,))
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) as total FROM license_keys")
    total_keys = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as active FROM license_keys WHERE status = 'ACTIVE'")
    active_keys = cursor.fetchone()["active"]
    
    cursor.execute("SELECT COUNT(*) as online FROM bot_telemetry WHERE status = 'ONLINE'")
    online_bots = cursor.fetchone()["online"]
    
    cursor.execute("SELECT COUNT(*) as offline FROM bot_telemetry WHERE status = 'OFFLINE'")
    offline_bots = cursor.fetchone()["offline"]
    
    cursor.execute("SELECT * FROM bot_telemetry ORDER BY last_seen DESC LIMIT 50")
    bots = [dict(r) for r in cursor.fetchall()]
    for b in bots:
        is_on = (now_ts - b["last_seen"]) <= 25 and b["status"] == "ONLINE"
        b["is_online"] = is_on
        b["last_seen_sec"] = int(now_ts - b["last_seen"])
    
    cursor.execute("SELECT * FROM license_keys ORDER BY created_at DESC")
    keys = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "stats": {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "online_bots": online_bots,
            "offline_bots": offline_bots
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
# ULTRA-LUXURY OBSIDIAN GOLD COMMAND CENTER DASHBOARD (MODULAR ZONES)
# -----------------------------------------------------------------------------
ADMIN_HTML = """<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>👑 MR.KRIT AI ULTRA • ศูนย์บัญชาการคลาวด์สูงสุด</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=Prompt:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --gold-primary: #FFD700;
            --gold-light: #FFF099;
            --gold-dark: #C59B27;
            --gold-gradient: linear-gradient(135deg, #FFF099 0%, #FFD700 45%, #C59B27 100%);
            --gold-glow: rgba(255, 215, 0, 0.4);
            --gold-border: rgba(255, 215, 0, 0.22);
            --gold-subtle: rgba(255, 215, 0, 0.08);
            
            --bg-deep: #040406;
            --bg-card: rgba(11, 11, 16, 0.90);
            --bg-card-hover: rgba(18, 18, 26, 0.95);
            --bg-input: #08080C;
            
            --text-main: #FFFFFF;
            --text-muted: #8E8E9F;
            --text-gold: #FFDF59;
            
            --neon-green: #00E676;
            --neon-red: #FF3B5C;
            --neon-cyan: #00F0FF;
            
            --radius-lg: 20px;
            --radius-md: 12px;
            --radius-sm: 8px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', 'Prompt', sans-serif;
        }

        body {
            background-color: var(--bg-deep);
            color: var(--text-main);
            min-height: 100vh;
            overflow-x: hidden;
            background-image: 
                radial-gradient(ellipse 60% 40% at 50% 0%, rgba(255, 215, 0, 0.08) 0%, transparent 70%),
                radial-gradient(ellipse 50% 30% at 90% 100%, rgba(197, 155, 39, 0.05) 0%, transparent 60%);
            background-attachment: fixed;
        }

        /* ─── NAVBAR ────────────────────────────────────────── */
        .navbar {
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 36px;
            background: rgba(4, 4, 6, 0.92);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--gold-border);
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.8);
        }
        .nav-brand {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .crown-badge {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: var(--gold-gradient);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            box-shadow: 0 0 24px var(--gold-glow);
        }
        .brand-title {
            font-size: 18px;
            font-weight: 900;
            letter-spacing: 1px;
            background: var(--gold-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .brand-sub {
            font-size: 11px;
            color: var(--text-muted);
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        .nav-actions {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .live-status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            font-weight: 700;
            color: var(--neon-green);
            background: rgba(0, 230, 118, 0.1);
            border: 1px solid rgba(0, 230, 118, 0.3);
            padding: 6px 14px;
            border-radius: 30px;
        }
        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--neon-green);
            box-shadow: 0 0 10px var(--neon-green);
            animation: pulse-glow 1.8s infinite;
        }
        @keyframes pulse-glow {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.3); opacity: 0.6; }
        }

        /* ─── MAIN CONTAINER ─────────────────────────────────── */
        .container {
            max-width: 1440px;
            margin: 0 auto;
            padding: 32px 28px;
        }

        /* ─── STATS GRID ─────────────────────────────────────── */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 36px;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--gold-border);
            border-radius: var(--radius-lg);
            padding: 24px 26px;
            position: relative;
            overflow: hidden;
            backdrop-filter: blur(16px);
            transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
        }
        .stat-card:hover {
            transform: translateY(-4px);
            border-color: rgba(255, 215, 0, 0.55);
            box-shadow: 0 12px 36px rgba(255, 215, 0, 0.12);
        }
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--gold-gradient);
        }
        .stat-icon {
            font-size: 28px;
            margin-bottom: 10px;
            display: inline-block;
        }
        .stat-label {
            font-size: 11.5px;
            font-weight: 800;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1.5px;
        }
        .stat-value {
            font-size: 38px;
            font-weight: 900;
            color: #FFFFFF;
            margin: 6px 0 2px;
            letter-spacing: -0.5px;
        }
        .stat-value.green {
            color: var(--neon-green);
            text-shadow: 0 0 20px rgba(0, 230, 118, 0.4);
        }
        .stat-value.gold {
            background: var(--gold-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 24px rgba(255, 215, 0, 0.3);
        }
        .stat-value.red {
            color: var(--neon-red);
            text-shadow: 0 0 20px rgba(255, 59, 92, 0.3);
        }
        .stat-desc {
            font-size: 12px;
            color: var(--text-muted);
        }

        /* ─── MODULAR ZONE PANELS ────────────────────────────── */
        .zone-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(255, 215, 0, 0.12);
            color: var(--gold-primary);
            border: 1px solid rgba(255, 215, 0, 0.3);
            border-radius: 6px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .panel {
            background: var(--bg-card);
            border: 1px solid var(--gold-border);
            border-radius: var(--radius-lg);
            backdrop-filter: blur(16px);
            margin-bottom: 36px;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
        }
        .panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 24px 30px;
            border-bottom: 1px solid var(--gold-border);
            background: rgba(255, 215, 0, 0.025);
        }
        .panel-title-wrap {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .panel-icon-box {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: rgba(255, 215, 0, 0.12);
            border: 1px solid rgba(255, 215, 0, 0.28);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
        }
        .panel-title {
            font-size: 17px;
            font-weight: 800;
            color: #FFFFFF;
            letter-spacing: 0.5px;
        }
        .panel-subtitle {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 3px;
        }

        /* ─── BUTTONS ────────────────────────────────────────── */
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            border-radius: var(--radius-md);
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            border: none;
            transition: all 0.25s ease;
            text-decoration: none;
            white-space: nowrap;
        }
        .btn-gold {
            background: var(--gold-gradient);
            color: #040406;
            box-shadow: 0 4px 18px rgba(255, 215, 0, 0.35);
        }
        .btn-gold:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 28px rgba(255, 215, 0, 0.55);
            filter: brightness(1.08);
        }
        .btn-outline {
            background: rgba(255, 255, 255, 0.04);
            color: var(--text-gold);
            border: 1px solid rgba(255, 215, 0, 0.35);
        }
        .btn-outline:hover {
            background: rgba(255, 215, 0, 0.12);
            border-color: var(--gold-primary);
            color: #FFFFFF;
        }
        .btn-danger {
            background: rgba(255, 59, 92, 0.12);
            color: var(--neon-red);
            border: 1px solid rgba(255, 59, 92, 0.35);
        }
        .btn-danger:hover {
            background: var(--neon-red);
            color: #FFFFFF;
            box-shadow: 0 0 16px rgba(255, 59, 92, 0.5);
        }
        .btn-success {
            background: rgba(0, 230, 118, 0.12);
            color: var(--neon-green);
            border: 1px solid rgba(0, 230, 118, 0.35);
        }
        .btn-success:hover {
            background: var(--neon-green);
            color: #000;
        }
        .btn-sm {
            padding: 6px 12px;
            font-size: 12px;
            border-radius: var(--radius-sm);
        }

        /* ─── TABLES ─────────────────────────────────────────── */
        .table-responsive {
            overflow-x: auto;
            width: 100%;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }
        thead th {
            padding: 16px 22px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: var(--text-muted);
            border-bottom: 1px solid var(--gold-border);
            background: rgba(0, 0, 0, 0.3);
            white-space: nowrap;
        }
        tbody td {
            padding: 18px 22px;
            font-size: 14px;
            border-bottom: 1px solid rgba(255, 215, 0, 0.06);
            color: #E2E2E8;
        }
        tbody tr:last-child td {
            border-bottom: none;
        }
        tbody tr {
            transition: background 0.15s ease;
        }
        tbody tr:hover td {
            background: rgba(255, 215, 0, 0.035);
        }

        /* ─── BADGES ─────────────────────────────────────────── */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 800;
        }
        .badge-online {
            background: rgba(0, 230, 118, 0.15);
            color: var(--neon-green);
            border: 1px solid rgba(0, 230, 118, 0.4);
            box-shadow: 0 0 12px rgba(0, 230, 118, 0.15);
        }
        .badge-offline {
            background: rgba(255, 59, 92, 0.12);
            color: var(--neon-red);
            border: 1px solid rgba(255, 59, 92, 0.35);
        }
        .badge-active {
            background: rgba(255, 215, 0, 0.15);
            color: var(--gold-primary);
            border: 1px solid rgba(255, 215, 0, 0.35);
        }
        .badge-banned {
            background: rgba(255, 59, 92, 0.2);
            color: var(--neon-red);
            border: 1px solid var(--neon-red);
        }
        .badge-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
        }

        /* ─── LOGIN SCREEN ───────────────────────────────────── */
        #login-view {
            min-height: 85vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .login-card {
            background: var(--bg-card);
            border: 1px solid var(--gold-border);
            border-radius: 26px;
            padding: 46px 40px;
            width: 100%;
            max-width: 440px;
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(20px);
            position: relative;
        }
        .login-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 20%;
            right: 20%;
            height: 3px;
            background: var(--gold-gradient);
            box-shadow: 0 0 24px var(--gold-primary);
        }
        .login-header {
            text-align: center;
            margin-bottom: 30px;
        }
        .login-crown {
            width: 68px;
            height: 68px;
            border-radius: 20px;
            background: var(--gold-gradient);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 34px;
            margin: 0 auto 16px;
            box-shadow: 0 0 35px var(--gold-glow);
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-label {
            display: block;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1px;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .form-control {
            width: 100%;
            padding: 14px 18px;
            background: var(--bg-input);
            border: 1px solid rgba(255, 215, 0, 0.18);
            border-radius: var(--radius-md);
            color: #FFFFFF;
            font-size: 14px;
            outline: none;
            transition: all 0.2s ease;
        }
        .form-control:focus {
            border-color: var(--gold-primary);
            box-shadow: 0 0 0 3px rgba(255, 215, 0, 0.15);
        }

        /* ─── MODAL ──────────────────────────────────────────── */
        .modal-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.88);
            backdrop-filter: blur(14px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .modal-box {
            background: #09090E;
            border: 1px solid var(--gold-border);
            border-radius: 24px;
            padding: 36px;
            width: 100%;
            max-width: 520px;
            box-shadow: 0 30px 80px rgba(0, 0, 0, 0.95);
            position: relative;
        }
        .modal-title {
            font-size: 20px;
            font-weight: 800;
            color: var(--gold-primary);
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .modal-close {
            position: absolute;
            top: 20px;
            right: 22px;
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 24px;
            cursor: pointer;
            transition: color 0.2s;
        }
        .modal-close:hover {
            color: var(--neon-red);
        }

        /* Responsive */
        @media (max-width: 1024px) {
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 640px) {
            .stats-grid { grid-template-columns: 1fr; }
            .navbar { padding: 14px 18px; }
            .container { padding: 20px 14px; }
        }
    </style>
</head>
<body>

    <!-- ═══════════════════════════════════════════ NAVBAR ═══ -->
    <nav class="navbar">
        <div class="nav-brand">
            <div class="crown-badge">👑</div>
            <div>
                <div class="brand-title">MR.KRIT AI ULTRA • MASTER CLOUD HUB</div>
                <div class="brand-sub">ศูนย์ควบคุมลิขสิทธิ์และตรวจจับบอทสด</div>
            </div>
        </div>
        <div class="nav-actions">
            <div class="live-status" id="live-indicator" style="display: none;">
                <div class="pulse-dot"></div>
                <span>EDGE GATEWAY: ONLINE</span>
            </div>
            <div id="nav-user-actions" style="display: none;">
                <button class="btn btn-outline btn-sm" onclick="fetchDashboard()">🔄 รีเฟรชข้อมูล</button>
                <button class="btn btn-danger btn-sm" onclick="logout()" style="margin-left: 8px;">🚪 ออกจากระบบ</button>
            </div>
        </div>
    </nav>

    <!-- ═══════════════════════════════════════════ LOGIN VIEW ═══ -->
    <div id="login-view">
        <div class="login-card">
            <div class="login-header">
                <div class="login-crown">👑</div>
                <h2 style="font-size: 22px; font-weight: 900; color: #FFF; margin-bottom: 6px;">Master Command Access</h2>
                <p style="color: var(--text-muted); font-size: 13px;">เข้าสู่ระบบศูนย์กลางบัญชาการระดับสูงสุด</p>
            </div>
            <div class="form-group">
                <label class="form-label">ชื่อผู้ใช้ (Username)</label>
                <input type="text" id="login-user" class="form-control" placeholder="admin" value="admin">
            </div>
            <div class="form-group">
                <label class="form-label">รหัสผ่าน (Password)</label>
                <input type="password" id="login-pass" class="form-control" placeholder="••••••••" onkeydown="if(event.key==='Enter')handleLogin()">
            </div>
            <button class="btn btn-gold" style="width: 100%; justify-content: center; padding: 14px; font-size: 15px; margin-top: 8px;" onclick="handleLogin()" id="btn-login-submit">
                🔐 เข้าสู่ศูนย์บัญชาการ (ACCESS SYSTEM)
            </button>
            <div id="login-error-msg" style="color: var(--neon-red); font-size: 13px; text-align: center; margin-top: 14px; display: none;"></div>
        </div>
    </div>

    <!-- ═══════════════════════════════════════════ DASHBOARD VIEW ═══ -->
    <div id="dash-view" class="container" style="display: none;">
        
        <!-- Stats Grid (Online / Active Keys / Offline / Cloud Security) -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">🟢</div>
                <div class="stat-label">บอทออนไลน์สด (Live Online)</div>
                <div class="stat-value green" id="stat-online">0</div>
                <div class="stat-desc">เครื่องที่กำลังเปิดโปรแกรมและส่งสัญญาณอยู่</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🔑</div>
                <div class="stat-label">คีย์เปิดใช้งาน (Active Keys)</div>
                <div class="stat-value gold" id="stat-keys">0 / 0</div>
                <div class="stat-desc">จำนวนคีย์ที่ได้รับอนุญาตในระบบ</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🔴</div>
                <div class="stat-label">เครื่องออฟไลน์ (Offline Devices)</div>
                <div class="stat-value red" id="stat-offline">0</div>
                <div class="stat-desc">เครื่องที่ปิดโปรแกรมหรือขาดการเชื่อมต่อ</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🛡️</div>
                <div class="stat-label">ระบบคลาวด์เกตเวย์ (Security Shield)</div>
                <div class="stat-value gold" style="font-size: 26px; padding-top: 6px;">ENCRYPTED</div>
                <div class="stat-desc">Vercel Global Edge · Active 24/7</div>
            </div>
        </div>

        <!-- ═══════════════════════════════════════════ ZONE 1: LIVE BOT TELEMETRY RADAR ═══ -->
        <div class="panel">
            <div class="panel-header">
                <div class="panel-title-wrap">
                    <div class="panel-icon-box">🛰️</div>
                    <div>
                        <div class="zone-badge">ZONE 1 • LIVE TELEMETRY</div>
                        <div class="panel-title">เรดาร์ตรวจจับอุปกรณ์สดและสถานะการเชื่อมต่อ (Live Devices Radar)</div>
                        <div class="panel-subtitle">แสดงเครื่องที่เปิด-ปิดโปรแกรมหน้าบ้านแบบ Real-Time ทันที</div>
                    </div>
                </div>
                <button class="btn btn-outline btn-sm" onclick="fetchDashboard()">🔄 รีเฟรชสด</button>
            </div>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>สถานะการเชื่อมต่อ</th>
                            <th>รหัสเครื่อง (HWID)</th>
                            <th>บัญชี MT5 / โหมด</th>
                            <th>โหนดเซิร์ฟเวอร์</th>
                            <th>ออเดอร์ค้าง</th>
                            <th>สัญญาณล่าสุด (Last Seen)</th>
                            <th>จัดการการเชื่อมต่อ</th>
                        </tr>
                    </thead>
                    <tbody id="bot-table-body">
                        <tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 32px;">🛰️ ยังไม่มีอุปกรณ์ส่งสัญญาณเข้ามาในขณะนี้</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ═══════════════════════════════════════════ ZONE 2: KEY GENERATOR & LICENSE SUITE ═══ -->
        <div class="panel">
            <div class="panel-header">
                <div class="panel-title-wrap">
                    <div class="panel-icon-box">🔑</div>
                    <div>
                        <div class="zone-badge">ZONE 2 • LICENSE GENERATOR</div>
                        <div class="panel-title">ระบบสร้างและจัดการคีย์ผลิตภัณฑ์ (License Keys Master Suite)</div>
                        <div class="panel-subtitle">ออกคีย์สิทธิ์การใช้งานใหม่ และควบคุมวันหมดอายุของลูกค้า</div>
                    </div>
                </div>
                <button class="btn btn-gold" onclick="openKeyModal()">➕ สร้างคีย์ใหม่ (Generate Key)</button>
            </div>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>รหัสคีย์ผลิตภัณฑ์ (Product License Key)</th>
                            <th>ชื่อลูกค้า / ผู้ใช้งาน</th>
                            <th>สถานะสิทธิ์</th>
                            <th>เครื่องที่ผูก (Bound HWID)</th>
                            <th>วันหมดอายุ</th>
                            <th>คำสั่งควบคุมสิทธิ์</th>
                        </tr>
                    </thead>
                    <tbody id="key-table-body">
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ═══════════════════════════════════════════ ZONE 3: REMOTE CONTROL & SECURITY SUITE ═══ -->
        <div class="panel">
            <div class="panel-header">
                <div class="panel-title-wrap">
                    <div class="panel-icon-box">🛑</div>
                    <div>
                        <div class="zone-badge">ZONE 3 • REMOTE DEVICE CONTROL</div>
                        <div class="panel-title">ศูนย์ควบคุมและระงับเครื่องระยะไกล (Remote Security & Ban Suite)</div>
                        <div class="panel-subtitle">ปลดล็อคเครื่องเพื่อให้ลูกค้าย้ายเครื่องใหม่ หรือสั่งระงับสิทธิ์ทันที</div>
                    </div>
                </div>
            </div>
            <div style="padding: 24px 30px; display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                <div style="background: var(--bg-input); border: 1px solid var(--gold-border); border-radius: var(--radius-md); padding: 20px;">
                    <div style="font-size: 16px; font-weight: 800; color: var(--gold-primary); margin-bottom: 6px;">🔄 ปลดล็อค HWID (Reset Device Binding)</div>
                    <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 14px;">ใช้เมื่อลูกค้าเปลี่ยนคอมพิวเตอร์หรือลง Windows ใหม่ เพื่อให้ลูกค้านำคีย์เดิมไปเปิดใช้งานบนเครื่องใหม่ได้</p>
                    <span style="font-size: 12px; color: var(--neon-green);">✓ สามารถกดปุ่ม [🔄 ปลดล็อค HWID] ในตาราง Zone 2 ได้ทันที</span>
                </div>
                <div style="background: var(--bg-input); border: 1px solid rgba(255, 59, 92, 0.35); border-radius: var(--radius-md); padding: 20px;">
                    <div style="font-size: 16px; font-weight: 800; color: var(--neon-red); margin-bottom: 6px;">🚫 สั่งระงับสิทธิ์ทันที (Instant Ban / Kill Switch)</div>
                    <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 14px;">เมื่อสั่งระงับสิทธิ์ โปรแกรมหน้าบ้านและบอทของเครื่องเป้าหมายจะถูกสั่งหยุดการทำงานและตัดสิทธิ์การเทรดทันที</p>
                    <span style="font-size: 12px; color: var(--neon-red);">✓ สามารถกดปุ่ม [🚫 ระงับคีย์] ในตาราง Zone 2 ได้ทันที</span>
                </div>
            </div>
        </div>

    </div>

    <!-- ═══════════════════════════════════════════ MODAL: CREATE KEY ═══ -->
    <div id="key-modal" class="modal-overlay">
        <div class="modal-box">
            <button class="modal-close" onclick="closeKeyModal()">✕</button>
            <div class="modal-title">✨ สร้างรหัสสิทธิ์การใช้งานใหม่ (New License)</div>
            <div class="form-group">
                <label class="form-label">ชื่อลูกค้า (Customer Name)</label>
                <input type="text" id="new-cust-name" class="form-control" placeholder="เช่น คุณสมชาย (VIP Client)">
            </div>
            <div class="form-group">
                <label class="form-label">ระยะเวลาสิทธิ์ (Duration)</label>
                <select id="new-duration" class="form-control">
                    <option value="7">7 วัน (ทดลองใช้งาน Trial)</option>
                    <option value="30" selected>30 วัน (1 เดือน)</option>
                    <option value="90">90 วัน (3 เดือน)</option>
                    <option value="180">180 วัน (6 เดือน)</option>
                    <option value="365">365 วัน (1 ปี)</option>
                    <option value="29000">ตลอดชีพ (Lifetime VIP Unlimited)</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">บันทึกช่วยจำ (Notes)</label>
                <input type="text" id="new-notes" class="form-control" placeholder="เช่น ชำระแล้วทางไลน์, แพ็กเกจ Gold">
            </div>
            <div style="display: flex; gap: 12px; justify-content: flex-end; margin-top: 28px;">
                <button class="btn btn-outline" onclick="closeKeyModal()">ยกเลิก</button>
                <button class="btn btn-gold" onclick="submitCreateKey()">✦ ยืนยันสร้างคีย์</button>
            </div>
        </div>
    </div>

    <!-- ═══════════════════════════════════════════ MODAL: RESULT ═══ -->
    <div id="result-modal" class="modal-overlay">
        <div class="modal-box" style="text-align: center; max-width: 460px;">
            <button class="modal-close" onclick="closeResultModal()">✕</button>
            <div style="font-size: 48px; margin-bottom: 12px;">🎉</div>
            <h3 style="font-size: 20px; font-weight: 800; color: var(--gold-primary); margin-bottom: 8px;">สร้างคีย์สำเร็จเรียบร้อย!</h3>
            <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 20px;">คัดลอกรหัสคีย์นี้ส่งให้ลูกค้าได้ทันที</p>
            <div style="background: var(--bg-input); border: 1px solid rgba(255, 215, 0, 0.35); border-radius: var(--radius-md); padding: 18px 20px; margin-bottom: 22px;">
                <div id="result-key-code" style="font-size: 16px; font-weight: 900; color: var(--gold-primary); letter-spacing: 1px; word-break: break-all;"></div>
                <div id="result-key-exp" style="font-size: 12px; color: var(--text-muted); margin-top: 8px;"></div>
            </div>
            <button class="btn btn-gold" style="width: 100%; justify-content: center;" onclick="copyResultKey()" id="btn-copy-key">
                📋 คัดลอกรหัสคีย์ (Copy Key)
            </button>
        </div>
    </div>

    <script>
        let adminToken = localStorage.getItem('mrkrit_admin_token') || '';
        let currentGeneratedKey = '';

        function checkAuth() {
            if (adminToken) {
                document.getElementById('login-view').style.display = 'none';
                document.getElementById('dash-view').style.display = 'block';
                document.getElementById('live-indicator').style.display = 'flex';
                document.getElementById('nav-user-actions').style.display = 'flex';
                fetchDashboard();
                if (!window.refreshInterval) {
                    window.refreshInterval = setInterval(fetchDashboard, 6000); // รีเฟรชสดทุก 6 วินาที
                }
            } else {
                document.getElementById('login-view').style.display = 'flex';
                document.getElementById('dash-view').style.display = 'none';
                document.getElementById('live-indicator').style.display = 'none';
                document.getElementById('nav-user-actions').style.display = 'none';
            }
        }

        async function handleLogin() {
            const btn = document.getElementById('btn-login-submit');
            const errBox = document.getElementById('login-error-msg');
            const u = document.getElementById('login-user').value.trim();
            const p = document.getElementById('login-pass').value.trim();
            
            btn.disabled = true;
            btn.innerText = 'กำลังเข้าสู่ระบบ...';
            errBox.style.display = 'none';

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
                    errBox.innerText = '❌ ' + (data.message || 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง');
                    errBox.style.display = 'block';
                }
            } catch (e) {
                errBox.innerText = '⚠️ ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้';
                errBox.style.display = 'block';
            } finally {
                btn.disabled = false;
                btn.innerText = '🔐 เข้าสู่ศูนย์บัญชาการ (ACCESS SYSTEM)';
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

                // 1. Stats Counter (Online / Active Keys / Offline)
                document.getElementById('stat-online').innerText = data.stats.online_bots;
                document.getElementById('stat-keys').innerText = `${data.stats.active_keys} / ${data.stats.total_keys}`;
                document.getElementById('stat-offline').innerText = data.stats.offline_bots;

                // 2. Zone 1: Bots Radar Table
                const botTbody = document.getElementById('bot-table-body');
                if (data.bots.length === 0) {
                    botTbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 32px;">🛰️ ยังไม่มีอุปกรณ์ส่งสัญญาณเข้ามาในขณะนี้</td></tr>`;
                } else {
                    botTbody.innerHTML = data.bots.map(b => `
                        <tr>
                            <td>
                                <span class="badge ${b.is_online ? 'badge-online' : 'badge-offline'}">
                                    <span class="badge-dot"></span>${b.is_online ? '🟢 ออนไลน์ (ONLINE)' : '🔴 ออฟไลน์ (OFFLINE)'}
                                </span>
                            </td>
                            <td><code style="background: rgba(255, 215, 0, 0.08); border: 1px solid rgba(255, 215, 0, 0.2); padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: 800; color: var(--gold-primary);">${b.hwid}</code></td>
                            <td><strong style="color: #FFF;">#${b.account_login || 'N/A'}</strong></td>
                            <td style="color: var(--text-muted); font-size: 13px;">${b.broker_server || 'Web Cockpit Engine'}</td>
                            <td><span class="badge badge-active">${b.open_orders} ไม้</span></td>
                            <td style="color: ${b.is_online ? 'var(--neon-green)' : 'var(--text-muted)'}; font-size: 13px; font-weight: 600;">
                                ${b.is_online ? `⚡ ติดต่ออยู่ (${b.last_seen_sec}s ที่แล้ว)` : `⏳ ขาดการติดต่อ (${b.last_seen_sec}s ที่แล้ว)`}
                            </td>
                            <td>
                                <button class="btn btn-danger btn-sm" onclick="keyAction('${b.key_code}', 'BAN')">🛑 สั่งตัดการเชื่อมต่อ</button>
                            </td>
                        </tr>
                    `).join('');
                }

                // 3. Zone 2: License Keys Table
                const keyTbody = document.getElementById('key-table-body');
                keyTbody.innerHTML = data.keys.map(k => `
                    <tr>
                        <td><strong style="color: var(--gold-primary); letter-spacing: 0.8px; font-size: 14px;">${k.key_code}</strong></td>
                        <td>
                            <div style="font-weight: 700; color: #FFF;">${k.customer_name}</div>
                            ${k.notes ? `<div style="color: var(--text-muted); font-size: 12px;">${k.notes}</div>` : ''}
                        </td>
                        <td>
                            <span class="badge ${k.status === 'ACTIVE' ? 'badge-active' : (k.status === 'BANNED' ? 'badge-banned' : 'badge-offline')}">
                                <span class="badge-dot"></span>${k.status}
                            </span>
                        </td>
                        <td style="font-size: 13px;">
                            ${k.hwid_bound ? `<code style="color: var(--neon-green); background: rgba(0, 230, 118, 0.08); padding: 3px 8px; border-radius: 6px;">${k.hwid_bound}</code>` : '<span style="color: var(--text-muted);">(ยังไม่ผูกเครื่อง)</span>'}
                        </td>
                        <td style="font-size: 13px; color: var(--text-muted);">${k.expires_at}</td>
                        <td>
                            <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                                ${k.hwid_bound ? `<button class="btn btn-outline btn-sm" onclick="keyAction('${k.key_code}', 'RESET_HWID')">🔄 ปลดล็อค HWID</button>` : ''}
                                <button class="btn btn-outline btn-sm" onclick="keyAction('${k.key_code}', 'EXTEND_30D')">+30 วัน</button>
                                ${k.status === 'ACTIVE' ? `<button class="btn btn-danger btn-sm" onclick="keyAction('${k.key_code}', 'BAN')">🚫 ระงับคีย์</button>` : `<button class="btn btn-success btn-sm" onclick="keyAction('${k.key_code}', 'ACTIVATE')">✅ เปิดใช้งาน</button>`}
                                <button class="btn btn-danger btn-sm" style="padding: 6px 8px;" onclick="keyAction('${k.key_code}', 'DELETE')" title="ลบคีย์นี้">🗑️</button>
                            </div>
                        </td>
                    </tr>
                `).join('');

            } catch (e) {
                console.error("Dashboard sync error:", e);
            }
        }

        async function keyAction(keyCode, action) {
            if (action === 'BAN' && !confirm('⚠️ คุณแน่ใจหรือไม่ว่าต้องการระงับสิทธิ์คีย์นี้? บอทจะหยุดทำงานทันที!')) return;
            if (action === 'DELETE' && !confirm('⚠️ คุณแน่ใจหรือไม่ว่าต้องการลบคีย์นี้ออกจากระบบ?')) return;
            const fd = new FormData();
            fd.append('key_code', keyCode);
            fd.append('action', action);
            fd.append('token', adminToken);
            await fetch('/api/admin/keys/action', { method: 'POST', body: fd });
            fetchDashboard();
        }

        function openKeyModal() { document.getElementById('key-modal').style.display = 'flex'; }
        function closeKeyModal() { document.getElementById('key-modal').style.display = 'none'; }
        function closeResultModal() { document.getElementById('result-modal').style.display = 'none'; }

        async function submitCreateKey() {
            const name = document.getElementById('new-cust-name').value.trim();
            const duration = parseInt(document.getElementById('new-duration').value);
            const notes = document.getElementById('new-notes').value.trim();
            if (!name) { alert('กรุณากรอกชื่อลูกค้า'); return; }

            const res = await fetch(`/api/admin/keys/create?token=${adminToken}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ customer_name: name, duration_days: duration, notes: notes })
            });
            const data = await res.json();
            if (data.success) {
                currentGeneratedKey = data.key_code;
                closeKeyModal();
                document.getElementById('result-key-code').innerText = data.key_code;
                document.getElementById('result-key-exp').innerText = 'วันหมดอายุ: ' + data.expires_at;
                document.getElementById('result-modal').style.display = 'flex';
                fetchDashboard();
            }
        }

        function copyResultKey() {
            navigator.clipboard.writeText(currentGeneratedKey).then(() => {
                const btn = document.getElementById('btn-copy-key');
                btn.innerText = '✅ คัดลอกสำเร็จแล้ว!';
                setTimeout(() => { btn.innerText = '📋 คัดลอกรหัสคีย์ (Copy Key)'; }, 2000);
            });
        }

        // Initialize view
        checkAuth();
    </script>
</body>
</html>
"""

@app.get("/admin", response_class=HTMLResponse)
@app.get("/api/index/admin", response_class=HTMLResponse)
def get_admin_portal():
    return HTMLResponse(content=ADMIN_HTML)
