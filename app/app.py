import streamlit as st
import streamlit.components.v1 as components
import sys
import os
import joblib
import pandas as pd
import random
import numpy as np
import io
from datetime import datetime
import base64
import re
import sqlite3
import matplotlib.pyplot as plt

# PDF (report generation)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# -----------------------------
# Paths
# -----------------------------
APP_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(APP_DIR, "assets")

# -----------------------------
# Local History Storage (uploaded PDFs)
# -----------------------------
HISTORY_DIR = os.path.join(APP_DIR, "history_files")
HISTORY_INDEX = os.path.join(HISTORY_DIR, "history_index.csv")
os.makedirs(HISTORY_DIR, exist_ok=True)

def _safe_name(s: str) -> str:
    s = (s or "").strip()
    keep = []
    for ch in s:
        if ch.isalnum() or ch in ("-", "_"):
            keep.append(ch)
        elif ch.isspace():
            keep.append("_")
    return "".join(keep)[:60] or "unknown"

def save_history_record(patient_id: str, uploaded_file, notes: str = ""):
    pid = _safe_name(patient_id) if patient_id else "unknown"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    file_name = uploaded_file.name if uploaded_file else ""
    ext = os.path.splitext(file_name)[1].lower() if file_name else ""
    stored_name = f"{pid}_{ts}{ext}" if ext else f"{pid}_{ts}.bin"
    stored_path = os.path.join(HISTORY_DIR, stored_name)

    with open(stored_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    header_needed = not os.path.exists(HISTORY_INDEX)
    row = pd.DataFrame([{
        "timestamp": ts,
        "patient_id": patient_id if patient_id else "",
        "original_name": file_name,
        "stored_name": stored_name,
        "notes": (notes or "")[:4000]
    }])

    if header_needed:
        row.to_csv(HISTORY_INDEX, index=False)
    else:
        row.to_csv(HISTORY_INDEX, mode="a", header=False, index=False)

def load_history_index():
    if not os.path.exists(HISTORY_INDEX):
        return pd.DataFrame(columns=["timestamp","patient_id","original_name","stored_name","notes"])
    try:
        return pd.read_csv(HISTORY_INDEX).fillna("")
    except Exception:
        return pd.DataFrame(columns=["timestamp","patient_id","original_name","stored_name","notes"])

def get_patient_history_files(patient_id: str):
    """Return rows from history_index.csv for one patient_id (latest first)."""
    df = load_history_index()
    if df.empty:
        return df

    pid = (patient_id or "").strip()
    if not pid:
        return df.iloc[0:0]

    df = df[df["patient_id"].astype(str).str.strip() == pid]
    df = df.sort_values("timestamp", ascending=False)
    return df
# -----------------------------
# SQLite DB (patient + visits)
# -----------------------------
DB_PATH = os.path.join(APP_DIR, "triage.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        patient_id TEXT PRIMARY KEY,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT,
        timestamp TEXT,
        age INTEGER,
        gender TEXT,
        bp INTEGER,
        hr INTEGER,
        temp REAL,
        symptom TEXT,
        pre_existing TEXT,
        risk TEXT,
        confidence REAL,
        department TEXT,
        priority TEXT,
        hospital_load INTEGER,
        est_wait INTEGER,
        pdf_note TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
    )
    """)

    conn.commit()
    conn.close()

def save_visit(patient_id, input_data, result_data, pdf_note=""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO patients (patient_id, created_at)
        VALUES (?, ?)
    """, (patient_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    cur.execute("""
        INSERT INTO visits (
            patient_id, timestamp, age, gender, bp, hr, temp, symptom, pre_existing,
            risk, confidence, department, priority, hospital_load, est_wait, pdf_note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        patient_id,
        input_data.get("timestamp",""),
        input_data.get("age", None),
        input_data.get("gender",""),
        input_data.get("bp", None),
        input_data.get("hr", None),
        input_data.get("temp", None),
        input_data.get("symptom",""),
        input_data.get("pre_existing",""),
        result_data.get("risk",""),
        float(result_data.get("confidence", 0.0)),
        result_data.get("department",""),
        result_data.get("priority",""),
        int(result_data.get("hospital_load", 0)),
        int(result_data.get("est_wait", 0)),
        (pdf_note or "")[:2000]
    ))

    conn.commit()
    conn.close()

def get_all_patients():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT patient_id, created_at FROM patients ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_recent_visits(limit=50):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT patient_id, timestamp, age, gender, bp, hr, temp, symptom, pre_existing,
               risk, confidence, department, priority, hospital_load, est_wait
        FROM visits
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def history_files_for_patient(patient_id: str):
    df = load_history_index()
    if df.empty:
        return df
    pid = (patient_id or "").strip()
    if not pid:
        return df.iloc[0:0]
    return df[df["patient_id"].astype(str).str.strip() == pid].sort_values("timestamp", ascending=False)
def get_patient_visits(patient_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT timestamp, risk, confidence, department, priority, symptom, pre_existing, bp, hr, temp, hospital_load, est_wait
        FROM visits
        WHERE patient_id = ?
        ORDER BY id DESC
    """, (patient_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_patient(patient_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Delete visits first (foreign key safety)
    cur.execute("DELETE FROM visits WHERE patient_id = ?", (patient_id,))
    cur.execute("DELETE FROM patients WHERE patient_id = ?", (patient_id,))

    conn.commit()
    conn.close()


def delete_visit(patient_id, timestamp):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM visits 
        WHERE patient_id = ? AND timestamp = ?
    """, (patient_id, timestamp))

    conn.commit()
    conn.close()
# -----------------------------
# UI helpers
# -----------------------------
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.stop()

def spacer(h=18):
    st.markdown(f"<div style='height:{h}px'></div>", unsafe_allow_html=True)

def set_bg_image_local(filename: str, page_key: str):
    path = os.path.join(ASSETS_DIR, filename)
    if not os.path.exists(path):
        return
    with open(path, "rb") as f:
        data = f.read()
    encoded = base64.b64encode(data).decode("utf-8")
    st.markdown(
        f"""
        <style>
        /* bg refresh key: {page_key} */
        .stApp {{
            background: url("data:image/jpg;base64,{encoded}") no-repeat center center fixed !important;
            background-size: cover !important;
        }}
        [data-testid="stAppViewContainer"] {{
            background: transparent !important;
        }}
        [data-testid="stAppViewContainer"] > .main {{
            background: transparent !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
def set_bg_video_local(filename: str, page_key: str, opacity: float = 0.30):
    path = os.path.join(ASSETS_DIR, filename)

    if not os.path.exists(path):
        st.warning(f"Background video not found: {path}")
        return

    with open(path, "rb") as f:
        data = f.read()

    encoded = base64.b64encode(data).decode("utf-8")

    st.markdown(
        f"""
        <style>
        /* bg video refresh key: {page_key} */

        /* 1) Put video fixed at very back */
        .bg-video-wrap {{
            position: fixed;
            top: 0; left: 0;
            width: 100vw;
            height: 100vh;
            overflow: hidden;
            z-index: -9999;   /* ✅ force behind everything */
        }}

        .bg-video-wrap video {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}

        /* 2) Keep Streamlit background transparent */
        .stApp {{
            background: transparent !important;
        }}
        [data-testid="stAppViewContainer"] {{
            background: transparent !important;
        }}
        [data-testid="stAppViewContainer"] > .main {{
            background: transparent !important;
            position: relative;
            z-index: 2;  /* ✅ UI ABOVE overlay */
        }}

        /* 3) Overlay ABOVE video but BELOW UI */
        .bg-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,{opacity});
            z-index: -9998;  /* ✅ above video, below everything else */
            pointer-events: none;
        }}
        </style>

        <div class="bg-video-wrap">
            <video autoplay muted loop playsinline>
                <source src="data:video/mp4;base64,{encoded}" type="video/mp4">
            </video>
        </div>
        <div class="bg-overlay"></div>
        """,
        unsafe_allow_html=True
    )

def typed_int(label, default=""):
    val = st.text_input(label, value=str(default))
    try:
        return int(val), None
    except:
        return None, f"Enter a valid number for {label}"

def typed_float(label, default=""):
    val = st.text_input(label, value=str(default))
    try:
        return float(val), None
    except:
        return None, f"Enter a valid number for {label}"

def extract_pdf_text(uploaded_file) -> str:
    try:
        from PyPDF2 import PdfReader
    except Exception:
        return ""
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
        return text.strip()
    except Exception:
        return ""

# -----------------------------
# Fix import path for utils
# -----------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.risk_rules import apply_safety_rules
from utils.department_engine import route_patient
from utils.explainability import get_feature_importance
from utils.translator import translate

# -----------------------------
# Load model
# -----------------------------
MODEL_PATH = "../models/risk_model.pkl"
ENCODER_PATH = "../models/label_encoders.pkl"
model = joblib.load(MODEL_PATH)
encoders = joblib.load(ENCODER_PATH)

# -----------------------------
# App config + CSS
# -----------------------------
st.set_page_config(page_title="Triage AI", layout="centered")
init_db()

st.markdown("""
<style>
            /* ===== HERO TITLE UPGRADE ===== */

.big-title{
  font-size: 72px !important;
  font-weight: 900 !important;
  text-align: center !important;
  width: 100% !important;
  margin: 0 auto 18px auto !important;
  background: linear-gradient(90deg,#1e3a8a,#2563eb,#06b6d4) !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
}

.subtitle {
  text-align: center;
  font-size: 25px;
  font-weight: 500;
  color: #cbd5e1;
  letter-spacing: 0.5px;
  margin-bottom: 25px;
}

/* Soft glow effect */
.hero-glow {
  text-align: center;
  font-size: 20px;
  color: #38bdf8;
  margin-top: 6px;
  font-weight: 600;
  opacity: 0.9;
}
            /* Center content block on home */
.home-wrap{
  display:flex;
  justify-content:center;
  align-items:center;
  flex-direction:column;
  gap:14px;
}
/* HOME BUTTONS CENTER + SIZE */
.home-center{
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  gap:16px;
  margin-top:20px;
  width:100%;
}

.home-center div.stButton{
  width:100%;
  display:flex;
  justify-content:center;
}

.home-center div.stButton > button{
  width: 340px !important;       /* little bigger */
  height: 60px !important;       /* thicker */
  border-radius: 16px !important;
  font-size: 20px !important;    /* ✅ BIGGER TEXT */
  font-weight: 900 !important;
  letter-spacing: 0.4px !important;
  background: rgba(15,23,42,0.9) !important;
  color: white !important;
  border: 1px solid rgba(255,255,255,0.18) !important;
  box-shadow: 0 12px 28px rgba(0,0,0,0.28) !important;
}

.home-center div.stButton > button:hover{
  transform: translateY(-1px);
  background: rgba(30,41,59,0.92) !important;
  border: 1px solid rgba(56,189,248,0.35) !important;
}

[data-testid="stDecoration"] {display:none !important;}
header[data-testid="stHeader"] {display:none !important;}
div[data-testid="stToolbar"] {display:none !important;}
#MainMenu {visibility:hidden !important;}
footer {visibility:hidden !important;}

hr { display:none !important; }
[data-testid="stDivider"] { display:none !important; }
[data-testid="stMarkdownContainer"] hr { display:none !important; }

.main .block-container{
  padding-top: 1.6rem !important;
  padding-bottom: 2rem !important;
  max-width: 950px;
}


.card{
  background: rgba(255,255,255,0.93);
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 15px 40px rgba(0,0,0,0.25);
  backdrop-filter: blur(12px);
}
.small-muted{ color:#455a64; font-size:14px; }


a[data-testid="stMarkdownContainer"] svg{ display:none !important; }
.center-wrap{
  max-width: 980px;
  margin: 0 auto;
}

.patient-tile{
  background: rgba(255,255,255,0.94);
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 14px 40px rgba(0,0,0,0.20);
  border-left: 10px solid #64748b;
}

.badge{
  display:inline-block;
  padding:6px 12px;
  border-radius:999px;
  font-weight:800;
  font-size:13px;
  color:white;
}

.notice {
  padding: 12px 14px;
  border-radius: 12px;
  margin-top: 10px;
  margin-bottom: 10px;
  font-weight: 700;
  color: #0b1f2a;
  background: rgba(255,255,255,0.92);
  border: 1px solid rgba(255,255,255,0.35);
  box-shadow: 0 8px 24px rgba(0,0,0,0.18);
}
.notice-ok { border-left: 10px solid #22c55e; }
.notice-info { border-left: 10px solid #3b82f6; }
.notice-warn { border-left: 10px solid #f59e0b; }
/* ✅ FORCE readable text inside cards (fix invisible text) */
.card, .card * {
  color: #0f172a !important;
}

.card b { 
  color: #0f172a !important;
  font-weight: 900 !important;
}

.card .small-muted {
  color: #475569 !important;
}
/* ===== HOME BUTTONS: TRUE CENTER + SAME SIZE ===== */
.home-btns {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 18px;
}

.home-btns > div {
  width: 100%;
  display: flex;
  justify-content: center;
}

.home-btns div.stButton {
  width: auto !important;
  display: flex;
  justify-content: center;
}

.home-btns div.stButton > button {
  width: 460px !important;    /* ✅ change size here */
  height: 68px !important;    /* ✅ change size here */
  font-size: 22px !important; /* ✅ button text size */
  font-weight: 900 !important;
  border-radius: 18px !important;
  background: rgba(15,23,42,0.92) !important;
  color: white !important;
  border: 1px solid rgba(255,255,255,0.18) !important;
  box-shadow: 0 14px 32px rgba(0,0,0,0.30) !important;
}

.home-btns div.stButton > button:hover {
  transform: translateY(-2px);
  background: rgba(30,41,59,0.95) !important;
  border: 1px solid rgba(56,189,248,0.35) !important;
}
/* HOME buttons only (by key) */
button[key="home_new"], button[key="home_history"]{
  height: 120px !important;
  font-size: 50px !important;
  font-weight: 1300 !important;
  border-radius: 18px !important;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Session state
# -----------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"
if "language" not in st.session_state:
    st.session_state.language = "English"
if "input_data" not in st.session_state:
    st.session_state.input_data = {}
if "visit_saved_key" not in st.session_state:
    st.session_state.visit_saved_key = ""

# ==========================================================
# PAGE 1: HOME
# ==========================================================
# -----------------------------
# GLOBAL BACKGROUND VIDEO
# -----------------------------
current_page = st.session_state.get("page", "home")

if current_page == "home":
    set_bg_video_local("a.mp4", "HOMEVID")
elif current_page == "patient_input":
    set_bg_image_local("input.jpg", "INPUTVID")
elif current_page == "results":
    set_bg_video_local("results.mp4", "RESULTVID")
elif current_page == "history":
    set_bg_image_local("results.jpg", "HISTORYVID")
elif current_page == "patient_file":
    set_bg_image_local("results.jpg", "PATIENT_FILE")
else:
    set_bg_video_local("results.mp4", "DEFAULTVID")

if st.session_state.page == "home":
    #set_bg_video_local("a.mp4", "HOME", opacity=0.25)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="big-title">🩺 Triage AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Explainable • Responsible • AI-Powered Clinical Triage</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-glow">⚡ Real-time Decision Support for Hospitals</div>', unsafe_allow_html=True)

    language = st.selectbox("🌍 Language", ["English", "Hindi", "Telugu", "Tamil", "Kannada"], key="lang_home")
    st.session_state.language = language

    spacer(12)

# ---- PERFECT CENTER BUTTONS (Streamlit-safe) ----
    left, mid, right = st.columns([1.6, 1.1, 1.6])  # adjust ratios to control width

    with mid:
        if st.button("➕ New Patient", key="home_new", use_container_width=True):
            st.session_state.page = "patient_input"
            safe_rerun()

        spacer(10)

        if st.button("📂 View Patient History", key="home_history", use_container_width=True):
            st.session_state.page = "history"
            safe_rerun()

# ==========================================================
# PAGE 2: PATIENT INPUT
# ==========================================================
elif st.session_state.page == "patient_input":
    #set_bg_image_local("input.jpg", "INPUT")
    language = st.session_state.language

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Patient Intake")
    st.markdown('<div class="small-muted">Enter patient details for triage assessment.</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    spacer(14)

    errors = []
    default_bp = 120
    default_hr = 80
    default_temp = 98.6

    col1, col2 = st.columns(2)

    with col1:
        age, e = typed_int(translate("Age", language), default=30)
        if e: errors.append(e)

        gender = st.selectbox(translate("Gender", language), ["Male", "Female"])

        bp, e = typed_int(translate("Blood Pressure", language), default=default_bp)
        if e: errors.append(e)

        hr, e = typed_int(translate("Heart Rate", language), default=default_hr)
        if e: errors.append(e)

    with col2:
        temp, e = typed_float(translate("Temperature", language), default=default_temp)
        if e: errors.append(e)

        symptom = st.selectbox(
            translate("Symptoms", language),
            ["Chest Pain", "Seizure", "Shortness of Breath", "Severe Headache", "Fever", "Cough"]
        )

        pre_existing = st.selectbox(
            translate("Pre-Existing Condition", language),
            ["None", "Diabetes", "Hypertension", "Heart Disease", "Asthma"]
        )

        patient_id = st.text_input("Patient ID (optional)", value="")

    spacer(10)
    uploaded_file = st.file_uploader("Upload Past Medical Report (PDF)", type=["pdf"])

    detected = {}
    pdf_text = ""

    if uploaded_file is not None:
        pdf_text = extract_pdf_text(uploaded_file)
        st.session_state["uploaded_pdf_bytes"] = uploaded_file.getvalue()
        st.session_state["uploaded_pdf_name"] = uploaded_file.name
        st.session_state["uploaded_pdf_text"] = pdf_text

        if not pdf_text:
            st.markdown('<div class="notice notice-warn">⚠️ This PDF looks scanned (no readable text). OCR needed.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="notice notice-ok">✅ PDF text found — I can read details from this report.</div>', unsafe_allow_html=True)

            bp_match = re.search(r'(\d{2,3})\s*/\s*(\d{2,3})', pdf_text)
            hr_match = re.search(r'(heart\s*rate|hr)\s*[:\-]?\s*(\d{2,3})', pdf_text, re.I)
            temp_match = re.search(r'(temperature|temp)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)', pdf_text, re.I)

            if bp_match:
                detected["BP"] = f"{bp_match.group(1)}/{bp_match.group(2)}"
            if hr_match:
                detected["HR"] = hr_match.group(2)
            if temp_match:
                detected["Temp"] = temp_match.group(2)

            if detected:
                st.markdown(
                    '<div class="notice notice-info">ℹ️ Detected from PDF (best-effort): '
                    + "  |  ".join([f"{k}: {v}" for k, v in detected.items()])
                    + "</div>",
                    unsafe_allow_html=True
                )

            colx, coly = st.columns(2)
            with colx:
                if st.button("📄 View Report (Full PDF)", use_container_width=True):
                    st.session_state.page = "report_view"
                    safe_rerun()
            with coly:
                if st.button("🧾 View Extracted Text", use_container_width=True):
                    st.session_state.page = "report_text"
                    safe_rerun()

    history_notes = st.text_area(
        "Quick Notes (optional) – allergies / diabetes / surgeries / meds",
        value="",
        key="history_notes"
    )

    spacer(12)
    colA, colB = st.columns(2)

    with colA:
        if st.button("⬅ Back to Home", use_container_width=True):
            st.session_state.page = "home"
            safe_rerun()

    with colB:
        if st.button("✅ Analyze", use_container_width=True):
            if errors:
                st.error(" | ".join(errors))
            else:
                st.session_state.input_data = {
                    "patient_id": patient_id.strip(),
                    "age": age,
                    "gender": gender,
                    "bp": bp,
                    "hr": hr,
                    "temp": temp,
                    "symptom": symptom,
                    "pre_existing": pre_existing,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                if uploaded_file is not None:
                    save_history_record(
                        patient_id=patient_id.strip(),
                        uploaded_file=uploaded_file,
                        notes=history_notes.strip()
                    )

                st.session_state.page = "results"
                safe_rerun()

# ==========================================================
# PAGE 3: RESULTS
# ==========================================================
elif st.session_state.page == "results":
    #set_bg_video_local("results.mp4", "RESULTVID")
    language = st.session_state.language
    input_data = st.session_state.get("input_data", {})

    if not input_data:
        st.warning("No patient data found. Please enter details again.")
        if st.button("⬅ Back to Patient Intake", use_container_width=True):
            st.session_state.page = "patient_input"
            safe_rerun()
        st.stop()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Triage Assessment Dashboard")
    st.markdown('<div class="small-muted">Decision support output for hospital triage workflow.</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    override = apply_safety_rules(
        input_data["age"], input_data["bp"], input_data["hr"],
        input_data["temp"], input_data["symptom"], input_data["pre_existing"]
    )

    gender_encoded = encoders["gender"].transform([input_data["gender"]])[0]
    symptom_encoded = encoders["symptom"].transform([input_data["symptom"]])[0]
    condition_encoded = encoders["pre_existing"].transform([input_data["pre_existing"]])[0]

    input_df = pd.DataFrame([{
        "age": input_data["age"],
        "gender": gender_encoded,
        "bp": input_data["bp"],
        "hr": input_data["hr"],
        "temp": input_data["temp"],
        "symptom": symptom_encoded,
        "pre_existing": condition_encoded
    }])

    if override:
        final_risk = override
        confidence = 1.0
        probabilities = None
    else:
        pred = model.predict(input_df)[0]
        probabilities = model.predict_proba(input_df)[0]
        final_risk = encoders["risk"].inverse_transform([pred])[0]
        confidence = float(max(probabilities))

    confidence_percent = round(confidence * 100, 2)
    translated_risk = translate(final_risk, language)

    routing_info = route_patient(final_risk, input_data["symptom"], input_data["pre_existing"])
    hospital_load = random.randint(20, 100)
    adjusted_wait = int(routing_info["estimated_wait"] * (1 + hospital_load / 100))
    translated_minutes = translate("minutes", language)

    pid = (input_data.get("patient_id") or "").strip()
    if not pid:
        pid = f"PAT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    input_data["patient_id"] = pid

    # ✅ prevent duplicate DB save on reruns
    save_key = f"{pid}-{input_data.get('timestamp','')}"
    if st.session_state.visit_saved_key != save_key:
        result_data = {
            "risk": final_risk,
            "confidence": confidence_percent,
            "department": routing_info["department"],
            "priority": routing_info["priority"],
            "hospital_load": hospital_load,
            "est_wait": adjusted_wait
        }
        pdf_note = st.session_state.get("uploaded_pdf_text", "")
        save_visit(pid, input_data, result_data, pdf_note=pdf_note)
        st.session_state.visit_saved_key = save_key

    spacer(14)
    c1, c2, c3 = st.columns(3)
    c1.metric(label=translate("Risk Level", language), value=f"{translated_risk}", delta=f"{confidence_percent}% confidence")
    c2.metric(label=translate("Department", language), value=routing_info["department"])
    c3.metric(label=translate("Priority", language), value=translate(routing_info["priority"], language))

    risk_color = {"Low":"#22c55e", "Medium":"#f59e0b", "High":"#ef4444"}
    risk_hex = risk_color.get(final_risk, "#64748b")

    spacer(12)
    st.markdown(f"""
    <div class="card" style="border-left: 12px solid {risk_hex}; color:#102027;">
      <h2 style="margin:0; font-weight:900; color:#0f172a;">Triage Decision</h2>
      <div style="margin-top:12px; font-size:18px;">
        <b>Risk:</b>
        <span style="background:{risk_hex}; color:white; padding:6px 12px; border-radius:999px; font-weight:800;">
          {final_risk}
        </span>
        &nbsp;&nbsp; <b>Confidence:</b> {confidence_percent}%
      </div>
      <div style="margin-top:10px; font-size:16px;">
        <b>Department:</b> {routing_info["department"]}
        &nbsp; • &nbsp;
        <b>Priority:</b> {routing_info["priority"]}
      </div>
    </div>
    """, unsafe_allow_html=True)

    spacer(12)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Hospital Status")
    st.write(f"**Hospital Load:** {hospital_load}%")
    st.write(f"**{translate('Estimated Wait Time', language)}:** {adjusted_wait} {translated_minutes}")
    st.markdown("</div>", unsafe_allow_html=True)

    # Clinical drivers
    spacer(12)
    st.markdown("### Clinical Drivers")
    feature_names = ["age", "gender", "bp", "hr", "temp", "symptom", "pre_existing"]
    top_features = get_feature_importance(model, feature_names, top_n=5)

    driver_color = {
        "hr": "#ef4444", "temp": "#f97316", "symptom": "#f59e0b",
        "age": "#3b82f6", "bp": "#14b8a6", "gender": "#64748b", "pre_existing": "#8b5cf6"
    }

    st.markdown('<div class="card">', unsafe_allow_html=True)
    for item in top_features:
        feature = item["feature"]
        importance = round(item["importance"] * 100, 1)
        color = driver_color.get(feature, "#334155")
        st.markdown(f"""
        <div style="margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between;">
                <span style="font-weight:700;">{feature.upper()}</span>
                <span style="font-weight:700;">{importance}% influence</span>
            </div>
            <div style="height:8px;background:#e2e8f0;border-radius:8px;overflow:hidden;">
                <div style="width:{importance}%;height:8px;background:{color};border-radius:8px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Fairness
    spacer(12)
    st.subheader("Fairness Monitoring")
    male_encoded = encoders["gender"].transform(["Male"])[0]
    female_encoded = encoders["gender"].transform(["Female"])[0]
    base_array = input_df.values[0]
    male_array = base_array.copy()
    female_array = base_array.copy()
    male_array[1] = male_encoded
    female_array[1] = female_encoded
    male_pred = model.predict([male_array])[0]
    female_pred = model.predict([female_array])[0]
    fairness_flag = (male_pred != female_pred)
    if fairness_flag:
        st.warning("Potential gender bias detected ⚠️ (same vitals, different gender produced different outcome)")
    else:
        st.success("No gender bias detected ✅ (same vitals produced same outcome across gender toggle)")

    # PDF Download (same as your old version)
    def fig_to_png_bytes(fig):
        img_buf = io.BytesIO()
        fig.savefig(img_buf, format="png", dpi=200, bbox_inches="tight")
        plt.close(fig)
        img_buf.seek(0)
        return img_buf

    def generate_pdf_report():
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("TRIAGE AI - PATIENT TRIAGE REPORT", styles["Title"]))
        story.append(Paragraph(f"Generated: {input_data.get('timestamp','')}", styles["Normal"]))
        story.append(Spacer(1, 12))

        pid_show = input_data.get("patient_id", "") or "N/A"
        patient_table = [
            ["Patient ID", pid_show],
            ["Age", str(input_data["age"])],
            ["Gender", input_data["gender"]],
            ["Symptom", input_data["symptom"]],
            ["Pre-existing Condition", input_data["pre_existing"]],
        ]
        t = Table(patient_table, colWidths=[170, 330])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("FONTSIZE", (0,0), (-1,-1), 10),
        ]))
        story.append(Paragraph("Patient Details", styles["Heading2"]))
        story.append(t)
        story.append(Spacer(1, 12))

        vitals_table = [
            ["Blood Pressure", str(input_data["bp"])],
            ["Heart Rate", str(input_data["hr"])],
            ["Temperature", str(input_data["temp"])],
        ]
        t2 = Table(vitals_table, colWidths=[170, 330])
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("FONTSIZE", (0,0), (-1,-1), 10),
        ]))
        story.append(Paragraph("Vitals", styles["Heading2"]))
        story.append(t2)
        story.append(Spacer(1, 12))

        story.append(Paragraph("Triage Output", styles["Heading2"]))
        res_table = [
            ["Risk Level", f"{final_risk} ({confidence_percent}%)"],
            ["Department", routing_info["department"]],
            ["Priority", routing_info["priority"]],
            ["Hospital Load", f"{hospital_load}%"],
            ["Estimated Wait Time", f"{adjusted_wait} minutes"],
            ["Safety Override", "YES" if override else "NO"],
            ["Fairness (Gender Toggle)", "POTENTIAL BIAS" if fairness_flag else "NO BIAS FLAG"],
        ]
        t3 = Table(res_table, colWidths=[170, 330])
        t3.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("FONTSIZE", (0,0), (-1,-1), 10),
        ]))
        story.append(t3)
        story.append(Spacer(1, 12))

        story.append(Paragraph(
            "Disclaimer: This report is decision-support output generated from synthetic-data-trained ML + safety rules. "
            "Not a substitute for clinical judgement.",
            styles["Italic"]
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    spacer(12)
    st.subheader("Download Report")
    st.download_button(
        label="⬇ Download PDF Report",
        data=generate_pdf_report(),
        file_name=f"triage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    spacer(12)
    col_back, col_new = st.columns(2)
    with col_back:
        if st.button("⬅ Return to Home", use_container_width=True):
            st.session_state.page = "home"
            safe_rerun()
    with col_new:
        if st.button("➕ New Patient", use_container_width=True):
            st.session_state.page = "patient_input"
            st.session_state.input_data = {}
            st.session_state.visit_saved_key = ""
            safe_rerun()

# ==========================================================
# PAGE: REPORT VIEW (PDF iframe)
# ==========================================================
elif st.session_state.page == "report_view":
    #set_bg_image_local("input.jpg", "REPORT_VIEW")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Past Medical Report Viewer")
    st.markdown('<div class="small-muted">Full PDF view for doctor/nurse verification.</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    pdf_bytes = st.session_state.get("uploaded_pdf_bytes", b"")
    pdf_name = st.session_state.get("uploaded_pdf_name", "report.pdf")

    if not pdf_bytes:
        st.markdown('<div class="notice notice-warn">⚠️ No PDF found. Upload again in Patient Intake.</div>', unsafe_allow_html=True)
    else:
        st.download_button("⬇ Download PDF", data=pdf_bytes, file_name=pdf_name, mime="application/pdf", use_container_width=True)
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        components.html(
            f"""
            <iframe 
              src="data:application/pdf;base64,{pdf_base64}" 
              width="100%" 
              height="720" 
              style="border:none; border-radius:14px; overflow:hidden; background:white;">
            </iframe>
            """,
            height=740
        )

    spacer(10)
    if st.button("⬅ Back to Patient Intake", use_container_width=True):
        st.session_state.page = "patient_input"
        safe_rerun()

# ==========================================================
# PAGE: REPORT TEXT (ONLY extracted text)
# ==========================================================
elif st.session_state.page == "report_text":
    #set_bg_image_local("input.jpg", "REPORT_TEXT")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Extracted Report Text")
    st.markdown('<div class="small-muted">For doctor/nurse quick verification.</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    text = st.session_state.get("uploaded_pdf_text", "")
    if not text:
        st.markdown('<div class="notice notice-warn">⚠️ No text found. PDF may be scanned.</div>', unsafe_allow_html=True)
    else:
        st.text_area("Extracted Text", value=text, height=650)

    spacer(10)
    colA, colB = st.columns(2)
    with colA:
        if st.button("⬅ Back to Patient Intake", use_container_width=True):
            st.session_state.page = "patient_input"
            safe_rerun()
    with colB:
        if st.button("📊 Go to Triage Dashboard", use_container_width=True):
            st.session_state.page = "results"
            safe_rerun()

# ==========================================================
# PAGE 4: HISTORY (Doctor View)
# ==========================================================
elif st.session_state.page == "history":
    #set_bg_image_local("results.jpg", "HISTORY")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## 🩺 Patient Records Dashboard")
    st.markdown('<div class="small-muted">Search patients • view visits • download uploaded history files</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    spacer(12)

    # ---- Search + Filters ----
    colS1, colS2, colS3 = st.columns([2,1,1])
    with colS1:
        query = st.text_input("🔎 Search Patient ID", value="")
    with colS2:
        max_patients = st.selectbox("Patients", [10, 20, 50, 100], index=2)
    with colS3:
        max_visits = st.selectbox("Visits", [10, 20, 50, 100], index=2)

    patients = get_all_patients()
    visits = get_recent_visits(limit=max_visits)

    # optional: if you want “max_patients”
    patients = patients[:max_patients]

    # If search typed, filter both lists
    if query.strip():
        q = query.strip().lower()
        patients = [p for p in patients if (p[0] or "").lower().find(q) != -1]
        visits = [v for v in visits if (v[0] or "").lower().find(q) != -1]

    spacer(10)

    tab1, tab2 = st.tabs(["👤 Patients", "🧾 Recent Visits"])

    # ========== TAB 1: Patients ==========
    with tab1:
        st.markdown('<div class="center-wrap">', unsafe_allow_html=True)

        if not patients:
            st.markdown('<div class="notice notice-warn">⚠️ No patients found.</div>', unsafe_allow_html=True)
        else:
            cols = st.columns(3, gap="large")

            for i, (patient_id, created_at) in enumerate(patients):
                pid = patient_id or "Unknown"

                # Pull last visit for badge + preview
                p_visits = get_patient_visits(pid)
                last = p_visits[0] if p_visits else None

                # last visit fields:
                # timestamp, risk, confidence, department, priority, symptom, pre_existing, bp, hr, temp, hospital_load, est_wait
                last_risk = last[1] if last else "N/A"
                last_conf = float(last[2]) if last else 0.0
                last_dept = last[3] if last else "—"
                last_prio = last[4] if last else "—"

                risk_color = {"Low":"#22c55e", "Medium":"#f59e0b", "High":"#ef4444"}
                risk_hex = risk_color.get(last_risk, "#64748b")

                with cols[i % 3]:
                    st.markdown(
                        f"""
                        <div class="patient-tile" style="border-left-color:{risk_hex};">
                        <div style="display:flex; justify-content:space-between; align-items:center; gap:10px;">
                            <div style="font-size:18px; font-weight:900;">🧑‍⚕️ {pid}</div>
                            <span class="badge" style="background:{risk_hex};">{last_risk}</span>
                        </div>

                        <div class="small-muted" style="margin-top:6px;">
                            Registered: {created_at}
                        </div>

                        <div style="margin-top:10px; font-size:14px; line-height:1.6;">
                            <b>Dept:</b> {last_dept} &nbsp;•&nbsp; <b>Priority:</b> {last_prio}<br>
                            <b>Confidence:</b> {round(last_conf, 2)}%
                        </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if st.button("📂 Open Patient File", key=f"open_{pid}", use_container_width=True):
                        st.session_state.selected_patient = pid
                        st.session_state.page = "patient_file"
                        safe_rerun()

        st.markdown("</div>", unsafe_allow_html=True)
    # ========== TAB 2: Recent Visits ==========
    with tab2:
        if not visits:
            st.markdown('<div class="notice notice-warn">⚠️ No visits found.</div>', unsafe_allow_html=True)
        else:
            for v in visits[:20]:
                (pid, ts, age, gender, bp, hr, temp, symptom, cond,
                 risk, conf, dept, prio, load, wait) = v

                badge = "#64748b"
                if risk == "Low": badge = "#22c55e"
                elif risk == "Medium": badge = "#f59e0b"
                elif risk == "High": badge = "#ef4444"

                st.markdown(f"""
                <div class="card" style="border-left:10px solid {badge}; margin-bottom:12px;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                      <b>Patient:</b> {pid} <br>
                      <span class="small-muted">{ts}</span>
                    </div>
                    <div style="background:{badge}; color:white; padding:6px 12px; border-radius:999px; font-weight:900;">
                      {risk} ({round(float(conf),2)}%)
                    </div>
                  </div>

                  <div style="margin-top:10px;">
                    <b>Age/Gender:</b> {age} / {gender} &nbsp; • &nbsp;
                    <b>Vitals:</b> BP {bp} | HR {hr} | Temp {temp}
                  </div>
                  <div style="margin-top:8px;">
                    <b>Symptom:</b> {symptom} &nbsp; • &nbsp; <b>Condition:</b> {cond}
                  </div>
                  <div style="margin-top:8px;">
                    <b>Routing:</b> {dept} • {prio} &nbsp; | &nbsp; <b>Load:</b> {load}% • <b>Wait:</b> {wait} min
                  </div>
                </div>
                """, unsafe_allow_html=True)

    spacer(12)
    if st.button("⬅ Back to Home", use_container_width=True):
        st.session_state.page = "home"
        safe_rerun()

elif st.session_state.page == "patient_file":
    

    pid = st.session_state.get("selected_patient", "").strip()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"## 📁 Patient File: {pid}")
    st.markdown('<div class="small-muted">Complete triage history and uploaded reports for doctor/nurse.</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    spacer(10)

    # Top nav buttons (unique keys to avoid duplicate ID error)
    nav1, nav2 = st.columns(2)
    with nav1:
        if st.button("← Back to Dashboard", use_container_width=True, key=f"pf_back_{pid}"):
            st.session_state.page = "history"
            safe_rerun()
    with nav2:
        if st.button("🏠 Home", use_container_width=True, key=f"pf_home_{pid}"):
            st.session_state.page = "home"
            safe_rerun()

    spacer(10)

    # Tabs: Visits + Reports
    tabV, tabR = st.tabs(["🩺 Visits", "📄 Uploaded Reports"])

    # -------------------------
    # TAB 1: VISITS
    # -------------------------
    with tabV:
        visits = get_patient_visits(pid)

        # -----------------------------
    # Uploaded Medical History (PDFs)
    # -----------------------------
    spacer(10)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📎 Uploaded Medical History")
    st.markdown('<div class="small-muted">Reports uploaded during intake for this patient.</div>', unsafe_allow_html=True)

    df_files = get_patient_history_files(pid)

    if df_files.empty:
        st.markdown('<div class="notice notice-warn">⚠️ No uploaded reports found for this patient.</div>', unsafe_allow_html=True)
    else:
        for idx, row in df_files.iterrows():
            ts = row.get("timestamp", "")
            orig = row.get("original_name", "report.pdf") or "report.pdf"
            notes = row.get("notes", "") or ""
            stored = row.get("stored_name", "") or ""

            stored_path = os.path.join(HISTORY_DIR, stored)

            with st.expander(f"📄 {orig}  •  {ts}"):
                if notes:
                    st.markdown(f"**Notes:** {notes}")

                if os.path.exists(stored_path):
                    with open(stored_path, "rb") as f:
                        data = f.read()

                    # download
                    st.download_button(
                        "⬇ Download Report",
                        data=data,
                        file_name=orig,
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"dl_{pid}_{stored}"
                    )

                    # open viewer
                    if st.button("👁 Open Report", use_container_width=True, key=f"openpdf_{pid}_{stored}"):
                        st.session_state["uploaded_pdf_bytes"] = data
                        st.session_state["uploaded_pdf_name"] = orig
                        st.session_state.page = "report_view"
                        safe_rerun()
                else:
                    st.markdown('<div class="notice notice-warn">⚠️ Stored file missing on server.</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------
    # TAB 2: REPORTS
    # -------------------------
    with tabR:
        df_rep = get_patient_history_files(pid)

        if df_rep.empty:
            st.markdown('<div class="notice notice-warn">⚠️ No uploaded reports found for this patient.</div>', unsafe_allow_html=True)
        else:
            for i, row in df_rep.iterrows():
                ts = row.get("timestamp", "")
                orig = row.get("original_name", "report.pdf")
                notes = row.get("notes", "")
                stored_name = row.get("stored_name", "")

                stored_path = os.path.join(HISTORY_DIR, stored_name)

                st.markdown('<div class="card" style="margin-bottom:12px;">', unsafe_allow_html=True)
                st.markdown(f"**📄 {orig}**  \n<span class='small-muted'>Uploaded: {ts}</span>", unsafe_allow_html=True)
                if notes:
                    st.markdown(f"<div class='small-muted' style='margin-top:6px;'><b>Notes:</b> {notes}</div>", unsafe_allow_html=True)

                if os.path.exists(stored_path):
                    with open(stored_path, "rb") as f:
                        st.download_button(
                            "⬇ Download Report",
                            data=f.read(),
                            file_name=orig,
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"dl_{pid}_{ts}_{i}"
                        )
                else:
                    st.markdown('<div class="notice notice-warn">⚠️ Stored file missing.</div>', unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

    spacer(14)

    # -------------------------
    # Professional delete section (NOT on home/dashboard)
    # -------------------------
    st.markdown('<div class="card" style="border-left: 10px solid #ef4444;">', unsafe_allow_html=True)
    st.markdown("### 🗑 Delete Patient Record")
    st.markdown('<div class="small-muted">This permanently deletes this patient and all associated visits.</div>', unsafe_allow_html=True)

    # confirmation toggle
    confirm_key = f"confirm_delete_{pid}"
    if confirm_key not in st.session_state:
        st.session_state[confirm_key] = False

    spacer(8)

    if not st.session_state[confirm_key]:
        if st.button("Delete Patient", use_container_width=True, key=f"btn_delete_{pid}"):
            st.session_state[confirm_key] = True
            safe_rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Confirm Delete", use_container_width=True, key=f"btn_confirm_{pid}"):
                # delete visits then patient
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("DELETE FROM visits WHERE patient_id = ?", (pid,))
                cur.execute("DELETE FROM patients WHERE patient_id = ?", (pid,))
                conn.commit()
                conn.close()

                # reset
                st.session_state[confirm_key] = False
                st.session_state.page = "history"
                safe_rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key=f"btn_cancel_{pid}"):
                st.session_state[confirm_key] = False
                safe_rerun()

    st.markdown("</div>", unsafe_allow_html=True)