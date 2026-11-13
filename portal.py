#!/usr/bin/env python3
"""
Pi Dashboard Web Portal — http://<pi-ip>:5000
"""
import json, os, subprocess
from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.utils import secure_filename

BASE_DIR       = os.environ.get("DASHBOARD_DIR", os.path.expanduser("~/dashboard"))
SETTINGS_FILE  = f"{BASE_DIR}/settings.json"
REMINDERS_FILE = f"{BASE_DIR}/reminders.json"
ROUTINE_FILE   = f"{BASE_DIR}/routine.json"
FONTS_DIR      = f"{BASE_DIR}/fonts"
BG_FILE        = f"{BASE_DIR}/background.jpg"
IMG_EXT        = {"jpg","jpeg","png","webp"}
AUDIO_EXT      = {"wav","mp3","ogg"}
FONT_EXT       = {"ttf","otf","woff","woff2"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

DEFAULT_ORDER = ["time","routine","date_en","date_bn","countdown","event","status"]
DEFAULT_ELEMENTS = {
    "time":      {"size":82,"bold":True, "color":"#ffffff","alpha":255,"font":"","align":"center"},
    "routine":   {"size":22,"bold":False,"color":"#ffffff","alpha":200,"font":"","align":"center"},
    "date_en":   {"size":26,"bold":False,"color":"#ffffff","alpha":220,"font":"","align":"center"},
    "date_bn":   {"size":26,"bold":True, "color":"#ffffff","alpha":170,"font":"","align":"center"},
    "countdown": {"size":24,"bold":False,"color":"#ffffff","alpha":210,"font":"","align":"center"},
    "event":     {"size":19,"bold":False,"color":"#ffffff","alpha":190,"font":"","align":"center"},
    "status":    {"size":18,"bold":False,"color":"#ffffff","alpha":155,"font":"","align":"center"},
}

def load_json(path, default):
    try:
        with open(path) as f: return json.load(f)
    except: return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w") as f: json.dump(data,f,indent=2,ensure_ascii=False)

def find_audio(prefix):
    for ext in AUDIO_EXT:
        p = f"{BASE_DIR}/{prefix}.{ext}"
        if os.path.isfile(p): return p, ext
    return None, None

PORTAL_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Pi Dashboard Portal</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Playfair+Display:wght@600&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0b0f1a;--surf:#141927;--surf2:#192030;--border:#1e2a40;
  --accent:#4f9cf9;--text:#e8eaf0;--muted:#6b7a9b;
  --ok:#3ecf8e;--warn:#f9c74f;--err:#f97058;--r:10px;
  --mono:'DM Mono',monospace;--serif:'Playfair Display',serif;
}
html,body{min-height:100%;background:var(--bg);color:var(--text);font-family:var(--mono);font-size:14px;}
.shell{display:grid;grid-template-columns:220px 1fr;min-height:100vh;}
nav{background:var(--surf);border-right:1px solid var(--border);padding:28px 0 16px;
  display:flex;flex-direction:column;gap:2px;position:sticky;top:0;height:100vh;overflow-y:auto;}
.logo{font-family:var(--serif);font-size:1.18rem;color:var(--accent);padding:0 22px 22px;
  border-bottom:1px solid var(--border);margin-bottom:12px;line-height:1.3;}
.logo small{display:block;font-family:var(--mono);font-size:.63rem;color:var(--muted);margin-top:3px;}
nav a{display:flex;align-items:center;gap:10px;padding:9px 22px;color:var(--muted);
  text-decoration:none;border-radius:6px;margin:0 8px;font-size:.79rem;transition:.15s;}
nav a:hover,nav a.on{background:rgba(79,156,249,.1);color:var(--accent);}
.ic{font-size:.95rem;width:18px;text-align:center;}
.nav-sep{margin:8px 22px;border:none;border-top:1px solid var(--border);}
main{padding:38px 46px;max-width:920px;}
.sec{display:none;animation:fadeUp .2s ease both;}.sec.on{display:block;}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
h2{font-family:var(--serif);font-size:1.5rem;margin-bottom:4px;}
.sub{color:var(--muted);font-size:.74rem;margin-bottom:26px;}
.card{background:var(--surf);border:1px solid var(--border);border-radius:var(--r);padding:22px 26px;margin-bottom:18px;}
.card h3{font-size:.75rem;color:var(--accent);text-transform:uppercase;letter-spacing:.6px;margin-bottom:16px;}
.field{margin-bottom:14px;}
label{display:block;font-size:.72rem;color:var(--muted);margin-bottom:5px;}
input[type=text],input[type=date],input[type=time],select{
  width:100%;background:var(--bg);border:1px solid var(--border);border-radius:7px;
  padding:9px 12px;color:var(--text);font-family:var(--mono);font-size:.82rem;outline:none;transition:.15s;}
input:focus,select:focus{border-color:var(--accent);}
input[type=range]{width:100%;accent-color:var(--accent);}
input[type=color]{height:38px;padding:3px 7px;cursor:pointer;width:60px;}
.tog-row{display:flex;align-items:center;justify-content:space-between;padding:4px 0;}
.tog{position:relative;width:42px;height:23px;flex-shrink:0;}
.tog input{opacity:0;width:0;height:0;}
.sl{position:absolute;inset:0;background:var(--border);border-radius:23px;cursor:pointer;transition:.22s;}
.sl::before{content:'';position:absolute;width:17px;height:17px;left:3px;bottom:3px;
  background:var(--muted);border-radius:50%;transition:.22s;}
input:checked+.sl{background:var(--accent);}
input:checked+.sl::before{transform:translateX(19px);background:#fff;}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;}
.btn{display:inline-flex;align-items:center;gap:7px;padding:9px 18px;border-radius:7px;
  font-family:var(--mono);font-size:.78rem;cursor:pointer;border:none;transition:.15s;}
.btn-p{background:var(--accent);color:#0b0f1a;font-weight:500;}.btn-p:hover{background:#74b4ff;}
.btn-g{background:var(--surf2);color:var(--text);border:1px solid var(--border);}.btn-g:hover{border-color:var(--accent);color:var(--accent);}
.btn-d{background:transparent;color:var(--err);border:1px solid var(--err);}.btn-d:hover{background:rgba(249,112,88,.1);}
.btn-w{background:transparent;color:var(--warn);border:1px solid var(--warn);}.btn-w:hover{background:rgba(249,199,79,.1);}
.btn-sm{padding:5px 11px;font-size:.71rem;}
.ri{display:flex;align-items:center;justify-content:space-between;padding:11px 14px;
  background:var(--bg);border:1px solid var(--border);border-radius:7px;margin-bottom:7px;}
.ri .inf{display:flex;flex-direction:column;gap:2px;}
.ri .tit{color:var(--text);font-size:.84rem;}.ri .met{color:var(--muted);font-size:.71rem;}
.empty{color:var(--muted);font-size:.77rem;padding:18px 0;text-align:center;}
.upz{border:2px dashed var(--border);border-radius:9px;padding:26px 20px;text-align:center;
  cursor:pointer;color:var(--muted);font-size:.78rem;transition:.18s;user-select:none;}
.upz:hover,.upz.drag{border-color:var(--accent);color:var(--accent);background:rgba(79,156,249,.04);}
.upz .upz-icon{font-size:1.6rem;margin-bottom:6px;}
.upz .upz-hint{font-size:.68rem;margin-top:4px;color:var(--muted);}
.audio-card{display:flex;align-items:center;gap:14px;padding:14px 16px;
  background:var(--bg);border:1px solid var(--border);border-radius:8px;margin-top:12px;}
.audio-icon{font-size:1.5rem;}.audio-info{flex:1;min-width:0;}
.audio-name{font-size:.82rem;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.audio-size{font-size:.68rem;color:var(--muted);margin-top:2px;}
.preview-wrap{position:relative;margin-top:14px;border-radius:8px;overflow:hidden;border:1px solid var(--border);}
#bg-preview{display:block;width:100%;height:160px;object-fit:cover;opacity:0;transition:opacity .4s;}
#bg-preview.loaded{opacity:1;}
.preview-label{position:absolute;bottom:0;left:0;right:0;background:rgba(0,0,0,.55);
  backdrop-filter:blur(4px);font-size:.69rem;color:rgba(255,255,255,.75);padding:5px 10px;
  display:flex;align-items:center;justify-content:space-between;}
.status-msg{font-size:.73rem;margin-top:10px;padding:7px 11px;border-radius:6px;
  background:rgba(79,156,249,.08);border:1px solid rgba(79,156,249,.18);color:var(--accent);display:none;}
.status-msg.show{display:block;}.status-msg.ok{background:rgba(62,207,142,.08);border-color:rgba(62,207,142,.2);color:var(--ok);}
.status-msg.err{background:rgba(249,112,88,.08);border-color:rgba(249,112,88,.2);color:var(--err);}
.prog-wrap{margin-top:10px;display:none;}.prog-wrap.show{display:block;}
.prog-bar{height:4px;background:var(--border);border-radius:4px;overflow:hidden;}
.prog-fill{height:100%;background:var(--accent);border-radius:4px;width:0%;transition:width .2s;}
.prog-label{font-size:.68rem;color:var(--muted);margin-top:4px;}
#toast{position:fixed;bottom:26px;right:26px;z-index:9999;padding:10px 22px;border-radius:8px;
  font-size:.78rem;opacity:0;transition:.25s;pointer-events:none;background:var(--ok);color:#0b0f1a;}
#toast.show{opacity:1;}#toast.err{background:var(--err);color:#fff;}
/* Typography cards */
.el-card{background:var(--surf2);border:1px solid var(--border);border-radius:8px;padding:16px 18px;margin-bottom:14px;}
.el-title{font-size:.84rem;color:var(--text);margin-bottom:14px;font-weight:500;}
.range-row{display:flex;align-items:center;gap:10px;}
.range-val{font-size:.8rem;color:var(--accent);min-width:28px;text-align:right;flex-shrink:0;}
/* Layout / order */
.order-list{display:flex;flex-direction:column;gap:8px;}
.order-item{display:flex;align-items:center;gap:12px;padding:12px 16px;
  background:var(--surf2);border:1px solid var(--border);border-radius:8px;cursor:grab;user-select:none;}
.order-item.dragging{opacity:.4;border-style:dashed;}
.order-item.drag-over{border-color:var(--accent);background:rgba(79,156,249,.08);}
.order-handle{color:var(--muted);font-size:1rem;cursor:grab;}
.order-label{flex:1;font-size:.84rem;color:var(--text);}
.align-btns{display:flex;gap:4px;}
.align-btn{padding:4px 10px;border-radius:5px;font-size:.72rem;cursor:pointer;border:1px solid var(--border);
  background:var(--bg);color:var(--muted);transition:.15s;}
.align-btn.on{background:rgba(79,156,249,.15);border-color:var(--accent);color:var(--accent);}
/* Weekday tabs */
.day-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px;}
.day-tab{padding:5px 12px;border-radius:6px;font-size:.75rem;cursor:pointer;
  background:var(--surf2);border:1px solid var(--border);color:var(--muted);transition:.15s;}
.day-tab.on{background:rgba(79,156,249,.15);border-color:var(--accent);color:var(--accent);}
/* Font list */
.font-item{display:flex;align-items:center;justify-content:space-between;
  padding:9px 12px;background:var(--bg);border:1px solid var(--border);border-radius:7px;margin-bottom:7px;}
/* Reset */
.reset-card{background:rgba(249,112,88,.06);border:1px solid rgba(249,112,88,.2);border-radius:var(--r);padding:20px 24px;}
@media(max-width:640px){
  .shell{grid-template-columns:1fr;}
  nav{position:static;height:auto;flex-direction:row;flex-wrap:wrap;padding:10px 8px;}
  .logo{display:none;}nav a{padding:7px 12px;font-size:.75rem;}
  main{padding:20px 16px;}.g2,.g3{grid-template-columns:1fr;}
}
</style>
</head>
<body>
<div class="shell">
<nav>
  <div class="logo">Pi Dashboard<small>Web Portal</small></div>
  <a href="#" class="on" data-s="general"    onclick="go(this)"><span class="ic">⚙️</span>General</a>
  <a href="#"            data-s="typography" onclick="go(this)"><span class="ic">🔤</span>Typography</a>
  <a href="#"            data-s="layout"     onclick="go(this)"><span class="ic">📐</span>Layout & Order</a>
  <hr class="nav-sep"/>
  <a href="#"            data-s="routine"    onclick="go(this)"><span class="ic">📋</span>Routine</a>
  <a href="#"            data-s="reminders"  onclick="go(this)"><span class="ic">🔔</span>Reminders</a>
  <hr class="nav-sep"/>
  <a href="#"            data-s="background" onclick="go(this)"><span class="ic">🖼️</span>Background</a>
  <a href="#"            data-s="chime"      onclick="go(this)"><span class="ic">🔊</span>Chime</a>
  <a href="#"            data-s="fonts"      onclick="go(this)"><span class="ic">🔡</span>Fonts</a>
  <hr class="nav-sep"/>
  <a href="#"            data-s="reset"      onclick="go(this)"><span class="ic">♻️</span>Reset</a>
</nav>
<main>

<!-- GENERAL -->
<div id="sec-general" class="sec on">
  <h2>General Settings</h2><p class="sub">Clock, countdown, chime and visibility</p>
  <div class="card"><h3>Clock</h3>
    <div class="g2">
      <div class="field"><label>Time Format</label>
        <select id="time_format"><option value="12">12-hour (AM/PM)</option><option value="24">24-hour</option></select></div>
      <div class="field"><label>HSC Exam Date</label><input type="date" id="hsc_date"/></div>
    </div>
    <div class="tog-row"><label style="margin:0">Show HSC Countdown</label>
      <label class="tog"><input type="checkbox" id="show_countdown"/><span class="sl"></span></label></div>
  </div>
  <div class="card"><h3>Chime</h3>
    <div class="tog-row"><label style="margin:0">Hourly Chime</label>
      <label class="tog"><input type="checkbox" id="chime"/><span class="sl"></span></label></div>
    <div class="tog-row" style="margin-top:10px"><label style="margin:0">Half-hour Chime</label>
      <label class="tog"><input type="checkbox" id="chime_half"/><span class="sl"></span></label></div>
    <hr style="border:none;border-top:1px solid var(--border);margin:16px 0"/>
    <h3 style="margin-bottom:10px">🔇 Mute</h3>
    <div class="tog-row">
      <div><label style="margin:0;font-size:.82rem;color:var(--text)">Mute All Chimes</label>
        <div style="font-size:.7rem;color:var(--muted);margin-top:2px">Takes effect in ~30 s</div></div>
      <label class="tog"><input type="checkbox" id="chime_muted" onchange="quickMute(this)"/><span class="sl"></span></label></div>
    <div id="mute-indicator" style="display:none;margin-top:8px;padding:7px 11px;background:rgba(249,112,88,.1);
      border:1px solid rgba(249,112,88,.25);border-radius:7px;font-size:.75rem;color:var(--err);">🔇 Chimes are muted</div>
    <hr style="border:none;border-top:1px solid var(--border);margin:16px 0"/>
    <h3 style="margin-bottom:10px">🌙 Quiet Hours</h3>
    <div class="g2">
      <div class="field"><label>Mute From</label><input type="time" id="quiet_from"/></div>
      <div class="field"><label>Unmute At</label><input type="time" id="quiet_to"/></div>
    </div>
    <hr style="border:none;border-top:1px solid var(--border);margin:16px 0"/>
    <h3 style="margin-bottom:10px">📅 Snooze Until</h3>
    <div class="g2">
      <div class="field"><label>Date</label><input type="date" id="mute_until_date"/></div>
      <div class="field"><label>Time</label><input type="time" id="mute_until_time"/></div>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px">
      <button class="btn btn-w btn-sm" onclick="muteUntil(1)">1 hr</button>
      <button class="btn btn-w btn-sm" onclick="muteUntil(4)">4 hrs</button>
      <button class="btn btn-w btn-sm" onclick="muteUntil(8)">8 hrs</button>
      <button class="btn btn-w btn-sm" onclick="muteUntil(24)">24 hrs</button>
      <button class="btn btn-g btn-sm" onclick="clearMuteUntil()">Clear</button>
    </div>
    <div id="mute-until-status" style="font-size:.73rem;color:var(--warn);display:none;margin-top:6px"></div>
  </div>
  <div class="card"><h3>Visibility</h3>
    <div class="tog-row"><label style="margin:0">Show English Date</label>
      <label class="tog"><input type="checkbox" id="show_date_en"/><span class="sl"></span></label></div>
    <div class="tog-row" style="margin-top:10px"><label style="margin:0">Show Bangla Date</label>
      <label class="tog"><input type="checkbox" id="show_date_bn"/><span class="sl"></span></label></div>
    <div class="tog-row" style="margin-top:10px"><label style="margin:0">Show Next Reminder</label>
      <label class="tog"><input type="checkbox" id="show_event"/><span class="sl"></span></label></div>
  </div>
  <div class="card"><h3>Background Overlay Darkness</h3>
    <div class="range-row"><input type="range" id="overlay" min="0" max="100"
      oninput="document.getElementById('ov-val').textContent=this.value"/>
      <span class="range-val" id="ov-val">55</span></div>
  </div>
  <div class="card"><h3>Status Message</h3>
    <div class="field"><label>Small line at bottom — leave blank to hide</label>
      <input type="text" id="status" placeholder="Exam Week · Stay Focused"/></div>
  </div>
  <button class="btn btn-p" onclick="saveSettings()">💾&nbsp; Save Settings</button>
</div>

<!-- TYPOGRAPHY -->
<div id="sec-typography" class="sec">
  <h2>Typography</h2><p class="sub">Font, size, color and opacity for each element</p>
  <div id="type-cards"></div>
  <button class="btn btn-p" onclick="saveTypography()">💾&nbsp; Save Typography</button>
</div>

<!-- LAYOUT -->
<div id="sec-layout" class="sec">
  <h2>Layout &amp; Order</h2>
  <p class="sub">Drag to reorder. Set each element's horizontal alignment.</p>
  <div class="card">
    <h3>Element Order &amp; Alignment</h3>
    <p style="font-size:.72rem;color:var(--muted);margin-bottom:14px">
      Drag rows up/down to reorder. Click L / C / R to set alignment.
    </p>
    <div class="order-list" id="order-list"></div>
  </div>
  <button class="btn btn-p" onclick="saveLayout()">💾&nbsp; Save Layout</button>
</div>

<!-- ROUTINE -->
<div id="sec-routine" class="sec">
  <h2>Daily Routine</h2><p class="sub">Time blocks shown on the clock below the time</p>
  <div class="card"><h3>Mode</h3>
    <div class="tog-row">
      <div><label style="margin:0;font-size:.82rem;color:var(--text)">Different routine per weekday</label>
        <div style="font-size:.7rem;color:var(--muted);margin-top:2px">Off = same every day</div></div>
      <label class="tog"><input type="checkbox" id="routine_per_day" onchange="toggleRoutineMode()"/><span class="sl"></span></label>
    </div>
  </div>
  <div class="card"><h3>Blocks</h3>
    <div id="day-tabs-wrap" style="display:none">
      <div class="day-tabs">
        <div class="day-tab on" data-day="monday"    onclick="selDay(this)">Mon</div>
        <div class="day-tab"    data-day="tuesday"   onclick="selDay(this)">Tue</div>
        <div class="day-tab"    data-day="wednesday" onclick="selDay(this)">Wed</div>
        <div class="day-tab"    data-day="thursday"  onclick="selDay(this)">Thu</div>
        <div class="day-tab"    data-day="friday"    onclick="selDay(this)">Fri</div>
        <div class="day-tab"    data-day="saturday"  onclick="selDay(this)">Sat</div>
        <div class="day-tab"    data-day="sunday"    onclick="selDay(this)">Sun</div>
      </div>
    </div>
    <div class="g3" style="margin-bottom:12px">
      <div class="field"><label>Start</label><input type="time" id="rt_start"/></div>
      <div class="field"><label>End (optional)</label><input type="time" id="rt_end"/></div>
      <div class="field"><label>Label</label><input type="text" id="rt_label" placeholder="📖 Study Time"/></div>
    </div>
    <button class="btn btn-p btn-sm" onclick="addBlock()">+ Add Block</button>
    <div id="routine-list" style="margin-top:16px"></div>
  </div>
</div>

<!-- REMINDERS -->
<div id="sec-reminders" class="sec">
  <h2>Reminders</h2><p class="sub">Birthdays, holidays and events</p>
  <div class="card"><h3>Add Reminder</h3>
    <div class="g2">
      <div class="field"><label>Title</label><input type="text" id="r_title" placeholder="🎂 Someone's Birthday"/></div>
      <div class="field"><label>Date</label><input type="date" id="r_date"/></div>
      <div class="field"><label>Time (optional)</label><input type="time" id="r_time"/></div>
      <div class="field"><label>Type</label>
        <select id="r_note">
          <option value="">General</option>
          <option value="Birthday">Birthday</option>
          <option value="Anniversary">Anniversary</option>
          <option value="Public Holiday">Public Holiday</option>
        </select></div>
    </div>
    <button class="btn btn-p btn-sm" onclick="addReminder()">+ Add</button>
  </div>
  <div class="card"><h3>All Reminders</h3><div id="rlist"></div></div>
</div>

<!-- BACKGROUND -->
<div id="sec-background" class="sec">
  <h2>Background Image</h2><p class="sub">JPG · PNG · WebP, max 50 MB</p>
  <div class="card"><h3>Current</h3>
    <div class="preview-wrap" id="preview-wrap" style="display:none">
      <img id="bg-preview" src="" alt=""/>
      <div class="preview-label"><span id="bg-filename"></span>
        <button class="btn btn-d btn-sm" onclick="removeBg()">✕ Remove</button></div>
    </div>
    <div id="no-bg" style="color:var(--muted);font-size:.78rem;padding:10px 0">No background set.</div>
  </div>
  <div class="card"><h3>Upload</h3>
    <div class="upz" id="bg-dz" onclick="document.getElementById('bgfile').click()"
         ondragover="dzOver(event,'bg-dz')" ondragleave="dzLeave('bg-dz')" ondrop="dzDrop(event,'bgfile','bg-dz')">
      <div class="upz-icon">🖼️</div><div>Click or drag & drop</div>
      <div class="upz-hint">JPG · PNG · WebP · max 50 MB</div></div>
    <input type="file" id="bgfile" accept=".jpg,.jpeg,.png,.webp" style="display:none" onchange="uploadBg()"/>
    <div class="prog-wrap" id="bg-prog"><div class="prog-bar"><div class="prog-fill" id="bg-prog-fill"></div></div>
      <div class="prog-label" id="bg-prog-label"></div></div>
    <div class="status-msg" id="bg-status"></div>
  </div>
</div>

<!-- CHIME -->
<div id="sec-chime" class="sec">
  <h2>Chime Sounds</h2><p class="sub">Regular chime and birthday chime</p>
  <div class="card"><h3>🔔 Test Chime</h3>
    <p style="font-size:.73rem;color:var(--muted);margin-bottom:12px">Play the chime right now to confirm it works.</p>
    <button class="btn btn-p" onclick="testChime()">▶&nbsp; Play Chime Now</button>
    <div class="status-msg" id="test-chime-status" style="margin-top:10px"></div>
  </div>
  <div class="card"><h3>🔔 Regular Chime</h3>
    <div id="no-chime" style="color:var(--muted);font-size:.78rem;padding:6px 0 12px">No chime uploaded.</div>
    <div class="audio-card" id="chime-card" style="display:none">
      <div class="audio-icon">🔊</div>
      <div class="audio-info"><div class="audio-name" id="chime-name"></div><div class="audio-size" id="chime-size"></div></div>
      <button class="btn btn-g btn-sm" onclick="previewAudio('chime-player','/chime-audio')">▶ Play</button>
      <button class="btn btn-d btn-sm" onclick="removeAudio('chime','chime-card','no-chime','chime-player')">✕</button>
    </div>
    <audio id="chime-player" controls style="display:none;width:100%;margin-top:10px"></audio>
    <div class="upz" style="margin-top:14px" id="chime-dz"
         onclick="document.getElementById('chimefile').click()"
         ondragover="dzOver(event,'chime-dz')" ondragleave="dzLeave('chime-dz')" ondrop="dzDrop(event,'chimefile','chime-dz')">
      <div class="upz-icon">🔉</div><div>Upload chime</div><div class="upz-hint">WAV · MP3 · OGG</div></div>
    <input type="file" id="chimefile" accept=".wav,.mp3,.ogg" style="display:none"
           onchange="uploadAudio(this,'chime','chime-prog','chime-prog-fill','chime-prog-label','chime-status',showChimeCard)"/>
    <div class="prog-wrap" id="chime-prog"><div class="prog-bar"><div class="prog-fill" id="chime-prog-fill"></div></div>
      <div class="prog-label" id="chime-prog-label"></div></div>
    <div class="status-msg" id="chime-status"></div>
  </div>
  <div class="card"><h3>🎂 Birthday Chime</h3>
    <p style="font-size:.73rem;color:var(--muted);margin-bottom:12px">Plays on birthdays instead of regular chime.</p>
    <div id="no-bday-chime" style="color:var(--muted);font-size:.78rem;padding:6px 0 12px">No birthday chime uploaded.</div>
    <div class="audio-card" id="bday-chime-card" style="display:none">
      <div class="audio-icon">🎂</div>
      <div class="audio-info"><div class="audio-name" id="bday-chime-name"></div><div class="audio-size" id="bday-chime-size"></div></div>
      <button class="btn btn-g btn-sm" onclick="previewAudio('bday-chime-player','/birthday-chime-audio')">▶ Play</button>
      <button class="btn btn-d btn-sm" onclick="removeAudio('birthday-chime','bday-chime-card','no-bday-chime','bday-chime-player')">✕</button>
    </div>
    <audio id="bday-chime-player" controls style="display:none;width:100%;margin-top:10px"></audio>
    <div class="upz" style="margin-top:14px" id="bday-dz"
         onclick="document.getElementById('bdaychimefile').click()"
         ondragover="dzOver(event,'bday-dz')" ondragleave="dzLeave('bday-dz')" ondrop="dzDrop(event,'bdaychimefile','bday-dz')">
      <div class="upz-icon">🎵</div><div>Upload birthday chime</div><div class="upz-hint">WAV · MP3 · OGG</div></div>
    <input type="file" id="bdaychimefile" accept=".wav,.mp3,.ogg" style="display:none"
           onchange="uploadAudio(this,'birthday_chime','bday-chime-prog','bday-chime-prog-fill','bday-chime-prog-label','bday-chime-status',showBdayChimeCard)"/>
    <div class="prog-wrap" id="bday-chime-prog"><div class="prog-bar"><div class="prog-fill" id="bday-chime-prog-fill"></div></div>
      <div class="prog-label" id="bday-chime-prog-label"></div></div>
    <div class="status-msg" id="bday-chime-status"></div>
  </div>
</div>

<!-- FONTS -->
<div id="sec-fonts" class="sec">
  <h2>Fonts</h2><p class="sub">Upload TTF/OTF fonts — appear in Typography instantly</p>
  <div class="card"><h3>Upload Font</h3>
    <div class="upz" id="font-dz" onclick="document.getElementById('fontfile').click()"
         ondragover="dzOver(event,'font-dz')" ondragleave="dzLeave('font-dz')" ondrop="dzDrop(event,'fontfile','font-dz')">
      <div class="upz-icon">🔡</div><div>Click or drag & drop</div>
      <div class="upz-hint">TTF · OTF · WOFF · WOFF2</div></div>
    <input type="file" id="fontfile" accept=".ttf,.otf,.woff,.woff2" style="display:none" onchange="uploadFont()"/>
    <div class="prog-wrap" id="font-prog"><div class="prog-bar"><div class="prog-fill" id="font-prog-fill"></div></div>
      <div class="prog-label" id="font-prog-label"></div></div>
    <div class="status-msg" id="font-status"></div>
  </div>
  <div class="card"><h3>Installed Fonts</h3><div id="font-list"></div></div>
</div>

<!-- RESET -->
<div id="sec-reset" class="sec">
  <h2>Reset</h2><p class="sub">Restore defaults — uploaded files and reminders are kept</p>
  <div class="reset-card">
    <h3 style="color:var(--err);margin-bottom:10px">⚠️ Reset to Defaults</h3>
    <p style="font-size:.78rem;color:var(--muted);margin-bottom:18px">
      Resets typography, layout, order, general settings and routine.<br>
      Uploaded files and reminders are <strong style="color:var(--text)">not deleted</strong>.
    </p>
    <button class="btn btn-d" onclick="resetAll()">🔄&nbsp; Reset Everything to Defaults</button>
  </div>
</div>

</main>
</div>
<div id="toast"></div>
<script>
const ELEMENT_META = {
  time:      {label:'🕐 Time'},
  routine:   {label:'📋 Routine Block'},
  date_en:   {label:'📅 English Date'},
  date_bn:   {label:'🇧🇩 Bangla Date'},
  countdown: {label:'🎯 HSC Countdown'},
  event:     {label:'🔔 Next Reminder'},
  status:    {label:'💬 Status Message'},
};
const DEFAULT_ORDER = ['time','routine','date_en','date_bn','countdown','event','status'];

let cfg={}, fonts=[], routine={}, reminders=[], curDay='everyday';
let orderArr = [...DEFAULT_ORDER];

// Nav
function go(el){
  document.querySelectorAll('nav a').forEach(a=>a.classList.remove('on'));
  document.querySelectorAll('.sec').forEach(s=>s.classList.remove('on'));
  el.classList.add('on'); document.getElementById('sec-'+el.dataset.s).classList.add('on'); return false;
}

// Toast
function toast(msg,err=false){
  const t=document.getElementById('toast'); t.textContent=msg;
  t.className='show'+(err?' err':''); clearTimeout(t._t); t._t=setTimeout(()=>t.className='',3000);
}
function setStatus(id,msg,type=''){
  const el=document.getElementById(id); el.textContent=msg;
  el.className='status-msg show'+(type?' '+type:'');
}
function escHtml(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

// Settings
async function loadSettings(){
  cfg=await fetch('/api/settings').then(r=>r.json());
  document.getElementById('time_format').value     =cfg.time_format||'12';
  document.getElementById('hsc_date').value         =cfg.hsc_date||'2026-06-20';
  document.getElementById('show_countdown').checked =cfg.show_countdown!==false;
  document.getElementById('chime').checked          =cfg.chime!==false;
  document.getElementById('chime_half').checked     =cfg.chime_half===true;
  document.getElementById('chime_muted').checked    =cfg.chime_muted===true;
  document.getElementById('quiet_from').value       =cfg.quiet_from||'';
  document.getElementById('quiet_to').value         =cfg.quiet_to||'';
  document.getElementById('mute_until_date').value  =cfg.mute_until?cfg.mute_until.split('T')[0]:'';
  document.getElementById('mute_until_time').value  =cfg.mute_until?cfg.mute_until.split('T')[1]||'':'';
  document.getElementById('show_date_en').checked   =cfg.show_date_en!==false;
  document.getElementById('show_date_bn').checked   =cfg.show_date_bn!==false;
  document.getElementById('show_event').checked     =cfg.show_event!==false;
  document.getElementById('overlay').value          =cfg.overlay??55;
  document.getElementById('ov-val').textContent     =cfg.overlay??55;
  document.getElementById('status').value           =cfg.status||'';
  orderArr = cfg.order ? [...cfg.order] : [...DEFAULT_ORDER];
  updateMuteUI();
}
async function saveSettings(){
  const mu=()=>{const d=document.getElementById('mute_until_date').value,t=document.getElementById('mute_until_time').value;return d?`${d}T${t||'00:00'}`:'';}
  cfg={...cfg,
    time_format:   document.getElementById('time_format').value,
    hsc_date:      document.getElementById('hsc_date').value,
    show_countdown:document.getElementById('show_countdown').checked,
    chime:         document.getElementById('chime').checked,
    chime_half:    document.getElementById('chime_half').checked,
    chime_muted:   document.getElementById('chime_muted').checked,
    quiet_from:    document.getElementById('quiet_from').value,
    quiet_to:      document.getElementById('quiet_to').value,
    mute_until:    mu(),
    show_date_en:  document.getElementById('show_date_en').checked,
    show_date_bn:  document.getElementById('show_date_bn').checked,
    show_event:    document.getElementById('show_event').checked,
    overlay:       parseInt(document.getElementById('overlay').value)||55,
    status:        document.getElementById('status').value.trim(),
  };
  const r=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)});
  r.ok?toast('✓ Saved — clock updates in ~30 s'):toast('Save failed',true); updateMuteUI();
}
function updateMuteUI(){
  document.getElementById('mute-indicator').style.display=cfg.chime_muted?'block':'none';
  const mu=cfg.mute_until||'',el=document.getElementById('mute-until-status');
  if(mu){const dt=new Date(mu);if(dt>new Date()){el.style.display='block';
    el.textContent=`⏳ Muted until ${dt.toLocaleDateString()} ${dt.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}`;return;}}
  el.style.display='none';
}
async function quickMute(cb){cfg.chime_muted=cb.checked;await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)});updateMuteUI();toast(cb.checked?'🔇 Muted':'🔊 Unmuted');}
function muteUntil(h){const dt=new Date(Date.now()+h*3600000);document.getElementById('mute_until_date').value=dt.toISOString().split('T')[0];document.getElementById('mute_until_time').value=dt.toTimeString().slice(0,5);toast('Set — click Save to apply');}
function clearMuteUntil(){document.getElementById('mute_until_date').value='';document.getElementById('mute_until_time').value='';cfg.mute_until='';fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)});document.getElementById('mute-until-status').style.display='none';toast('Snooze cleared');}

// Typography
function buildTypographyCards(){
  const els=cfg.elements||{};
  const fontOpts=['<option value="">System Default</option>',...fonts.map(f=>`<option value="${escHtml(f)}">${escHtml(f)}</option>`)].join('');
  document.getElementById('type-cards').innerHTML=Object.entries(ELEMENT_META).map(([key,{label}])=>{
    const e=els[key]||{};
    return `<div class="el-card"><div class="el-title">${label}</div>
      <div class="g2">
        <div class="field"><label>Size (px)</label>
          <div class="range-row"><input type="range" id="t_size_${key}" min="10" max="160" value="${e.size||24}"
            oninput="document.getElementById('t_sv_${key}').textContent=this.value"/>
            <span class="range-val" id="t_sv_${key}">${e.size||24}</span></div></div>
        <div class="field"><label>Font</label><select id="t_font_${key}">${fontOpts}</select></div>
        <div class="field"><label>Color</label>
          <input type="color" id="t_color_${key}" value="${e.color||'#ffffff'}" style="height:38px;padding:3px 7px;cursor:pointer;width:60px"/></div>
        <div class="field"><label>Opacity (0–255)</label>
          <div class="range-row"><input type="range" id="t_alpha_${key}" min="0" max="255" value="${e.alpha??255}"
            oninput="document.getElementById('t_av_${key}').textContent=this.value"/>
            <span class="range-val" id="t_av_${key}">${e.alpha??255}</span></div></div>
      </div>
      <div class="tog-row" style="margin-top:10px">
        <label style="font-size:.75rem;color:var(--muted);margin:0">Bold</label>
        <label class="tog"><input type="checkbox" id="t_bold_${key}" ${e.bold?'checked':''}/><span class="sl"></span></label>
      </div>
    </div>`;
  }).join('');
  Object.keys(ELEMENT_META).forEach(key=>{
    const e=(cfg.elements||{})[key]||{};
    const sel=document.getElementById(`t_font_${key}`);
    if(sel&&e.font) sel.value=e.font;
  });
}
async function saveTypography(){
  if(!cfg.elements) cfg.elements={};
  Object.keys(ELEMENT_META).forEach(key=>{
    cfg.elements[key]={
      ...(cfg.elements[key]||{}),
      size:  parseInt(document.getElementById(`t_size_${key}`).value)||24,
      font:  document.getElementById(`t_font_${key}`).value,
      color: document.getElementById(`t_color_${key}`).value,
      alpha: parseInt(document.getElementById(`t_alpha_${key}`).value)??255,
      bold:  document.getElementById(`t_bold_${key}`).checked,
    };
  });
  const r=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)});
  r.ok?toast('✓ Typography saved'):toast('Save failed',true);
}

// Layout & Order
function buildOrderList(){
  const els=cfg.elements||{};
  const list=document.getElementById('order-list');
  list.innerHTML=orderArr.map((key,i)=>{
    const e=els[key]||{};
    const align=e.align||'center';
    return `<div class="order-item" draggable="true" data-key="${key}" data-idx="${i}"
      ondragstart="dragStart(event)" ondragover="dragOver(event)" ondrop="dropOn(event)" ondragleave="dragLeave(event)">
      <span class="order-handle">⠿</span>
      <span class="order-label">${ELEMENT_META[key]?.label||key}</span>
      <div class="align-btns">
        <button class="align-btn ${align==='left'?'on':''}"   onclick="setAlign('${key}','left',this)">L</button>
        <button class="align-btn ${align==='center'?'on':''}" onclick="setAlign('${key}','center',this)">C</button>
        <button class="align-btn ${align==='right'?'on':''}"  onclick="setAlign('${key}','right',this)">R</button>
      </div>
    </div>`;
  }).join('');
}

function setAlign(key, align, btn){
  if(!cfg.elements) cfg.elements={};
  if(!cfg.elements[key]) cfg.elements[key]={};
  cfg.elements[key].align=align;
  // Update button states
  btn.parentElement.querySelectorAll('.align-btn').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');
}

// Drag & drop for order
let dragIdx=null;
function dragStart(e){dragIdx=parseInt(e.currentTarget.dataset.idx);e.currentTarget.classList.add('dragging');}
function dragOver(e){e.preventDefault();e.currentTarget.classList.add('drag-over');}
function dragLeave(e){e.currentTarget.classList.remove('drag-over');}
function dropOn(e){
  e.preventDefault();
  const targetIdx=parseInt(e.currentTarget.dataset.idx);
  e.currentTarget.classList.remove('drag-over');
  document.querySelectorAll('.order-item').forEach(el=>el.classList.remove('dragging'));
  if(dragIdx===null||dragIdx===targetIdx)return;
  const moved=orderArr.splice(dragIdx,1)[0];
  orderArr.splice(targetIdx,0,moved);
  buildOrderList();
}

async function saveLayout(){
  cfg.order=[...orderArr];
  if(!cfg.elements) cfg.elements={};
  const r=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)});
  r.ok?toast('✓ Layout saved'):toast('Save failed',true);
}

// Routine
async function loadRoutine(){
  routine=await fetch('/api/routine').then(r=>r.json());
  document.getElementById('routine_per_day').checked=cfg.routine_per_day===true;
  curDay=cfg.routine_per_day?'monday':'everyday';
  toggleRoutineMode(); renderRoutine();
}
function toggleRoutineMode(){
  const perDay=document.getElementById('routine_per_day').checked;
  document.getElementById('day-tabs-wrap').style.display=perDay?'block':'none';
  curDay=perDay?(document.querySelector('.day-tab.on')||{dataset:{day:'monday'}}).dataset.day:'everyday';
  renderRoutine();
}
function selDay(el){document.querySelectorAll('.day-tab').forEach(t=>t.classList.remove('on'));el.classList.add('on');curDay=el.dataset.day;renderRoutine();}
function renderRoutine(){
  const blocks=routine[curDay]||[];
  const el=document.getElementById('routine-list');
  if(!blocks.length){el.innerHTML='<div class="empty">No blocks yet.</div>';return;}
  el.innerHTML=blocks.map((b,i)=>`
    <div class="ri"><div class="inf">
      <span class="tit">${escHtml(b.label)}</span>
      <span class="met">${b.start}${b.end?' → '+b.end:''}</span>
    </div><button class="btn btn-d btn-sm" onclick="delBlock(${i})">✕</button></div>`).join('');
}
async function addBlock(){
  const start=document.getElementById('rt_start').value;
  const end=document.getElementById('rt_end').value;
  const label=document.getElementById('rt_label').value.trim();
  if(!start){toast('Pick a start time',true);return;}
  if(!label){toast('Enter a label',true);return;}
  if(!routine[curDay]) routine[curDay]=[];
  routine[curDay].push({start,end,label});
  routine[curDay].sort((a,b)=>a.start<b.start?-1:1);
  await pushRoutine();
  ['rt_start','rt_end','rt_label'].forEach(id=>document.getElementById(id).value='');
  toast('✓ Block added');
}
async function delBlock(i){if(!routine[curDay])return;routine[curDay].splice(i,1);await pushRoutine();toast('Block removed');}
async function pushRoutine(){
  cfg.routine_per_day=document.getElementById('routine_per_day').checked;
  await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)});
  await fetch('/api/routine',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(routine)});
  renderRoutine();
}

// Reminders
async function loadReminders(){reminders=await fetch('/api/reminders').then(r=>r.json());renderReminders();}
function renderReminders(){
  const el=document.getElementById('rlist');
  if(!reminders.length){el.innerHTML='<div class="empty">No reminders.</div>';return;}
  el.innerHTML=reminders.map((r,i)=>`
    <div class="ri"><div class="inf">
      <span class="tit">${escHtml(r.title)}</span>
      <span class="met">${[r.date,r.time,r.note].filter(Boolean).map(escHtml).join(' · ')}</span>
    </div><button class="btn btn-d btn-sm" onclick="delReminder(${i})">✕</button></div>`).join('');
}
async function addReminder(){
  const title=document.getElementById('r_title').value.trim();
  if(!title){toast('Enter a title',true);return;}
  reminders.push({title,date:document.getElementById('r_date').value,
    time:document.getElementById('r_time').value,note:document.getElementById('r_note').value});
  reminders.sort((a,b)=>a.date+a.time<b.date+b.time?-1:1);
  await pushReminders();
  ['r_title','r_date','r_time'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('r_note').value=''; toast('✓ Added');
}
async function delReminder(i){reminders.splice(i,1);await pushReminders();toast('Removed');}
async function pushReminders(){
  await fetch('/api/reminders',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(reminders)});
  renderReminders();
}

// Background
async function loadBgStatus(){
  const d=await fetch('/api/bg-status').then(r=>r.json());
  if(d.exists) showBgPreview('/bg-image?t='+Date.now(),d.filename,d.size_kb);
  else{document.getElementById('preview-wrap').style.display='none';document.getElementById('no-bg').style.display='block';}
}
function showBgPreview(src,filename,size_kb){
  document.getElementById('no-bg').style.display='none';
  const wrap=document.getElementById('preview-wrap');wrap.style.display='block';
  const img=document.getElementById('bg-preview');img.classList.remove('loaded');
  img.onload=()=>img.classList.add('loaded');img.src=src;
  document.getElementById('bg-filename').textContent=filename+(size_kb?` (${size_kb} KB)`:'');
}
function uploadBg(){
  const file=document.getElementById('bgfile').files[0];if(!file)return;
  uploadFile('/api/background','background',file,'bg-prog','bg-prog-fill','bg-prog-label','bg-status',(d)=>{
    showBgPreview('/bg-image?t='+Date.now(),file.name,Math.round(file.size/1024));cfg.background=d.path;toast('✓ Uploaded');
  });
}
async function removeBg(){
  if(!confirm('Remove background?'))return;
  await fetch('/api/background',{method:'DELETE'});
  document.getElementById('preview-wrap').style.display='none';
  document.getElementById('no-bg').style.display='block';
  cfg.background='';
  await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)});
  toast('Removed');
}

// Chime
async function loadChimeStatus(){const d=await fetch('/api/chime-status').then(r=>r.json());if(d.exists)showChimeCard(d.filename,d.size_kb);}
async function loadBdayChimeStatus(){const d=await fetch('/api/birthday-chime-status').then(r=>r.json());if(d.exists)showBdayChimeCard(d.filename,d.size_kb);}
function showChimeCard(fn,sz){document.getElementById('no-chime').style.display='none';document.getElementById('chime-card').style.display='flex';document.getElementById('chime-name').textContent=fn;document.getElementById('chime-size').textContent=sz?sz+' KB':'';}
function showBdayChimeCard(fn,sz){document.getElementById('no-bday-chime').style.display='none';document.getElementById('bday-chime-card').style.display='flex';document.getElementById('bday-chime-name').textContent=fn;document.getElementById('bday-chime-size').textContent=sz?sz+' KB':'';}
function previewAudio(playerId,src){const p=document.getElementById(playerId);p.src=src+'?t='+Date.now();p.style.display='block';p.play();}
async function removeAudio(endpoint,cardId,noId,playerId){
  if(!confirm('Remove?'))return;
  await fetch('/api/'+endpoint,{method:'DELETE'});
  document.getElementById(cardId).style.display='none';
  document.getElementById(noId).style.display='block';
  document.getElementById(playerId).style.display='none';toast('Removed');
}
function uploadAudio(input,fieldName,progWrapId,progFillId,progLabelId,statusId,onSuccess){
  const file=input.files[0];if(!file)return;
  const endpoint=fieldName.replace(/_/g,'-');
  uploadFile('/api/'+endpoint,fieldName,file,progWrapId,progFillId,progLabelId,statusId,(d)=>{
    onSuccess(file.name,Math.round(file.size/1024));toast('✓ Uploaded');
  });
}

// Fonts
async function loadFonts(){fonts=await fetch('/api/fonts').then(r=>r.json());renderFonts();}
function renderFonts(){
  const el=document.getElementById('font-list');
  if(!fonts.length){el.innerHTML='<div class="empty">No fonts yet.</div>';return;}
  el.innerHTML=fonts.map(f=>`<div class="font-item">
    <span style="font-size:.82rem;color:var(--text)">${escHtml(f)}</span>
    <button class="btn btn-d btn-sm" onclick="deleteFont('${escHtml(f)}')">✕ Remove</button>
  </div>`).join('');
}
function uploadFont(){
  const file=document.getElementById('fontfile').files[0];if(!file)return;
  uploadFile('/api/fonts','font',file,'font-prog','font-prog-fill','font-prog-label','font-status',async()=>{
    await loadFonts();buildTypographyCards();toast('✓ Font installed');
  });
}
async function deleteFont(name){
  if(!confirm(`Remove ${name}?`))return;
  await fetch('/api/fonts/'+encodeURIComponent(name),{method:'DELETE'});
  await loadFonts();buildTypographyCards();toast('Font removed');
}

// Reset
async function resetAll(){
  if(!confirm('Reset ALL settings to defaults? Files and reminders are kept.'))return;
  const r=await fetch('/api/reset',{method:'POST'});
  if(r.ok){
    cfg=await fetch('/api/settings').then(r=>r.json());
    orderArr=[...DEFAULT_ORDER];
    await loadSettings();buildTypographyCards();buildOrderList();
    toast('✓ Reset to defaults');
  } else toast('Reset failed',true);
}

// Upload helper
function uploadFile(url,fieldName,file,progWrapId,progFillId,progLabelId,statusId,onSuccess){
  const wrap=document.getElementById(progWrapId),fill=document.getElementById(progFillId),lbl=document.getElementById(progLabelId);
  wrap.classList.add('show');fill.style.width='0%';lbl.textContent='Uploading…';setStatus(statusId,'Uploading…');
  const fd=new FormData();fd.append(fieldName,file);
  const xhr=new XMLHttpRequest();xhr.open('POST',url);
  xhr.upload.onprogress=(e)=>{if(e.lengthComputable){const p=Math.round(e.loaded/e.total*100);fill.style.width=p+'%';lbl.textContent=p+'%';}};
  xhr.onload=()=>{wrap.classList.remove('show');if(xhr.status===200){setStatus(statusId,'✓ Done','ok');onSuccess(JSON.parse(xhr.responseText));}else{setStatus(statusId,'✗ Failed','err');toast('Upload failed',true);}};
  xhr.onerror=()=>{wrap.classList.remove('show');setStatus(statusId,'✗ Error','err');toast('Error',true);};
  xhr.send(fd);
}
function dzOver(e,id){e.preventDefault();document.getElementById(id).classList.add('drag');}
function dzLeave(id){document.getElementById(id).classList.remove('drag');}
function dzDrop(e,inputId,dzId){
  e.preventDefault();dzLeave(dzId);
  if(e.dataTransfer.files.length){const dt=new DataTransfer();dt.items.add(e.dataTransfer.files[0]);
    const inp=document.getElementById(inputId);inp.files=dt.files;inp.dispatchEvent(new Event('change'));}
}

// Test chime
async function testChime(){
  const el=document.getElementById('test-chime-status');
  el.className='status-msg show'; el.textContent='Playing…';
  const r=await fetch('/api/test-chime',{method:'POST'});
  if(r.ok){el.className='status-msg show ok';el.textContent='✓ Chime played!';}
  else{const d=await r.json();el.className='status-msg show err';el.textContent='✗ '+(d.error||'Failed');}
  setTimeout(()=>el.className='status-msg',4000);
}

// Boot
async function init(){
  await loadFonts();
  await loadSettings();
  buildTypographyCards();
  buildOrderList();
  await loadRoutine();
  await loadReminders();
  await loadBgStatus();
  await loadChimeStatus();
  await loadBdayChimeStatus();
}
init();
</script>
</body>
</html>"""

# Routes
@app.route("/")
def index(): return render_template_string(PORTAL_HTML)

@app.route("/api/settings",methods=["GET"])
def get_settings(): return jsonify(load_json(SETTINGS_FILE,{}))

@app.route("/api/settings",methods=["POST"])
def post_settings(): save_json(SETTINGS_FILE,request.get_json(force=True)); return jsonify({"ok":True})

@app.route("/api/reminders",methods=["GET"])
def get_reminders(): return jsonify(load_json(REMINDERS_FILE,[]))

@app.route("/api/reminders",methods=["POST"])
def post_reminders(): save_json(REMINDERS_FILE,request.get_json(force=True)); return jsonify({"ok":True})

@app.route("/api/routine",methods=["GET"])
def get_routine(): return jsonify(load_json(ROUTINE_FILE,{}))

@app.route("/api/routine",methods=["POST"])
def post_routine(): save_json(ROUTINE_FILE,request.get_json(force=True)); return jsonify({"ok":True})

@app.route("/api/background",methods=["POST"])
def upload_bg():
    if "background" not in request.files: return jsonify({"error":"no file"}),400
    f=request.files["background"]; ext=f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
    if ext not in IMG_EXT: return jsonify({"error":"bad type"}),400
    os.makedirs(BASE_DIR,exist_ok=True); f.save(BG_FILE)
    s=load_json(SETTINGS_FILE,{}); s["background"]=BG_FILE; save_json(SETTINGS_FILE,s)
    return jsonify({"ok":True,"path":BG_FILE})

@app.route("/api/background",methods=["DELETE"])
def delete_bg():
    if os.path.isfile(BG_FILE): os.remove(BG_FILE)
    s=load_json(SETTINGS_FILE,{}); s["background"]=""; save_json(SETTINGS_FILE,s); return jsonify({"ok":True})

@app.route("/bg-image")
def serve_bg(): return send_file(BG_FILE,"image/jpeg") if os.path.isfile(BG_FILE) else ("",404)

@app.route("/api/bg-status")
def bg_status():
    if os.path.isfile(BG_FILE): return jsonify({"exists":True,"filename":"background.jpg","size_kb":round(os.path.getsize(BG_FILE)/1024)})
    return jsonify({"exists":False})

def _audio_upload(prefix,field):
    if field not in request.files: return jsonify({"error":"no file"}),400
    f=request.files[field]; ext=f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
    if ext not in AUDIO_EXT: return jsonify({"error":"bad type"}),400
    for e in AUDIO_EXT:
        p=f"{BASE_DIR}/{prefix}.{e}"
        if os.path.isfile(p): os.remove(p)
    dest=f"{BASE_DIR}/{prefix}.{ext}"; f.save(dest)
    s=load_json(SETTINGS_FILE,{}); s[f"{prefix}_file"]=dest; save_json(SETTINGS_FILE,s)
    return jsonify({"ok":True,"path":dest})

def _audio_delete(prefix):
    for e in AUDIO_EXT:
        p=f"{BASE_DIR}/{prefix}.{e}"
        if os.path.isfile(p): os.remove(p)
    s=load_json(SETTINGS_FILE,{}); s[f"{prefix}_file"]=""; save_json(SETTINGS_FILE,s); return jsonify({"ok":True})

def _audio_serve(prefix):
    p,ext=find_audio(prefix)
    if p: return send_file(p,{"wav":"audio/wav","mp3":"audio/mpeg","ogg":"audio/ogg"}.get(ext,"audio/wav"))
    return "",404

def _audio_status(prefix):
    p,ext=find_audio(prefix)
    if p: return jsonify({"exists":True,"filename":f"{prefix}.{ext}","size_kb":round(os.path.getsize(p)/1024)})
    return jsonify({"exists":False})

@app.route("/api/chime",methods=["POST"])
def up_chime(): return _audio_upload("chime","chime")
@app.route("/api/chime",methods=["DELETE"])
def del_chime(): return _audio_delete("chime")
@app.route("/chime-audio")
def srv_chime(): return _audio_serve("chime")
@app.route("/api/chime-status")
def st_chime(): return _audio_status("chime")
@app.route("/api/birthday-chime",methods=["POST"])
def up_bchime(): return _audio_upload("birthday_chime","birthday_chime")
@app.route("/api/birthday-chime",methods=["DELETE"])
def del_bchime(): return _audio_delete("birthday_chime")
@app.route("/birthday-chime-audio")
def srv_bchime(): return _audio_serve("birthday_chime")
@app.route("/api/birthday-chime-status")
def st_bchime(): return _audio_status("birthday_chime")

@app.route("/api/fonts",methods=["GET"])
def get_fonts():
    os.makedirs(FONTS_DIR,exist_ok=True)
    return jsonify([f for f in os.listdir(FONTS_DIR) if f.rsplit(".",1)[-1].lower() in FONT_EXT])

@app.route("/api/fonts",methods=["POST"])
def upload_font():
    if "font" not in request.files: return jsonify({"error":"no file"}),400
    f=request.files["font"]; ext=f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
    if ext not in FONT_EXT: return jsonify({"error":"bad type"}),400
    name=secure_filename(f.filename)
    if not name: return jsonify({"error":"bad name"}),400
    os.makedirs(FONTS_DIR,exist_ok=True); dest=os.path.join(FONTS_DIR,name); f.save(dest)
    return jsonify({"ok":True,"filename":name})

@app.route("/api/fonts/<filename>",methods=["DELETE"])
def delete_font(filename):
    p=os.path.join(FONTS_DIR,os.path.basename(filename))
    if os.path.isfile(p): os.remove(p)
    return jsonify({"ok":True})

@app.route("/fonts/<filename>")
def serve_font(filename):
    p=os.path.join(FONTS_DIR,os.path.basename(filename))
    mt={"ttf":"font/ttf","otf":"font/otf","woff":"font/woff","woff2":"font/woff2"}.get(filename.rsplit(".",1)[-1].lower(),"font/ttf")
    return send_file(p,mt) if os.path.isfile(p) else ("",404)

@app.route("/api/reset",methods=["POST"])
def reset_all():
    existing=load_json(SETTINGS_FILE,{})
    save_json(SETTINGS_FILE,{
        "time_format":"12","hsc_date":"2026-06-20","show_countdown":True,
        "chime":True,"chime_half":False,"chime_muted":False,
        "quiet_from":"","quiet_to":"","mute_until":"","status":"",
        "show_date_en":True,"show_date_bn":True,"show_event":True,
        "overlay":55,"routine_per_day":False,
        "order":["time","routine","date_en","date_bn","countdown","event","status"],
        "background":existing.get("background",""),
        "chime_file":existing.get("chime_file",""),
        "birthday_chime_file":existing.get("birthday_chime_file",""),
        "elements":{
            "time":      {"size":82,"bold":True, "color":"#ffffff","alpha":255,"font":"","align":"center"},
            "routine":   {"size":22,"bold":False,"color":"#ffffff","alpha":200,"font":"","align":"center"},
            "date_en":   {"size":26,"bold":False,"color":"#ffffff","alpha":220,"font":"","align":"center"},
            "date_bn":   {"size":26,"bold":True, "color":"#ffffff","alpha":170,"font":"","align":"center"},
            "countdown": {"size":24,"bold":False,"color":"#ffffff","alpha":210,"font":"","align":"center"},
            "event":     {"size":19,"bold":False,"color":"#ffffff","alpha":190,"font":"","align":"center"},
            "status":    {"size":18,"bold":False,"color":"#ffffff","alpha":155,"font":"","align":"center"},
        }
    })
    save_json(ROUTINE_FILE,{})
    return jsonify({"ok":True})

@app.route("/api/test-chime", methods=["POST"])
def test_chime():
    s = load_json(SETTINGS_FILE, {})
    chime_path = s.get("chime_file", "")
    if not chime_path or not os.path.isfile(chime_path):
        for ext in ("wav", "mp3", "ogg"):
            p = f"{BASE_DIR}/chime.{ext}"
            if os.path.isfile(p): chime_path = p; break
    if not chime_path or not os.path.isfile(chime_path):
        return jsonify({"error": "No chime file found"}), 404
    try:
        env = {**os.environ, "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")}
        subprocess.Popen(["paplay", chime_path], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__=="__main__":
    os.makedirs(BASE_DIR,exist_ok=True); os.makedirs(FONTS_DIR,exist_ok=True)
    host=os.environ.get("PORTAL_HOST","0.0.0.0"); port=int(os.environ.get("PORTAL_PORT","5000"))
    print(f"Portal → http://{host}:{port}")
    app.run(host=host,port=port,debug=False)
