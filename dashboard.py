#!/usr/bin/env python3
"""
Pi Dashboard Clock — 800x480 (5" HDMI)
Vertical stacked layout. Per-element: horizontal align, font, size, color, opacity.
Order controlled by settings["order"] list.
"""
import sys, json, os, subprocess
from datetime import datetime, date
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtGui import (QPixmap, QPalette, QBrush, QColor, QPainter,
                          QLinearGradient, QFont, QFontDatabase)

BASE_DIR       = os.environ.get("DASHBOARD_DIR", os.path.expanduser("~/dashboard"))
SETTINGS_FILE  = f"{BASE_DIR}/settings.json"
REMINDERS_FILE = f"{BASE_DIR}/reminders.json"
ROUTINE_FILE   = f"{BASE_DIR}/routine.json"
FONTS_DIR      = f"{BASE_DIR}/fonts"

SCREEN_W, SCREEN_H = 800, 480

# ── Bangla calendar ───────────────────────────────────────────────────────────
BANGLA_MONTHS = [
    "বৈশাখ","জ্যৈষ্ঠ","আষাঢ়","শ্রাবণ",
    "ভাদ্র","আশ্বিন","কার্তিক","অগ্রহায়ণ",
    "পৌষ","মাঘ","ফাল্গুন","চৈত্র"
]
_BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
def to_bn(n): return str(n).translate(_BN)

def bangla_date(g: date) -> str:
    y, m, d = g.year, g.month, g.day
    by = (y-593) if (m>4 or (m==4 and d>=14)) else (y-594)
    bounds = [(4,14,0),(5,15,1),(6,15,2),(7,16,3),(8,16,4),(9,16,5),
              (10,16,6),(11,15,7),(12,15,8),(1,14,9),(2,13,10),(3,14,11)]
    bm, bd = 11, d
    for gm,gd,idx in bounds:
        if m==gm and d>=gd:  bm,bd=idx,d-gd+1; break
        elif m==gm:          bm=(idx-1)%12; bd=d+30-gd+1; break
    return f"{to_bn(bd)} {BANGLA_MONTHS[bm]}, {to_bn(by)} BS"

# ── Loaders ───────────────────────────────────────────────────────────────────
def load_json(path, default):
    try:
        with open(path) as f: return json.load(f)
    except: return default

def load_settings():  return load_json(SETTINGS_FILE,  {})
def load_reminders(): return load_json(REMINDERS_FILE, [])
def load_routine():   return load_json(ROUTINE_FILE,   {})

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_ORDER  = ["time","routine","date_en","date_bn","countdown","event","status"]
DEFAULT_ELEMENTS = {
    "time":      {"size":82,"bold":True, "color":"#ffffff","alpha":255,"font":"","align":"center"},
    "routine":   {"size":22,"bold":False,"color":"#ffffff","alpha":200,"font":"","align":"center"},
    "date_en":   {"size":26,"bold":False,"color":"#ffffff","alpha":220,"font":"","align":"center"},
    "date_bn":   {"size":26,"bold":True, "color":"#ffffff","alpha":170,"font":"","align":"center"},
    "countdown": {"size":24,"bold":False,"color":"#ffffff","alpha":210,"font":"","align":"center"},
    "event":     {"size":19,"bold":False,"color":"#ffffff","alpha":190,"font":"","align":"center"},
    "status":    {"size":18,"bold":False,"color":"#ffffff","alpha":155,"font":"","align":"center"},
}

ALIGN_MAP = {
    "left":   Qt.AlignLeft   | Qt.AlignVCenter,
    "center": Qt.AlignCenter,
    "right":  Qt.AlignRight  | Qt.AlignVCenter,
}

# ── Font cache ────────────────────────────────────────────────────────────────
_font_cache = {}
def get_qfont(font_name, size, bold):
    key = (font_name, size, bold)
    if key not in _font_cache:
        if font_name:
            path = os.path.join(FONTS_DIR, font_name)
            if os.path.isfile(path):
                fid = QFontDatabase.addApplicationFont(path)
                fams = QFontDatabase.applicationFontFamilies(fid)
                f = QFont(fams[0] if fams else "", size)
            else:
                f = QFont("", size)
        else:
            f = QFont("", size)
        f.setBold(bold)
        _font_cache[key] = f
    return _font_cache[key]

# ── Text helpers ──────────────────────────────────────────────────────────────
def countdown_text(hsc_str):
    try:
        hsc  = datetime.strptime(hsc_str, "%Y-%m-%d")
        days = (hsc - datetime.now()).days
        if days < 0:  return ""
        if days == 0: return "🎯  HSC Exam is TODAY!"
        return f"HSC Countdown  —  {days} days"
    except: return ""

def next_event_text(reminders):
    today     = date.today()
    today_str = today.isoformat()

    # Birthday (3 days)
    bday_msg = ""
    for r in reminders:
        if r.get("note") != "Birthday": continue
        raw = r.get("date","")
        if not raw: continue
        try:
            bday = date.fromisoformat(raw).replace(year=today.year)
            if bday < today: bday = bday.replace(year=today.year+1)
            dl = (bday-today).days
            name = r.get("title","").replace("🎂","").replace("Birthday","").strip().rstrip("'s").strip()
            if dl==0:          bday_msg=f"🎂  Happy Birthday, {name}! 🎉"; break
            elif dl<=3 and not bday_msg:
                bday_msg = f"🎂  {name}'s Birthday — {'Tomorrow!' if dl==1 else f'{dl} days'}"
        except: continue
    if bday_msg: return bday_msg

    # Anniversary (3 days)
    for r in reminders:
        if r.get("note") != "Anniversary": continue
        raw = r.get("date","")
        if not raw: continue
        try:
            aday = date.fromisoformat(raw).replace(year=today.year)
            if aday < today: aday = aday.replace(year=today.year+1)
            dl = (aday-today).days
            name = r.get("title","").replace("💍","").replace("Marriage Day","").replace("Anniversary","").strip().strip("-").strip()
            if dl==0:   return f"💍  Wish {name} on their Marriage Day! 🌸"
            elif dl==1: return f"💍  {name}'s Marriage Day — Tomorrow!"
            elif dl<=3: return f"💍  {name}'s Marriage Day — {dl} days"
        except: continue

    # Holiday (1 day)
    for r in reminders:
        if r.get("note") != "Public Holiday": continue
        raw = r.get("date","")
        if not raw: continue
        try:
            hday = date.fromisoformat(raw)
            dl = (hday-today).days
            title = r.get("title","")
            if dl==0:   return f"{title} Today! 🎉"
            elif dl==1: return f"{title} — Tomorrow!"
        except: continue

    # Regular
    upcoming = [r for r in reminders if r.get("date","") >= today_str]
    if not upcoming: return ""
    r = upcoming[0]
    if r.get("note") in ("Birthday","Anniversary","Public Holiday"):
        others = [x for x in upcoming if x.get("note") not in ("Birthday","Anniversary","Public Holiday")]
        if not others: return ""
        r = others[0]
    return "  ·  ".join(filter(None,[r.get("title"),r.get("date"),r.get("time")]))

def current_routine_block(routine, settings):
    now     = datetime.now()
    weekday = now.strftime("%A").lower()
    per_day = settings.get("routine_per_day", False)
    blocks  = routine.get(weekday if per_day else "everyday", [])
    if not blocks: return ""
    now_mins = now.hour*60 + now.minute
    current  = ""
    for block in blocks:
        try:
            h,m = map(int, block["start"].split(":"))
            start = h*60+m
            if block.get("end"):
                eh,em = map(int, block["end"].split(":"))
                end = eh*60+em
                if end == 0: end = 1440
                if start <= now_mins < end:
                    current = block.get("label","")
            else:
                if now_mins >= start:
                    current = block.get("label","")
        except: continue
    return current

# ── Audio ─────────────────────────────────────────────────────────────────────
def play_audio(chime_path):
    """Play audio via paplay (PipeWire-pulse). Fire-and-forget."""
    try:
        env = {**os.environ, "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")}
        subprocess.Popen(
            ["paplay", chime_path],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

# ── Gradient overlay ──────────────────────────────────────────────────────────
class Overlay(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setGeometry(0,0,SCREEN_W,SCREEN_H)
        self._pct = 55

    def set_opacity(self, pct):
        self._pct = pct; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        g = QLinearGradient(0,0,0,SCREEN_H)
        g.setColorAt(0.0, QColor(0,0,0, min(int(self._pct*0.30),255)))
        g.setColorAt(0.5, QColor(0,0,0, min(int(self._pct*0.90),255)))
        g.setColorAt(1.0, QColor(0,0,0, min(int(self._pct*2.30),255)))
        p.fillRect(self.rect(), g)

# ── Dashboard ─────────────────────────────────────────────────────────────────
class Dashboard(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard")
        self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.X11BypassWindowManagerHint)
        self.setFixedSize(SCREEN_W, SCREEN_H)
        self.move(0,0)

        self.settings  = load_settings()
        self.reminders = load_reminders()
        self.routine   = load_routine()
        self._last_min = -1

        self._apply_background()
        self._build_ui()

        QTimer(self, timeout=self._reload, interval=30_000).start()
        QTimer(self, timeout=self._tick,   interval=1_000).start()
        self._tick()

    # ── Background ────────────────────────────────────────────────────────────
    def _apply_background(self):
        bg  = self.settings.get("background", f"{BASE_DIR}/background.jpg")
        pix = QPixmap(bg)
        if pix.isNull():
            pix = QPixmap(SCREEN_W, SCREEN_H)
            pix.fill(QColor("#0d1b2a"))
        else:
            pix = pix.scaled(SCREEN_W, SCREEN_H,
                             Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        pal = QPalette()
        pal.setBrush(QPalette.Window, QBrush(pix))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.overlay = Overlay(self)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(36, 24, 36, 24)
        outer.setSpacing(0)
        outer.setAlignment(Qt.AlignVCenter)

        self._stack = QtWidgets.QVBoxLayout()
        self._stack.setSpacing(2)
        self._stack.setAlignment(Qt.AlignVCenter)
        outer.addLayout(self._stack)

        self._labels = {}
        for key in DEFAULT_ELEMENTS:
            lbl = QtWidgets.QLabel()
            lbl.setAttribute(Qt.WA_TranslucentBackground)
            lbl.setStyleSheet("background:transparent;")
            lbl.setWordWrap(False)
            self._labels[key] = lbl

        self._rebuild_order()
        self.overlay.raise_()
        for lbl in self._labels.values():
            lbl.raise_()

    def _rebuild_order(self):
        while self._stack.count():
            item = self._stack.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        order = self.settings.get("order", DEFAULT_ORDER)
        spacing_after = {"time": 8, "routine": 6, "date_bn": 10, "countdown": 4}

        for key in order:
            if key not in self._labels: continue
            self._stack.addWidget(self._labels[key])
            if key in spacing_after:
                self._stack.addSpacing(spacing_after[key])

        self._apply_element_styles()

    def _apply_element_styles(self):
        els = self.settings.get("elements", DEFAULT_ELEMENTS)
        for key, lbl in self._labels.items():
            cfg   = els.get(key, DEFAULT_ELEMENTS.get(key, {}))
            size  = cfg.get("size", 24)
            bold  = cfg.get("bold", False)
            color = cfg.get("color","#ffffff")
            alpha = cfg.get("alpha",255)
            fname = cfg.get("font","")
            align = cfg.get("align","center")

            c = QColor(color); c.setAlpha(alpha)
            pal = lbl.palette()
            pal.setColor(lbl.foregroundRole(), c)
            lbl.setPalette(pal)
            lbl.setFont(get_qfont(fname, size, bold))
            lbl.setAlignment(ALIGN_MAP.get(align, Qt.AlignCenter))

    # ── Reload ────────────────────────────────────────────────────────────────
    def _reload(self):
        self.settings  = load_settings()
        self.reminders = load_reminders()
        self.routine   = load_routine()
        self._apply_background()
        self.overlay.set_opacity(self.settings.get("overlay",55))
        self._rebuild_order()

    # ── Mute check ────────────────────────────────────────────────────────────
    def _is_muted(self, s, now):
        if s.get("chime_muted", False): return True
        mu = s.get("mute_until","")
        if mu:
            try:
                if now < datetime.fromisoformat(mu): return True
                else:
                    s["mute_until"]=""
                    with open(SETTINGS_FILE,"w") as f: json.dump(s,f,indent=2,ensure_ascii=False)
            except: pass
        qf = s.get("quiet_from",""); qt = s.get("quiet_to","")
        if qf and qt:
            try:
                nt=now.hour*60+now.minute
                ft=int(qf[:2])*60+int(qf[3:5])
                tt=int(qt[:2])*60+int(qt[3:5])
                if ft<=tt:
                    if ft<=nt<tt: return True
                else:
                    if nt>=ft or nt<tt: return True
            except: pass
        return False

    # ── Tick ──────────────────────────────────────────────────────────────────
    def _tick(self):
        now = datetime.now()
        qt  = QTime.currentTime()
        s   = self.settings

        def show(key, text, visible=True):
            lbl = self._labels.get(key)
            if lbl:
                lbl.setText(text)
                lbl.setVisible(visible and bool(text))

        # Time
        fmt = s.get("time_format","12")
        show("time",
             now.strftime("%H:%M") if fmt=="24"
             else now.strftime("%I:%M %p").lstrip("0"))

        # Routine
        block = current_routine_block(self.routine, s)
        show("routine", block)

        # English date
        show("date_en", now.strftime("%A, %d %B %Y"),
             s.get("show_date_en", True))

        # Bangla date
        show("date_bn", bangla_date(now.date()),
             s.get("show_date_bn", True))

        # Countdown
        cd = countdown_text(s.get("hsc_date","2026-06-20")) if s.get("show_countdown",True) else ""
        show("countdown", cd)

        # Event
        ev = next_event_text(self.reminders) if s.get("show_event",True) else ""
        show("event", f"⏰  {ev}" if ev else "")

        # Status
        show("status", s.get("status",""))

        # Chime
        m   = qt.minute()
        sec = qt.second()
        do_chime = False
        if s.get("chime",True):
            if m==0  and sec==0 and self._last_min!=0:  do_chime=True
            elif s.get("chime_half",False) and m==30 and sec==0 and self._last_min!=30: do_chime=True

        if do_chime and not self._is_muted(s, now):
            today = now.date()
            is_bday = any(
                r.get("note")=="Birthday" and
                r.get("date","").endswith(f"-{today.month:02d}-{today.day:02d}")
                for r in self.reminders
            )
            chime_path = ""
            if is_bday:
                chime_path = s.get("birthday_chime_file","")
                if not chime_path or not os.path.isfile(chime_path):
                    for ext in ("wav","mp3","ogg"):
                        c = f"{BASE_DIR}/birthday_chime.{ext}"
                        if os.path.isfile(c): chime_path=c; break
            if not chime_path or not os.path.isfile(chime_path):
                chime_path = s.get("chime_file","")
                if not chime_path or not os.path.isfile(chime_path):
                    for ext in ("wav","mp3","ogg"):
                        c = f"{BASE_DIR}/chime.{ext}"
                        if os.path.isfile(c): chime_path=c; break
            if chime_path and os.path.isfile(chime_path):
                play_audio(chime_path)

        self._last_min = m

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Escape, Qt.Key_Q):
            QtWidgets.QApplication.quit()
        elif e.key() == Qt.Key_F5:
            self._reload(); self._tick()


if __name__ == "__main__":
    os.makedirs(FONTS_DIR, exist_ok=True)
    app = QtWidgets.QApplication(sys.argv)
    win = Dashboard()
    win.show()
    sys.exit(app.exec_())
